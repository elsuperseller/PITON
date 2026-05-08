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

def _fetch_playwright(url, scrolls=6):
    """
    Abre la URL en Chromium headless, espera a que cargue la SPA y scrollea
    para disparar lazy-loading de más productos.
    scrolls × ~1.5s ≈ tiempo de carga adicional.
    """
    print(f"  🎭 Playwright: {url[:60]}", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                locale="es-MX",
                extra_http_headers={
                    "Accept-Language": "es-MX,es;q=0.9",
                    "User-Agent": _HEADERS["User-Agent"],
                }
            )
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=35000)
            page.wait_for_timeout(3000)  # Dejar que React monte los componentes

            for i in range(scrolls):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)  # Esperar lazy-load por scroll

            # Scroll de vuelta arriba para capturar cualquier contenido inicial
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(800)

            html = page.content()

            if _es_bot_challenge(html):
                return None, "bot_challenge"
            return html, "ok"
        except PWTimeout:
            return None, "timeout"
        except Exception as e:
            return None, str(e)[:80]
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


# ── FETCH PRINCIPAL ─────────────────────────────────────────────────

def _fetch_html(url):
    """
    Intenta obtener el HTML completo de una URL de Amazon.
    Usa Playwright si está instalado; si no, cae a requests.
    """
    if _PLAYWRIGHT_OK:
        html, estado = _fetch_playwright(url)
        if html is not None:
            return html, estado
        print(f"  ⚠️  Playwright falló ({estado}), intentando con requests…", flush=True)

    return _fetch_requests(url)


# ── API PÚBLICA ─────────────────────────────────────────────────────

def scrape_url(url_key_or_url):
    """
    Extrae ASINs de una URL de deals. Acepta key de DEALS_URLS o URL completa.
    Retorna (asins_list, estado).
    """
    url   = DEALS_URLS.get(url_key_or_url, url_key_or_url)
    label = url_key_or_url if url_key_or_url in DEALS_URLS else url[:60]

    html, estado = _fetch_html(url)
    if html is None:
        print(f"  ⚠️  {label}: {estado}", flush=True)
        return [], estado

    asins = extraer_asins(html)
    print(f"  📄 {label} → {len(asins)} ASINs extraídos", flush=True)
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
