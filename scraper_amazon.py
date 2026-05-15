#!/usr/bin/env python3
"""
scraper_amazon.py — Amazon México Deals Scraper
Extrae ASINs de las páginas de ofertas de Amazon MX.

Estrategia (en orden de preferencia):
  1. Playwright (headless Chromium) — ejecuta JS y scrollea para cargar
     todos los productos. Requiere: pip install playwright && playwright install chromium
  2. requests — fallback sin JS; puede devolver pocos o cero ASINs en
     páginas SPA como /deals ya que Amazon las renderiza 100% client-side.
"""

import random
import re
import time
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# ── PLAYWRIGHT OPCIONAL ─────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    _PLAYWRIGHT_OK = True
except ImportError:
    _PLAYWRIGHT_OK = False

DEALS_URLS = {
    "deals_hoy": "https://www.amazon.com.mx/deals?ref_=nav_cs_gb&bubble-id=discounts-collection-deals-started-today",
    "trending":  "https://www.amazon.com.mx/deals?ref_=nav_cs_gb&bubble-id=trending-bubble",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

_BOT_SIGNALS = [
    "type the characters you see",
    "robot check",
    "captcha",
    "automated access",
    "service unavailable",
    "enter the characters",
]

# ── EXTRACCIÓN DE ASINS ─────────────────────────────────────────────

def extraer_asins(html):
    """
    Extrae ASINs únicos del HTML de Amazon.
    Descarta la sección de historial/recomendaciones para evitar contaminación.
    """
    for marca in ["purchase-sims", "sims-consolidated", "similarities-widget",
                  "p13n-desktop-sims", "rhf-container"]:
        idx = html.lower().find(marca)
        if idx != -1:
            html = html[:idx]
            break

    asins = set()
    asins.update(re.findall(r'data-asin="([A-Z0-9]{10})"', html))
    asins.update(re.findall(r'/dp/([A-Z0-9]{10})', html))
    asins.update(re.findall(r'"asin"\s*:\s*"([A-Z0-9]{10})"', html))
    asins.update(re.findall(r'"ASIN"\s*:\s*"([A-Z0-9]{10})"', html))
    # sspa/click links: /sspa/click?...&asin=B0XXXX o itemASIN=B0XXXX
    asins.update(re.findall(r'[?&]asin=([A-Z0-9]{10})', html))
    asins.update(re.findall(r'itemASIN=([A-Z0-9]{10})', html))

    return [a for a in asins if re.match(r'^[B0-9][A-Z0-9]{9}$', a)]


def _es_bot_challenge(html):
    html_lower = html.lower()
    return any(s in html_lower for s in _BOT_SIGNALS)


# ── FETCH CON PLAYWRIGHT ────────────────────────────────────────────

def _extraer_asins_js(page):
    """
    Extrae ASINs directamente del DOM vivo via JavaScript.
    Más confiable que regex sobre el HTML serializado porque captura
    atributos de React aunque no aparezcan en el innerHTML.
    """
    try:
        return page.evaluate("""
            () => {
                const asins = new Set()
                const pat = /^[B0-9][A-Z0-9]{9}$/

                // 1. data-asin en cualquier elemento
                document.querySelectorAll('[data-asin]').forEach(el => {
                    const a = el.getAttribute('data-asin')
                    if (a && pat.test(a)) asins.add(a)
                })

                // 2. Links /dp/ASIN
                document.querySelectorAll('a[href*="/dp/"]').forEach(el => {
                    const m = el.href.match(/\\/dp\\/([A-Z0-9]{10})/)
                    if (m && pat.test(m[1])) asins.add(m[1])
                })

                // 3. Links /gp/product/ASIN
                document.querySelectorAll('a[href*="/gp/product/"]').forEach(el => {
                    const m = el.href.match(/\\/gp\\/product\\/([A-Z0-9]{10})/)
                    if (m && pat.test(m[1])) asins.add(m[1])
                })

                // 4. JSON embebido en scripts
                document.querySelectorAll('script').forEach(s => {
                    const matches = s.textContent.matchAll(/"asin"\s*:\s*"([A-Z0-9]{10})"/g)
                    for (const m of matches) if (pat.test(m[1])) asins.add(m[1])
                })

                return Array.from(asins)
            }
        """)
    except Exception as e:
        print(f"  ⚠️  JS extraction error: {e}", flush=True)
        return []


_STEALTH_SCRIPT = """
    // Ocultar flag navigator.webdriver (señal más obvia de headless)
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

    // Simular chrome object (ausente en Chromium headless puro)
    window.chrome = {
        app: { isInstalled: false, InstallState: {}, RunningState: {} },
        runtime: { OnInstalledReason: {}, PlatformOs: {}, PlatformArch: {} }
    };

    // Simular plugins (headless = 0 plugins, real Chrome tiene 3+)
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const fakePlugin = (n, d, f) => Object.assign(Object.create(Plugin.prototype), {name:n, description:d, filename:f, length:1});
            return Object.assign([
                fakePlugin('Chrome PDF Plugin','Portable Document Format','internal-pdf-viewer'),
                fakePlugin('Chrome PDF Viewer','','mhjfbmdgcfjbbpaeojofohoefgiehjai'),
                fakePlugin('Native Client','','internal-nacl-plugin'),
            ], {item: i => this[i], namedItem: n => null, refresh: ()=>{}});
        }
    });

    // Idioma consistente con el contexto
    Object.defineProperty(navigator, 'languages', {get: () => ['es-MX', 'es', 'en-US', 'en']});

    // Permissions API — headless siempre devuelve 'denied', real Chrome varía
    const origQuery = window.navigator.permissions?.query;
    if (origQuery) {
        window.navigator.permissions.query = params =>
            params.name === 'notifications'
                ? Promise.resolve({state: Notification.permission})
                : origQuery(params);
    }
"""

def _click_load_more(page):
    """
    Intenta detectar y pulsar el botón "Ver más ofertas" usando tres estrategias
    en orden de confiabilidad: API nativa Playwright → texto parcial → JS querySelector.
    Retorna el texto del botón si lo encontró y pulsó, o None.
    """
    TEXTOS = ["Ver más ofertas", "Cargar más ofertas", "Load more deals",
              "Mostrar más ofertas", "Ver más deals"]

    # Estrategia 1: locator por texto exacto (Playwright nativo — más confiable)
    for texto in TEXTOS:
        try:
            loc = page.get_by_role("button", name=texto, exact=False)
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.scroll_into_view_if_needed()
                loc.first.click()
                return texto
        except Exception:
            pass

    # Estrategia 2: cualquier elemento visible con esos textos
    for texto in TEXTOS:
        try:
            loc = page.get_by_text(texto, exact=False)
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.scroll_into_view_if_needed()
                loc.first.click()
                return texto
        except Exception:
            pass

    # Estrategia 3: JavaScript con normalización de acentos (fallback)
    resultado = page.evaluate("""
        () => {
            const norm = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').trim().toLowerCase()
            const CLAVES = ['ver mas ofertas','cargar mas ofertas','load more deals',
                            'mostrar mas ofertas','more deals']
            const all = Array.from(document.querySelectorAll(
                'button, a, [role="button"], [data-action], span, div'
            ))
            const btn = all.find(el => {
                if (!el.offsetParent) return false  // ignorar elementos ocultos
                const t = norm(el.textContent)
                return CLAVES.some(c => t === c || t.startsWith(c))
            })
            if (btn) { btn.scrollIntoView({behavior:'smooth',block:'center'}); btn.click(); return btn.textContent.trim() }
            return null
        }
    """)
    return resultado


def _fetch_playwright(url, scrolls=25):
    """
    Abre la URL con Chrome del sistema (o Chromium con stealth patches),
    scrollea y extrae ASINs del DOM vivo.
    """
    print(f"  🎭 Playwright: {url[:60]}", flush=True)
    with sync_playwright() as p:
        # Intentar con Chrome del sistema primero (menos detectable que Chromium bundled)
        try:
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            print(f"  🌐 Usando Chrome del sistema", flush=True)
        except Exception:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            print(f"  🌐 Usando Chromium bundled", flush=True)
        try:
            ctx = browser.new_context(
                locale="es-MX",
                viewport={"width": 1366, "height": 768},
                extra_http_headers={"Accept-Language": "es-MX,es;q=0.9"},
                user_agent=_HEADERS["User-Agent"],
            )
            ctx.add_init_script(_STEALTH_SCRIPT)
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=35000)

            # Diagnóstico inicial
            titulo = page.title()
            html_len = page.evaluate("document.documentElement.innerHTML.length")
            print(f"  📋 Título: {titulo[:60]} | HTML: {html_len} chars", flush=True)

            if _es_bot_challenge(page.content()):
                return [], "bot_challenge"

            # Espera hasta que el primer batch se estabilice (Amazon carga en dos etapas).
            # Revisamos cada 4s; si el conteo no cambia dos veces seguidas, empezamos a scrollear.
            print(f"  ⏳ Esperando carga inicial…", flush=True)
            conteo_prev, estable = 0, 0
            for _ in range(8):  # máximo 32s de espera inicial
                page.wait_for_timeout(4000)
                conteo_ahora = len(set(_extraer_asins_js(page)))
                if conteo_ahora > 0 and conteo_ahora == conteo_prev:
                    estable += 1
                    if estable >= 2:
                        break
                else:
                    estable = 0
                conteo_prev = conteo_ahora

            # ASINs antes del primer scroll
            asins = set(_extraer_asins_js(page))
            print(f"  📦 Carga inicial estable: {len(asins)} ASINs", flush=True)

            # Scroll humano: 70% de pantalla a la vez para no saltarse el botón.
            # NOTA: Amazon usa scroll virtual — items de arriba desaparecen del DOM.
            # Por eso acumulamos con |= en lugar de reemplazar.
            sin_nuevos = 0
            for i in range(scrolls):
                page.evaluate("window.scrollBy({ top: Math.round(window.innerHeight * 0.7), behavior: 'smooth' })")

                # Pausa 7-9s: Amazon tarda ~5-7s en cargar el siguiente batch
                page.wait_for_timeout(random.randint(7000, 9000))

                # Detectar y pulsar "Ver más ofertas" (3 estrategias)
                boton_cargado = _click_load_more(page)
                if boton_cargado:
                    print(f"  🖱️  Botón '{boton_cargado[:40]}' pulsado — esperando carga…", flush=True)
                    page.wait_for_timeout(6000)

                # Acumular — nunca reemplazar
                visibles = set(_extraer_asins_js(page))
                nuevos   = visibles - asins
                asins   |= visibles
                print(f"  📦 Scroll {i+1}: {len(asins)} acumulados (+{len(nuevos)} nuevos)", flush=True)

                if len(nuevos) == 0 and not boton_cargado:
                    sin_nuevos += 1
                    if sin_nuevos >= 5:
                        print(f"  ⏹  5 scrolls sin ASINs nuevos — página completa", flush=True)
                        break
                else:
                    sin_nuevos = 0

            print(f"  ✅ Total ASINs extraídos por JS: {len(asins)}", flush=True)
            return list(asins), "ok"
        except PWTimeout:
            return [], "timeout"
        except Exception as e:
            return [], str(e)[:80]
        finally:
            browser.close()


