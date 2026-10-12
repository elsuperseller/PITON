#!/usr/bin/env python3
"""
scraper_ml.py — Mercado Libre México
Extrae JSON embebido de páginas ML (no requiere API key).
Normaliza al objeto oferta común compatible con Amazon.
"""

import json
import re
import time
import os
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

# Perfil de Chrome persistente con sesión de ML
ML_BROWSER_PROFILE = os.path.expanduser('~/Desktop/SUPERSELLER/.ml_browser_profile')

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
    - URLs con ?page=N existente → incrementa desde ese número base
    - /ofertas o ?container_id= → page=N  (containers usan page=, no _from=)
    - Resto                      → _from=N (48 ítems por página, listados estándar)
    El fragment (#...) se descarta: es solo para el browser, el server lo ignora.
    """
    if pagina <= 1:
        return url
    parsed = urlparse(url)
    parsed = parsed._replace(fragment="")   # strip #fragment
    params = parse_qs(parsed.query, keep_blank_values=True)
    if "page" in params:
        page_base = int(params["page"][0])
        params["page"] = [str(page_base + pagina - 1)]
    elif "/ofertas" in parsed.path or "container_id" in parsed.query:
        params["page"] = [str(pagina)]
    else:
        params["_from"] = [str((pagina - 1) * 48)]
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


def _extraer_items_de_html(html):
    """
    Extrae el array 'items' del JSON embebido en cualquier página ML.
    Funciona en páginas de ofertas, categorías y búsqueda (cualquier página).
    """
    # Buscar todos los scripts que contengan "items":[
    for script in re.findall(r'<script[^>]*>(.*?)</script>', html, re.S):
        if '"items":[' not in script:
            continue

        # Buscar el array de items más grande (el que probablemente contiene los productos)
        # Puede tener {"position":, {"id":"POLYCARD", o cualquier otro formato
        idx = script.find('"items":[')
        if idx < 0:
            continue

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
            items = json.loads(script[start:end])
            # Validar que sea un array válido con al menos un elemento
            if isinstance(items, list) and len(items) > 0:
                # Verificar si contiene datos de productos (card, polycard, metadata, etc.)
                first = items[0] if items else {}
                if any(k in first for k in ['card', 'polycard', 'metadata', 'position', 'id']):
                    return items
        except Exception:
            continue
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

            # Extraer precio con descuento (actual)
            price_disc = float(p.get("current_price", {}).get("value", 0) or 0)

            # Extraer precio original y descuento de price_labels
            price_orig = price_disc  # Default si no hay descuento
            desc_pct = 0.0

            price_labels = p.get("price_labels", [])
            for label_group in price_labels:
                values = label_group.get("values", [])
                for val in values:
                    # Buscar precio original
                    if val.get("key") == "previous_price":
                        price_data = val.get("price", {})
                        price_orig = float(price_data.get("value", 0) or price_disc)

                    # Buscar descuento en la etiqueta pill (ej: "25% OFF")
                    if val.get("key") == "previous_label":
                        pill = val.get("pill", {})
                        pill_text = pill.get("text", "")
                        # Extraer número del texto "25% OFF"
                        import re
                        match = re.search(r'(\d+)%', pill_text)
                        if match:
                            desc_pct = float(match.group(1))

            # Si no encontramos descuento en pill, calcular manualmente
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
    Ejemplo: /_Envio_Full_Discount_15-100_PriceRange_0MXN-999MXN_Container_...
    → {discount:"15-100", shipping:"me2", price:"0-999"}
    """
    path   = urlparse(url).path
    params = {}

    # Descuento: _Discount_15-100_ (rango porcentual)
    m = re.search(r'_Discount_(\d+)-(\d+)', path, re.IGNORECASE)
    if m:
        params["discount"] = f"{m.group(1)}-{m.group(2)}"

    # Precio: _PriceRange_0-999_ o _PriceRange_0MXN-999MXN_
    m = re.search(r'_PriceRange_(\d+)(?:MXN)?-(\d+)(?:MXN)?', path, re.IGNORECASE)
    if m:
        params["price"] = f"{m.group(1)}-{m.group(2)}"

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


def _extraer_polycards(body, min_discount=0, precio_min=0, precio_max=0):
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
        if not p or p["id"] in seen_ids:
            continue
        # Filtros
        if p["descuento_pct"] < min_discount:
            continue
        if precio_max > 0 and p["price_discounted"] > precio_max:
            continue
        if precio_min > 0 and p["price_discounted"] < precio_min:
            continue
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


def _scrape_listado_playwright(url, pages=3, min_discount=0, precio_min=0, precio_max=0):
    """
    Renderiza URLs de ML con Playwright extrayendo productos del DOM.
    ML cambió su estructura - ahora renderiza productos client-side en HTML.
    IMPORTANTE: Corre en modo visible (headless=False) porque ML detecta headless.
    """
    if not _PLAYWRIGHT_OK:
        print("  ⚠️  Playwright no disponible — pip install playwright && playwright install chrome", flush=True)
        return []

    productos = []

    try:
        with _sync_playwright() as pw:
            # Usar perfil persistente con sesión de ML guardada
            # IMPORTANTE: headless=False porque ML detecta headless y no carga productos
            ctx = pw.chromium.launch_persistent_context(
                ML_BROWSER_PROFILE,
                headless=False,  # ML no carga productos en headless
                channel='chrome',
                viewport={'width': 1280, 'height': 800},
                locale='es-MX',
                args=['--disable-blink-features=AutomationControlled'],
            )

            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            print(f"  🎭 Playwright ML: {url[:80]} ({pages} página(s))", flush=True)

            # Procesar múltiples páginas
            todos_productos = []

            for page_num in range(1, pages + 1):
                # Construir URL de página
                if page_num == 1:
                    page_url = url
                else:
                    # Remover fragment (#...) antes de agregar page=
                    # El fragment no se envía al servidor y causa que page= se ignore
                    url_sin_fragment = url.split('#')[0]
                    separator = '&' if '?' in url_sin_fragment else '?'
                    page_url = f"{url_sin_fragment}{separator}page={page_num}"

                print(f"  📄 Página {page_num}/{pages}: {page_url}", flush=True)

                # Navegar a la página
                page.goto(page_url, wait_until='networkidle', timeout=60000)
                page.wait_for_timeout(4000)  # Esperar más para asegurar carga completa

                # Scroll para asegurar que todo cargó
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(1000)

                # Extraer productos del DOM (ML ya no usa JSON embebido)
                productos_raw = page.evaluate("""() => {
                const productos = [];
                const cards = document.querySelectorAll('.poly-card, [class*="poly-card"]');

                cards.forEach(card => {
                    try {
                        const linkElem = card.querySelector('a[href*="/p/"]');
                        if (!linkElem) return;

                        const link = linkElem.href;
                        const idMatch = link.match(/MLM\\d+/);
                        if (!idMatch) return;
                        const id = idMatch[0];

                        const titleElem = card.querySelector('.poly-component__title, [class*="title"]');
                        const title = titleElem ? titleElem.textContent.trim() : '';
                        if (!title) return;

                        const precioElems = card.querySelectorAll('.andes-money-amount__fraction');
                        if (precioElems.length === 0) return;

                        let precio = 0;
                        let precioOrig = 0;

                        if (precioElems.length >= 2) {
                            precioOrig = parseFloat(precioElems[0].textContent.replace(/[^0-9]/g, ''));
                            precio = parseFloat(precioElems[1].textContent.replace(/[^0-9]/g, ''));
                        } else {
                            precio = parseFloat(precioElems[0].textContent.replace(/[^0-9]/g, ''));
                            precioOrig = precio;
                        }

                        if (precio === 0) return;

                        let descuento = 0;
                        if (precioOrig > precio) {
                            descuento = Math.round(((precioOrig - precio) / precioOrig) * 100);
                        }

                        const descuentoElem = card.querySelector('[class*="discount"], [class*="off"]');
                        if (descuentoElem) {
                            const match = descuentoElem.textContent.match(/(\\d+)%/);
                            if (match) descuento = parseInt(match[1]);
                        }

                        const imgElem = card.querySelector('img');
                        const img = imgElem ? (imgElem.src || imgElem.dataset.src || '') : '';

                        productos.push({
                            id: id,
                            title: title,
                            link: link,
                            price_discounted: precio,
                            price_original: precioOrig,
                            descuento_pct: descuento,
                            img: img
                        });
                    } catch (e) {}
                });

                return productos;
            }""")

                # Deduplicar por ID dentro de esta página (puede haber duplicados en DOM)
                ids_vistos = set()
                productos_unicos_pagina = []
                for p in productos_raw:
                    if p['id'] not in ids_vistos:
                        ids_vistos.add(p['id'])
                        productos_unicos_pagina.append(p)

                primer_id = productos_unicos_pagina[0]['id'] if productos_unicos_pagina else 'ninguno'
                print(f"    ✅ {len(productos_raw)} elementos → {len(productos_unicos_pagina)} únicos en p{page_num} (primer ID: {primer_id})", flush=True)
                todos_productos.extend(productos_unicos_pagina)

                # Delay entre páginas
                if page_num < pages:
                    import time
                    time.sleep(2)

            print(f"  📊 Total: {len(todos_productos)} productos de {pages} página(s)", flush=True)

            # Normalizar al formato común y aplicar filtros
            for p_raw in todos_productos:
                # Filtro de descuento mínimo
                if p_raw['descuento_pct'] < min_discount:
                    continue

                # Filtro de precio
                precio = p_raw['price_discounted']
                if precio_min > 0 and precio < precio_min:
                    continue
                if precio_max > 0 and precio > precio_max:
                    continue

                # Normalizar al formato común de ML
                productos.append({
                    'id': p_raw['id'],
                    'title': p_raw['title'],
                    'link': p_raw['link'],
                    'img': p_raw['img'],
                    'price_discounted': p_raw['price_discounted'],
                    'price_original': p_raw['price_original'],
                    'descuento_pct': p_raw['descuento_pct'],
                    'source': 'Mercado Libre',  # Identificar origen
                    'canal': 'Mercado Libre',    # Para export a Sheets
                })

            print(f"  📊 {len(productos)} con descuento≥{min_discount}%", flush=True)

            ctx.close()
    except Exception as e:
        print(f"  ❌ Playwright ML error: {e}", flush=True)

    return productos


def _scrape_via_api(filtros, pages=3, min_discount=0, precio_min=0, precio_max=0):
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
        page_prods = []
        for i in items:
            p = _normalizar_api_item(i)
            if not p or p["descuento_pct"] < min_discount:
                continue
            if precio_max > 0 and p["price_discounted"] > precio_max:
                continue
            if precio_min > 0 and p["price_discounted"] < precio_min:
                continue
            page_prods.append(p)
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
def scrape_url(url, min_discount=0, pages=1, precio_min=0, precio_max=0):
    """
    Extrae todos los productos de una URL de ML, paginando hasta `pages` páginas.
    Para listado.mercadolibre.com.mx con filtros reconocibles usa la API pública
    (paginación real por offset). Para el resto usa HTML scraping con ?_from=N.

    precio_min/precio_max: filtro de precio (0 = sin límite)
    """
    # Extraer filtros de precio de la URL si no se especificaron explícitamente
    if precio_min == 0 and precio_max == 0:
        # Probar ambos formatos: _PriceRange_0-999_ y _PriceRange_0MXN-999MXN_
        m = re.search(r'_PriceRange_(\d+)(?:MXN)?-(\d+)(?:MXN)?', url, re.IGNORECASE)
        if m:
            precio_min = int(m.group(1))
            precio_max = int(m.group(2))
            print(f"  💰 Filtro de precio detectado: ${precio_min}-${precio_max} MXN", flush=True)

    # Listado URLs y ofertas son SPAs — renderizar con Playwright e interceptar XHR
    if "listado.mercadolibre.com.mx" in url or "/ofertas" in url:
        # 1. Intentar Playwright primero
        if _PLAYWRIGHT_OK:
            resultados_pw = _scrape_listado_playwright(url, pages=pages, min_discount=min_discount,
                                                       precio_min=precio_min, precio_max=precio_max)
            if resultados_pw:  # Si Playwright funcionó, retornar
                return resultados_pw
            print(f"  ⚠️  Playwright devolvió 0 productos, intentando fallback...", flush=True)

        # 2. Fallback: intentar API con filtros extraídos
        filtros = _parse_filtros_listado(url)
        if filtros:
            print(f"  🔌 Listado → ML API (filtros: {filtros})", flush=True)
            resultados_api = _scrape_via_api(filtros, pages=pages, min_discount=min_discount,
                                            precio_min=precio_min, precio_max=precio_max)
            if resultados_api:  # Si API funcionó, retornar
                return resultados_api
            print(f"  ⚠️  API devolvió 0 productos, intentando HTML scraping...", flush=True)

        # 3. Último fallback: convertir a container y scrapear HTML

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

        page_prods = []
        for raw in raw_items:
            p = _normalizar(raw)
            if p is None:
                continue
            # Filtrar por precio si se especificó
            if precio_max > 0 and p["price_discounted"] > precio_max:
                continue
            if precio_min > 0 and p["price_discounted"] < precio_min:
                continue
            page_prods.append(p)

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
            resultados.extend(scrape_url(u, pages=1, precio_min=precio_min, precio_max=precio_max))
            time.sleep(1.2)

    for url in (urls or []):
        print(f"📄 ML URL: {url[:70]}", flush=True)
        resultados.extend(scrape_url(url, pages=pages, precio_min=precio_min, precio_max=precio_max))
        time.sleep(1.2)

    # Si no se especificó nada, descubrir y scrapear todas las fuentes diarias
    if not categorias and not urls and not queries:
        daily_urls = _descubrir_containers(f"{ML_BASE}/ofertas")
        print(f"📦 ML: scrapeando {len(daily_urls)} fuentes diarias", flush=True)
        for u in daily_urls:
            resultados.extend(scrape_url(u, pages=1, precio_min=precio_min, precio_max=precio_max))
            time.sleep(1.2)

    resultados = deduplicar(resultados)
    print(f"✅ ML total: {len(resultados)} ofertas únicas", flush=True)
    return resultados


if __name__ == "__main__":
    ofertas = scrape(categorias=["ofertas", "electronica"], min_discount=20)
    print(json.dumps(ofertas[:2], indent=2, ensure_ascii=False))
