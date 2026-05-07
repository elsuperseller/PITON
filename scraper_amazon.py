#!/usr/bin/env python3
"""
scraper_amazon.py — Amazon México Deals Scraper
Extrae ASINs de las páginas de ofertas de Amazon MX.
La extracción automática usa requests (best-effort); el fallback es HTML manual.
"""

import re
import time
import requests

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


def extraer_asins(html):
    """
    Extrae ASINs únicos del HTML de Amazon.
    Descarta la sección de historial/recomendaciones para evitar contaminación.
    """
    # Cortar antes de las secciones de recomendaciones personales
    for marca in ["purchase-sims", "sims-consolidated", "similarities-widget",
                  "p13n-desktop-sims", "rhf-container"]:
        idx = html.lower().find(marca)
        if idx != -1:
            html = html[:idx]
            break

    asins = set()
    # data-asin="..." — solo aparece en cards de producto reales
    asins.update(re.findall(r'data-asin="([A-Z0-9]{10})"', html))
    # /dp/ASIN en href de enlaces
    asins.update(re.findall(r'/dp/([A-Z0-9]{10})', html))
    # "asin":"..." en JSON embebido (React state, etc.)
    asins.update(re.findall(r'"asin"\s*:\s*"([A-Z0-9]{10})"', html))

    # Validar formato: empieza en B o dígito, 10 caracteres alfanuméricos
    return [a for a in asins if re.match(r'^[B0-9][A-Z0-9]{9}$', a)]


def _es_bot_challenge(html):
    html_lower = html.lower()
    return any(s in html_lower for s in _BOT_SIGNALS)


def _fetch_html(url):
    """
    Intenta obtener el HTML de una URL de Amazon.
    Retorna (html, estado) donde estado es "ok", "bot_challenge" o mensaje de error.
    """
    try:
        session = requests.Session()
        # Warmup: visitar homepage para obtener cookies base
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
    Retorna lista de ASINs.
    """
    asins = extraer_asins(html_texto)
    print(f"  📄 HTML manual → {len(asins)} ASINs", flush=True)
    return asins