# ── FETCH CON REQUESTS (fallback) ───────────────────────────────────

def _fetch_requests(url):
    """Intenta obtener HTML vía requests. Funciona para páginas server-rendered."""
    try:
        session = requests.Session()
        try:
            session.get("https://www.amazon.com.mx", headers=_HEADERS, timeout=10)
            time.sleep(0.8)
        except Exception:
            pass
        r = session.get(url, headers=_HEADERS, timeout=25, allow_redirects=True)
        r.raise_for_status()
        if _es_bot_challenge(r.text):
            return None, "bot_challenge"
        return r.text, "ok"
    except requests.exceptions.HTTPError as e:
        return None, f"http_{e.response.status_code}"
    except Exception as e:
        return None, str(e)[:80]


# ── API PÚBLICA ─────────────────────────────────────────────────────

def scrape_url(url_key_or_url):
    """
    Extrae ASINs de una URL de deals. Acepta key de DEALS_URLS o URL completa.
    Retorna (asins_list, estado).
    Usa Playwright (DOM JS) si disponible; si no, fallback a requests + regex.
    """
    url   = DEALS_URLS.get(url_key_or_url, url_key_or_url)
    label = url_key_or_url if url_key_or_url in DEALS_URLS else url[:60]

    if _PLAYWRIGHT_OK:
        asins, estado = _fetch_playwright(url)
        if estado == "ok":
            print(f"  📄 {label} → {len(asins)} ASINs (Playwright)", flush=True)
            return asins, "ok"
        print(f"  ⚠️  Playwright falló ({estado}), intentando requests…", flush=True)

    # Fallback: requests + regex sobre HTML
    html, estado = _fetch_requests(url)
    if html is None:
        print(f"  ⚠️  {label}: {estado}", flush=True)
        return [], estado

    asins = extraer_asins(html)
    print(f"  📄 {label} → {len(asins)} ASINs (requests)", flush=True)
    return asins, "ok"


