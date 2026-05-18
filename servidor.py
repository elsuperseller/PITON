#!/usr/bin/env python3
"""SUPERSELLER SERVIDOR v1.4 — Amazon Creators API"""

import json
import requests
import re
import os
import sys as _sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    import scraper_ml as _ml
    _ML_OK = True
except ImportError:
    _ML_OK = False

try:
    import scraper_amazon as _az
    _AZ_OK = True
except ImportError:
    _AZ_OK = False

try:
    import historial_variedad as _hv
    _HV_OK = True
except ImportError:
    _HV_OK = False

# CREDENCIALES (reemplazar con las tuyas)
CREDS = {
    "client_id": "amzn1.application-oa2-client.71a0b70614ce461580b328d6122e4b4e",  # Reemplazar
    "client_secret": "amzn1.oa2-cs.v1.264318baad75178ea2a8774f53b38f8540174b9d26d9e626ad41818dbef95de2",  # Reemplazar
    "partner_tag": "bunkerxstudio-20"
}

def get_token():
    """Obtener token Bearer para API Amazon"""
    r = requests.post("https://api.amazon.com/auth/o2/token", json={
        "grant_type": "client_credentials",
        "client_id": CREDS["client_id"],
        "client_secret": CREDS["client_secret"],
        "scope": "creatorsapi::default"
    }, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]

