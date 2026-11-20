"""
Utilidades para scraping de canales de Telegram.
Se integra automáticamente con el sistema de feeds.
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

def extraer_asin_de_url(url):
    """
    Extrae ASIN de URLs de Amazon (completas o cortas).
    """
    if not url:
        return None

    if 'amazon' in url.lower():
        match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url, re.IGNORECASE)
        if match:
            return match.group(1)

    return None

def es_link_mercadolibre(url):
    """
    Detecta si una URL apunta a MercadoLibre (completa o acortada tipo meli.la).
    """
    if not url:
        return False
    dominios_ml = ['mercadolibre.com', 'meli.la']
    return any(d in url.lower() for d in dominios_ml)

def extraer_mlm_de_url(url):
    """
    Extrae el ID de producto de MercadoLibre (ej. MLM60359404) de una URL.
    Solo funciona con links directos a producto; links de afiliado/social
    que no apuntan a un producto específico retornan None.
    """
    if not url:
        return None
    match = re.search(r'MLM-?(\d{6,})', url, re.IGNORECASE)
    return f"MLM{match.group(1)}" if match else None

def resolver_enlace_corto(short_url):
    """
    Resuelve enlaces cortos siguiendo redirects.
    Usa GET en vez de HEAD porque algunos servicios requieren el request completo.
    """
    try:
        # Usar GET con allow_redirects para obtener la URL final real
        response = requests.get(short_url, allow_redirects=True, timeout=10,
                               headers={'User-Agent': 'Mozilla/5.0'})
        final_url = response.url
        print(f"      🔗 {short_url.split('/')[-1]} → {final_url.split('/')[-2:] if '/' in final_url else final_url[:50]}", flush=True)
        return final_url
    except Exception as e:
        print(f"      ⚠️  Error resolviendo {short_url}: {e}", flush=True)
        return short_url

def scrape_telegram_ultimos_dias(channel_url, dias=5, nombre_canal=None):
    """
    Scrape de canal público de Telegram.
    Filtra solo mensajes de los últimos N días.
    Retorna (asins_metadata, ml_metadata):
      - asins_metadata: {asin: {"timestamp": ts, "canal": nombre_canal}} (Amazon)
      - ml_metadata: {mlm_id: {"timestamp": ts, "url": url_final, "canal": nombre_canal}} (MercadoLibre)

    nombre_canal: nombre a mostrar del canal (para saber qué canal trajo cada producto
    cuando un feed tiene varios canales de Telegram configurados).
    """
    if not nombre_canal:
        nombre_canal = channel_url.split('/')[-1]
    print(f"  📡 Scrapeando Telegram (últimos {dias} días): {channel_url.split('/')[-1]}", flush=True)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    # Calcular fecha límite (últimos N días)
    now = datetime.now(timezone.utc)
    fecha_limite = now - timedelta(days=dias)

    asins_metadata = {}  # {asin: {"timestamp": ts, "canal": nombre_canal}}
    ml_metadata = {}     # {mlm_id: {"timestamp": ts, "url": url_final, "canal": nombre_canal}}

    # ✅ PAGINACIÓN: una sola petición a t.me/s/canal solo trae ~20 mensajes
    # (unas pocas horas en canales activos). Hay que pedir páginas anteriores
    # con ?before={id_mensaje} hasta cubrir los `dias` solicitados.
    before = None
    MAX_PAGINAS = 30  # Tope de seguridad (~600 mensajes) para no pedir infinito
    llego_al_limite = False

    for pagina in range(MAX_PAGINAS):
        url_pagina = channel_url if before is None else f"{channel_url}?before={before}"
        try:
            response = requests.get(url_pagina, headers=headers, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"    ⚠️  Error scrapeando Telegram (página {pagina + 1}): {e}", flush=True)
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        mensajes = soup.find_all('div', class_='tgme_widget_message')

        if not mensajes:
            break  # Se llegó al inicio del canal

        ids_mensajes = []
        for msg in mensajes:
            try:
                data_post = msg.get('data-post', '')
                if '/' in data_post:
                    ids_mensajes.append(int(data_post.split('/')[-1]))

                # Extraer timestamp del mensaje
                time_elem = msg.find('time')
                if not time_elem or 'datetime' not in time_elem.attrs:
                    continue

                timestamp_str = time_elem['datetime']
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

                # Filtrar solo mensajes recientes
                if timestamp < fecha_limite:
                    llego_al_limite = True
                    continue

                # Extraer enlaces
                enlaces = msg.find_all('a', href=True)

                for enlace in enlaces:
                    href = enlace['href']
                    href_lower = href.lower()

                    # Amazon
                    if 'amazon' in href_lower or 'amzn.to' in href_lower or 'link.amazon' in href_lower:
                        # Resolver si es corto
                        if 'link.amazon' in href_lower or 'amzn.to' in href_lower:
                            href = resolver_enlace_corto(href)

                        asin = extraer_asin_de_url(href)
                        if asin:
                            # Guardar solo el timestamp más reciente para cada ASIN
                            if asin not in asins_metadata or timestamp_str > asins_metadata[asin]["timestamp"]:
                                asins_metadata[asin] = {"timestamp": timestamp_str, "canal": nombre_canal}
                        continue

                    # MercadoLibre
                    if es_link_mercadolibre(href):
                        # Los links de ML en Telegram casi siempre son acortados (meli.la, /sec/)
                        href_final = resolver_enlace_corto(href)
                        mlm_id = extraer_mlm_de_url(href_final)

                        # Si no se encontró ID directo y es un link de "perfil social"
                        # (/social/tienda?matt_word=...), ese link no apunta a un producto
                        # específico sino a una página de afiliado — hay que visitarla y
                        # tomar el producto DESTACADO (el primero que aparece, marcado por
                        # ML internamente), no cualquier recomendación genérica de abajo.
                        if not mlm_id and '/social/' in href_final:
                            import scraper_ml
                            mlm_id, href_producto = scraper_ml.resolver_producto_destacado_social(href_final)
                            if mlm_id:
                                href_final = href_producto

                        if mlm_id:
                            if mlm_id not in ml_metadata or timestamp_str > ml_metadata[mlm_id]["timestamp"]:
                                ml_metadata[mlm_id] = {"timestamp": timestamp_str, "url": href_final, "canal": nombre_canal}
                        # Si aún así no se pudo extraer MLM, se ignora (no era un producto)

            except Exception as e:
                continue

        print(f"    📄 Página {pagina + 1}: {len(mensajes)} mensajes", flush=True)

        if llego_al_limite:
            break  # Ya pasamos la fecha límite, no hace falta pedir páginas más viejas

        if not ids_mensajes:
            break  # No se pudo extraer ID de paginación, evitar loop infinito

        nuevo_before = min(ids_mensajes)
        if before is not None and nuevo_before >= before:
            break  # No avanzó — evitar loop infinito
        before = nuevo_before

    print(f"    ✅ {len(asins_metadata)} ASINs de Amazon + {len(ml_metadata)} productos de MercadoLibre", flush=True)
    return asins_metadata, ml_metadata

def obtener_asins_de_telegram(perfil):
    """
    Obtiene productos de Amazon y MercadoLibre de todos los canales de Telegram
    configurados en un perfil.
    Retorna (asins_metadata, ml_metadata):
      - asins_metadata: {asin: {"timestamp": ts, "canal": nombre_canal}} (Amazon)
      - ml_metadata: {mlm_id: {"timestamp": ts, "url": url_final, "canal": nombre_canal}} (MercadoLibre)
    """
    telegram_sources = perfil.get('telegram_sources', [])
    if not telegram_sources:
        return {}, {}

    todos_asins_metadata = {}
    todos_ml_metadata = {}
    for source in telegram_sources:
        url = source.get('url')
        dias = source.get('dias_historico', 5)  # Por defecto 5 días
        nombre_canal = source.get('nombre') or (url.split('/')[-1] if url else 'Telegram')
        if url:
            asins_metadata, ml_metadata = scrape_telegram_ultimos_dias(url, dias, nombre_canal)

            # Merge Amazon manteniendo el timestamp más reciente (y su canal)
            for asin, data in asins_metadata.items():
                if asin not in todos_asins_metadata or data["timestamp"] > todos_asins_metadata[asin]["timestamp"]:
                    todos_asins_metadata[asin] = data

            # Merge MercadoLibre manteniendo el timestamp más reciente (y su canal)
            for mlm_id, data in ml_metadata.items():
                if mlm_id not in todos_ml_metadata or data["timestamp"] > todos_ml_metadata[mlm_id]["timestamp"]:
                    todos_ml_metadata[mlm_id] = data

    return todos_asins_metadata, todos_ml_metadata