def extraer_asins_de_html(html_texto):
    """
    Procesa HTML descargado manualmente desde Chrome.
    Compatible con páginas de deals, búsquedas y PDPs de Amazon MX.
    """
    asins = extraer_asins(html_texto)
    print(f"  📄 HTML manual → {len(asins)} ASINs", flush=True)
    return asins


def _fetch_playwright_pages(url, pages=3):
    """
    Navega por páginas 1-N de una URL de búsqueda/categoría Amazon
    reutilizando el mismo browser (sin re-lanzar entre páginas).
    Añade &page=N a la URL para paginar.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                channel="chrome", headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            print(f"  🌐 Usando Chrome del sistema", flush=True)
        except Exception:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            print(f"  🌐 Usando Chromium bundled", flush=True)
        try:
            ctx = browser.new_context(
                locale="es-MX",
                viewport={"width": 1366, "height": 768},
                extra_http_headers={"Accept-Language": "es-MX,es;q=0.9"},
                user_agent=_HEADERS["User-Agent"],
            )
            ctx.add_init_script(_STEALTH_SCRIPT)
            pg = ctx.new_page()

            all_asins = set()
            for num in range(1, pages + 1):
                # Construir URL paginada
                if num == 1:
                    page_url = url
                else:
                    parsed = urlparse(url)
                    params  = parse_qs(parsed.query, keep_blank_values=True)
                    params["page"] = [str(num)]
                    page_url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))

                print(f"  📄 Amazon p{num}: {page_url[:70]}", flush=True)
                pg.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                pg.wait_for_timeout(random.randint(3500, 4500))

                if _es_bot_challenge(pg.content()):
                    print(f"  ⚠️  Bot challenge en página {num}", flush=True)
                    break

                visibles = set(_extraer_asins_js(pg))
                nuevos   = visibles - all_asins
                all_asins |= visibles
                print(f"  📦 p{num}: {len(all_asins)} ASINs acumulados (+{len(nuevos)} nuevos)", flush=True)

                if not nuevos:
                    print(f"  ⏹  Sin ASINs nuevos — fin de resultados", flush=True)
                    break

                if num < pages:
                    time.sleep(random.uniform(2.0, 3.5))

            return list(all_asins), "ok"
        except PWTimeout:
            return [], "timeout"
        except Exception as e:
            return [], str(e)[:80]
        finally:
            browser.close()


def _extraer_asins_todos_frames(page):
    """
    Extrae ASINs del frame principal Y de todos los iframes.
    Amazon Stores embebe cada widget en un iframe — los productos no están en el frame principal.
    También corre regex sobre el HTML serializado como red de seguridad.
    """
    all_asins = set()

    # Frame principal via JS
    all_asins.update(_extraer_asins_js(page))

    # Todos los sub-frames (iframes de widgets)
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            frame_asins = frame.evaluate("""
                () => {
                    const asins = new Set()
                    const pat = /^[B0-9][A-Z0-9]{9}$/
                    document.querySelectorAll('[data-asin]').forEach(el => {
                        const a = el.getAttribute('data-asin')
                        if (a && pat.test(a)) asins.add(a)
                    })
                    document.querySelectorAll('a[href*=\"/dp/\"]').forEach(el => {
                        const m = el.href.match(/\\/dp\\/([A-Z0-9]{10})/)
                        if (m && pat.test(m[1])) asins.add(m[1])
                    })
                    document.querySelectorAll('a[href*=\"/gp/product/\"]').forEach(el => {
                        const m = el.href.match(/\\/gp\\/product\\/([A-Z0-9]{10})/)
                        if (m && pat.test(m[1])) asins.add(m[1])
                    })
                    document.querySelectorAll('script').forEach(s => {
                        const ms = s.textContent.matchAll(/"asin"\\s*:\\s*"([A-Z0-9]{10})"/g)
                        for (const m of ms) if (pat.test(m[1])) asins.add(m[1])
                    })
                    return Array.from(asins)
                }
            """)
            all_asins.update(frame_asins)
        except Exception:
            try:
                all_asins.update(extraer_asins(frame.content()))
            except Exception:
                pass

    # Regex sobre el HTML completo del frame principal como red de seguridad
    try:
        all_asins.update(extraer_asins(page.content()))
    except Exception:
        pass

    return list(all_asins)


def _fetch_playwright_store(url):
    """
    Maneja páginas de Amazon Stores (/stores/) que son SPA completas (React).
    Los productos viven dentro de iframes de widgets, no en el frame principal.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                channel="chrome", headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            print(f"  🌐 Usando Chrome del sistema (store)", flush=True)
        except Exception:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            print(f"  🌐 Usando Chromium bundled (store)", flush=True)
        try:
            ctx = browser.new_context(
                locale="es-MX",
                viewport={"width": 1366, "height": 768},
                extra_http_headers={"Accept-Language": "es-MX,es;q=0.9"},
                user_agent=_HEADERS["User-Agent"],
            )
            ctx.add_init_script(_STEALTH_SCRIPT)
            pg = ctx.new_page()

            print(f"  📄 Store: {url[:100]}", flush=True)
            pg.goto(url, wait_until="networkidle", timeout=45000)
            pg.wait_for_timeout(4000)

            titulo = pg.title()
            n_frames = len(pg.frames)
            html_len = len(pg.content())
            print(f"  📋 '{titulo[:50]}' | {html_len} chars | {n_frames} frames", flush=True)

            if _es_bot_challenge(pg.content()):
                return [], "bot_challenge"

            all_asins = set(_extraer_asins_todos_frames(pg))
            print(f"  📦 Carga inicial: {len(all_asins)} ASINs ({n_frames} frames)", flush=True)

            # Scroll para activar lazy loading de widgets/iframes
            sin_nuevos = 0
            for i in range(15):
                pg.evaluate("window.scrollBy({ top: Math.round(window.innerHeight * 0.8), behavior: 'smooth' })")
                pg.wait_for_timeout(random.randint(1800, 2800))

                visibles = set(_extraer_asins_todos_frames(pg))
                nuevos = visibles - all_asins
                all_asins |= visibles

                if nuevos:
                    print(f"  📦 Scroll {i+1}: {len(all_asins)} ASINs (+{len(nuevos)} nuevos)", flush=True)
                    sin_nuevos = 0
                else:
                    sin_nuevos += 1
                    if sin_nuevos >= 3:
                        print(f"  ⏹  Página completa: {len(all_asins)} ASINs total", flush=True)
                        break

            return list(all_asins), "ok"
        except PWTimeout:
            return [], "timeout"
        except Exception as e:
            return [], str(e)[:80]
        finally:
            browser.close()


