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

_PLAYWRIGHT_OK = False
try:
    from playwright.sync_api import sync_playwright as _sync_playwright
    _PLAYWRIGHT_OK = True
except ImportError:
    pass

# ── CONFIG ──────────────────────────────────────────────────────────
ML_BASE     = "https://www.mercadolibre.com.mx"
ML_API_BASE = "https://api.mercadolibre.com/sites/MLM/search"
IMG_TPL     = "https://http2.mlstatic.com/D_NQ_NP_{pic_id}-F.webp"

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
    """
    Construye la URL para la página N respetando el esquema de paginación de la URL base.
    - URLs con ?page=N  → incrementa desde ese número base (ofertas, deals)
    - Resto            → usa ?_from=N (48 ítems por página, listados estándar)
    """
    if pagina <= 1:
        return url
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    if "page" in params:
        page_base = int(params["page"][0])
        params["page"] = [str(page_base + pagina - 1)]
    else:
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

# ── ML API PÚBLICA (sin key) ─────────────────────────────────────────
def _parse_filtros_listado(url):
    """
    Extrae filtros de búsqueda desde una URL listado.mercadolibre.com.mx.
    Devuelve dict con params para la API pública de ML (sin key).
    Ejemplo: /_Envio_Full_Discount_15-100_Container_... → {discount:"15-100", shipping:"me2"}
    """
    path   = urlparse(url).path
    params = {}

    # Descuento: _Discount_15-100_ (rango porcentual)
    m = re.search(r'_Discount_(\d+)-(\d+)', path, re.IGNORECASE)
    if m:
        params["discount"] = f"{m.group(1)}-{m.group(2)}"

    # Envío full/gratis
    if re.search(r'_Envio_Full|_Free_Shipping|_Envio_Gratis', path, re.IGNORECASE):
        params["shipping"] = "me2"   # Mercado Envíos Full

    return params


def _normalizar_api_item(item):
    """Normaliza un resultado de la API pública de ML al objeto oferta común."""
    pid        = item.get("id", "")
    title      = item.get("title", "")
    price_disc = float(item.get("price", 0) or 0)
    price_orig = float(item.get("original_price", 0) or price_disc)
    link       = item.get("permalink", "")
    thumbnail  = item.get("thumbnail", "")

    # Mejora resolución: thumbnail _I_.jpg → _F_.webp
    img = re.sub(r'-[A-Z]\.(jpg|webp)', '-F.webp', thumbnail) if thumbnail else ""

    desc_pct = 0.0
    if price_orig > price_disc > 0:
        desc_pct = round((price_orig - price_disc) / price_orig * 100, 1)

    if not pid or not title or price_disc == 0:
        return None

    return {
        "id":               pid,
        "asin":             pid,
        "source":           "ml",
        "title":            title,
        "link":             link,
        "img":              img,
        "price_original":   price_orig,
        "price_discounted": price_disc,
        "descuento_pct":    desc_pct,
        "vigencia":         "oferta",
        "tipo":             "DEAL",
        "badge":            "",
        "start_time":       None,
        "end_time":         None,
    }


def _extraer_polycards(body, min_discount=0):
    """
    Extrae productos buscando directamente cada objeto {"id":"POLYCARD",...}
    en cualquier punto del body, sin depender de la estructura del array padre.
    Funciona en páginas de búsqueda, categoría, Container y carruseles anidados.
    """
    productos = []
    seen_ids  = set()

    for m in re.finditer(r'\{"id"\s*:\s*"POLYCARD"', body):
        obj_start = m.start()
        depth, end = 0, obj_start
        for i, c in enumerate(body[obj_start:]):
            if   c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = obj_start + i + 1
                    break
        try:
            item = json.loads(body[obj_start:end])
        except Exception:
            continue

        poly = item.get("polycard", {})
        if not poly:
            continue
        pseudo = {"card": poly}
        p = _normalizar(pseudo)
        if p and p["descuento_pct"] >= min_discount and p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            productos.append(p)

    return productos


