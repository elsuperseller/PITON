#!/usr/bin/env python3
"""scraper_ml.py — Mercado Libre México · normaliza al objeto oferta común"""

import json
import re
import time

import requests
from bs4 import BeautifulSoup

# ── CONFIG ──────────────────────────────────────────────────────────
ML_SITE  = "MLM"
BASE_API = "https://api.mercadolibre.com"

_UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]
_ua_idx = 0

def _ua():
    global _ua_idx
    u = _UA_POOL[_ua_idx % len(_UA_POOL)]
    _ua_idx += 1
    return u

def _api_hdrs():
    return {"User-Agent": _ua(), "Accept": "application/json", "Accept-Language": "es-MX,es;q=0.9"}

def _web_hdrs():
    return {"User-Agent": _ua(), "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "es-MX,es;q=0.9", "Accept-Encoding": "gzip, deflate, br"}

# ── NORMALIZADOR ────────────────────────────────────────────────────
def normalizar(item):
    """ML API item → objeto oferta común (mismo schema que Amazon)."""
    pid        = item.get("id", "")
    price_disc = float(item.get("price") or 0)
    price_orig = float(item.get("original_price") or price_disc)
    desc_pct   = round((price_orig - price_disc) / price_orig * 100, 1) if price_orig > price_disc > 0 else 0.0

    vigencia   = "permanente"
    tipo       = ""
    badge      = ""
    start_time = None
    end_time   = None

    for promo in item.get("promotions", []):
        pt = (promo.get("type") or "").lower()
        if "lightning" in pt or "flash" in pt or "oferta_del_dia" in pt:
            vigencia = "relampago"
            tipo     = "LIGHTNING_DEAL"
        elif not tipo:
            tipo     = promo.get("type", "")
            vigencia = "oferta"
        badge      = promo.get("name", "") or badge
        start_time = promo.get("start_time") or start_time
        end_time   = promo.get("end_time")   or end_time

    if not tipo and item.get("deal_ids"):
        vigencia = "oferta"
        tipo     = "DEAL"

    img = (item.get("thumbnail") or "").replace("-I.jpg", "-O.jpg").replace("-I.webp", "-O.webp")

    return {
        "id":               pid,
        "asin":             pid,   # compatibilidad con frontend Amazon
        "source":           "ml",
        "title":            item.get("title", ""),
        "link":             item.get("permalink", ""),
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

# ── API: ITEM INDIVIDUAL ────────────────────────────────────────────
def _obtener_item(item_id):
    """Datos completos de un item por MLID (incluye promotions)."""
    try:
        r = requests.get(f"{BASE_API}/items/{item_id}", headers=_api_hdrs(), timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

# ── API: BÚSQUEDA POR KEYWORD ───────────────────────────────────────
def buscar_ml(query, min_discount=15, max_results=50, precio_min=0, precio_max=0):
    resultados = []
    offset     = 0

    while len(resultados) < max_results:
        params = {
            "q":      query,
            "sort":   "highest_discount",
            "limit":  min(50, max_results - len(resultados)),
            "offset": offset,
        }
        if precio_min > 0 and precio_max > 0:
            params["price"] = f"{int(precio_min)}-{int(precio_max)}"
        elif precio_min > 0:
            params["price"] = f"{int(precio_min)}-*"
        elif precio_max > 0:
            params["price"] = f"*-{int(precio_max)}"

        try:
            r = requests.get(f"{BASE_API}/sites/{ML_SITE}/search",
                             params=params, headers=_api_hdrs(), timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ❌ ML keyword '{query}' offset={offset}: {e}", flush=True)
            break

        items = data.get("results", [])
        if not items:
            break

        for item in items:
            p = normalizar(item)
            if p["descuento_pct"] >= min_discount:
                resultados.append(p)

        offset += len(items)
        if offset >= data.get("paging", {}).get("total", 0):
            break
        time.sleep(0.4)

    return resultados

# ── API: BÚSQUEDA POR CATEGORÍA ─────────────────────────────────────
def buscar_categoria(cat_id, min_discount=15, max_results=50):
    """cat_id: ID de categoría ML, ej. 'MLM1055' (Electrónica)."""
    resultados = []
    offset     = 0

    while len(resultados) < max_results:
        params = {
            "category": cat_id,
            "sort":     "highest_discount",
            "limit":    min(50, max_results - len(resultados)),
            "offset":   offset,
        }
        try:
            r = requests.get(f"{BASE_API}/sites/{ML_SITE}/search",
                             params=params, headers=_api_hdrs(), timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ❌ ML categoría {cat_id}: {e}", flush=True)
            break

        items = data.get("results", [])
        if not items:
            break

        for item in items:
            p = normalizar(item)
            if p["descuento_pct"] >= min_discount:
                resultados.append(p)

        offset += len(items)
        if offset >= data.get("paging", {}).get("total", 0):
            break
        time.sleep(0.4)

    return resultados

# ── SCRAPER: DESDE URL ML ───────────────────────────────────────────
def scrape_url(url, min_discount=15):
    """
    Extrae MLIDs de cualquier URL de ML (campaña, categoría, oferta especial)
    usando BeautifulSoup, luego consulta la API por cada item.
    """
    resultados = []
    try:
        r = requests.get(url, headers=_web_hdrs(), timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # IDs en atributos data-* y en hrefs
        texto = soup.get_text(" ") + " ".join(str(t) for t in soup.find_all(href=True))
        ids   = list(set(re.findall(r'MLM-?(\d{7,10})', texto)))
        print(f"  📄 URL → {len(ids)} IDs encontrados", flush=True)
    except Exception as e:
        print(f"  ❌ Scrape URL: {e}", flush=True)
        return []

    for mlid in ids[:100]:
        data = _obtener_item(f"MLM{mlid}")
        if not data:
            continue
        p = normalizar(data)
        if p["descuento_pct"] >= min_discount:
            resultados.append(p)
        time.sleep(0.3)

    return resultados

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
           min_discount=15, max_per_query=50, precio_min=0, precio_max=0):
    """
    queries   : list[str]  — keywords a buscar
    urls      : list[str]  — URLs de ML (campañas, categorías especiales)
    categorias: list[str]  — IDs de categoría ML (ej. ['MLM1055', 'MLM1459'])
    """
    resultados = []

    for q in (queries or []):
        print(f"🔍 ML keyword: {q}", flush=True)
        items = buscar_ml(q, min_discount=min_discount, max_results=max_per_query,
                          precio_min=precio_min, precio_max=precio_max)
        print(f"  → {len(items)} ofertas", flush=True)
        resultados.extend(items)
        time.sleep(1)

    for cat in (categorias or []):
        print(f"📦 ML categoría: {cat}", flush=True)
        items = buscar_categoria(cat, min_discount=min_discount, max_results=max_per_query)
        print(f"  → {len(items)} ofertas", flush=True)
        resultados.extend(items)
        time.sleep(1)

    for url in (urls or []):
        print(f"📄 ML URL: {url[:70]}", flush=True)
        items = scrape_url(url, min_discount=min_discount)
        print(f"  → {len(items)} ofertas", flush=True)
        resultados.extend(items)
        time.sleep(1.5)

    resultados = deduplicar(resultados)
    print(f"✅ ML total: {len(resultados)} ofertas únicas", flush=True)
    return resultados


# ── CATEGORÍAS ML MÉXICO (referencia) ──────────────────────────────
# MLM1055  Electrónica          MLM1459  Deportes y Fitness
# MLM1276  Hogar, Muebles       MLM1367  Juguetes y Bebés
# MLM1499  Salud y Belleza      MLM1132  Ropa y Accesorios
# MLM1747  Autos y Motos        MLM1144  Videojuegos
# MLM1648  Industria y Oficina  MLM1700  Animales y Mascotas

if __name__ == "__main__":
    ofertas = scrape(
        queries=["laptop", "auriculares inalámbricos", "smart tv"],
        min_discount=20,
        max_per_query=20,
    )
    print(json.dumps(ofertas[:3], indent=2, ensure_ascii=False))