_ZG_PATTERNS = ("/gp/movers-and-shakers/", "/gp/bestsellers/", "/gp/new-releases/", "/zgbs/", "/zg/new-releases/")


def _zg_scrape_paginas(pg, base_url, pages, all_asins):
    """Scrapea N páginas de un ranking ZG reutilizando una página Playwright ya abierta."""
    nuevos_total = 0
    es_ms = "movers-and-shakers" in base_url

    for num in range(1, pages + 1):
        page_url = base_url if num == 1 else f"{base_url}{'&' if '?' in base_url else '?'}pg={num}"
        print(f"  📄 Ranking p{num}: {page_url[:90]}", flush=True)

        # M&S es más dinámica — usa networkidle; Best Sellers/New Releases con domcontentloaded
        wait = "networkidle" if es_ms else "domcontentloaded"
        try:
            pg.goto(page_url, wait_until=wait, timeout=35000)
        except Exception:
            pg.wait_for_timeout(3000)  # timeout de networkidle → esperar igual

        pg.wait_for_timeout(random.randint(2000, 3000))

        titulo = pg.title()
        html_len = len(pg.content())
        print(f"  📋 '{titulo[:50]}' | {html_len} chars", flush=True)

        if _es_bot_challenge(pg.content()):
            print(f"  ⚠️  Bot challenge en p{num}", flush=True)
            break

        # Diagnóstico de frames y patrones en la página
        n_frames = len(pg.frames)
        try:
            diag = pg.evaluate("""
                () => {
                    const dpLinks   = document.querySelectorAll('a[href*="/dp/"]').length
                    const sspaLinks = document.querySelectorAll('a[href*="/sspa/"]').length
                    const asinEls   = document.querySelectorAll('[data-asin]').length
                    const firstHref = (document.querySelector('a[href*="/sspa/"], a[href*="/dp/"]') || {}).href || ''
                    return {dpLinks, sspaLinks, asinEls, firstHref: firstHref.slice(0,120)}
                }
            """)
            print(f"  🔬 data-asin={diag['asinEls']} /dp/={diag['dpLinks']} /sspa/={diag['sspaLinks']}", flush=True)
            if diag['firstHref']:
                print(f"  🔗 Primer link: {diag['firstHref']}", flush=True)
        except Exception:
            pass

        # Scroll para disparar lazy-load (acumula en cada paso por si hay virtual scroll)
        acumulado = set(_extraer_asins_todos_frames(pg))
        for _ in range(8):
            pg.evaluate("window.scrollBy({ top: Math.round(window.innerHeight * 0.8), behavior: 'smooth' })")
            pg.wait_for_timeout(1200)
            acumulado.update(_extraer_asins_todos_frames(pg))
            if len(acumulado) >= 48:
                break

        visibles = acumulado
        nuevos = visibles - all_asins
        all_asins |= visibles
        nuevos_total += len(nuevos)
        print(f"  📦 p{num}: {len(visibles)} en pág ({n_frames} frames), {len(all_asins)} total (+{len(nuevos)} nuevos)", flush=True)

        if not nuevos:
            print(f"  ⏹  Sin ASINs nuevos — fin", flush=True)
            break
        if num < pages:
            time.sleep(random.uniform(1.0, 1.8))

    return nuevos_total