def _extraer_next_url(body):
    """Extrae la URL de la siguiente página del initialState de una listado URL."""
    idx = body.find('"next_page":{"value"')
    if idx < 0:
        return None
    start = body.find('{', idx)
    depth, end = 0, start
    for i, c in enumerate(body[start:]):
        if   c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = start + i + 1
                break
    try:
        obj = json.loads(body[start:end])
        raw = obj.get('url', '')
        return raw.replace('\\u002F', '/') if raw else None
    except Exception:
        return None


def _scrape_listado_playwright(url, pages=3, min_discount=0):
    """
    Renderiza URLs listado.mercadolibre.com.mx con Playwright.
    Captura el cuerpo completo (2-3 MB) que incluye el initialState con polycards.
    Navega automáticamente a páginas siguientes usando next_page.url del initialState.
    """
    if not _PLAYWRIGHT_OK:
        print("  ⚠️  Playwright no disponible — pip install playwright && playwright install chrome", flush=True)
        return []

    captured = {}

    try:
        with _sync_playwright() as pw:
            browser = pw.chromium.launch(
                channel='chrome',
                headless=True,
                args=['--disable-blink-features=AutomationControlled',
                      '--no-sandbox', '--disable-setuid-sandbox'],
            )
            ctx = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                locale='es-MX',
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/124.0.0.0 Safari/537.36',
            )
            page = ctx.new_page()
            current_url = url

            for page_num in range(1, pages + 1):
                big_body = [None]   # lista para captura en closure

                all_responses = []  # diagnóstico

                def _on_response(resp, _holder=big_body, _log=all_responses):
                    if resp.status != 200:
                        return
                    try:
                        body = resp.text()
                    except Exception:
                        return
                    # Usar comillas para distinguir JSON de variables JS en bundles
                    has_state = '"initialState"' in body
                    has_poly  = '"POLYCARD"' in body or '"results"' in body
                    if len(body) > 5000:  # loguear cualquier respuesta grande
                        _log.append((resp.url[:90], len(body), has_state, has_poly))
                    # Preferir la respuesta más grande con JSON real (no JS bundles)
                    if len(body) > 50000 and has_state and '"results"' in body:
                        if _holder[0] is None or len(body) > len(_holder[0]):
                            _holder[0] = body

                page.on('response', _on_response)
                print(f"  🎭 Playwright ML p{page_num}: {current_url[:80]}", flush=True)
                page.goto(current_url, wait_until='networkidle', timeout=40000)
                page.wait_for_timeout(3000)
                page.remove_listener('response', _on_response)

                titulo = page.title()
                print(f"  📋 Título: '{titulo[:60]}'", flush=True)
                print(f"  📡 Respuestas >5KB capturadas: {len(all_responses)}", flush=True)
                for r_url, r_len, r_has_state, r_has_poly in sorted(all_responses, key=lambda x: -x[1])[:8]:
                    flags = ('✅initialState ' if r_has_state else '') + ('🃏polycards' if r_has_poly else '')
                    print(f"    {r_len:>9} bytes {flags:<25} {r_url}", flush=True)

                if not big_body[0]:
                    print(f"  ⚠️  p{page_num}: sin initialState — deteniendo", flush=True)
                    break

                prods = _extraer_polycards(big_body[0], min_discount)
                nuevos = sum(1 for p in prods if p['id'] not in captured)
                for p in prods:
                    captured[p['id']] = p
                print(f"  📄 p{page_num}: {len(prods)} polycards → {nuevos} nuevos (total={len(captured)})", flush=True)

                if page_num < pages:
                    next_url = _extraer_next_url(big_body[0])
                    if not next_url:
                        print(f"  ⏹  Sin página siguiente — deteniendo", flush=True)
                        break
                    current_url = next_url
                    time.sleep(1.5)

            browser.close()
    except Exception as e:
        print(f"  ❌ Playwright ML error: {e}", flush=True)

    result = list(captured.values())
    print(f"  ✅ Playwright listado → {len(result)} productos total", flush=True)
    return result


