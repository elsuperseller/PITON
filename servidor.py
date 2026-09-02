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
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Sistema de jobs en background
import threading
import uuid
JOBS_BACKGROUND = {}  # {job_id: {"status": "processing|completed|error", "progreso": {...}, "resultados": [...]}}

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

def buscar(search_index, pagina=1, sort_by="NewestArrivals", browse_node_id=None, min_saving=1, precio_min=0, precio_max=0, keywords="a"):
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
        "itemCount": 15,  # Aumentado de 10 a 15 (15×2 páginas = 30 productos/keyword)
        "itemPage": pagina,
        "sortBy": sort_by,
        "keywords": keywords,
        "minSavingPercent": min_saving,
        "condition": "New",
        "availability": "Available",
        "languagesOfPreference": ["es_MX"],
        "currencyOfPreference": "MXN",
        "resources": [
            "itemInfo.title", "itemInfo.externalIds", "images.primary.medium",
            "offersV2.listings.price", "offersV2.listings.dealDetails",
            "offersV2.listings.isBuyBoxWinner", "offersV2.listings.type",
            "offersV2.listings.availability",
            "browseNodeInfo.browseNodes"
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
        # EAN para detección cross-platform
        ext  = item.get("itemInfo", {}).get("externalIds", {})
        eans = ext.get("eans", {}).get("displayValues", [])
        ean  = eans[0] if eans else ""
        return {
            "asin": asin, "link": link, "title": title, "img": img,
            "price_original": po, "price_discounted": pd_, "descuento_pct": desc,
            "vigencia": vigencia, "tipo": tipo, "badge": badge, "access_type": acc,
            "start_time": start, "end_time": end, "pct_claimed": deal.get("percentageClaimed"),
            "ean": ean,
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

# ==================== FEEDS POR AUDIENCIA ====================

def cargar_perfiles():
    """Carga perfiles de audiencia desde JSON"""
    ruta = os.path.join(BASE_DIR, 'feeds', 'perfiles_audiencia.json')
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Error cargando perfiles: {e}", flush=True)
        return {}

def cargar_feed_cache():
    """Carga cache de feeds"""
    ruta = os.path.join(BASE_DIR, 'feeds', 'feeds_cache.json')
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def guardar_feed_cache(cache):
    """Guarda cache de feeds"""
    ruta = os.path.join(BASE_DIR, 'feeds', 'feeds_cache.json')
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def cargar_historial_feed(feed_id):
    """Carga historial específico de un feed"""
    ruta = os.path.join(BASE_DIR, 'feeds', feed_id, 'historial.json')
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def guardar_historial_feed(feed_id, historial):
    """Guarda historial específico de un feed"""
    ruta = os.path.join(BASE_DIR, 'feeds', feed_id, 'historial.json')
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(historial, f, indent=2, ensure_ascii=False)

def cargar_keyword_stats(feed_id):
    """Carga estadísticas de keywords de un feed"""
    ruta = os.path.join(BASE_DIR, 'feeds', feed_id, 'keyword_stats.json')
    if os.path.exists(ruta):
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_keyword_stats(feed_id, stats):
    """Guarda estadísticas de keywords de un feed"""
    ruta = os.path.join(BASE_DIR, 'feeds', feed_id, 'keyword_stats.json')
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

def get_keywords_originales():
    """Retorna el set de keywords originales que NUNCA se eliminan"""
    return {
        "Funko Pop", "Funko", "Hot Toys", "Bandai", "Banpresto", "Hasbro",
        "McFarlane", "NECA", "Good Smile", "Kotobukiya", "Square Enix",
        "Mattel", "LEGO", "Sideshow", "Iron Studios", "Diamond Select",
        "Jada Toys", "Jazwares", "Medicom", "Beast Kingdom",
        "Marvel Legends", "Marvel", "DC Multiverse", "DC Comics",
        "Batman", "Superman", "Spider-Man", "Avengers", "X-Men",
        "Deadpool", "Venom",
        "Dragon Ball", "Dragon Ball Z", "Dragon Ball Super",
        "One Piece", "Naruto", "Demon Slayer", "Kimetsu no Yaiba",
        "Jujutsu Kaisen", "My Hero Academia", "Attack on Titan",
        "Pokemon", "Digimon", "Sailor Moon", "Gundam",
        "Star Wars", "Harry Potter", "Lord of the Rings",
        "Transformers", "G.I. Joe", "Teenage Mutant Ninja Turtles",
        "Power Rangers", "Spawn", "The Walking Dead", "Fortnite",
        "Halo", "Minecraft", "Disney", "Pixar", "Hello Kitty",
        "Godzilla", "King Kong"
    }

def aplicar_limite_keywords(feed_id, perfil, limite=200):
    """
    Aplica límite de keywords manteniendo las mejores por score.

    Lógica:
    - Keywords originales: SIEMPRE protegidas
    - Keywords aprendidas: ordenadas por score, mantener solo las mejores
    """
    keywords_actuales = perfil.get('keywords', [])

    if len(keywords_actuales) <= limite:
        return perfil  # No hay nada que hacer

    # Cargar stats
    stats = cargar_keyword_stats(feed_id)
    keywords_originales = get_keywords_originales()

    # Separar keywords
    kw_protegidas = []
    kw_aprendidas = []

    for kw in keywords_actuales:
        if kw in keywords_originales:
            kw_protegidas.append(kw)
        else:
            kw_aprendidas.append(kw)

    # Si después de proteger las originales aún excedemos, eliminar aprendidas por score
    espacio_disponible = limite - len(kw_protegidas)

    if len(kw_aprendidas) > espacio_disponible:
        # Ordenar aprendidas por score (descendente)
        kw_aprendidas_con_score = [
            (kw, stats.get(kw, {}).get('score', 0))
            for kw in kw_aprendidas
        ]
        kw_aprendidas_con_score.sort(key=lambda x: x[1], reverse=True)

        # Mantener solo las mejores
        kw_aprendidas_mantener = [kw for kw, score in kw_aprendidas_con_score[:espacio_disponible]]
        kw_eliminadas = [kw for kw, score in kw_aprendidas_con_score[espacio_disponible:]]

        print(f"  🧹 Límite de {limite} keywords alcanzado: eliminando {len(kw_eliminadas)} keywords con menor score", flush=True)

        # Mostrar ejemplos de eliminadas
        if kw_eliminadas:
            ejemplos_eliminadas = kw_eliminadas[:5]
            if len(kw_eliminadas) > 5:
                print(f"     Ejemplos eliminados: {', '.join(ejemplos_eliminadas)}... (+{len(kw_eliminadas)-5} más)", flush=True)
            else:
                print(f"     Eliminados: {', '.join(ejemplos_eliminadas)}", flush=True)

        # Actualizar perfil
        perfil['keywords'] = sorted(kw_protegidas + kw_aprendidas_mantener)

    return perfil

def esta_bloqueado(feed_id, asin):
    """Verifica si un ASIN fue descartado manualmente por el usuario"""
    historial = cargar_historial_feed(feed_id)
    return historial.get(asin, {}).get("blocked", False)

def marcar_asins_vistos(feed_id, asins_o_items):
    """
    Marca ASINs como ya vistos en el historial del feed.
    Acepta lista de ASINs (strings) o lista de items (dicts con asin y title).
    """
    from datetime import datetime
    historial = cargar_historial_feed(feed_id)
    timestamp = datetime.now().isoformat()

    # Determinar si son ASINs simples o items completos
    if not asins_o_items:
        return 0

    es_dict = isinstance(asins_o_items[0], dict)

    for item in asins_o_items:
        if es_dict:
            asin = item.get('asin', '')
            title = item.get('title', '')
        else:
            asin = item
            title = ''

        if not asin:
            continue

        if asin not in historial:
            historial[asin] = {
                "primera_vez": timestamp,
                "ultima_vez": timestamp,
                "veces_visto": 1
            }
            if title:
                historial[asin]["title"] = title
        else:
            historial[asin]["ultima_vez"] = timestamp
            historial[asin]["veces_visto"] = historial[asin].get("veces_visto", 0) + 1
            # Actualizar título si está disponible y no existía antes
            if title and not historial[asin].get("title"):
                historial[asin]["title"] = title

    guardar_historial_feed(feed_id, historial)
    return len(asins_o_items)

def aplicar_novedad_score_feed(items, feed_id):
    """
    Aplica novedad_score a items basándose en el historial del feed específico.
    1.0  — nunca visto
    0.8  — publicado hace >14 días
    0.5  — publicado hace 7-14 días
    0.2  — publicado hace 3-7 días
    0.0  — publicado hace <3 días o bloqueado
    """
    from datetime import datetime, timezone

    historial_feed = cargar_historial_feed(feed_id)
    now = datetime.now(timezone.utc)

    for producto in items:
        asin = producto.get('asin') or producto.get('id', '')

        if not asin:
            producto['novedad_score'] = 1.0
            continue

        # Verificar si está bloqueado
        if historial_feed.get(asin, {}).get('blocked', False):
            producto['novedad_score'] = 0.0
            producto['blocked'] = True
            continue

        # Verificar si ya fue visto
        if asin in historial_feed:
            registro = historial_feed[asin]
            ultima_vez = registro.get('ultima_vez', '')

            try:
                ultima_fecha = datetime.fromisoformat(ultima_vez.replace('Z', '+00:00'))
                if ultima_fecha.tzinfo is None:
                    ultima_fecha = ultima_fecha.replace(tzinfo=timezone.utc)
                dias = (now - ultima_fecha).days

                # Scoring de novedad
                if dias >= 14:
                    score = 0.8
                elif dias >= 7:
                    score = 0.5
                elif dias >= 3:
                    score = 0.2
                else:
                    score = 0.0

                producto['novedad_score'] = score
            except:
                producto['novedad_score'] = 0.5
        else:
            producto['novedad_score'] = 1.0

    # Ordenar por novedad_score (mayor a menor)
    items.sort(key=lambda p: p.get('novedad_score', 1.0), reverse=True)
    return items

def extraer_precio(item):
    """Extrae precio con descuento de un item de Amazon"""
    try:
        listings = item.get("offersV2", {}).get("listings", [])
        if not listings:
            return None
        lst = next((l for l in listings if l.get("isBuyBoxWinner")), listings[0])
        price_info = lst.get("price", {})
        amount = price_info.get("money", {}).get("amount")
        if amount:
            return float(amount)
        return None
    except:
        return None

def extraer_descuento(item):
    """Extrae porcentaje de descuento de un item (calculado desde precio original)"""
    try:
        listings = item.get("offersV2", {}).get("listings", [])
        if not listings:
            return 0
        lst = next((l for l in listings if l.get("isBuyBoxWinner")), listings[0])

        # Obtener precio actual
        pi = lst.get("price", {})
        pd = pi.get("money", {}).get("amount")
        if not pd:
            return 0
        pd = float(pd)

        # Obtener precio original
        sb = pi.get("savingBasis", {})
        sv = pi.get("savings", {})
        if sb and sb.get("money", {}).get("amount"):
            po = float(sb["money"]["amount"])
        elif sv and sv.get("money", {}).get("amount"):
            po = pd + float(sv["money"]["amount"])
        else:
            return 0

        # Calcular porcentaje
        desc = round((po - pd) / po * 100) if po > pd else 0
        return int(desc)
    except:
        return 0

def buscar_productos_amazon(keyword, minSavingPercent=10, maxPages=5):
    """Busca productos en Amazon usando la función buscar existente"""
    productos = []
    for pagina in range(1, maxPages + 1):
        try:
            # Usar la función buscar existente con keyword específico
            items = buscar(
                search_index="All",
                pagina=pagina,
                sort_by="NewestArrivals",
                min_saving=minSavingPercent,
                keywords=keyword
            )
            # Agregar todos los items encontrados (la API ya filtró por keyword)
            productos.extend(items)
            time.sleep(0.3)  # Rate limiting
        except Exception as e:
            print(f"⚠️  Error buscando '{keyword}' página {pagina}: {e}", flush=True)
            break
    return productos

def es_categoria_coleccionable(item):
    """
    Verifica si un producto pertenece a categorías de coleccionables/juguetes
    basándose en sus browseNodes de Amazon
    """
    try:
        browse_nodes = item.get("browseNodeInfo", {}).get("browseNodes", [])
        if not browse_nodes:
            return True  # Si no hay info, dejarlo pasar (benefit of doubt)

        # IDs de nodos de categorías de coleccionables/juguetes en Amazon MX
        # Estos son los nodos de Toys, Collectibles, VideoGames, etc.
        NODOS_COLECCIONABLES = [
            "11260443011",  # Action Figures & Statues
            "20940159011",  # Collectibles
            "9482591011",   # Toys & Games
            "9482600011",   # Video Games
            "9482593011",   # Building Toys (LEGO)
            "9482595011",   # Dolls & Accessories
            "9482597011",   # Games
            "9482599011",   # Stuffed Animals & Plush
        ]

        # Verificar si algún nodo del producto coincide con categorías coleccionables
        for node in browse_nodes:
            node_id = node.get("id", "")
            # Verificar coincidencia exacta o si el producto está en subcategorías
            if any(nodo_col in node_id for nodo_col in NODOS_COLECCIONABLES):
                return True

        # Si llegamos aquí, el producto NO está en categorías de coleccionables
        return False
    except:
        return True  # En caso de error, dejarlo pasar

def extraer_keywords_inteligentes(titulo):
    """
    Extrae SOLO el NÚCLEO: personajes, franquicias, marcas.
    NO extrae tipos de producto (reloj, camisa, figura, etc.)

    Ejemplo:
    - "Reloj Yoshi Nintendo" → ["Yoshi", "Nintendo"]
    - "Figura Dragon Ball Z Goku" → ["Dragon Ball Z", "Goku"]

    Retorna: lista de keywords núcleo (máximo 3)
    """
    import re

    # Stopwords
    STOPWORDS = {
        'the', 'and', 'for', 'with', 'from', 'that', 'this', 'have',
        'para', 'con', 'de', 'la', 'el', 'en', 'y', 'of', 'to', 'in', 'a', 'an'
    }

    # TIPOS DE PRODUCTO - Filtrar estas palabras (NO son el núcleo)
    TIPOS_PRODUCTO = {
        # Productos físicos
        'figura', 'figure', 'statue', 'estatua', 'toy', 'juguete',
        'reloj', 'watch', 'camisa', 'shirt', 'playera', 'camiseta',
        'libro', 'book', 'comic', 'manga', 'album', 'poster',
        'funko', 'pop', 'plush', 'peluche', 'mug', 'taza',
        'card', 'carta', 'game', 'juego', 'videojuego',
        'model', 'modelo', 'kit', 'set', 'pack', 'collection',
        'collectible', 'coleccionable', 'merchandise',
        # Descriptores
        'deluxe', 'premium', 'special', 'limited', 'exclusive',
        'edition', 'edicion', 'version', 'series', 'vol', 'volume',
        'new', 'nuevo', 'original', 'official', 'oficial',
        'mini', 'mega', 'super', 'ultra', 'giant', 'large', 'small',
        # Números
        'one', 'two', 'three', 'four', 'five', 'first', 'second',
        'piece', 'pieces', 'pcs', 'cm', 'inch', 'pulgadas'
    }

    # MARCAS reconocidas (pueden ser keywords pero de baja prioridad)
    MARCAS = {
        'bandai', 'hasbro', 'mattel', 'lego', 'neca', 'mcfarlane',
        'good smile', 'kotobukiya', 'square enix', 'sideshow',
        'hot toys', 'diamond select', 'jada', 'jazwares', 'medicom',
        'beast kingdom', 'iron studios', 'banpresto'
    }

    # Limpiar título
    titulo_lower = titulo.lower()
    titulo_clean = re.sub(r'[^\w\s]', ' ', titulo_lower)
    palabras = titulo_clean.split()

    # Filtrar stopwords y tipos de producto
    palabras_filtradas = [
        p for p in palabras
        if p not in STOPWORDS
        and p not in TIPOS_PRODUCTO
        and len(p) > 2
        and not p.isdigit()
    ]

    keywords_extraidas = []

    # 1. Buscar franquicias compuestas conocidas (bigramas/trigramas)
    FRANQUICIAS_COMPUESTAS = [
        'dragon ball z', 'dragon ball super', 'dragon ball',
        'one piece', 'my hero academia', 'demon slayer',
        'star wars', 'harry potter', 'lord of the rings',
        'teenage mutant ninja turtles', 'power rangers',
        'marvel legends', 'dc multiverse', 'dc comics',
        'jujutsu kaisen', 'attack on titan', 'sailor moon',
        'the walking dead'
    ]

    for franquicia in FRANQUICIAS_COMPUESTAS:
        if franquicia in titulo_lower:
            keywords_extraidas.append(franquicia.title())

    # 2. Extraer nombres propios (primera letra mayúscula en título original)
    # Buscar palabras que empiezan con mayúscula (probable personaje/franquicia)
    palabras_originales = re.findall(r'\b[A-Z][a-z]+\b', titulo)
    for palabra in palabras_originales:
        palabra_lower = palabra.lower()
        if (palabra_lower not in TIPOS_PRODUCTO
            and palabra_lower not in STOPWORDS
            and len(palabra_lower) > 3):
            keywords_extraidas.append(palabra)

    # 3. Si no encontramos nombres propios, buscar palabras largas únicas (≥6 chars)
    if not keywords_extraidas:
        for palabra in palabras_filtradas:
            if len(palabra) >= 6 and palabra not in MARCAS:
                keywords_extraidas.append(palabra.title())

    # Deduplicar (case-insensitive)
    keywords_unicas = []
    vistos = set()
    for kw in keywords_extraidas:
        kw_lower = kw.lower()
        if kw_lower not in vistos:
            keywords_unicas.append(kw)
            vistos.add(kw_lower)

    # Retornar máximo 3 keywords núcleo
    return keywords_unicas[:3]

def evaluar_exclusion_contextual(titulo, perfil, es_url_fija=False):
    """
    Evalúa si un producto debe excluirse considerando el contexto completo.

    Retorna: (debe_excluir: bool, razon: str)

    Lógica:
    - Si viene de URL fija (Best Sellers, etc.) y es de marca premium → NO excluir
    - Si tiene múltiples keywords positivas → Alta tolerancia a excludeKeywords
    - Solo excluir si las palabras negativas son claramente problemáticas
    """
    titulo_lower = titulo.lower()

    # Marcas premium que tienen prioridad (no se excluyen fácilmente)
    MARCAS_PREMIUM = {
        'hot toys', 'bandai', 'hasbro', 'funko', 'mcfarlane', 'neca',
        'good smile', 'kotobukiya', 'square enix', 'mattel', 'lego',
        'sideshow', 'prime 1', 'iron studios', 'tweeterhead', 'medicom'
    }

    # Franquicias/keywords positivas importantes
    FRANQUICIAS_IMPORTANTES = {
        'marvel', 'dc comics', 'dc', 'star wars', 'pokemon', 'dragon ball',
        'naruto', 'one piece', 'anime', 'disney', 'pixar', 'transformers',
        'spawn', 'batman', 'superman', 'spider-man', 'iron man', 'deadpool'
    }

    # Verificar si es de marca premium
    es_marca_premium = any(marca in titulo_lower for marca in MARCAS_PREMIUM)

    # Contar keywords positivas presentes
    keywords_positivas = perfil.get('keywords', [])
    keywords_presentes = sum(1 for kw in keywords_positivas if kw.lower() in titulo_lower)

    # Contar franquicias importantes
    franquicias_presentes = sum(1 for franq in FRANQUICIAS_IMPORTANTES if franq in titulo_lower)

    # Calcular "confianza" del producto (0-100)
    confianza = 0
    if es_url_fija:
        confianza += 30  # URL fija da +30 puntos
    if es_marca_premium:
        confianza += 40  # Marca premium da +40 puntos
    confianza += min(keywords_presentes * 10, 30)  # Hasta +30 por keywords
    confianza += min(franquicias_presentes * 10, 20)  # Hasta +20 por franquicias

    # Obtener excludeKeywords
    exclude_keywords = perfil.get('filtros', {}).get('excludeKeywords', [])

    # Buscar palabras excluidas presentes
    palabras_excluidas_encontradas = [
        ex for ex in exclude_keywords
        if ex.lower() in titulo_lower
    ]

    if not palabras_excluidas_encontradas:
        return False, ""  # No hay palabras excluidas, no excluir

    # Si tiene alta confianza (≥60), solo excluir por palabras MUY problemáticas
    PALABRAS_MUY_PROBLEMATICAS = {
        'pirata', 'replica', 'bootleg', 'fake', 'copia', 'imitacion',
        'usado', 'dañado', 'roto', 'defecto', 'segunda mano'
    }

    palabras_muy_problematicas_encontradas = [
        p for p in palabras_excluidas_encontradas
        if p.lower() in PALABRAS_MUY_PROBLEMATICAS
    ]

    if confianza >= 60:
        # Alta confianza: solo excluir si tiene palabras MUY problemáticas
        if palabras_muy_problematicas_encontradas:
            return True, f"Palabra crítica: {palabras_muy_problematicas_encontradas[0]}"
        else:
            # Tiene palabras excluidas pero el contexto es bueno
            return False, ""

    elif confianza >= 40:
        # Confianza media: tolerancia moderada
        # Excluir solo si tiene 2+ palabras excluidas o 1 muy problemática
        if palabras_muy_problematicas_encontradas:
            return True, f"Palabra crítica: {palabras_muy_problematicas_encontradas[0]}"
        elif len(palabras_excluidas_encontradas) >= 2:
            return True, f"Múltiples keywords excluidas: {', '.join(palabras_excluidas_encontradas[:2])}"
        else:
            return False, ""

    else:
        # Baja confianza: aplicar excludeKeywords normalmente
        return True, f"Keyword excluida: {palabras_excluidas_encontradas[0]}"

def _procesar_urls_completo(job_id, urls, pages, min_discount, feed_id=""):
    """Procesa URLs y actualiza el progreso en JOBS_BACKGROUND[job_id]"""
    job = JOBS_BACKGROUND[job_id]

    try:
        # Fase 1: Scraping
        job["progreso"]["fase"] = "scraping"
        _ZG = ("/gp/movers-and-shakers/", "/gp/bestsellers/", "/gp/new-releases/", "/zgbs/")
        zg_urls   = [u for u in urls if any(p in u for p in _ZG)]
        rest_urls = [u for u in urls if not any(p in u for p in _ZG)]

        all_asins, vistos = [], set()

        # Ranking ZG
        if zg_urls:
            print(f"  📊 Batch ranking: {len(zg_urls)} URL(s) en 1 browser", flush=True)
            asins, _ = _az.scrape_zg_batch(zg_urls, pages=1, per_url_limit=50)
            for a in asins:
                if a not in vistos:
                    vistos.add(a); all_asins.append(a)
            job["progreso"]["urls_procesadas"] += len(zg_urls)

        # Resto de URLs
        for i, url in enumerate(rest_urls, 1):
            asins, _ = _az.scrape_url_custom(url, pages=pages)
            for a in asins:
                if a not in vistos:
                    vistos.add(a); all_asins.append(a)
            job["progreso"]["urls_procesadas"] += 1

        job["progreso"]["asins_extraidos"] = len(all_asins)
        print(f"  → {len(all_asins)} ASINs únicos, enriqueciendo…", flush=True)

        if not all_asins:
            job["status"] = "completed"
            job["resultados"] = {"ok": True, "items": [], "total": 0}
            return

        # Fase 2: Enriquecimiento
        job["progreso"]["fase"] = "enriquecimiento"
        token = get_token()
        api_headers = {"Authorization": f"Bearer {token}",
                       "Content-Type": "application/json",
                       "x-marketplace": "www.amazon.com.mx"}

        _RECURSOS = ["itemInfo.title", "itemInfo.externalIds", "images.primary.medium",
                     "offersV2.listings.price", "offersV2.listings.dealDetails",
                     "offersV2.listings.isBuyBoxWinner"]
        _stats = {"ok": 0, "no200": 0, "empty": 0, "no_listing": 0, "err": 0}

        def _enriquecer_batch(batch):
            try:
                r = requests.post(
                    "https://creatorsapi.amazon/catalog/v1/getItems",
                    headers=api_headers,
                    json={"partnerTag": CREDS["partner_tag"],
                          "marketplace": "www.amazon.com.mx",
                          "itemIds": batch,
                          "languagesOfPreference": ["es_MX"],
                          "currencyOfPreference": "MXN",
                          "resources": _RECURSOS},
                    timeout=60  # Aumentado de 20 a 60 segundos
                )
                if r.status_code != 200:
                    _stats["no200"] += len(batch)
                    if r.status_code in (429, 500, 502, 503):
                        time.sleep(3.0)
                        r2 = requests.post(
                            "https://creatorsapi.amazon/catalog/v1/getItems",
                            headers=api_headers,
                            json={"partnerTag": CREDS["partner_tag"],
                                  "marketplace": "www.amazon.com.mx",
                                  "itemIds": batch,
                                  "languagesOfPreference": ["es_MX"],
                                  "currencyOfPreference": "MXN",
                                  "resources": _RECURSOS},
                            timeout=60
                        )
                        if r2.status_code != 200:
                            return []
                        r = r2
                    else:
                        return []
                items = r.json().get("itemsResult", {}).get("items", [])
                if not items:
                    _stats["empty"] += len(batch)
                    return []
                resultados_batch = []
                for item in items:
                    p = parsear_item(item)
                    if p is None:
                        _stats["no_listing"] += 1
                    else:
                        _stats["ok"] += 1
                        if p["descuento_pct"] >= min_discount:
                            resultados_batch.append(p)
                return resultados_batch
            except Exception as e:
                _stats["err"] += len(batch)
                return []

        batches = [all_asins[i:i+10] for i in range(0, len(all_asins), 10)]
        job["progreso"]["batches_total"] = len(batches)
        print(f"  📦 {len(all_asins)} ASINs → {len(batches)} batches vía getItems", flush=True)

        resultados = []
        completados = 0
        with ThreadPoolExecutor(max_workers=5) as pool:
            futuros = {pool.submit(_enriquecer_batch, b): b for b in batches}
            for fut in as_completed(futuros):
                completados += 1
                resultados.extend(fut.result())
                job["progreso"]["batches_completados"] = completados
                job["progreso"]["productos_ok"] = _stats['ok']
                if completados % 20 == 0:
                    print(f"  ⏳ {completados}/{len(batches)} | ok={_stats['ok']} no200={_stats['no200']}", flush=True)

        print(f"  📊 Final: ok={_stats['ok']} no200={_stats['no200']} sin_listing={_stats['no_listing']}", flush=True)

        # Fase 3: Deduplicación e historial
        job["progreso"]["fase"] = "finalizando"
        seen, unicos = set(), []
        for p in resultados:
            if p["asin"] not in seen:
                seen.add(p["asin"])
                unicos.append(p)

        if _HV_OK:
            if feed_id:
                unicos = aplicar_novedad_score_feed(unicos, feed_id)
                print(f"  📚 Historial del feed '{feed_id}': {sum(1 for i in unicos if i.get('novedad_score',1)<1.0)} ya vistos", flush=True)
            else:
                unicos = _hv.aplicar_scores(unicos)
                print(f"  📚 Historial global aplicado: {sum(1 for i in unicos if i.get('novedad_score',1)<1.0)} ya vistos", flush=True)

        job["status"] = "completed"
        job["resultados"] = {"ok": True, "items": unicos, "total": len(unicos), "asins": len(all_asins)}

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        print(f"❌ Job {job_id} error: {e}", flush=True)

def enriquecer_asins(asins, minSavingPercent=1):
    """Enriquece ASINs usando Creators API getItems en batches de 10"""
    if not asins:
        return []

    token = get_token()
    api_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-marketplace": "www.amazon.com.mx"
    }
    _RECURSOS = ["itemInfo.title", "itemInfo.externalIds", "images.primary.medium",
                 "offersV2.listings.price", "offersV2.listings.dealDetails",
                 "offersV2.listings.isBuyBoxWinner", "offersV2.listings.type",
                 "offersV2.listings.availability",
                 "browseNodeInfo.browseNodes"]

    def _enriquecer_batch(batch):
        try:
            r = requests.post(
                "https://creatorsapi.amazon/catalog/v1/getItems",
                headers=api_headers,
                json={"partnerTag": CREDS["partner_tag"],
                      "marketplace": "www.amazon.com.mx",
                      "itemIds": batch,
                      "languagesOfPreference": ["es_MX"],
                      "currencyOfPreference": "MXN",
                      "resources": _RECURSOS},
                timeout=20
            )
            if r.status_code != 200:
                return []

            items_api = r.json().get("itemsResult", {}).get("items", [])
            return items_api
        except Exception as e:
            print(f"  ❌ Error enriqueciendo batch: {e}", flush=True)
            return []

    # Dividir en batches de 10
    batches = [asins[i:i+10] for i in range(0, len(asins), 10)]
    all_items = []

    for batch in batches:
        items = _enriquecer_batch(batch)
        all_items.extend(items)
        time.sleep(0.3)  # Rate limiting

    return all_items

# ==================== FIN FEEDS ====================

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
                feed_id = body.get("feed_id", "") or body.get("audiencia_id", "")  # Aceptar ambos nombres

                if not query:
                    raise ValueError("query requerida")

                log_prefix = f"[Feed: {feed_id}] " if feed_id else ""
                print(f"🔍 {log_prefix}Búsqueda directa: {query}", flush=True)
                
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

                if _HV_OK:
                    # Usar historial del feed si feed_id está disponible
                    if feed_id:
                        resultados = aplicar_novedad_score_feed(resultados, feed_id)
                        print(f"  📚 Historial del feed '{feed_id}': {sum(1 for i in resultados if i.get('novedad_score',1)<1.0)} ya vistos de {len(resultados)}", flush=True)
                    else:
                        resultados = _hv.aplicar_scores(resultados)
                        print(f"  📚 Historial global aplicado: {sum(1 for i in resultados if i.get('novedad_score',1)<1.0)} ya vistos de {len(resultados)}", flush=True)

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
                feed_id  = self.headers.get("X-Feed-Id", "")  # Opcional: feed ID desde header

                import re as _re
                # Cortar el HTML en el punto donde empiezan productos de historial/recomendaciones
                # "purchase-sims" marca el inicio de "vistos anteriormente" en Amazon
                corte = html_text.lower().find("purchase-sims")
                html_principal = html_text[:corte] if corte != -1 else html_text
                asins = list(set(_re.findall(r"/dp/([A-Z0-9]{10})", html_principal)))
                total_html = len(set(_re.findall(r"/dp/([A-Z0-9]{10})", html_text)))

                log_prefix = f"[Feed: {feed_id}] " if feed_id else ""
                print(f"📦 {log_prefix}/procesar-html → {len(asins)} ASINs principales (de {total_html} totales, {total_html - len(asins)} descartados por historial)", flush=True)

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

                if _HV_OK:
                    if feed_id:
                        resultados = aplicar_novedad_score_feed(resultados, feed_id)
                        print(f"  📚 Historial del feed '{feed_id}': {sum(1 for i in resultados if i.get('novedad_score',1)<1.0)} ya vistos de {len(resultados)}", flush=True)
                    else:
                        resultados = _hv.aplicar_scores(resultados)
                        print(f"  📚 Historial global aplicado: {sum(1 for i in resultados if i.get('novedad_score',1)<1.0)} ya vistos de {len(resultados)}", flush=True)

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
                feed_id      = body.get("feed_id", "") or body.get("audiencia_id", "")
                filtros      = body.get("filtros", {})
                queries      = body.get("queries")      or None
                urls         = body.get("urls")         or None
                categorias   = body.get("categorias")   or None
                min_discount = int(filtros.get("descuento_min", 0))
                precio_min   = float(filtros.get("precio_min", 0))
                precio_max   = float(filtros.get("precio_max", 0))
                max_por_query= int(body.get("max_por_query", 50))
                paginas      = int(body.get("paginas", 1))

                log_prefix = f"[Feed: {feed_id}] " if feed_id else ""
                print(f"🛒 {log_prefix}/buscar-ml → queries={queries} cats={categorias} urls={len(urls or [])} desc≥{min_discount}% pages={paginas}", flush=True)

                items = _ml.scrape(
                    queries=queries, urls=urls, categorias=categorias,
                    min_discount=min_discount, max_per_query=max_por_query,
                    precio_min=precio_min, precio_max=precio_max,
                    pages=paginas,
                )

                if _HV_OK:
                    if feed_id:
                        items = aplicar_novedad_score_feed(items, feed_id)
                        print(f"  📚 Historial del feed '{feed_id}': {sum(1 for i in items if i.get('novedad_score',1)<1.0)} ya vistos de {len(items)}", flush=True)
                    else:
                        items = _hv.aplicar_scores(items)
                        print(f"  📚 Historial global aplicado: {sum(1 for i in items if i.get('novedad_score',1)<1.0)} ya vistos de {len(items)}", flush=True)

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
                feed_id  = self.headers.get("X-Feed-Id", "")  # Opcional: feed ID desde header
                min_disc = 1
                try:
                    qs = self.headers.get("X-Min-Discount", "1")
                    min_disc = int(qs)
                except Exception:
                    pass
                items, total_raw = _ml.scrape_html_texto(html_txt, min_discount=min_disc)

                log_prefix = f"[Feed: {feed_id}] " if feed_id else ""
                print(f"📦 {log_prefix}/procesar-html-ml → {total_raw} raw → {len(items)} con ≥{min_disc}%", flush=True)

                if _HV_OK:
                    if feed_id:
                        items = aplicar_novedad_score_feed(items, feed_id)
                        print(f"  📚 Historial del feed '{feed_id}': {sum(1 for i in items if i.get('novedad_score',1)<1.0)} ya vistos de {len(items)}", flush=True)
                    else:
                        items = _hv.aplicar_scores(items)
                        print(f"  📚 Historial global aplicado: {sum(1 for i in items if i.get('novedad_score',1)<1.0)} ya vistos de {len(items)}", flush=True)

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
                feed_id      = body.get("feed_id", "") or body.get("audiencia_id", "")
                urls         = body.get("urls", [])
                pages        = int(body.get("pages", 1))  # Reducido de 3 a 1 para evitar timeout
                min_discount = int(body.get("min_discount", 0))
                background   = body.get("background", False)  # Por default síncrono (compatibilidad)

                if not urls:
                    raise ValueError("Se requiere al menos una URL")

                for i, u in enumerate(urls):
                    print(f"  🔎 URL[{i}] len={len(u)}: {repr(u)}", flush=True)

                log_prefix = f"[Feed: {feed_id}] " if feed_id else ""
                print(f"🛒 {log_prefix}/buscar-amazon-url → {len(urls)} URL(s), {pages} páginas c/u", flush=True)

                # Si background=True, devolver job_id inmediatamente y procesar en thread
                if background:
                    job_id = str(uuid.uuid4())
                    JOBS_BACKGROUND[job_id] = {
                        "status": "processing",
                        "progreso": {
                            "fase": "iniciando",
                            "urls_total": len(urls),
                            "urls_procesadas": 0,
                            "asins_extraidos": 0,
                            "batches_total": 0,
                            "batches_completados": 0,
                            "productos_ok": 0
                        },
                        "resultados": None,
                        "error": None
                    }

                    # Procesar en background
                    def procesar_urls_bg():
                        try:
                            _procesar_urls_completo(job_id, urls, pages, min_discount, feed_id)
                        except Exception as e:
                            JOBS_BACKGROUND[job_id]["status"] = "error"
                            JOBS_BACKGROUND[job_id]["error"] = str(e)
                            print(f"❌ Job {job_id} error: {e}", flush=True)

                    thread = threading.Thread(target=procesar_urls_bg, daemon=True)
                    thread.start()

                    # Devolver job_id inmediatamente
                    self.send_response(202); self._cors()  # 202 Accepted
                    self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": True,
                        "job_id": job_id,
                        "message": "Procesando en background. Consulta /progreso-busqueda?job_id=" + job_id
                    }).encode())
                    return

                # Si background=False, procesar síncronamente (comportamiento original)
                job_id = "sync"
                JOBS_BACKGROUND[job_id] = {
                    "status": "processing",
                    "progreso": {"fase": "iniciando", "urls_total": len(urls)},
                    "resultados": None
                }

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

                _RECURSOS = ["itemInfo.title", "itemInfo.externalIds", "images.primary.medium",
                             "offersV2.listings.price", "offersV2.listings.dealDetails",
                             "offersV2.listings.isBuyBoxWinner"]
                _stats = {"ok": 0, "no200": 0, "empty": 0, "no_listing": 0, "err": 0}

                def _enriquecer_batch(batch):
                    """Llama getItems con hasta 10 ASINs — lookup directo, más datos que searchItems."""
                    try:
                        r = requests.post(
                            "https://creatorsapi.amazon/catalog/v1/getItems",
                            headers=api_headers,
                            json={"partnerTag": CREDS["partner_tag"],
                                  "marketplace": "www.amazon.com.mx",
                                  "itemIds": batch,
                                  "languagesOfPreference": ["es_MX"],
                                  "currencyOfPreference": "MXN",
                                  "resources": _RECURSOS},
                            timeout=60  # Aumentado de 20 a 60 segundos
                        )
                        if r.status_code != 200:
                            _stats["no200"] += len(batch)
                            if r.status_code in (429, 500, 502, 503):
                                time.sleep(3.0)
                                r2 = requests.post(
                                    "https://creatorsapi.amazon/catalog/v1/getItems",
                                    headers=api_headers,
                                    json={"partnerTag": CREDS["partner_tag"],
                                          "marketplace": "www.amazon.com.mx",
                                          "itemIds": batch,
                                          "languagesOfPreference": ["es_MX"],
                                          "currencyOfPreference": "MXN",
                                          "resources": _RECURSOS},
                                    timeout=60  # Aumentado de 20 a 60 segundos
                                )
                                if r2.status_code != 200:
                                    return []
                                r = r2
                            else:
                                return []
                        items = r.json().get("itemsResult", {}).get("items", [])
                        if not items:
                            _stats["empty"] += len(batch)
                            return []
                        resultados_batch = []
                        for item in items:
                            p = parsear_item(item)
                            if p is None:
                                _stats["no_listing"] += 1
                            else:
                                _stats["ok"] += 1
                                if p["descuento_pct"] >= min_discount:
                                    resultados_batch.append(p)
                        return resultados_batch
                    except Exception as e:
                        _stats["err"] += len(batch)
                        print(f"  ❌ batch {batch[:2]}…: {e}", flush=True)
                        return []

                # Dividir en batches de 10 ASINs
                batches = [all_asins[i:i+10] for i in range(0, len(all_asins), 10)]
                print(f"  📦 {len(all_asins)} ASINs → {len(batches)} batches de 10 vía getItems", flush=True)

                resultados = []
                completados = 0
                with ThreadPoolExecutor(max_workers=5) as pool:
                    futuros = {pool.submit(_enriquecer_batch, b): b for b in batches}
                    for fut in as_completed(futuros):
                        completados += 1
                        resultados.extend(fut.result())
                        if completados % 20 == 0:
                            print(f"  ⏳ {completados}/{len(batches)} batches | ok={_stats['ok']} no200={_stats['no200']} empty={_stats['empty']} sin_listing={_stats['no_listing']}", flush=True)

                print(f"  📊 Final: ok={_stats['ok']} no200={_stats['no200']} empty={_stats['empty']} sin_listing={_stats['no_listing']} err={_stats['err']}", flush=True)

                seen, unicos = set(), []
                for p in resultados:
                    if p["asin"] not in seen:
                        seen.add(p["asin"])
                        unicos.append(p)

                if _HV_OK:
                    if feed_id:
                        unicos = aplicar_novedad_score_feed(unicos, feed_id)
                        print(f"  📚 Historial del feed '{feed_id}': {sum(1 for i in unicos if i.get('novedad_score',1)<1.0)} ya vistos de {len(unicos)}", flush=True)
                    else:
                        unicos = _hv.aplicar_scores(unicos)
                        print(f"  📚 Historial global aplicado: {sum(1 for i in unicos if i.get('novedad_score',1)<1.0)} ya vistos de {len(unicos)}", flush=True)

                print(f"  → {len(unicos)} productos", flush=True)
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "items": unicos,
                    "total": len(unicos), "asins": len(all_asins)}).encode())
            except Exception as e:
                print(f"❌ /buscar-amazon-url: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path.startswith("/progreso-busqueda"):
            # Endpoint para consultar el progreso de un job en background
            try:
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                job_id = params.get("job_id", [None])[0]

                if not job_id or job_id not in JOBS_BACKGROUND:
                    self.send_response(404); self._cors()
                    self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Job no encontrado"}).encode())
                    return

                job = JOBS_BACKGROUND[job_id]

                response = {
                    "ok": True,
                    "job_id": job_id,
                    "status": job["status"],
                    "progreso": job["progreso"]
                }

                # Si está completado, incluir resultados
                if job["status"] == "completed":
                    response["resultados"] = job["resultados"]
                elif job["status"] == "error":
                    response["error"] = job["error"]

                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            except Exception as e:
                print(f"❌ /progreso-busqueda: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/buscar-amazon-deals":
            try:
                if not _AZ_OK:
                    raise ImportError("scraper_amazon no disponible")
                length  = int(self.headers.get("Content-Length", 0))
                body    = json.loads(self.rfile.read(length)) if length else {}
                feed_id = body.get("feed_id", "") or body.get("audiencia_id", "")
                buckets = body.get("buckets", list(_az.DEALS_URLS.keys()))
                min_discount = int(body.get("min_discount", 0))
                pw_ok = _az.playwright_disponible()

                log_prefix = f"[Feed: {feed_id}] " if feed_id else ""
                print(f"🛒 {log_prefix}/buscar-amazon-deals → buckets={buckets} playwright={'✅' if pw_ok else '❌'}", flush=True)

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

                # 2. Enriquecer vía Creators API — getItems en batches de 10
                token = get_token()
                api_headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "x-marketplace": "www.amazon.com.mx"
                }
                _RECURSOS = ["itemInfo.title", "itemInfo.externalIds", "images.primary.medium",
                             "offersV2.listings.price", "offersV2.listings.dealDetails",
                             "offersV2.listings.isBuyBoxWinner"]

                def _enriquecer_batch_deals(batch):
                    try:
                        r = requests.post(
                            "https://creatorsapi.amazon/catalog/v1/getItems",
                            headers=api_headers,
                            json={"partnerTag": CREDS["partner_tag"],
                                  "marketplace": "www.amazon.com.mx",
                                  "itemIds": batch,
                                  "languagesOfPreference": ["es_MX"],
                                  "currencyOfPreference": "MXN",
                                  "resources": _RECURSOS},
                            timeout=20
                        )
                        if r.status_code != 200:
                            if r.status_code in (429, 500, 502, 503):
                                time.sleep(3.0)
                                r2 = requests.post(
                                    "https://creatorsapi.amazon/catalog/v1/getItems",
                                    headers=api_headers,
                                    json={"partnerTag": CREDS["partner_tag"],
                                          "marketplace": "www.amazon.com.mx",
                                          "itemIds": batch,
                                          "languagesOfPreference": ["es_MX"],
                                          "currencyOfPreference": "MXN",
                                          "resources": _RECURSOS},
                                    timeout=20
                                )
                                if r2.status_code != 200:
                                    return []
                                r = r2
                            else:
                                return []
                        items_api = r.json().get("itemsResult", {}).get("items", [])
                        out = []
                        for item in items_api:
                            p = parsear_item(item)
                            if p and p["descuento_pct"] >= min_discount:
                                out.append(p)
                        return out
                    except Exception as e:
                        print(f"  ❌ batch: {e}", flush=True)
                        return []

                batches   = [all_asins[i:i+10] for i in range(0, len(all_asins), 10)]
                resultados = []
                print(f"  📦 {len(all_asins)} ASINs → {len(batches)} batches vía getItems", flush=True)
                with ThreadPoolExecutor(max_workers=5) as pool:
                    for res in pool.map(_enriquecer_batch_deals, batches):
                        resultados.extend(res)

                # dedup por ASIN
                seen, unicos = set(), []
                for p in resultados:
                    if p["asin"] not in seen:
                        seen.add(p["asin"])
                        unicos.append(p)

                if _HV_OK:
                    if feed_id:
                        unicos = aplicar_novedad_score_feed(unicos, feed_id)
                        print(f"  📚 Historial del feed '{feed_id}': {sum(1 for i in unicos if i.get('novedad_score',1)<1.0)} ya vistos", flush=True)
                    else:
                        unicos = _hv.aplicar_scores(unicos)
                        print(f"  📚 Historial global aplicado: {sum(1 for i in unicos if i.get('novedad_score',1)<1.0)} ya vistos", flush=True)

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
                action  = body.get("action", "score")
                items   = body.get("items", [])
                feed_id = body.get("feed_id", "") or body.get("audiencia_id", "")

                if action == "score":
                    if feed_id:
                        resultado = aplicar_novedad_score_feed(items, feed_id)
                    else:
                        resultado = _hv.aplicar_scores(items)
                    resp = {"ok": True, "items": resultado}

                elif action == "filtrar":
                    min_score = float(body.get("min_score", 0.1))
                    if feed_id:
                        resultado = aplicar_novedad_score_feed(items, feed_id)
                        resultado = [p for p in resultado if p.get("novedad_score", 1.0) >= min_score]
                    else:
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
                r = requests.post(SHEETS_URL, data=json.dumps(items),
                                  headers={"Content-Type": "application/json"},
                                  allow_redirects=True, timeout=120)
                r.raise_for_status()
                resp_data = r.json()
                # Marcar como publicados en historial
                if _HV_OK:
                    n = _hv.marcar_varios(items)
                    print(f"  📚 {n} items marcados en historial", flush=True)
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "rows": resp_data.get("rows", len(items))}).encode())
            except Exception as e:
                print(f"❌ /exportar-sheets: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/feeds/export-sheets":
            # Endpoint específico para exportar feeds a Google Sheets
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                feed_id = body.get("feed_id", "")
                items = body.get("items", [])

                if not feed_id:
                    raise ValueError("feed_id requerido")
                if not items:
                    raise ValueError("Sin items para exportar")

                # Cargar configuración del feed
                perfiles = cargar_perfiles()
                perfil = perfiles.get(feed_id)

                if not perfil:
                    raise ValueError(f"Feed '{feed_id}' no encontrado")

                sheets_url = perfil.get("sheets_export_url")
                if not sheets_url:
                    raise ValueError(f"Feed '{feed_id}' no tiene sheets_export_url configurado")

                print(f"📊 /feeds/export-sheets → Feed: {feed_id}, Items recibidos: {len(items)}", flush=True)

                # FILTRO DE SEGURIDAD: Eliminar productos bloqueados/descartados
                items_antes = len(items)
                items = [
                    item for item in items
                    if not esta_bloqueado(feed_id, item.get('asin', ''))
                ]
                items_bloqueados = items_antes - len(items)

                if items_bloqueados > 0:
                    print(f"  🚫 {items_bloqueados} productos descartados filtrados (no se exportarán)", flush=True)

                if not items:
                    raise ValueError("Todos los productos seleccionados fueron descartados previamente")

                print(f"  📤 Exportando {len(items)} productos a Google Sheets...", flush=True)

                # Enviar a Google Apps Script
                r = requests.post(sheets_url, data=json.dumps(items),
                                headers={"Content-Type": "application/json"},
                                allow_redirects=True, timeout=120)
                r.raise_for_status()
                resp_data = r.json()

                print(f"  ✅ Exportado a Google Sheets: {resp_data.get('rows', len(items))} productos", flush=True)

                # Marcar SOLO en historial del feed (NO en el core de Superseller)
                # Pasar items completos para guardar títulos
                items_con_asin = [item for item in items if item.get('asin')]
                if items_con_asin:
                    n = marcar_asins_vistos(feed_id, items_con_asin)
                    print(f"  📚 {n} productos marcados en historial del feed '{feed_id}' (con títulos)", flush=True)

                # Aprender keywords INTELIGENTES de productos publicados
                # SOLO núcleo: personajes, franquicias, marcas (NO tipos de producto)
                todas_keywords = set()
                for item in items:
                    title = item.get('title', '')
                    if title:
                        keywords_nucleo = extraer_keywords_inteligentes(title)
                        todas_keywords.update(keywords_nucleo)

                if todas_keywords:
                    # Cargar stats de keywords
                    stats = cargar_keyword_stats(feed_id)

                    # Incrementar score de keywords extraídas (aprobadas)
                    for kw in todas_keywords:
                        if kw not in stats:
                            stats[kw] = {'score': 0, 'productos_aprobados': 0}
                        stats[kw]['score'] += 1
                        stats[kw]['productos_aprobados'] += 1

                    # Guardar stats actualizadas
                    guardar_keyword_stats(feed_id, stats)

                    # Agregar nuevas keywords al perfil
                    keywords_actuales = set(perfil.get('keywords', []))
                    keywords_nuevas = [k for k in todas_keywords if k not in keywords_actuales]

                    if keywords_nuevas:
                        keywords_actuales.update(keywords_nuevas)
                        perfil['keywords'] = sorted(list(keywords_actuales))

                        # Aplicar límite de 200 keywords
                        perfil = aplicar_limite_keywords(feed_id, perfil, limite=200)

                        # Guardar cambios
                        perfiles[feed_id] = perfil
                        perfiles_path = os.path.join(BASE_DIR, 'feeds', 'perfiles_audiencia.json')
                        with open(perfiles_path, 'w', encoding='utf-8') as f:
                            json.dump(perfiles, f, indent=2, ensure_ascii=False)

                        # Mostrar keywords aprendidas
                        ejemplos = list(keywords_nuevas)[:10]
                        if len(keywords_nuevas) > 10:
                            print(f"  🎓 {len(keywords_nuevas)} keywords núcleo aprendidas: {', '.join(ejemplos)}... (+{len(keywords_nuevas)-10} más)", flush=True)
                        else:
                            print(f"  🎓 {len(keywords_nuevas)} keywords núcleo aprendidas: {', '.join(ejemplos)}", flush=True)
                        print(f"  📊 Total keywords activas: {len(perfil['keywords'])}/200", flush=True)

                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "rows": resp_data.get("rows", len(items)),
                    "sheetUrl": resp_data.get("sheetUrl", "")
                }).encode())

            except Exception as e:
                print(f"❌ /feeds/export-sheets: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/feeds/descartar":
            # Endpoint para descartar productos y aprender exclusiones por feed
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                audiencia_id = body.get("audiencia_id", "")
                asin = body.get("asin", "")
                title = body.get("title", "")

                if not audiencia_id or not asin:
                    raise ValueError("audiencia_id y asin requeridos")

                print(f"🚫 Descartando producto en '{audiencia_id}': {asin}", flush=True)

                # 1. Marcar ASIN como bloqueado en historial del feed
                from datetime import datetime as dt, timezone as tz
                historial_feed = cargar_historial_feed(audiencia_id)
                historial_feed[asin] = {
                    "blocked": True,
                    "blocked_at": dt.now(tz.utc).isoformat(),
                    "title": title
                }
                guardar_historial_feed(audiencia_id, historial_feed)
                print(f"  ✅ ASIN {asin} marcado como bloqueado en historial", flush=True)

                # 2. Extraer keywords DEL TÍTULO del producto descartado
                # NO tocar las keywords de búsqueda (para evitar matar búsquedas buenas)
                palabras_clave = []
                titulo_lower = title.lower()

                # Stopwords comunes que no son útiles para filtrar
                stopwords = {
                    'de', 'del', 'la', 'el', 'los', 'las', 'un', 'una', 'en', 'y', 'o',
                    'para', 'con', 'sin', 'por', 'the', 'a', 'an', 'and', 'or', 'of',
                    'to', 'for', 'with', 'in', 'on', 'at', 'by', 'from', 'set', 'pack',
                    'piezas', 'piece', 'pieces', 'color', 'size', 'talla', 'modelo'
                }

                # WHITELIST: Palabras genéricas que NUNCA se deben descartar
                # (categorías amplias, colores, atributos, conectividad, materiales)
                palabras_genericas = {
                    # Categorías amplias que podrían tener productos buenos
                    'figura', 'figuras', 'figure', 'figures', 'juguete', 'juguetes', 'toy', 'toys',
                    'libro', 'libros', 'book', 'books', 'caja', 'box', 'case', 'estuche',
                    'camiseta', 'playera', 'shirt', 'tshirt', 'tenis', 'zapatos', 'shoes',
                    'poster', 'póster', 'print', 'cuadro', 'arte', 'artwork',
                    'colección', 'collection', 'collectible', 'coleccionable',
                    'edición', 'edition', 'limited', 'limitada', 'exclusivo', 'exclusive',
                    'set', 'pack', 'bundle', 'kit', 'combo',

                    # Colores
                    'negro', 'black', 'blanco', 'white', 'azul', 'blue', 'rojo', 'red',
                    'verde', 'green', 'amarillo', 'yellow', 'rosa', 'pink', 'gris', 'gray', 'grey',
                    'morado', 'purple', 'naranja', 'orange', 'café', 'brown', 'dorado', 'gold',
                    'plateado', 'silver', 'multicolor',

                    # Conectividad y tecnología genérica (podría aplicar a coleccionables tech)
                    'bluetooth', 'wifi', 'wireless', 'inalámbrico', 'inalámbricos',
                    'cable', 'usb', 'hdmi', 'aux', 'jack',

                    # Materiales comunes
                    'papel', 'paper', 'plástico', 'plastic', 'metal', 'vinyl', 'vinilo',
                    'tela', 'fabric', 'foam', 'goma', 'rubber', 'madera', 'wood',

                    # Atributos y tamaños
                    'grande', 'large', 'pequeño', 'small', 'mini', 'micro', 'giant', 'gigante',
                    'mediano', 'medium', 'xl', 'xxl', 'jumbo',
                    'nuevo', 'new', 'usado', 'used', 'original', 'authentic', 'auténtico',
                    'oficial', 'official', 'premium', 'deluxe', 'standard', 'básico', 'basic',

                    # Palabras de empaquetado/presentación
                    'caja', 'empaque', 'packaging', 'display', 'incluye', 'includes',
                    'con', 'with', 'sin', 'without', 'más', 'more', 'extra',

                    # Palabras temporales/comerciales
                    'nuevo', 'oferta', 'sale', 'deal', 'descuento', 'discount',
                    'regalo', 'gift', 'gratis', 'free', 'bonus'
                }

                # Extraer palabras del título, filtrando genéricas
                palabras = titulo_lower.split()
                for palabra in palabras:
                    # Limpiar caracteres especiales
                    palabra_limpia = ''.join(c for c in palabra if c.isalnum())

                    # Filtrar palabras que SÍ deben descartarse:
                    # - Más de 3 caracteres
                    # - No es solo números
                    # - No es stopword
                    # - NO es palabra genérica (NUEVO FILTRO)
                    if (len(palabra_limpia) > 3 and
                        not palabra_limpia.isdigit() and
                        palabra_limpia not in stopwords and
                        palabra_limpia not in palabras_genericas):
                        palabras_clave.append(palabra_limpia)

                # 3. Actualizar excludeKeywords del perfil (si encontramos palabras relevantes)
                palabras_a_excluir = []
                palabras_protegidas = []

                if palabras_clave:
                    perfiles = cargar_perfiles()
                    perfil = perfiles.get(audiencia_id)

                    if perfil:
                        # FILTRO INTELIGENTE: NO agregar palabras que están en keywords POSITIVAS del perfil
                        # (estas son parte del nicho y no deberían excluirse)
                        keywords_positivas = set(kw.lower() for kw in perfil.get('keywords', []))

                        # Filtrar palabras que NO están en keywords positivas
                        palabras_a_excluir = [
                            palabra for palabra in palabras_clave
                            if palabra not in keywords_positivas
                        ]

                        if palabras_a_excluir:
                            exclude_actual = set(perfil['filtros'].get('excludeKeywords', []))
                            exclude_actual.update(palabras_a_excluir)
                            perfil['filtros']['excludeKeywords'] = sorted(list(exclude_actual))
                        else:
                            palabras_a_excluir = []  # Para logging

                        # Palabras protegidas (no se excluyeron porque están en keywords positivas)
                        palabras_protegidas = [p for p in palabras_clave if p in keywords_positivas]

                        # Guardar cambios en archivo si hubo modificaciones
                        if palabras_a_excluir:
                            perfiles_path = os.path.join(BASE_DIR, 'feeds', 'perfiles_audiencia.json')
                            with open(perfiles_path, 'w', encoding='utf-8') as f:
                                json.dump(perfiles, f, indent=2, ensure_ascii=False)

                        # Logging mejorado
                        print(f"  📝 Palabras del título: {palabras_clave}", flush=True)
                        if palabras_protegidas:
                            print(f"  🛡️  Protegidas (en keywords positivas): {palabras_protegidas}", flush=True)
                        if palabras_a_excluir:
                            print(f"  ❌ Excluidas: {palabras_a_excluir}", flush=True)
                        else:
                            print(f"  ✅ Ninguna palabra excluida (todas están protegidas o son genéricas)", flush=True)

                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "asin": asin,
                    "palabras_del_titulo": palabras_clave,
                    "palabras_excluidas": palabras_a_excluir,
                    "palabras_protegidas": palabras_protegidas,
                    "mensaje": f"Producto descartado. {len(palabras_a_excluir)} palabras excluidas, {len(palabras_protegidas)} protegidas"
                }).encode())

            except Exception as e:
                print(f"❌ /feeds/descartar: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/feeds/agregar_manual":
            # Endpoint para agregar productos manualmente, URLs de categorías o keywords
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                audiencia_id = body.get("audiencia_id", "")
                input_value = body.get("asin", "")  # Puede ser ASIN, URL o keyword
                es_keyword = body.get("es_keyword", False)

                if not audiencia_id or not input_value:
                    raise ValueError("audiencia_id y asin/url/keyword requeridos")

                # Si es keyword directa
                if es_keyword:
                    print(f"🔑 Agregando keyword en '{audiencia_id}': {input_value}", flush=True)

                    perfiles = cargar_perfiles()
                    perfil = perfiles.get(audiencia_id)

                    if not perfil:
                        raise ValueError(f"Feed '{audiencia_id}' no encontrado")

                    keywords_actuales = set(perfil.get('keywords', []))
                    keyword_normalizada = input_value.lower().strip()

                    if keyword_normalizada in keywords_actuales:
                        raise ValueError("Esta keyword ya está agregada")

                    keywords_actuales.add(keyword_normalizada)
                    perfil['keywords'] = sorted(list(keywords_actuales))
                    perfiles[audiencia_id] = perfil

                    # Guardar cambios
                    perfiles_path = os.path.join(BASE_DIR, 'feeds', 'perfiles_audiencia.json')
                    with open(perfiles_path, 'w', encoding='utf-8') as f:
                        json.dump(perfiles, f, indent=2, ensure_ascii=False)

                    print(f"  ✅ Keyword agregada: {keyword_normalizada}", flush=True)

                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": True,
                        "tipo": "keyword",
                        "mensaje": f"Keyword '{keyword_normalizada}' agregada exitosamente"
                    }).encode())
                    return

                # Detectar si es URL de categoría o producto individual
                if 'amazon' in input_value.lower() and '/dp/' not in input_value and '/gp/product/' not in input_value:
                    # Es una URL de categoría (no tiene ASIN)
                    print(f"📂 Agregando URL de categoría en '{audiencia_id}': {input_value[:80]}...", flush=True)

                    perfiles = cargar_perfiles()
                    perfil = perfiles.get(audiencia_id)

                    if not perfil:
                        raise ValueError(f"Feed '{audiencia_id}' no encontrado")

                    # Agregar a urls_fijas
                    urls_fijas = perfil.get('urls_fijas', [])

                    # Verificar si ya existe
                    if any(u.get('url') == input_value for u in urls_fijas):
                        raise ValueError("Esta URL de categoría ya está agregada")

                    # Agregar nueva URL
                    urls_fijas.append({
                        "url": input_value,
                        "plataforma": "amazon",
                        "descripcion": f"Categoría agregada manualmente"
                    })

                    perfil['urls_fijas'] = urls_fijas
                    perfiles[audiencia_id] = perfil

                    # Guardar cambios
                    perfiles_path = os.path.join(BASE_DIR, 'feeds', 'perfiles_audiencia.json')
                    with open(perfiles_path, 'w', encoding='utf-8') as f:
                        json.dump(perfiles, f, indent=2, ensure_ascii=False)

                    print(f"  ✅ URL de categoría agregada a urls_fijas", flush=True)

                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": True,
                        "tipo": "categoria",
                        "mensaje": "URL de categoría agregada. Aparecerá en la próxima generación del feed."
                    }).encode())
                    return

                # Si llegamos aquí, es un ASIN o URL de producto individual
                asin = input_value
                print(f"➕ Agregando producto manual en '{audiencia_id}': {asin}", flush=True)

                # 1. Enriquecer el ASIN con la API de Amazon
                items = enriquecer_asins([asin], minSavingPercent=0)

                if not items or len(items) == 0:
                    raise ValueError(f"No se pudo enriquecer el ASIN {asin}. Verifica que sea válido.")

                item = items[0]
                parsed = parsear_item(item)

                if not parsed:
                    raise ValueError(f"No se pudo parsear el producto {asin}")

                title = parsed.get("title", "")
                print(f"  📦 Producto: {title[:80]}...", flush=True)

                # 2. Guardar en historial como aprobado manualmente
                from datetime import datetime as dt, timezone as tz
                historial_feed = cargar_historial_feed(audiencia_id)
                historial_feed[asin] = {
                    "manually_added": True,
                    "added_at": dt.now(tz.utc).isoformat(),
                    "title": title,
                    "blocked": False  # Explícitamente NO bloqueado
                }
                guardar_historial_feed(audiencia_id, historial_feed)
                print(f"  ✅ ASIN {asin} guardado en historial como aprobado", flush=True)

                # 3. Extraer keywords positivas del título
                # Estas son palabras que indican el tipo de producto que SÍ queremos
                palabras_clave = []
                titulo_words = title.lower().split()

                # Filtrar palabras significativas (más de 3 caracteres, no números puros)
                palabras_significativas = [
                    w for w in titulo_words
                    if len(w) > 3 and not w.isdigit()
                    and w not in ['para', 'with', 'from', 'that', 'this', 'have']
                ]

                # Tomar las primeras 3-5 palabras significativas
                palabras_clave = palabras_significativas[:5]

                print(f"  🎓 Keywords identificadas: {palabras_clave}", flush=True)

                # 4. Agregar keywords al perfil para futuras búsquedas
                if palabras_clave:
                    perfiles = cargar_perfiles()
                    perfil = perfiles.get(audiencia_id)

                    if perfil:
                        keywords_actuales = set(perfil.get('keywords', []))
                        keywords_nuevas = [k for k in palabras_clave if k not in keywords_actuales]

                        if keywords_nuevas:
                            keywords_actuales.update(keywords_nuevas)
                            perfil['keywords'] = sorted(list(keywords_actuales))

                            # Guardar cambios en archivo
                            perfiles_path = os.path.join(BASE_DIR, 'feeds', 'perfiles_audiencia.json')
                            with open(perfiles_path, 'w', encoding='utf-8') as f:
                                json.dump(perfiles, f, indent=2, ensure_ascii=False)

                            print(f"  ➕ {len(keywords_nuevas)} keywords agregadas al perfil: {keywords_nuevas}", flush=True)
                        else:
                            print(f"  ℹ️  Keywords ya existían en el perfil", flush=True)

                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "asin": asin,
                    "title": title,
                    "keywords_aprendidas": palabras_clave,
                    "mensaje": f"Producto agregado: {title[:50]}..."
                }).encode())

            except Exception as e:
                print(f"❌ /feeds/agregar_manual: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/feeds/stats":
            # Dashboard de performance del feed
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                feed_id = body.get("feed_id", "") or body.get("audiencia_id", "")
                dias = int(body.get("dias", 30))  # Período de análisis

                if not feed_id:
                    raise ValueError("feed_id requerido")

                print(f"📊 /feeds/stats → Feed: {feed_id}, Período: {dias} días", flush=True)

                # Generar estadísticas
                from datetime import timedelta
                from collections import Counter

                # Cargar datos
                perfiles = cargar_perfiles()
                if feed_id not in perfiles:
                    raise ValueError(f"Feed '{feed_id}' no encontrado")

                keywords_actuales = perfiles[feed_id].get('keywords', [])
                historial = cargar_historial_feed(feed_id)
                keyword_stats = cargar_keyword_stats(feed_id)

                # Análisis temporal
                ahora = datetime.now(timezone.utc)
                fecha_inicio = ahora - timedelta(days=dias)

                productos_periodo = []
                for asin, data in historial.items():
                    ultima_vez = data.get('ultima_vez', '')
                    if ultima_vez:
                        try:
                            if '+' in ultima_vez or ultima_vez.endswith('Z'):
                                fecha = datetime.fromisoformat(ultima_vez.replace('Z', '+00:00'))
                            else:
                                fecha = datetime.fromisoformat(ultima_vez).replace(tzinfo=timezone.utc)

                            if fecha >= fecha_inicio:
                                productos_periodo.append({
                                    'asin': asin,
                                    'title': data.get('title', ''),
                                    'fecha': fecha,
                                    'bloqueado': data.get('blocked', False)
                                })
                        except:
                            pass

                # Contar keywords en productos
                keyword_matches = Counter()
                for kw in keywords_actuales:
                    kw_lower = kw.lower()
                    for prod in productos_periodo:
                        if prod['title'] and kw_lower in prod['title'].lower():
                            keyword_matches[kw] += 1

                # Preparar respuesta
                stats = {
                    'feed_id': feed_id,
                    'nombre': perfiles[feed_id].get('nombre', ''),
                    'periodo_dias': dias,
                    'fecha_analisis': datetime.now(timezone.utc).isoformat(),

                    'keywords': {
                        'total_configuradas': len(keywords_actuales),
                        'activas': len([kw for kw in keywords_actuales if keyword_matches.get(kw, 0) > 0]),
                        'inactivas': len([kw for kw in keywords_actuales if keyword_matches.get(kw, 0) == 0]),
                        'porcentaje_activas': round(100 * len([kw for kw in keywords_actuales if keyword_matches.get(kw, 0) > 0]) / len(keywords_actuales), 1) if keywords_actuales else 0
                    },

                    'productos': {
                        'total': len(productos_periodo),
                        'con_titulo': len([p for p in productos_periodo if p['title']]),
                        'bloqueados': len([p for p in productos_periodo if p['bloqueado']]),
                        'promedio_diario': round(len(productos_periodo) / dias, 1) if dias > 0 else 0
                    },

                    'top_keywords': [
                        {
                            'keyword': kw,
                            'productos_generados': count,
                            'score_aprendizaje': keyword_stats.get(kw, {}).get('score', 0),
                            'productos_aprobados': keyword_stats.get(kw, {}).get('productos_aprobados', 0)
                        }
                        for kw, count in keyword_matches.most_common(30)
                    ],

                    'keywords_inactivas': sorted([
                        kw for kw in keywords_actuales
                        if keyword_matches.get(kw, 0) == 0
                    ])
                }

                # Tendencia por día (últimos 7 días)
                tendencia = {}
                for dias_atras in range(min(7, dias)):
                    fecha_dia = ahora - timedelta(days=dias_atras)
                    fecha_ant = fecha_dia - timedelta(days=1)

                    productos_dia = len([
                        p for p in productos_periodo
                        if fecha_ant <= p['fecha'] < fecha_dia
                    ])

                    fecha_str = fecha_dia.strftime('%Y-%m-%d')
                    tendencia[fecha_str] = productos_dia

                stats['tendencia_diaria'] = tendencia

                print(f"  ✅ Stats generadas: {stats['keywords']['activas']}/{stats['keywords']['total_configuradas']} keywords activas", flush=True)

                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "stats": stats}).encode())

            except Exception as e:
                print(f"❌ /feeds/stats: {e}", flush=True)
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif self.path == "/feeds/buscar":
            # Endpoint para validar ASINs de fuentes externas (Telegram, etc)
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                feed_id = body.get("audiencia_id", "")
                asins_externos = body.get("asins_telegram", [])

                if not feed_id:
                    raise ValueError("audiencia_id requerido")
                if not asins_externos:
                    raise ValueError("Sin ASINs para validar")

                # Cargar perfil del feed
                perfiles = cargar_perfiles()
                perfil = perfiles.get(feed_id)

                if not perfil:
                    raise ValueError(f"Feed '{feed_id}' no encontrado")

                print(f"🔍 /feeds/buscar → Feed: {feed_id}, ASINs: {len(asins_externos)}", flush=True)

                # Enriquecer ASINs con Amazon Creators API
                items = enriquecer_asins(asins_externos, perfil['filtros'].get('minSavingPercent', 1))
                print(f"  📦 {len(items)} items enriquecidos vía API", flush=True)

                # Aplicar filtros del perfil
                productos_validados = []
                for item in items:
                    precio = extraer_precio(item)

                    # Filtro de precio
                    if precio:
                        if precio < perfil['filtros'].get('minPrice', 0):
                            continue
                        if precio > perfil['filtros'].get('maxPrice', 999999):
                            continue

                    # Excluir keywords
                    titulo = item.get("itemInfo", {}).get("title", {}).get("displayValue", "").lower()
                    if any(ex.lower() in titulo for ex in perfil['filtros'].get('excludeKeywords', [])):
                        continue

                    # Parsear item
                    parsed = parsear_item(item)
                    if parsed:
                        # Verificar descuento mínimo
                        descuento_real = parsed.get("descuento_pct", 0)
                        min_descuento = perfil['filtros'].get('minSavingPercent', 1)

                        if descuento_real < min_descuento:
                            continue

                        productos_validados.append({
                            "asin": parsed.get("asin", ""),
                            "title": parsed.get("title", ""),
                            "price": parsed.get("price_discounted", precio),
                            "price_original": parsed.get("price_original", 0),
                            "price_discounted": parsed.get("price_discounted", precio),
                            "descuento_pct": descuento_real,
                            "discount": descuento_real,
                            "image": parsed.get("img", ""),
                            "img": parsed.get("img", ""),
                            "link": parsed.get("link", ""),
                            "source": "telegram"
                        })

                print(f"  ✅ {len(productos_validados)} productos pasaron filtros", flush=True)

                # Aplicar scoring de novedad usando historial del feed
                if _HV_OK and productos_validados:
                    historial_feed = cargar_historial_feed(feed_id)
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)

                    for producto in productos_validados:
                        asin = producto.get('asin')
                        title = producto.get('title', '')

                        # Extraer modelo usando la función del CORE
                        modelo = _hv._extraer_modelo(title) if hasattr(_hv, '_extraer_modelo') else ""

                        # Buscar en historial del feed
                        item_id = asin or modelo
                        if item_id and item_id in historial_feed:
                            registro = historial_feed[item_id]
                            ultima_vez = registro.get('ultima_vez', '')

                            try:
                                ultima_fecha = datetime.fromisoformat(ultima_vez.replace('Z', '+00:00'))
                                dias = (now - ultima_fecha).days

                                # Scoring de novedad
                                if dias > 14:
                                    score = 0.8
                                elif dias > 7:
                                    score = 0.5
                                elif dias > 3:
                                    score = 0.2
                                else:
                                    score = 0.0
                            except:
                                score = 0.5

                            producto['novedad_score'] = score
                        else:
                            producto['novedad_score'] = 1.0

                    ya_vistos = sum(1 for p in productos_validados if p.get('novedad_score', 1.0) < 1.0)
                    print(f"  📚 Historial: {ya_vistos} productos ya vistos", flush=True)

                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "items": productos_validados,
                    "total": len(productos_validados)
                }).encode())

            except Exception as e:
                print(f"❌ /feeds/buscar: {e}", flush=True)
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
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
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

        # Servir archivos .js del directorio base
        elif path.endswith(".js"):
            try:
                file_path = os.path.join(BASE_DIR, path.lstrip('/'))
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "application/javascript"); self.end_headers()
                    self.wfile.write(content.encode('utf-8'))
                else:
                    # Si no existe, devolver archivo vacío para evitar errores
                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "application/javascript"); self.end_headers()
                    self.wfile.write(b"// File not found but returning empty to prevent errors\nconsole.log('Placeholder JS file');\n")
            except Exception as e:
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/javascript"); self.end_headers()
                self.wfile.write(b"// Error loading JS file\n")

        # ==================== ENDPOINTS DE FEEDS ====================
        elif path == "/feeds/listar":
            try:
                perfiles = cargar_perfiles()
                audiencias = [{"id": k, **v} for k, v in perfiles.items()]
                print(f"📊 /feeds/listar → {len(audiencias)} audiencias", flush=True)
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "audiencias": audiencias}).encode())
            except Exception as e:
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif path.startswith("/feeds/"):
            try:
                # Extraer audiencia_id del path (ej: /feeds/coleccionistas?refresh=true)
                audiencia_id = path.split('/')[2].split('?')[0] if len(path.split('/')) > 2 else None
                if not audiencia_id:
                    raise ValueError("audiencia_id requerido")

                refresh = 'refresh=true' in path
                perfiles = cargar_perfiles()

                if audiencia_id not in perfiles:
                    self.send_response(404); self._cors()
                    self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Audiencia no encontrada"}).encode())
                    return

                perfil = perfiles[audiencia_id]
                cache = cargar_feed_cache()

                # Si tiene cache y no es refresh, verificar expiración
                if not refresh and audiencia_id in cache:
                    cache_data = cache[audiencia_id]
                    from datetime import datetime as dt, timedelta

                    # Obtener timestamp del cache
                    cache_timestamp_str = cache_data.get('timestamp')
                    if cache_timestamp_str:
                        try:
                            cache_timestamp = dt.fromisoformat(cache_timestamp_str)
                            now = dt.now()

                            # Determinar tiempo de expiración según configuración del perfil
                            frecuencia = perfil.get('frecuencia_actualizacion', 'diaria')

                            cache_valido = False
                            horas_restantes = 0

                            if frecuencia == 'diaria':
                                # Expiración por DÍA CALENDARIO (no por 24 horas exactas)
                                # Si el caché es de hoy, es válido. Si es de ayer o antes, expiró.
                                fecha_cache = cache_timestamp.date()
                                fecha_hoy = now.date()
                                cache_valido = (fecha_cache == fecha_hoy)
                                if cache_valido:
                                    # Calcular horas hasta medianoche
                                    medianoche = dt.combine(fecha_hoy + timedelta(days=1), dt.min.time())
                                    horas_restantes = int((medianoche - now).total_seconds() / 3600)
                            elif frecuencia == 'manual':
                                # Nunca expira automáticamente
                                cache_valido = True
                                horas_restantes = 999999
                            else:
                                # Expiración por HORAS EXACTAS (cada_12_horas, cada_6_horas, etc.)
                                expiracion_horas = {
                                    'cada_12_horas': 12,
                                    'cada_6_horas': 6,
                                    'cada_3_horas': 3
                                }.get(frecuencia, 24)

                                tiempo_transcurrido = now - cache_timestamp
                                cache_valido = tiempo_transcurrido < timedelta(hours=expiracion_horas)
                                if cache_valido:
                                    horas_restantes = int((timedelta(hours=expiracion_horas) - tiempo_transcurrido).total_seconds() / 3600)

                            # Si el cache sigue válido, retornarlo
                            if cache_valido:
                                horas_restantes = int((timedelta(hours=expiracion_horas) - tiempo_transcurrido).total_seconds() / 3600)

                                # Filtrar productos bloqueados del caché
                                productos_cache = cache_data.get('productos', [])
                                productos_filtrados = [
                                    p for p in productos_cache
                                    if not esta_bloqueado(audiencia_id, p.get('asin', ''))
                                ]

                                bloqueados_filtrados = len(productos_cache) - len(productos_filtrados)
                                if bloqueados_filtrados > 0:
                                    print(f"  🚫 {bloqueados_filtrados} productos descartados filtrados del caché", flush=True)

                                # RECALCULAR novedad_score con historial actualizado
                                # (el historial puede haber cambiado desde que se creó el cache)
                                historial_feed = cargar_historial_feed(audiencia_id)
                                from datetime import datetime as fecha_dt, timezone
                                now_recalc = fecha_dt.now(timezone.utc)

                                for producto in productos_filtrados:
                                    asin = producto.get('asin')
                                    title = producto.get('title', '')

                                    # Extraer modelo usando la función del CORE
                                    modelo = _hv._extraer_modelo(title) if _HV_OK and hasattr(_hv, '_extraer_modelo') else ""

                                    # Buscar en historial del feed
                                    item_id = asin or modelo
                                    if item_id and item_id in historial_feed:
                                        registro = historial_feed[item_id]
                                        ultima_vez = registro.get('ultima_vez', '')

                                        try:
                                            ultima_fecha = fecha_dt.fromisoformat(ultima_vez.replace('Z', '+00:00'))
                                            dias = (now_recalc - ultima_fecha).days

                                            # Scoring de novedad
                                            if dias > 14:
                                                score = 0.8
                                            elif dias > 7:
                                                score = 0.5
                                            elif dias > 3:
                                                score = 0.2
                                            else:
                                                score = 0.0
                                        except:
                                            score = 0.5

                                        producto['novedad_score'] = score
                                    else:
                                        producto['novedad_score'] = 1.0

                                ya_vistos_cache = sum(1 for p in productos_filtrados if p.get('novedad_score', 1.0) < 1.0)
                                print(f"📊 /feeds/{audiencia_id} → {len(productos_filtrados)} productos (cache, {ya_vistos_cache} ya vistos, válido {horas_restantes}h)", flush=True)

                                self.send_response(200); self._cors()
                                self.send_header("Content-Type", "application/json"); self.end_headers()
                                self.wfile.write(json.dumps({
                                    "ok": True,
                                    "audiencia": audiencia_id,
                                    "productos": productos_filtrados,
                                    "total": len(productos_filtrados),
                                    "from_cache": True,
                                    "cache_expira_en_horas": horas_restantes
                                }).encode())
                                return
                            else:
                                print(f"⏰ Cache de '{audiencia_id}' expirado (>{expiracion_horas}h), regenerando...", flush=True)
                        except Exception as e:
                            print(f"⚠️  Error verificando cache: {e}, regenerando...", flush=True)
                    else:
                        # Cache viejo sin timestamp, regenerar
                        print(f"⚠️  Cache sin timestamp, regenerando...", flush=True)

                # Buscar productos frescos
                print(f"🔄 Generando feed para '{audiencia_id}'...", flush=True)
                productos = []

                # Contadores para resumen de filtrado
                stats_filtrado = {
                    'total_procesados': 0,
                    'aceptados': 0,
                    'excluidos': 0,
                    'razones_exclusion': {
                        'sin_keywords_core': 0,
                        'precio_minimo': 0,
                        'precio_maximo': 0,
                        'keyword_excluida': 0,
                        'descuento_minimo': 0,
                        'bloqueado_manual': 0,
                        'sin_parsear': 0
                    }
                }

                # 0. SCRAPE TELEGRAM (si está configurado)
                telegram_sources = perfil.get('telegram_sources', [])
                if telegram_sources:
                    print(f"  📱 Scrapeando {len(telegram_sources)} canal(es) de Telegram...", flush=True)
                    try:
                        import telegram_utils
                        asins_telegram = telegram_utils.obtener_asins_de_telegram(perfil)

                        if asins_telegram:
                            print(f"    📦 {len(asins_telegram)} ASINs de Telegram a validar", flush=True)
                            # Enriquecer con Creators API
                            items_telegram = enriquecer_asins(asins_telegram, perfil['filtros'].get('minSavingPercent', 1))
                            print(f"    ✅ {len(items_telegram)} items enriquecidos desde Telegram", flush=True)

                            # Filtrar y agregar
                            items_validos_telegram = 0
                            items_sin_parse = 0

                            # 🎓 PRODUCTOS DE TELEGRAM: SIN FILTROS (fuente de aprendizaje)
                            # Los canales ya hacen curaduría manual, así que confiamos en ellos
                            # El historial se encargará de aprender nuevas categorías/productos
                            print(f"    🎓 Productos de Telegram: SIN FILTROS (modo aprendizaje)", flush=True)

                            for item in items_telegram:
                                parsed = parsear_item(item)
                                if not parsed:
                                    items_sin_parse += 1
                                    continue

                                # Verificar si fue descartado manualmente
                                asin = parsed.get("asin", "")
                                titulo = parsed.get("title", "")
                                titulo_short = (titulo[:60] + "...") if len(titulo) > 60 else titulo

                                if esta_bloqueado(audiencia_id, asin):
                                    print(f"      ❌ Excluido (Telegram): \"{titulo_short}\" (ASIN: {asin}) - Bloqueado manualmente", flush=True)
                                    continue

                                # Obtener precio (para mostrar, pero no filtrar)
                                precio = extraer_precio(item) or parsed.get("price_discounted", 0)

                                # Obtener nombre del canal
                                canal_nombre = telegram_sources[0].get('nombre', 'Telegram') if telegram_sources else 'Telegram'

                                # Agregar SIN FILTROS - todo pasa
                                productos.append({
                                    "asin": parsed.get("asin", ""),
                                    "title": parsed.get("title", ""),
                                    "price": parsed.get("price_discounted", precio),
                                    "discount": parsed.get("descuento_pct", 0),
                                    "image": parsed.get("img", ""),
                                    "link": parsed.get("link", ""),
                                    "source_channel": canal_nombre,
                                    "source_type": "telegram",
                                    "keyword_match": f"📱 {canal_nombre}"
                                })
                                items_validos_telegram += 1

                            print(f"    ✅ {items_validos_telegram} productos de Telegram agregados al feed", flush=True)
                            if items_sin_parse > 0:
                                print(f"    ⚠️  {items_sin_parse} items no pudieron parsearse", flush=True)

                    except Exception as e:
                        print(f"  ⚠️  Error scrapeando Telegram: {e}", flush=True)

                # 1. PROCESAR URLS FIJAS (si existen)
                urls_fijas = perfil.get('urls_fijas', [])
                if urls_fijas and _AZ_OK:
                    print(f"  🔗 Procesando {len(urls_fijas)} URLs fijas primero...", flush=True)
                    for url_config in urls_fijas:
                        try:
                            url = url_config.get('url', '')
                            desc = url_config.get('descripcion', 'URL Fija')

                            # Scrape ASINs
                            asins, estado = _az.scrape_url_custom(url, pages=3)
                            print(f"    🌐 {desc}: {len(asins)} ASINs extraídos", flush=True)

                            if asins:
                                # Enriquecer con Creators API
                                items = enriquecer_asins(asins, perfil['filtros'].get('minSavingPercent', 1))
                                print(f"    📦 {len(items)} items enriquecidos vía API", flush=True)

                                # Filtrar y parsear
                                items_validos = 0
                                for item in items:
                                    stats_filtrado['total_procesados'] += 1

                                    # Obtener título para logging
                                    titulo = item.get("itemInfo", {}).get("title", {}).get("displayValue", "")
                                    titulo_short = (titulo[:60] + "...") if len(titulo) > 60 else titulo

                                    precio = extraer_precio(item)
                                    if precio:
                                        min_price = perfil['filtros'].get('minPrice', 0)
                                        if precio < min_price:
                                            print(f"      ❌ Excluido: \"{titulo_short}\" - Precio ${precio:.0f} < mínimo ${min_price:.0f}", flush=True)
                                            stats_filtrado['excluidos'] += 1
                                            stats_filtrado['razones_exclusion']['precio_minimo'] += 1
                                            continue
                                        max_price = perfil['filtros'].get('maxPrice', 999999)
                                        if precio > max_price:
                                            print(f"      ❌ Excluido: \"{titulo_short}\" - Precio ${precio:.0f} > máximo ${max_price:.0f}", flush=True)
                                            stats_filtrado['excluidos'] += 1
                                            stats_filtrado['razones_exclusion']['precio_maximo'] += 1
                                            continue

                                    # Para URLs fijas: filtros MUY permisivos
                                    # El usuario configuró estas URLs porque son importantes

                                    # Solo aplicar exclusión contextual (palabras críticas)
                                    debe_excluir, razon_exclusion = evaluar_exclusion_contextual(
                                        titulo, perfil, es_url_fija=True
                                    )
                                    if debe_excluir:
                                        print(f"      ❌ Excluido: \"{titulo_short}\" - {razon_exclusion}", flush=True)
                                        stats_filtrado['excluidos'] += 1
                                        stats_filtrado['razones_exclusion']['keyword_excluida'] += 1
                                        continue

                                    # Parsear item
                                    parsed = parsear_item(item)
                                    if parsed:
                                        # Para URLs fijas: NO filtrar por descuento
                                        # Best Sellers pueden no tener descuento pero son importantes
                                        descuento_real = parsed.get("descuento_pct", 0)

                                        # Verificar si fue descartado manualmente
                                        asin = parsed.get("asin", "")
                                        if esta_bloqueado(audiencia_id, asin):
                                            print(f"      ❌ Excluido: \"{titulo_short}\" (ASIN: {asin}) - Bloqueado manualmente", flush=True)
                                            stats_filtrado['excluidos'] += 1
                                            stats_filtrado['razones_exclusion']['bloqueado_manual'] += 1
                                            continue

                                        productos.append({
                                            "asin": parsed.get("asin", ""),
                                            "title": parsed.get("title", ""),
                                            "price": parsed.get("price_discounted", precio),
                                            "discount": descuento_real,
                                            "image": parsed.get("img", ""),
                                            "link": parsed.get("link", ""),
                                            "source_channel": desc,
                                            "source_type": "url_fija",
                                            "keyword_match": f"🔗 {desc}"
                                        })
                                        items_validos += 1
                                        stats_filtrado['aceptados'] += 1

                                if items_validos > 0:
                                    print(f"    ✅ {desc}: {items_validos} productos agregados", flush=True)
                                else:
                                    print(f"    ⚠️  {desc}: 0 productos (descartados por filtros)", flush=True)

                        except Exception as e:
                            print(f"  ⚠️  Error con URL fija '{desc}': {e}", flush=True)
                            continue

                # 2. PROCESAR KEYWORDS
                keywords_procesados = 0
                print(f"  🔎 Procesando {len(perfil['keywords'])} keywords...", flush=True)

                for keyword in perfil['keywords']:
                    try:
                        items = buscar_productos_amazon(
                            keyword=keyword,
                            minSavingPercent=perfil['filtros'].get('minSavingPercent', 10),
                            maxPages=2
                        )

                        print(f"    🔎 '{keyword}': {len(items)} items de Amazon", flush=True)

                        # Filtrar según perfil
                        items_validos = 0
                        for item in items:
                            stats_filtrado['total_procesados'] += 1

                            # Obtener título para logging
                            titulo = item.get("itemInfo", {}).get("title", {}).get("displayValue", "")
                            titulo_short = (titulo[:60] + "...") if len(titulo) > 60 else titulo

                            precio = extraer_precio(item)
                            if precio:
                                min_price = perfil['filtros'].get('minPrice', 0)
                                if precio < min_price:
                                    print(f"      ❌ Excluido: \"{titulo_short}\" - Precio ${precio:.0f} < mínimo ${min_price:.0f}", flush=True)
                                    stats_filtrado['excluidos'] += 1
                                    stats_filtrado['razones_exclusion']['precio_minimo'] += 1
                                    continue
                                max_price = perfil['filtros'].get('maxPrice', 999999)
                                if precio > max_price:
                                    print(f"      ❌ Excluido: \"{titulo_short}\" - Precio ${precio:.0f} > máximo ${max_price:.0f}", flush=True)
                                    stats_filtrado['excluidos'] += 1
                                    stats_filtrado['razones_exclusion']['precio_maximo'] += 1
                                    continue

                            # Verificar que el producto tenga al menos UNA keyword core
                            keywords_perfil = [kw.lower() for kw in perfil.get('keywords', [])]
                            tiene_keyword_core = any(kw in titulo.lower() for kw in keywords_perfil)

                            if not tiene_keyword_core:
                                print(f"      ❌ Excluido: \"{titulo_short}\" - Sin relación con keywords core", flush=True)
                                stats_filtrado['excluidos'] += 1
                                stats_filtrado['razones_exclusion']['sin_keywords_core'] += 1
                                continue

                            # Evaluación contextual de exclusión
                            debe_excluir, razon_exclusion = evaluar_exclusion_contextual(
                                titulo, perfil, es_url_fija=False
                            )
                            if debe_excluir:
                                print(f"      ❌ Excluido: \"{titulo_short}\" - {razon_exclusion}", flush=True)
                                stats_filtrado['excluidos'] += 1
                                stats_filtrado['razones_exclusion']['keyword_excluida'] += 1
                                continue

                            # Parsear item
                            parsed = parsear_item(item)
                            if parsed:
                                # Verificar descuento real (no confiar solo en la API)
                                descuento_real = parsed.get("descuento_pct", 0)
                                min_descuento = perfil['filtros'].get('minSavingPercent', 1)

                                if descuento_real < min_descuento:
                                    print(f"      ❌ Excluido: \"{titulo_short}\" - Descuento {descuento_real}% < mínimo {min_descuento}%", flush=True)
                                    stats_filtrado['excluidos'] += 1
                                    stats_filtrado['razones_exclusion']['descuento_minimo'] += 1
                                    continue

                                # Verificar si fue descartado manualmente
                                asin = parsed.get("asin", "")
                                if esta_bloqueado(audiencia_id, asin):
                                    print(f"      ❌ Excluido: \"{titulo_short}\" (ASIN: {asin}) - Bloqueado manualmente", flush=True)
                                    stats_filtrado['excluidos'] += 1
                                    stats_filtrado['razones_exclusion']['bloqueado_manual'] += 1
                                    continue

                                # parsear_item() ya devuelve todo lo que necesitamos
                                productos.append({
                                    "asin": parsed.get("asin", ""),
                                    "title": parsed.get("title", ""),
                                    "price": parsed.get("price_discounted", precio),
                                    "discount": descuento_real,
                                    "image": parsed.get("img", ""),
                                    "link": parsed.get("link", ""),
                                    "source_channel": f"Keyword: {keyword}",
                                    "source_type": "keyword",
                                    "keyword_match": keyword
                                })
                                items_validos += 1
                                stats_filtrado['aceptados'] += 1

                        keywords_procesados += 1
                        if items_validos > 0:
                            print(f"  ✅ {keywords_procesados}/{len(perfil['keywords'])} '{keyword}': {items_validos} productos agregados", flush=True)
                        else:
                            print(f"  ⚠️  {keywords_procesados}/{len(perfil['keywords'])} '{keyword}': 0 productos (descartados por filtros)", flush=True)

                    except Exception as e:
                        print(f"  ⚠️  Error con keyword '{keyword}': {e}", flush=True)
                        continue

                # Deduplicar por ASIN
                productos_unicos = {p['asin']: p for p in productos if p.get('asin')}.values()
                productos_finales = list(productos_unicos)

                # Aplicar scoring usando LÓGICA del core pero HISTORIAL del feed
                if _HV_OK:
                    # Cargar historial específico del feed
                    historial_feed = cargar_historial_feed(audiencia_id)

                    # Usar la LÓGICA de historial_variedad pero con el historial del feed
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)

                    for producto in productos_finales:
                        asin = producto.get('asin')
                        title = producto.get('title', '')

                        # Extraer modelo usando la función del CORE
                        modelo = _hv._extraer_modelo(title) if hasattr(_hv, '_extraer_modelo') else ""

                        # Buscar en historial del feed (no del core)
                        item_id = asin or modelo
                        if item_id and item_id in historial_feed:
                            # Calcular score usando la LÓGICA del core
                            registro = historial_feed[item_id]
                            ultima_vez = registro.get('ultima_vez', '')

                            try:
                                ultima_fecha = datetime.fromisoformat(ultima_vez.replace('Z', '+00:00'))
                                dias = (now - ultima_fecha).days

                                # Misma lógica de scoring que el core
                                if dias > 14:
                                    score = 0.8
                                elif dias > 7:
                                    score = 0.5
                                elif dias > 3:
                                    score = 0.2
                                else:
                                    score = 0.0
                            except:
                                score = 0.5

                            producto['novedad_score'] = score
                        else:
                            producto['novedad_score'] = 1.0

                    ya_vistos = sum(1 for p in productos_finales if p.get('novedad_score', 1.0) < 1.0)
                    print(f"  📚 Historial Feed '{audiencia_id}': {ya_vistos} ya vistos", flush=True)
                else:
                    # Fallback simple
                    historial = cargar_historial_feed(audiencia_id)
                    for producto in productos_finales:
                        asin = producto.get('asin')
                        producto['novedad_score'] = 0.5 if (asin and asin in historial) else 1.0
                    print(f"  📚 Historial Feed: {sum(1 for p in productos_finales if p.get('novedad_score', 1.0) < 1.0)} ya vistos", flush=True)

                # Ordenar por novedad_score (prioridad) y descuento (secundario)
                # novedad_score: 1.0 (nuevos) aparecen primero, 0.0 (recién vistos) al final
                productos_finales.sort(key=lambda x: (
                    x.get('novedad_score', 0.5),  # Prioridad 1: novedad
                    x.get('discount', 0)          # Prioridad 2: descuento
                ), reverse=True)

                # Guardar en cache
                from datetime import datetime as dt
                now = dt.now()
                cache[audiencia_id] = {
                    "fecha": now.strftime('%Y-%m-%d'),
                    "timestamp": now.isoformat(),  # Timestamp preciso para expiración
                    "productos": productos_finales
                }
                guardar_feed_cache(cache)

                # IMPRIMIR RESUMEN DE FILTRADO
                print(f"\n📊 RESUMEN DE FILTRADO:", flush=True)
                print(f"  📦 Total procesados: {stats_filtrado['total_procesados']} productos", flush=True)
                print(f"  ✅ Aceptados: {stats_filtrado['aceptados']} productos", flush=True)
                print(f"  ❌ Excluidos: {stats_filtrado['excluidos']} productos", flush=True)

                if stats_filtrado['excluidos'] > 0:
                    print(f"\n  📋 Razones de exclusión:", flush=True)
                    razones = stats_filtrado['razones_exclusion']
                    if razones['sin_keywords_core'] > 0:
                        print(f"    • Sin keywords core: {razones['sin_keywords_core']}", flush=True)
                    if razones['precio_minimo'] > 0:
                        print(f"    • Precio < mínimo: {razones['precio_minimo']}", flush=True)
                    if razones['precio_maximo'] > 0:
                        print(f"    • Precio > máximo: {razones['precio_maximo']}", flush=True)
                    if razones['descuento_minimo'] > 0:
                        print(f"    • Descuento < mínimo: {razones['descuento_minimo']}", flush=True)
                    if razones['keyword_excluida'] > 0:
                        print(f"    • Keyword excluida: {razones['keyword_excluida']}", flush=True)
                    if razones['bloqueado_manual'] > 0:
                        print(f"    • Bloqueado manualmente: {razones['bloqueado_manual']}", flush=True)

                tasa_aprobacion = (stats_filtrado['aceptados'] / stats_filtrado['total_procesados'] * 100) if stats_filtrado['total_procesados'] > 0 else 0
                print(f"\n  📈 Tasa de aprobación: {tasa_aprobacion:.1f}%", flush=True)

                print(f"\n✅ Feed '{audiencia_id}' generado: {len(productos_finales)} productos únicos", flush=True)

                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "audiencia": audiencia_id,
                    "productos": productos_finales,
                    "total": len(productos_finales),
                    "from_cache": False
                }).encode())

            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
        # ==================== FIN ENDPOINTS DE FEEDS ====================

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