def scrape_zg_batch(urls, pages=2):
    """
    Scrapea varias URLs de ranking ZG (Best Sellers, New Releases, M&S)
    reutilizando UN solo browser para todas — evita el overhead de lanzar
    un browser nuevo por cada URL (ahorra ~3s × N URLs).
    """
    if not _PLAYWRIGHT_OK:
        return [], "playwright_no_disponible"

    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    all_asins = set()
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome", headless=True,
                    args=["--disable-blink-features=AutomationControlled"])
                print(f"  🌐 Chrome del sistema (ranking batch)", flush=True)
            except Exception:
                browser = p.chromium.launch(headless=True,
                    args=["--disable-blink-features=AutomationControlled"])
                print(f"  🌐 Chromium bundled (ranking batch)", flush=True)

            ctx = browser.new_context(locale="es-MX", viewport={"width": 1366, "height": 768},
                extra_http_headers={"Accept-Language": "es-MX,es;q=0.9"},
                user_agent=_HEADERS["User-Agent"])
            ctx.add_init_script(_STEALTH_SCRIPT)
            pg = ctx.new_page()

            for i, url in enumerate(urls, 1):
                parsed = urlparse(url)
                qs = parse_qs(parsed.query, keep_blank_values=True)
                qs.pop("pg", None)
                base_url = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
                print(f"  📂 URL {i}/{len(urls)}: {base_url[:70]}", flush=True)
                _zg_scrape_paginas(pg, base_url, pages, all_asins)
                if i < len(urls):
                    time.sleep(random.uniform(1.0, 2.0))

            browser.close()
    except Exception as e:
        print(f"  ❌ Error batch ZG: {e}", flush=True)

    return list(all_asins), "ok"