def _scrape_via_api(filtros, pages=3, min_discount=0):
    """
    Usa la API pública de ML (sin key) con paginación real por offset.
    Sirve para listado URLs donde _from= no funciona en containers merch/genéricos.
    """
    resultados = []
    limit      = 48

    for pagina in range(1, pages + 1):
        offset = (pagina - 1) * limit
        params = {**filtros, "limit": limit, "offset": offset, "sort": "relevance"}

        try:
            r = requests.get(ML_API_BASE, params=params, headers=_HEADERS, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ❌ ML API p{pagina}: {e}", flush=True)
            break

        items = data.get("results", [])
        total = data.get("paging", {}).get("total", 0)
        page_prods = [p for i in items if (p := _normalizar_api_item(i)) and p["descuento_pct"] >= min_discount]
        print(f"  📄 ML API p{pagina} (offset={offset}) → {len(items)} raw → {len(page_prods)} productos (total disponible: {total})", flush=True)
        resultados.extend(page_prods)

        if offset + limit >= total or len(items) < limit:
            break
        if pagina < pages:
            time.sleep(1.0)

    return resultados


# ── CONVERSOR DE URLs LISTADO → OFERTAS ─────────────────────────────
def _convertir_listado_url(url):
    """
    Las páginas listado.mercadolibre.com.mx/* son SPAs vacías.
    Extrae el container_id desde tres lugares posibles y construye
    la URL de ofertas equivalente que sí tiene JSON embebido.
    """
    if "listado.mercadolibre.com.mx" not in url:
        return url

    parsed   = urlparse(url)

    # 1. container_id= en el fragment (ej. #...container_id=MLM1234)
    m = re.search(r'container_id=([A-Za-z0-9_\-]+)', parsed.fragment)
    if m:
        cid = m.group(1)
        print(f"  🔄 Listado → ofertas (fragment): {cid}", flush=True)
        return f"{ML_BASE}/ofertas?container_id={cid}"

    # 2. container_id= en query params (ej. ?container_id=MLM1234)
    m2 = re.search(r'container_id=([A-Za-z0-9_\-]+)', parsed.query)
    if m2:
        cid = m2.group(1)
        print(f"  🔄 Listado → ofertas (query): {cid}", flush=True)
        return f"{ML_BASE}/ofertas?container_id={cid}"

    # 3. _Container_ID en el path (ej. /_Envio_Full_Discount_15-100_Container_ao-landing-all)
    m3 = re.search(r'_Container_([A-Za-z0-9][A-Za-z0-9_\-]*)', parsed.path)
    if m3:
        cid = m3.group(1)
        print(f"  🔄 Listado → ofertas (path): {cid}", flush=True)
        return f"{ML_BASE}/ofertas?container_id={cid}"

    print(f"  ⚠️  Listado sin container_id reconocible, ignorando: {url[:70]}", flush=True)
    return None

# ── SCRAPER DE URL ───────────────────────────────────────────────────
def scrape_url(url, min_discount=0, pages=1):
    """
    Extrae todos los productos de una URL de ML, paginando hasta `pages` páginas.
    Para listado.mercadolibre.com.mx con filtros reconocibles usa la API pública
    (paginación real por offset). Para el resto usa HTML scraping con ?_from=N.
    """
    # Listado URLs son SPAs — renderizar con Playwright e interceptar XHR
    if "listado.mercadolibre.com.mx" in url:
        if _PLAYWRIGHT_OK:
            return _scrape_listado_playwright(url, pages=pages, min_discount=min_discount)
        # Sin Playwright: intentar API con filtros extraídos
        filtros = _parse_filtros_listado(url)
        if filtros:
            print(f"  🔌 Listado → ML API (filtros: {filtros})", flush=True)
            return _scrape_via_api(filtros, pages=pages, min_discount=min_discount)
        # Sin filtros ni Playwright → convertir a container y scrapear HTML

    url = _convertir_listado_url(url)
    if not url:
        return []

    resultados = []

    for pagina in range(1, pages + 1):
        url_pag = _paginar_url(url, pagina)
        print(f"  🔗 ML HTML p{pagina}: {url_pag[:100]}", flush=True)
        try:
            r = requests.get(url_pag, headers=_HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  ❌ {url_pag}: {e}", flush=True)
            break

        raw_items = _extraer_items_de_html(r.text)
        if not raw_items:
            print(f"  📄 p{pagina} → 0 raw, deteniendo", flush=True)
            break

        page_prods = [p for raw in raw_items if (p := _normalizar(raw)) is not None]
        print(f"  📄 p{pagina} → {len(raw_items)} raw → {len(page_prods)} productos", flush=True)
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
