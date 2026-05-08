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

def _fetch_playwright(url, scrolls=15):
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
            # Espera inicial larga — Amazon tarda en montar React y cargar el primer bloque
            page.wait_for_timeout(5000)

            # Diagnóstico inicial
            titulo = page.title()
            html_len = page.evaluate("document.documentElement.innerHTML.length")
            print(f"  📋 Título: {titulo[:60]} | HTML: {html_len} chars", flush=True)

            if _es_bot_challenge(page.content()):
                return [], "bot_challenge"

            # ASINs antes del primer scroll — acumulados, nunca se pierden
            asins = set(_extraer_asins_js(page))
            print(f"  📦 Antes de scroll: {len(asins)} ASINs", flush=True)

            # Scroll humano: una pantalla a la vez, espera larga entre scrolls
            # NOTA: Amazon usa scroll virtual — los items de arriba desaparecen del DOM.
            # Por eso acumulamos en `asins` en lugar de reemplazar.
            sin_nuevos = 0  # scrolls consecutivos sin ASINs verdaderamente nuevos
            for i in range(scrolls):
                page.evaluate("window.scrollBy({ top: window.innerHeight, behavior: 'smooth' })")

                # Pausa 7-9s: Amazon tarda ~5-7s en cargar el siguiente batch
                page.wait_for_timeout(random.randint(7000, 9000))

                # Detectar y pulsar botón "Ver más ofertas" (solo coincidencia exacta)
                boton_cargado = page.evaluate("""
                    () => {
                        const norm = s => s.normalize('NFD')
                            .replace(/[\\u0300-\\u036f]/g, '')
                            .trim().toLowerCase()
                        // Claves que requieren la palabra "oferta/deal" para evitar falsos positivos
                        const CLAVES = [
                            'ver mas ofertas', 'cargar mas ofertas', 'cargar ofertas',
                            'mostrar mas ofertas', 'load more deals', 'show more deals',
                            'more deals'
                        ]
                        const candidatos = Array.from(document.querySelectorAll(
                            'button, a, input[type="button"], input[type="submit"], ' +
                            '[role="button"], [data-action]'
                        ))
                        const btn = candidatos.find(el => {
                            const t = norm(el.textContent)
                            return CLAVES.some(c => t.includes(c))
                        })
                        if (btn) {
                            btn.scrollIntoView({ behavior: 'smooth', block: 'center' })
                            btn.click()
                            return btn.textContent.trim()
                        }
                        return null
                    }
                """)
                if boton_cargado:
                    print(f"  🖱️  Botón '{boton_cargado[:40]}' pulsado — esperando carga…", flush=True)
                    page.wait_for_timeout(6000)

                # Acumular — nunca reemplazar (scroll virtual elimina items del DOM)
                visibles = set(_extraer_asins_js(page))
                nuevos   = visibles - asins
                asins   |= visibles
                print(f"  📦 Scroll {i+1}: {len(asins)} acumulados (+{len(nuevos)} nuevos)", flush=True)

                if len(nuevos) == 0 and not boton_cargado:
                    sin_nuevos += 1
                    if sin_nuevos >= 3:
                        print(f"  ⏹  3 scrolls sin ASINs nuevos — página completa", flush=True)
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


def playwright_disponible():
    return _PLAYWRIGHT_OK