def buscar(search_index, pagina=1, sort_by="NewestArrivals", browse_node_id=None, min_saving=1, precio_min=0, precio_max=0):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-marketplace": "www.amazon.com.mx"
    }
    body = {
        "partnerTag": CREDS["partner_tag"],
        "marketplace": "www.amazon.com.mx",
        "searchIndex": search_index,
        "itemCount": 10,
        "itemPage": pagina,
        "sortBy": sort_by,
        "keywords": "a",
        "minSavingPercent": min_saving,
        "condition": "New",
        "availability": "Available",
        "languagesOfPreference": ["es_MX"],
        "currencyOfPreference": "MXN",
        "resources": [
            "itemInfo.title", "images.primary.medium",
            "offersV2.listings.price", "offersV2.listings.dealDetails",
            "offersV2.listings.isBuyBoxWinner", "offersV2.listings.type",
            "offersV2.listings.availability"
        ]
    }
    if browse_node_id:
        body["browseNodeId"] = browse_node_id
    if precio_min > 0:
        body["minPrice"] = int(precio_min * 100)
    if precio_max > 0:
        body["maxPrice"] = int(precio_max * 100)
    r = requests.post("https://creatorsapi.amazon/catalog/v1/searchItems",
                      headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return r.json().get("searchResult", {}).get("items", [])

def parsear_item(item):
    try:
        title = item["itemInfo"]["title"]["displayValue"]
        link = item.get("detailPageURL", "")
        img = re.sub(r'\._SL\d+_', '._SL500_',
                     item.get("images",{}).get("primary",{}).get("medium",{}).get("url",""))
        asin = re.search(r'/dp/([A-Z0-9]{10})', link)
        asin = asin.group(1) if asin else ""
        listings = item.get("offersV2",{}).get("listings",[])
        if not listings: return None
        lst = next((l for l in listings if l.get("isBuyBoxWinner")), listings[0])
        deal = lst.get("dealDetails") or {}
        tipo = lst.get("type","")
        pi = lst.get("price",{})
        pd_ = pi.get("money",{}).get("amount")
        if not pd_: return None
        pd_ = float(pd_)
        sb = pi.get("savingBasis",{})
        sv = pi.get("savings",{})
        if sb and sb.get("money",{}).get("amount"):
            po = float(sb["money"]["amount"])
        elif sv and sv.get("money",{}).get("amount"):
            po = round(pd_ + float(sv["money"]["amount"]), 2)
        else:
            po = pd_
        desc = round((po - pd_) / po * 100) if po > pd_ else 0
        end = deal.get("endTime","")
        start = deal.get("startTime","")
        badge = deal.get("badge","")
        acc = deal.get("accessType","ALL")
        vigencia = "relámpago" if tipo == "LIGHTNING_DEAL" else "permanente" if not end else "oferta"
        return {
            "asin": asin, "link": link, "title": title, "img": img,
            "price_original": po, "price_discounted": pd_, "descuento_pct": desc,
            "vigencia": vigencia, "tipo": tipo, "badge": badge, "access_type": acc,
            "start_time": start, "end_time": end, "pct_claimed": deal.get("percentageClaimed")
        }
    except: return None

CATS = {
    "Electrónicos":                     "Electronics",
    "Hogar y Cocina":                   "HomeAndKitchen",
    "Deportes y Aire Libre":            "SportsAndOutdoors",
    "Juguetes y Juegos":                "ToysAndGames",
    "Herramientas y Mejoras del Hogar": "ToolsAndHomeImprovement",
    "Belleza":                          "HealthPersonalCare",
    "Salud y Cuidado Personal":         "HealthPersonalCare",
    "Ropa, Zapatos y Accesorios":       "Fashion",
    "Libros":                           "Books",
    "Tienda Kindle":                    "KindleStore",
    "Videojuegos":                      "VideoGames",
    "Automotriz y Motocicletas":        "Automotive",
    "Productos para Animales":          "PetSupplies",
    "Oficina y Papelería":              "OfficeProducts",
    "Alimentos y Bebidas":              "GroceryAndGourmetFood",
    "Bebé":                             "Baby",
    "Relojes":                          "Watches",
    "Instrumentos Musicales":           "MusicalInstruments",
    "Música":                           "Music",
    "Películas y Series de TV":         "MoviesAndTV",
    "Software":                         "Software",
    "Productos Handmade":               "Handmade",
    "Industria, Empresas y Ciencia":    "IndustrialAndScientific",
}

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path == "/buscar":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                cats = body.get("categorias", {})
                pags = int(body.get("paginas", 3))
                filtros = body.get("filtros", {})
                sort_by = body.get("sortBy", "NewestArrivals")
                # Log para ver qué llega del HTML
                print(f"📋 Categorías recibidas ({len(cats)}):", flush=True)
                for k, v in list(cats.items())[:5]:
                    print(f"   {k}: {v}", flush=True)
                desc_min = int(filtros.get("descuento_min", 15))
                pmin = float(filtros.get("precio_min", 0))
                pmax = float(filtros.get("precio_max", 0))

                # Si hay filtro de precio, buscar más páginas porque la API no filtra por precio
                if pmin > 0 or pmax > 0:
                    pags = max(pags, 8)
                    print(f"  💰 Filtro precio activo (${pmin}-${pmax}), ampliando a {pags} páginas", flush=True)

                resultados = []
                for nombre, cat_val in cats.items():
                    if isinstance(cat_val, dict):
                        cat_index = cat_val.get("searchIndex", "All")
                        browse_nid = cat_val.get("nodeId")
                    else:
                        cat_index = cat_val
                        browse_nid = None
                    for pag in range(1, pags + 1):
                        try:
                            print(f"  → Buscando: {cat_index} | nodeId: {browse_nid} | pag: {pag}", flush=True)
                            items = buscar(cat_index, pag, sort_by=sort_by, browse_node_id=browse_nid,
                                         min_saving=max(1, desc_min), precio_min=pmin, precio_max=pmax)
                            for item in items:
                                p = parsear_item(item)
                                if p and p["descuento_pct"] >= desc_min:
                                    if pmin > 0 and p["price_discounted"] < pmin: continue
                                    if pmax > 0 and p["price_discounted"] > pmax: continue
                                    resultados.append(p)
                            if not items: break
                            time.sleep(1.2)
                        except Exception as e:
                            if "429" in str(e): time.sleep(10)
                            break

                vistos = set()
                unicos = []
                for p in resultados:
                    if p["asin"] not in vistos:
                        vistos.add(p["asin"])
                        unicos.append(p)

                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "items": unicos}).encode())
            except Exception as e:
                self.send_response(500)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/buscar-directo":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                query = body.get("query", "").strip()
                
                if not query:
                    raise ValueError("query requerida")
                
                print(f"🔍 Búsqueda directa: {query}", flush=True)
                
                token = get_token()
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "x-marketplace": "www.amazon.com.mx"
                }
                
                resultados = []
                # Paginar: 10 páginas x 10 items = hasta 100 productos
                for pagina in range(1, 11):
                    payload = {
                        "partnerTag": CREDS["partner_tag"],
                        "marketplace": "www.amazon.com.mx",
                        "searchIndex": "All",
                        "keywords": query,
                        "itemCount": 10,
                        "itemPage": pagina,
                        "sortBy": "Relevance",
                        "languagesOfPreference": ["es_MX"],
                        "currencyOfPreference": "MXN",
                        "resources": [
                            "itemInfo.title", "images.primary.medium",
                            "offersV2.listings.price", "offersV2.listings.dealDetails",
                            "offersV2.listings.availability"
                        ]
                    }
                    
                    r = requests.post(
                        "https://creatorsapi.amazon/catalog/v1/searchItems",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    
                    if r.status_code != 200:
                        break  # Si falla, detener paginación
                    
                    data = r.json()
                    items = data.get("searchResult", {}).get("items", [])
                    
                    if not items:
                        break  # Si no hay más items, detener
                    
                    for item in items:
                        p = parsear_item(item)
                        if p:
                            resultados.append(p)
                    
                    time.sleep(0.5)  # Delay entre requests
                
                print(f"  → {len(resultados)} producto(s) encontrado(s)", flush=True)
                
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "items": resultados}).encode())
            except Exception as e:
                print(f"❌ {str(e)}", flush=True)
                self.send_response(500)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())


        elif self.path == "/procesar-html":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length)
                html_text = raw.decode("utf-8", errors="ignore")

                import re as _re
                # Cortar el HTML en el punto donde empiezan productos de historial/recomendaciones
                # "purchase-sims" marca el inicio de "vistos anteriormente" en Amazon
                corte = html_text.lower().find("purchase-sims")
                html_principal = html_text[:corte] if corte != -1 else html_text
                asins = list(set(_re.findall(r"/dp/([A-Z0-9]{10})", html_principal)))
                total_html = len(set(_re.findall(r"/dp/([A-Z0-9]{10})", html_text)))
                print(f"📦 /procesar-html → {len(asins)} ASINs principales (de {total_html} totales, {total_html - len(asins)} descartados por historial)", flush=True)

                if not asins:
                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "No se encontraron ASINs en el HTML"}).encode())
                    return

                token = get_token()
                api_headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "x-marketplace": "www.amazon.com.mx"
                }
                resultados = []
                for asin in asins:
                    try:
                        payload = {
                            "partnerTag": CREDS["partner_tag"],
                            "marketplace": "www.amazon.com.mx",
                            "searchIndex": "All",
                            "keywords": asin,
                            "itemCount": 1,
                            "itemPage": 1,
                            "languagesOfPreference": ["es_MX"],
                            "currencyOfPreference": "MXN",
                            "resources": [
                                "itemInfo.title", "images.primary.medium",
                                "offersV2.listings.price", "offersV2.listings.dealDetails",
                                "offersV2.listings.isBuyBoxWinner"
                            ]
                        }
                        r = requests.post(
                            "https://creatorsapi.amazon/catalog/v1/searchItems",
                            headers=api_headers, json=payload, timeout=15
                        )
                        if r.status_code != 200:
                            continue
                        items = r.json().get("searchResult", {}).get("items", [])
                        if not items:
                            continue
                        p = parsear_item(items[0])
                        if p:
                            resultados.append(p)
                            print(f"  ✅ {asin} → {p['price_discounted']} ({p['descuento_pct']}% off)", flush=True)
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"  ❌ {asin} → {str(e)}", flush=True)
                        continue

                print(f"  → {len(resultados)} productos con datos de API", flush=True)
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "items": resultados, "total_asins": len(asins)}).encode())

            except Exception as e:
                print(f"❌ /procesar-html: {str(e)}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/buscar-ml":
            try:
                if not _ML_OK:
                    raise ImportError("scraper_ml no disponible — instala: pip install beautifulsoup4")
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                filtros      = body.get("filtros", {})
                queries      = body.get("queries")      or None
                urls         = body.get("urls")         or None
                categorias   = body.get("categorias")   or None
                min_discount = int(filtros.get("descuento_min", 0))
                precio_min   = float(filtros.get("precio_min", 0))
                precio_max   = float(filtros.get("precio_max", 0))
                max_por_query= int(body.get("max_por_query", 50))
                paginas      = int(body.get("paginas", 1))

                print(f"🛒 /buscar-ml → queries={queries} cats={categorias} urls={len(urls or [])} desc≥{min_discount}% pages={paginas}", flush=True)

                items = _ml.scrape(
                    queries=queries, urls=urls, categorias=categorias,
                    min_discount=min_discount, max_per_query=max_por_query,
                    precio_min=precio_min, precio_max=precio_max,
                    pages=paginas,
                )

                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "items": items, "total": len(items)}).encode())
            except Exception as e:
                print(f"❌ /buscar-ml: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/procesar-html-ml":
            try:
                if not _ML_OK:
                    raise ImportError("scraper_ml no disponible")
                length   = int(self.headers.get("Content-Length", 0))
                html_txt = self.rfile.read(length).decode("utf-8", errors="ignore")
                min_disc = 1
                try:
                    qs = self.headers.get("X-Min-Discount", "1")
                    min_disc = int(qs)
                except Exception:
                    pass
                items, total_raw = _ml.scrape_html_texto(html_txt, min_discount=min_disc)
                print(f"📦 /procesar-html-ml → {total_raw} raw → {len(items)} con ≥{min_disc}%", flush=True)
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "items": items, "total_raw": total_raw}).encode())
            except Exception as e:
                print(f"❌ /procesar-html-ml: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/buscar-amazon-url":
            try:
                if not _AZ_OK:
                    raise ImportError("scraper_amazon no disponible")
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length)) if length else {}
                urls         = body.get("urls", [])
                pages        = int(body.get("pages", 3))
                min_discount = int(body.get("min_discount", 0))

                if not urls:
                    raise ValueError("Se requiere al menos una URL")

                for i, u in enumerate(urls):
                    print(f"  🔎 URL[{i}] len={len(u)}: {repr(u)}", flush=True)

                print(f"🛒 /buscar-amazon-url → {len(urls)} URL(s), {pages} páginas c/u", flush=True)

                _ZG = ("/gp/movers-and-shakers/", "/gp/bestsellers/", "/gp/new-releases/", "/zgbs/")
                zg_urls   = [u for u in urls if any(p in u for p in _ZG)]
                rest_urls = [u for u in urls if not any(p in u for p in _ZG)]

                all_asins, vistos = [], set()

                # Ranking ZG: un solo browser, top 50 por categoría (page 1 = top 50)
                if zg_urls:
                    print(f"  📊 Batch ranking: {len(zg_urls)} URL(s) en 1 browser", flush=True)
                    asins, _ = _az.scrape_zg_batch(zg_urls, pages=1, per_url_limit=50)
                    for a in asins:
                        if a not in vistos:
                            vistos.add(a); all_asins.append(a)

                # Resto de URLs (búsquedas, categorías, stores, etc.)
                for url in rest_urls:
                    asins, _ = _az.scrape_url_custom(url, pages=pages)
                    for a in asins:
                        if a not in vistos:
                            vistos.add(a); all_asins.append(a)

                print(f"  → {len(all_asins)} ASINs únicos, enriqueciendo…", flush=True)

                if not all_asins:
                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({"ok": True, "items": [], "total": 0,
                        "hint": "Sin ASINs encontrados. Verifica que las URLs sean de Amazon MX."}).encode())
                    return

                token = get_token()
                api_headers = {"Authorization": f"Bearer {token}",
                               "Content-Type": "application/json",
                               "x-marketplace": "www.amazon.com.mx"}

                def _enriquecer_asin(asin):
                    try:
                        r = requests.post(
                            "https://creatorsapi.amazon/catalog/v1/searchItems",
                            headers=api_headers,
                            json={"partnerTag": CREDS["partner_tag"], "marketplace": "www.amazon.com.mx",
                                  "searchIndex": "All", "keywords": asin, "itemCount": 1, "itemPage": 1,
                                  "languagesOfPreference": ["es_MX"], "currencyOfPreference": "MXN",
                                  "resources": ["itemInfo.title", "images.primary.medium",
                                                "offersV2.listings.price", "offersV2.listings.dealDetails",
                                                "offersV2.listings.isBuyBoxWinner"]},
                            timeout=15
                        )
                        if r.status_code != 200:
                            return None
                        items = r.json().get("searchResult", {}).get("items", [])
                        if not items:
                            return None
                        p = parsear_item(items[0])
                        return p if p and p["descuento_pct"] >= min_discount else None
                    except Exception as e:
                        print(f"  ❌ {asin}: {e}", flush=True)
                        return None

                resultados = []
                completados = 0
                with ThreadPoolExecutor(max_workers=12) as pool:
                    futuros = {pool.submit(_enriquecer_asin, a): a for a in all_asins}
                    for fut in as_completed(futuros):
                        completados += 1
                        p = fut.result()
                        if p:
                            resultados.append(p)
                        if completados % 50 == 0:
                            print(f"  ⏳ {completados}/{len(all_asins)} ASINs procesados, {len(resultados)} con descuento", flush=True)

                seen, unicos = set(), []
                for p in resultados:
                    if p["asin"] not in seen:
                        seen.add(p["asin"])
                        unicos.append(p)

                print(f"  → {len(unicos)} productos con descuento", flush=True)
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "items": unicos,
                    "total": len(unicos), "asins": len(all_asins)}).encode())
            except Exception as e:
                print(f"❌ /buscar-amazon-url: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/buscar-amazon-deals":
            try:
                if not _AZ_OK:
                    raise ImportError("scraper_amazon no disponible")
                length  = int(self.headers.get("Content-Length", 0))
                body    = json.loads(self.rfile.read(length)) if length else {}
                buckets = body.get("buckets", list(_az.DEALS_URLS.keys()))
                min_discount = int(body.get("min_discount", 0))
                pw_ok = _az.playwright_disponible()
                print(f"🛒 /buscar-amazon-deals → buckets={buckets} playwright={'✅' if pw_ok else '❌'}", flush=True)

                # 1. Extraer ASINs de cada bucket
                all_asins = []
                vistos_asins = set()
                advertencias = []
                for bucket in buckets:
                    asins, estado = _az.scrape_url(bucket)
                    if estado == "bot_challenge":
                        advertencias.append(f"{bucket}: bot_challenge — descarga el HTML manualmente")
                    for a in asins:
                        if a not in vistos_asins:
                            vistos_asins.add(a)
                            all_asins.append(a)

                print(f"🛒 /buscar-amazon-deals → {len(all_asins)} ASINs únicos de {buckets}", flush=True)

                if not all_asins:
                    hint = ("Amazon bloqueó el acceso automático. "
                            "Instala Playwright (pip install playwright && playwright install chromium) "
                            "para acceso completo, o abre la URL en Chrome, guarda el HTML (Cmd+S) y usa 'Procesar HTML'."
                            if not pw_ok else
                            "No se encontraron ASINs con Playwright. Prueba con 'Procesar HTML'.")
                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": True, "items": [], "total": 0,
                        "playwright": pw_ok,
                        "advertencias": advertencias,
                        "hint": hint,
                    }).encode())
                    return

                # 2. Enriquecer vía Creators API
                token = get_token()
                api_headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "x-marketplace": "www.amazon.com.mx"
                }
                resultados = []
                for asin in all_asins:
                    try:
                        payload = {
                            "partnerTag": CREDS["partner_tag"],
                            "marketplace": "www.amazon.com.mx",
                            "searchIndex": "All",
                            "keywords": asin,
                            "itemCount": 1,
                            "itemPage": 1,
                            "languagesOfPreference": ["es_MX"],
                            "currencyOfPreference": "MXN",
                            "resources": [
                                "itemInfo.title", "images.primary.medium",
                                "offersV2.listings.price", "offersV2.listings.dealDetails",
                                "offersV2.listings.isBuyBoxWinner"
                            ]
                        }
                        r = requests.post(
                            "https://creatorsapi.amazon/catalog/v1/searchItems",
                            headers=api_headers, json=payload, timeout=15
                        )
                        if r.status_code != 200:
                            continue
                        items = r.json().get("searchResult", {}).get("items", [])
                        if not items:
                            continue
                        p = parsear_item(items[0])
                        if p and p["descuento_pct"] >= min_discount:
                            resultados.append(p)
                            print(f"  ✅ {asin} → ${p['price_discounted']} ({p['descuento_pct']}% off)", flush=True)
                        time.sleep(0.4)
                    except Exception as e:
                        print(f"  ❌ {asin}: {e}", flush=True)

                # dedup por ASIN
                seen, unicos = set(), []
                for p in resultados:
                    if p["asin"] not in seen:
                        seen.add(p["asin"])
                        unicos.append(p)

                print(f"  → {len(unicos)} productos con descuento", flush=True)
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True, "items": unicos, "total": len(unicos),
                    "asins_encontrados": len(all_asins),
                    "playwright": pw_ok,
                    "advertencias": advertencias
                }).encode())
            except Exception as e:
                print(f"❌ /buscar-amazon-deals: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/historial":
            try:
                if not _HV_OK:
                    raise ImportError("historial_variedad no disponible")
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                action = body.get("action", "score")
                items  = body.get("items", [])

                if action == "score":
                    resultado = _hv.aplicar_scores(items)
                    resp = {"ok": True, "items": resultado}

                elif action == "filtrar":
                    min_score = float(body.get("min_score", 0.1))
                    resultado = _hv.filtrar(items, min_score=min_score)
                    resp = {"ok": True, "items": resultado, "total": len(resultado)}

                elif action == "marcar":
                    n = _hv.marcar_varios(items)
                    resp = {"ok": True, "marcados": n}

                elif action == "limpiar":
                    dias = int(body.get("dias", 60))
                    resp = {"ok": True, **_hv.limpiar(dias=dias)}

                else:
                    resp = {"ok": False, "error": f"Acción desconocida: {action}"}

                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                print(f"❌ /historial: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/exportar-sheets":
            SHEETS_URL = "https://script.google.com/macros/s/AKfycbydiVcrVOXuZWDGfUvtl38QxmHv0nPpPKtR1lUCHr0wvQB9ky0EU756uRtf2JeAcYZoww/exec"
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                items  = body.get("items", [])
                if not items:
                    raise ValueError("Sin items para exportar")
                print(f"📊 /exportar-sheets → {len(items)} items", flush=True)
                r = requests.post(SHEETS_URL, json=items, timeout=120)
                r.raise_for_status()
                resp_data = r.json()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "rows": resp_data.get("rows", len(items))}).encode())
            except Exception as e:
                print(f"❌ /exportar-sheets: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        SUBCATS_POR_CAT = {
            "Electrónicos": [
                {"nombre": "Audio y Hi-Fi",           "id": "9482558011", "searchIndex": "Electronics"},
                {"nombre": "Cámaras y Fotografía",    "id": "9482561011", "searchIndex": "Electronics"},
                {"nombre": "Celulares y Smartphones", "id": "9482563011", "searchIndex": "Electronics"},
                {"nombre": "Computadoras y Laptops",  "id": "9482565011", "searchIndex": "Electronics"},
                {"nombre": "Televisores",             "id": "9482567011", "searchIndex": "Electronics"},
                {"nombre": "Accesorios para PC",      "id": "9482571011", "searchIndex": "Electronics"},
                {"nombre": "Tablets",                 "id": "9482573011", "searchIndex": "Electronics"},
                {"nombre": "Wearables y Smartwatches","id": "9482577011", "searchIndex": "Electronics"},
            ],
            "Hogar y Cocina": [
                {"nombre": "Cocina y Comedor",   "id": "9482610011", "searchIndex": "HomeAndKitchen"},
                {"nombre": "Muebles",            "id": "9482612011", "searchIndex": "HomeAndKitchen"},
                {"nombre": "Decoración",         "id": "9482614011", "searchIndex": "HomeAndKitchen"},
                {"nombre": "Electrodomésticos",  "id": "9482616011", "searchIndex": "HomeAndKitchen"},
                {"nombre": "Jardinería",         "id": "9482618011", "searchIndex": "HomeAndKitchen"},
                {"nombre": "Iluminación",        "id": "9482620011", "searchIndex": "HomeAndKitchen"},
                {"nombre": "Ropa de Cama",       "id": "9482624011", "searchIndex": "HomeAndKitchen"},
            ],
            "Deportes y Aire Libre": [
                {"nombre": "Ejercicio y Fitness",      "id": "9482640011", "searchIndex": "SportsAndOutdoors"},
                {"nombre": "Deportes Acuáticos",       "id": "9482642011", "searchIndex": "SportsAndOutdoors"},
                {"nombre": "Deportes al Aire Libre",   "id": "9482644011", "searchIndex": "SportsAndOutdoors"},
                {"nombre": "Ciclismo",                 "id": "9482646011", "searchIndex": "SportsAndOutdoors"},
                {"nombre": "Ropa Deportiva",           "id": "9482648011", "searchIndex": "SportsAndOutdoors"},
                {"nombre": "Camping y Senderismo",     "id": "9482652011", "searchIndex": "SportsAndOutdoors"},
            ],
            "Juguetes y Juegos": [
                {"nombre": "Juegos de Mesa",        "id": "9482660011", "searchIndex": "ToysAndGames"},
                {"nombre": "Figuras de Acción",     "id": "9482662011", "searchIndex": "ToysAndGames"},
                {"nombre": "Juguetes Educativos",   "id": "9482664011", "searchIndex": "ToysAndGames"},
                {"nombre": "Muñecas y Accesorios",  "id": "9482666011", "searchIndex": "ToysAndGames"},
                {"nombre": "LEGO y Construcción",   "id": "9482668011", "searchIndex": "ToysAndGames"},
                {"nombre": "Vehículos de Juguete",  "id": "9482670011", "searchIndex": "ToysAndGames"},
                {"nombre": "Juegos al Aire Libre",  "id": "9482672011", "searchIndex": "ToysAndGames"},
                {"nombre": "Coleccionables",        "id": "9482676011", "searchIndex": "ToysAndGames"},
            ],
            "Belleza": [
                {"nombre": "Cuidado del Cabello",   "id": "9482690011", "searchIndex": "HealthPersonalCare"},
                {"nombre": "Maquillaje",            "id": "9482692011", "searchIndex": "HealthPersonalCare"},
                {"nombre": "Perfumes",              "id": "9482694011", "searchIndex": "HealthPersonalCare"},
                {"nombre": "Cuidado de la Piel",   "id": "9482696011", "searchIndex": "HealthPersonalCare"},
                {"nombre": "Afeitado y Depilación", "id": "9482698011", "searchIndex": "HealthPersonalCare"},
            ],
            "Salud y Cuidado Personal": [
                {"nombre": "Salud y Bienestar",    "id": "9482700011", "searchIndex": "HealthPersonalCare"},
                {"nombre": "Cuidado del Cabello",  "id": "9482690011", "searchIndex": "HealthPersonalCare"},
                {"nombre": "Vitaminas y Suplementos","id": None,       "searchIndex": "HealthPersonalCare"},
            ],
            "Herramientas y Mejoras del Hogar": [
                {"nombre": "Herramientas Eléctricas",       "id": "9482740011", "searchIndex": "ToolsAndHomeImprovement"},
                {"nombre": "Herramientas Manuales",         "id": "9482742011", "searchIndex": "ToolsAndHomeImprovement"},
                {"nombre": "Materiales de Construcción",    "id": "9482744011", "searchIndex": "ToolsAndHomeImprovement"},
                {"nombre": "Plomería",                      "id": "9482746011", "searchIndex": "ToolsAndHomeImprovement"},
                {"nombre": "Seguridad del Hogar",           "id": "9482748011", "searchIndex": "ToolsAndHomeImprovement"},
            ],
            "Ropa, Zapatos y Accesorios": [
                {"nombre": "Ropa Hombre",       "id": "9482710011", "searchIndex": "FashionMen"},
                {"nombre": "Ropa Mujer",        "id": "9482720011", "searchIndex": "FashionWomen"},
                {"nombre": "Calzado Hombre",    "id": "9482716011", "searchIndex": "FashionMen"},
                {"nombre": "Calzado Mujer",     "id": "9482726011", "searchIndex": "FashionWomen"},
                {"nombre": "Bolsas y Carteras", "id": "9482728011", "searchIndex": "FashionWomen"},
                {"nombre": "Joyería",           "id": "9482730011", "searchIndex": "FashionWomen"},
                {"nombre": "Ropa Niños",        "id": None,         "searchIndex": "FashionBoys"},
                {"nombre": "Ropa Niñas",        "id": None,         "searchIndex": "FashionGirls"},
                {"nombre": "Ropa Bebé",         "id": None,         "searchIndex": "FashionBaby"},
            ],
            "Productos para Animales": [
                {"nombre": "Perros",               "id": "9482760011", "searchIndex": "PetSupplies"},
                {"nombre": "Gatos",                "id": "9482762011", "searchIndex": "PetSupplies"},
                {"nombre": "Aves",                 "id": "9482764011", "searchIndex": "PetSupplies"},
                {"nombre": "Peces y Acuarios",     "id": "9482766011", "searchIndex": "PetSupplies"},
                {"nombre": "Alimento Mascotas",    "id": "9482768011", "searchIndex": "PetSupplies"},
            ],
            "Automotriz y Motocicletas": [
                {"nombre": "Accesorios para Auto", "id": "9482780011", "searchIndex": "Automotive"},
                {"nombre": "Audio para Auto",      "id": "9482782011", "searchIndex": "Automotive"},
                {"nombre": "Herramientas Auto",    "id": "9482784011", "searchIndex": "Automotive"},
                {"nombre": "GPS y Navegación",     "id": "9482786011", "searchIndex": "Automotive"},
                {"nombre": "Motos y Scooters",     "id": "9482788011", "searchIndex": "Automotive"},
            ],
            "Libros": [
                {"nombre": "Libros en Español",    "id": "9482800011", "searchIndex": "Books"},
                {"nombre": "Manga y Cómic",        "id": "9482802011", "searchIndex": "Books"},
                {"nombre": "Libros Infantiles",    "id": "9482804011", "searchIndex": "Books"},
                {"nombre": "Negocios y Finanzas",  "id": "9482806011", "searchIndex": "Books"},
                {"nombre": "Cocina y Gastronomía", "id": "9482808011", "searchIndex": "Books"},
            ],
            "Tienda Kindle": [
                {"nombre": "eBooks Kindle", "id": None, "searchIndex": "KindleStore"},
            ],
            "Videojuegos": [
                {"nombre": "Consolas",                    "id": "9482570011", "searchIndex": "VideoGames"},
                {"nombre": "Juegos para Consola",         "id": "9482572011", "searchIndex": "VideoGames"},
                {"nombre": "Accesorios para Videojuegos", "id": "9482574011", "searchIndex": "VideoGames"},
                {"nombre": "Juegos para PC",              "id": "9482576011", "searchIndex": "VideoGames"},
            ],
            "Oficina y Papelería": [
                {"nombre": "Material de Oficina",  "id": "9482820011", "searchIndex": "OfficeProducts"},
                {"nombre": "Impresión y Copiado",  "id": "9482822011", "searchIndex": "OfficeProducts"},
                {"nombre": "Mobiliario de Oficina","id": "9482824011", "searchIndex": "OfficeProducts"},
            ],
            "Alimentos y Bebidas": [
                {"nombre": "Snacks y Botanas", "id": "9482840011", "searchIndex": "GroceryAndGourmetFood"},
                {"nombre": "Bebidas",          "id": "9482842011", "searchIndex": "GroceryAndGourmetFood"},
                {"nombre": "Café y Té",        "id": "9482844011", "searchIndex": "GroceryAndGourmetFood"},
                {"nombre": "Suplementos",      "id": "9482846011", "searchIndex": "GroceryAndGourmetFood"},
            ],
            "Bebé": [
                {"nombre": "Carriolas y Cochecitos","id": "9482850011", "searchIndex": "Baby"},
                {"nombre": "Ropa de Bebé",         "id": "9482852011", "searchIndex": "Baby"},
                {"nombre": "Juguetes para Bebé",   "id": "9482854011", "searchIndex": "Baby"},
                {"nombre": "Alimentación del Bebé","id": "9482856011", "searchIndex": "Baby"},
                {"nombre": "Seguridad del Bebé",   "id": "9482858011", "searchIndex": "Baby"},
            ],
            "Relojes": [
                {"nombre": "Relojes para Hombre",  "id": "9482860011", "searchIndex": "Watches"},
                {"nombre": "Relojes para Mujer",   "id": "9482862011", "searchIndex": "Watches"},
                {"nombre": "Relojes Inteligentes", "id": "9482864011", "searchIndex": "Watches"},
            ],
            "Instrumentos Musicales": [
                {"nombre": "Guitarras",           "id": "9482870011", "searchIndex": "MusicalInstruments"},
                {"nombre": "Teclados y Pianos",   "id": "9482872011", "searchIndex": "MusicalInstruments"},
                {"nombre": "Percusión",           "id": "9482874011", "searchIndex": "MusicalInstruments"},
                {"nombre": "Accesorios Musicales","id": "9482876011", "searchIndex": "MusicalInstruments"},
            ],
            "Música":                [{"nombre": "Música Digital",       "id": None, "searchIndex": "Music"}],
            "Películas y Series de TV": [
                {"nombre": "Películas",     "id": None, "searchIndex": "MoviesAndTV"},
                {"nombre": "Series de TV",  "id": None, "searchIndex": "MoviesAndTV"},
            ],
            "Software":              [{"nombre": "Software",             "id": None, "searchIndex": "Software"}],
            "Productos Handmade":    [{"nombre": "Manualidades",         "id": None, "searchIndex": "Handmade"},
                                      {"nombre": "Arte y Pintura",       "id": None, "searchIndex": "Handmade"}],
            "Industria, Empresas y Ciencia": [
                {"nombre": "Equipos Industriales",  "id": None, "searchIndex": "IndustrialAndScientific"},
                {"nombre": "Seguridad Industrial",  "id": None, "searchIndex": "IndustrialAndScientific"},
                {"nombre": "Ciencia y Laboratorio", "id": None, "searchIndex": "IndustrialAndScientific"},
            ],
        }

        if path == "/" or path == "/superseller.html":
            try:
                with open(os.path.join(BASE_DIR, "superseller.html"), "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

        elif path == "/ping":
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "msg": "Servidor activo"}).encode())

        elif path == "/subcategorias":
            cat = params.get("cat", [""])[0]
            subs = SUBCATS_POR_CAT.get(cat, [])
            print(f"📂 /subcategorias?cat={cat} → {len(subs)}", flush=True)
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "subcategorias": subs}).encode())

        elif path == "/todas_subcategorias":
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "todas": SUBCATS_POR_CAT}).encode())

        elif path == "/historial":
            try:
                if not _HV_OK:
                    raise ImportError("historial_variedad no disponible")
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, **_hv.stats()}).encode())
            except Exception as e:
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif path == "/nodos":
            try:
                token = get_token()
                hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "x-marketplace": "www.amazon.com.mx"}
                body = {"partnerTag": CREDS["partner_tag"], "marketplace": "www.amazon.com.mx", "browseNodeIds": ["9482085011"], "resources": ["browseNodes.children", "browseNodes.displayName"]}
                r = requests.post("https://creatorsapi.amazon/catalog/v1/getBrowseNodes", headers=hdrs, json=body, timeout=15)
                data = r.json() if r.status_code == 200 else {"error": r.text}
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "nodos": data}).encode())
            except Exception as e:
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        else:
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "msg": "Servidor activo"}).encode())

    def log_message(self, format, *args):
        pass  # Suprimir logs de HTTP

class _Servidor(HTTPServer):
    """HTTPServer que suprime BrokenPipeError (cliente cierra conexión antes de recibir respuesta)."""
    def handle_error(self, request, client_address):
        exc = _sys.exc_info()[1]
        if isinstance(exc, BrokenPipeError):
            print("⚠️  Cliente desconectado — respuesta descartada (BrokenPipe)", flush=True)
        else:
            super().handle_error(request, client_address)


if __name__ == "__main__":
    port = 8765
    print(f"\n⚡ Superseller Servidor corriendo en http://localhost:{port}")
    print(f"   👉 Abre en Chrome: http://localhost:{port}")
    print("   Ctrl+C para detener\n")
    _Servidor(("localhost", port), Handler).serve_forever()
