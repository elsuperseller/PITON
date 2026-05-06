#!/usr/bin/env python3
"""
scraper_ml.py — Mercado Libre México
Extrae JSON embebido de páginas ML (no requiere API key).
Normaliza al objeto oferta común compatible con Amazon.
"""

import json
import re
import time

import requests
from bs4 import BeautifulSoup

# ── CONFIG ──────────────────────────────────────────────────────────
ML_BASE = "https://www.mercadolibre.com.mx"
IMG_TPL = "https://http2.mlstatic.com/D_NQ_NP_{pic_id}-F.webp"

# Fuentes principales de ofertas diarias
URLS_DIARIAS = [
    f"{ML_BASE}/ofertas#nav-header",
    f"{ML_BASE}/ofertas?container_id=MLM1297614-1&deal_ids=MLM27723",
    f"{ML_BASE}/ofertas?container_id=MLM1321208-1&deal_ids=MLM1321208",
]

URLS_PREDEFINIDAS = {
    "ofertas_dia":    URLS_DIARIAS,   # las 3 fuentes principales
    "electronica":    [f"{ML_BASE}/ofertas/tecnologia"],
    "hogar":          [f"{ML_BASE}/ofertas/hogar-y-muebles"],
    "deportes":       [f"{ML_BASE}/ofertas/deportes-y-fitness"],
    "juguetes":       [f"{ML_BASE}/ofertas/juguetes-y-bebes"],
    "belleza":        [f"{ML_BASE}/ofertas/salud-y-belleza"],
    "ropa":           [f"{ML_BASE}/ofertas/moda"],
    "herramientas":   [f"{ML_BASE}/ofertas/herramientas"],
    "automotriz":     [f"{ML_BASE}/ofertas/autos-motos-y-otros"],
    "mascotas":       [f"{ML_BASE}/ofertas/animales-y-mascotas"],
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── EXTRACTOR DE JSON EMBEBIDO ───────────────────────────────────────
def _extraer_items_de_html(html):
    """
    Extrae el array 'items' del JSON embebido en cualquier página ML.
    Funciona en páginas de ofertas, categorías y búsqueda.
    """
    for script in re.findall(r'<script[^>]*>(.*?)</script>', html, re.S):
        if '"items":[{"position":1' not in script:
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
    url  = "https://" + meta.get("url", "").lstrip("/")

    # Imagen: usar la primera picture disponible
    pics = card.get("pictures", {}).get("pictures", [])
    pic_id = pics[0].get("id", "") if pics else ""
    img  = IMG_TPL.format(pic_id=pic_id) if pic_id else ""

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
            hl_text = comp.get("highlight", {}).get("text", "").upper()
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
        "start_time":       None,
        "end_time":         None,
    }

# ── SCRAPER DE URL ───────────────────────────────────────────────────
def scrape_url(url, min_discount=0):
    """Extrae todos los productos de cualquier URL de ML que tenga JSON embebido."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  ❌ {url}: {e}", flush=True)
        return []

    raw_items  = _extraer_items_de_html(r.text)
    resultados = [p for raw in raw_items if (p := _normalizar(raw)) is not None]

    print(f"  📄 {url.split('/')[-1] or 'ofertas'} → {len(raw_items)} raw → {len(resultados)} productos", flush=True)
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
           min_discount=0, max_per_query=50, precio_min=0, precio_max=0):
    """
    queries   : ignorado (ML no tiene API pública, usar urls/categorias)
    urls      : list[str] — URLs completas de ML
    categorias: list[str] — keys de URLS_PREDEFINIDAS (ej. ['ofertas', 'electronica'])
    """
    resultados = []

    if queries:
        print(f"⚠️  Búsqueda por keyword no disponible sin API key ML — usa categorias o urls", flush=True)

    for cat in (categorias or []):
        cat_urls = URLS_PREDEFINIDAS.get(cat)
        if not cat_urls:
            print(f"  ⚠️  Categoría desconocida: {cat} — opciones: {list(URLS_PREDEFINIDAS)}", flush=True)
            continue
        print(f"📦 ML categoría: {cat} ({len(cat_urls)} URL(s))", flush=True)
        for u in cat_urls:
            resultados.extend(scrape_url(u))
            time.sleep(1.2)

    for url in (urls or []):
        print(f"📄 ML URL: {url[:70]}", flush=True)
        resultados.extend(scrape_url(url))
        time.sleep(1.2)

    # Si no se especificó nada, usar las 3 fuentes diarias principales
    if not categorias and not urls and not queries:
        print(f"📦 ML: scrapeando {len(URLS_DIARIAS)} fuentes diarias", flush=True)
        for u in URLS_DIARIAS:
            resultados.extend(scrape_url(u))
            time.sleep(1.2)

    resultados = deduplicar(resultados)
    print(f"✅ ML total: {len(resultados)} ofertas únicas", flush=True)
    return resultados


if __name__ == "__main__":
    ofertas = scrape(categorias=["ofertas", "electronica"], min_discount=20)
    print(json.dumps(ofertas[:2], indent=2, ensure_ascii=False))
