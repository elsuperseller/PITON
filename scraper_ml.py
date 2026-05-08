#!/usr/bin/env python3
"""
scraper_ml.py — Mercado Libre México
Extrae JSON embebido de páginas ML (no requiere API key).
Normaliza al objeto oferta común compatible con Amazon.
"""

import json
import re
import time
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup

# ── CONFIG ──────────────────────────────────────────────────────────
ML_BASE = "https://www.mercadolibre.com.mx"
IMG_TPL = "https://http2.mlstatic.com/D_NQ_NP_{pic_id}-F.webp"

URLS_PREDEFINIDAS = {
    "ofertas_dia": [f"{ML_BASE}/ofertas"],   # punto de entrada; se expande automáticamente
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── DESCUBRIDOR DE CONTAINERS ───────────────────────────────────────
def _descubrir_containers(base_url):
    """
    Scrapea una página de ofertas ML y extrae todos los container_ids
    embebidos en el JSON. Devuelve lista de URLs listas para scrapearse.
    """
    try:
        r = requests.get(base_url, headers=_HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  ❌ Error descubriendo containers: {e}", flush=True)
        return [base_url]

    containers = set()
    for script in re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.S):
        if '"container_id"' in script:
            for cid in re.findall(r'"container_id"\s*:\s*"([A-Z0-9_\-]+)"', script):
                containers.add(cid)

    if not containers:
        print(f"  ⚠️  Sin containers encontrados, usando URL base", flush=True)
        return [base_url]

    urls = [f"{ML_BASE}/ofertas?container_id={cid}" for cid in sorted(containers)]
    print(f"  🔍 {len(urls)} containers descubiertos", flush=True)
    return urls

# ── EXTRACTOR DE JSON EMBEBIDO ───────────────────────────────────────
def _paginar_url(url, pagina):
    """Agrega ?_from=N para paginación ML (48 ítems por página)."""
    if pagina <= 1:
        return url
    parsed  = urlparse(url)
    params  = parse_qs(parsed.query, keep_blank_values=True)
    params["_from"] = [str((pagina - 1) * 48)]
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


def _extraer_items_de_html(html):
    """
    Extrae el array 'items' del JSON embebido en cualquier página ML.
    Funciona en páginas de ofertas, categorías y búsqueda (cualquier página).
    """
    for script in re.findall(r'<script[^>]*>(.*?)</script>', html, re.S):
        # Buscar cualquier posición inicial, no solo 1 (para páginas 2, 3…)
        if '"items":[{"position":' not in script:
            continue
        idx   = script.find('"items":[')
        start = script.find('[', idx)
        depth, end = 0, start
        for i, c in enumerate(script[start:]):
            if   c == '[': depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    end = start + i + 1
                    break
        try:
            return json.loads(script[start:end])
        except Exception:
            return []
    return []

# ── NORMALIZADOR ────────────────────────────────────────────────────
def _normalizar(raw):
    """raw = elemento del array 'items' del JSON de ML → objeto oferta común."""
    card = raw.get("card", {})
    meta = card.get("metadata", {})

    pid  = meta.get("id", "")
    raw_url = meta.get("url", "")
    url  = "https://" + raw_url.lstrip("/") if raw_url else ""

    # Ignorar links de publicidad (no generan link de afiliado)
    if not url or "click1.mercadolibre" in url or "click2.mercadolibre" in url:
        return None

    # Imagen: usar la primera picture disponible
    pics = card.get("pictures", {}).get("pictures", [])
    pic_id = pics[0].get("id", "") if pics else ""
    img  = IMG_TPL.format(pic_id=pic_id) if pic_id else ""

    # Fechas de inicio/fin de la oferta
    start_time = meta.get("start_time") or meta.get("deal_start_time") or raw.get("start_time")
    end_time   = meta.get("stop_time")  or meta.get("deal_stop_time")  or meta.get("end_time") or raw.get("end_time")

    # Componentes (title, price, highlight/badge)
    title      = ""
    price_disc = 0.0
    price_orig = 0.0
    desc_pct   = 0.0
    badge      = ""
    vigencia   = "oferta"
    tipo       = ""

    for comp in card.get("components", []):
        t = comp.get("type", "")

        if t == "title":
            title = comp.get("title", {}).get("text", "")

        elif t == "price":
            p = comp.get("price", {})
            price_disc = float(p.get("current_price",  {}).get("value", 0) or 0)
            price_orig = float(p.get("previous_price", {}).get("value", 0) or price_disc)
            desc_pct   = float(p.get("discount",       {}).get("value", 0) or 0)
            if desc_pct == 0 and price_orig > price_disc > 0:
                desc_pct = round((price_orig - price_disc) / price_orig * 100, 1)

        elif t == "highlight":
            hl_text = re.sub(r'\{[^}]+\}', '', comp.get("highlight", {}).get("text", "")).strip().upper()
            badge   = hl_text
            if "RELÁMPAGO" in hl_text or "RELAMPAGO" in hl_text or "FLASH" in hl_text:
                vigencia = "relampago"
                tipo     = "LIGHTNING_DEAL"
            elif "DÍA" in hl_text or "DIA" in hl_text:
                vigencia = "oferta"
                tipo     = "DEAL_OF_DAY"
            else:
                vigencia = "oferta"
                tipo     = "DEAL"

        elif t == "countdown" or t == "timer":
            # Algunos containers incluyen un componente de cuenta regresiva con end_time
            if not end_time:
                end_time = comp.get("end_time") or comp.get("countdown", {}).get("end_time")

    if not pid or not title or price_disc == 0:
        return None

    return {
        "id":               pid,
        "asin":             pid,
        "source":           "ml",
        "title":            title,
        "link":             url,
        "img":              img,
        "price_original":   price_orig,
        "price_discounted": price_disc,
        "descuento_pct":    desc_pct,
        "vigencia":         vigencia,
        "tipo":             tipo,
        "badge":            badge,
        "start_time":       start_time,
        "end_time":         end_time,
    }

# ── CONVERSOR DE URLs LISTADO → OFERTAS ─────────────────────────────
def _convertir_listado_url(url):
    """
    Las páginas listado.mercadolibre.com.mx/_Container_* son SPAs vacías.
    El container_id real está en el fragment (#). Lo extrae y construye
    la URL de ofertas equivalente que sí tiene JSON embebido.
    """
    if "listado.mercadolibre.com.mx" not in url:
        return url

    parsed   = urlparse(url)
    fragment = parsed.fragment  # todo lo que viene después del #

    # Buscar container_id en el fragment
    m = re.search(r'container_id=([A-Z0-9_\-]+)', fragment)
    if m:
        container_id = m.group(1)
        nueva = f"{ML_BASE}/ofertas?container_id={container_id}"
        print(f"  🔄 Listado → ofertas: container_id={container_id}", flush=True)
        return nueva

    # Si no hay fragment, intentar con la URL base sin fragment (algunos tienen query param)
    m2 = re.search(r'container_id=([A-Z0-9_\-]+)', url)
    if m2:
        container_id = m2.group(1)
        nueva = f"{ML_BASE}/ofertas?container_id={container_id}"
        print(f"  🔄 Listado → ofertas: container_id={container_id}", flush=True)
        return nueva

    print(f"  ⚠️  Listado sin container_id reconocible, ignorando: {url[:70]}", flush=True)
    return None

# ── SCRAPER DE URL ───────────────────────────────────────────────────
def scrape_url(url, min_discount=0, pages=1):
    """
    Extrae todos los productos de una URL de ML, paginando hasta `pages` páginas.
    Usa ?_from=N (48 ítems/página). Se detiene si una página devuelve 0 ítems.
    """
    url = _convertir_listado_url(url)
    if not url:
        return []

    resultados = []
    label = url.split("/")[-1] or "ofertas"

    for pagina in range(1, pages + 1):
        url_pag = _paginar_url(url, pagina)
        try:
            r = requests.get(url_pag, headers=_HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  ❌ {url_pag}: {e}", flush=True)
            break

        raw_items = _extraer_items_de_html(r.text)
        if not raw_items:
            print(f"  📄 {label} p{pagina} → 0 raw, deteniendo", flush=True)
            break

        page_prods = [p for raw in raw_items if (p := _normalizar(raw)) is not None]
        print(f"  📄 {label} p{pagina} → {len(raw_items)} raw → {len(page_prods)} productos", flush=True)
        resultados.extend(page_prods)

        if len(raw_items) < 20:  # Página parcial = última disponible
            break
        if pagina < pages:
            time.sleep(1.2)

    return resultados

# ── SCRAPER DESDE HTML DESCARGADO (mismo flow que Amazon) ────────────
def scrape_html_texto(html_texto, min_discount=0):
    """
    Procesa HTML descargado manualmente por el usuario desde su navegador.
    Compatible con páginas de búsqueda, categoría y ofertas de ML.
    """
    raw_items  = _extraer_items_de_html(html_texto)
    resultados = []
    for raw in raw_items:
        p = _normalizar(raw)
        if p and p["descuento_pct"] >= min_discount:
            resultados.append(p)
    return resultados, len(raw_items)

# ── DEDUPLICAR ──────────────────────────────────────────────────────
def deduplicar(items):
    vistos, unicos = set(), []
    for p in items:
        if p["id"] not in vistos:
            vistos.add(p["id"])
            unicos.append(p)
    return unicos

# ── PUNTO DE ENTRADA ────────────────────────────────────────────────
def scrape(queries=None, urls=None, categorias=None,
           min_discount=0, max_per_query=50, precio_min=0, precio_max=0,
           pages=1):
    """
    queries   : ignorado (ML no tiene API pública, usar urls/categorias)
    urls      : list[str] — URLs completas de ML
    categorias: list[str] — keys de URLS_PREDEFINIDAS (ej. ['ofertas', 'electronica'])
    pages     : páginas a scrapear por URL (para categorías/URLs personalizadas)
    """
    resultados = []

    if queries:
        print(f"⚠️  Búsqueda por keyword no disponible sin API key ML — usa categorias o urls", flush=True)

    for cat in (categorias or []):
        cat_urls = URLS_PREDEFINIDAS.get(cat)
        if not cat_urls:
            print(f"  ⚠️  Categoría desconocida: {cat} — opciones: {list(URLS_PREDEFINIDAS)}", flush=True)
            continue
        expanded = []
        for u in cat_urls:
            if "container_id" not in u:
                expanded.extend(_descubrir_containers(u))
            else:
                expanded.append(u)
        print(f"📦 ML categoría: {cat} → {len(expanded)} URL(s)", flush=True)
        for u in expanded:
            # Las categorías ya usan discovery de containers; 1 página por container
            resultados.extend(scrape_url(u, pages=1))
            time.sleep(1.2)

    for url in (urls or []):
        print(f"📄 ML URL: {url[:70]}", flush=True)
        resultados.extend(scrape_url(url, pages=pages))
        time.sleep(1.2)

    # Si no se especificó nada, descubrir y scrapear todas las fuentes diarias
    if not categorias and not urls and not queries:
        daily_urls = _descubrir_containers(f"{ML_BASE}/ofertas")
        print(f"📦 ML: scrapeando {len(daily_urls)} fuentes diarias", flush=True)
        for u in daily_urls:
            resultados.extend(scrape_url(u, pages=1))
            time.sleep(1.2)

    resultados = deduplicar(resultados)
    print(f"✅ ML total: {len(resultados)} ofertas únicas", flush=True)
    return resultados


if __name__ == "__main__":
    ofertas = scrape(categorias=["ofertas", "electronica"], min_discount=20)
    print(json.dumps(ofertas[:2], indent=2, ensure_ascii=False))