def _fetch_playwright_zg(url, pages=2):
    """Scrapea una sola URL de ranking ZG (wrapper de scrape_zg_batch para compatibilidad)."""
    return scrape_zg_batch([url], pages=pages)


def scrape_url_custom(url, pages=3):
    """
    Scrapea una URL arbitraria de Amazon con paginación.
    - URLs /deals → usa el scroll approach existente (scrolls profundos)
    - URLs /stores/ → usa networkidle + scroll (SPA React, no tiene &page=N)
    - URLs M&S / Best Sellers / New Releases → usa ?pg=N
    - Otras URLs → navega por &page=1..N en el mismo browser
    Retorna (asins_list, estado).
    """
    if "/deals" in url or "bubble-id" in url:
        return scrape_url(url)  # scroll approach

    if any(p in url for p in _ZG_PATTERNS):
        if _PLAYWRIGHT_OK:
            asins, estado = _fetch_playwright_zg(url, pages=pages)
            print(f"  📄 {url[:90]} → {len(asins)} ASINs (ranking)", flush=True)
            return asins, estado
        html, estado = _fetch_requests(url)
        if html:
            return extraer_asins(html), "ok"
        return [], estado

    if "/stores/" in url:
        if _PLAYWRIGHT_OK:
            asins, estado = _fetch_playwright_store(url)
            print(f"  📄 {url[:90]} → {len(asins)} ASINs (store)", flush=True)
            return asins, estado
        # Fallback requests para stores (probablemente vacío pero intentamos)
        html, estado = _fetch_requests(url)
        if html:
            asins = extraer_asins(html)
            return asins, "ok"
        return [], estado

    label = url[:60]
    if _PLAYWRIGHT_OK:
        asins, estado = _fetch_playwright_pages(url, pages=pages)
        if estado == "ok":
            print(f"  📄 {label} → {len(asins)} ASINs ({pages} páginas)", flush=True)
        return asins, estado

    # Fallback requests
    all_asins, seen = [], set()
    for num in range(1, pages + 1):
        if num == 1:
            page_url = url
        else:
            parsed = urlparse(url)
            params  = parse_qs(parsed.query, keep_blank_values=True)
            params["page"] = [str(num)]
            page_url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
        html, estado = _fetch_requests(page_url)
        if not html:
            break
        nuevos = [a for a in extraer_asins(html) if a not in seen]
        if not nuevos:
            break
        seen.update(nuevos)
        all_asins.extend(nuevos)
        time.sleep(1.5)
    return all_asins, "ok"


def playwright_disponible():
    return _PLAYWRIGHT_OK
