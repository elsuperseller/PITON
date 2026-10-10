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

def scrape_telegram_ultimos_dias(channel_url, dias=5):
    """
    Scrape de canal público de Telegram.
    Filtra solo mensajes de los últimos N días.
    Retorna diccionario con ASINs y metadata (timestamp).
    """
    print(f"  📡 Scrapeando Telegram (últimos {dias} días): {channel_url.split('/')[-1]}", flush=True)

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(channel_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        mensajes = soup.find_all('div', class_='tgme_widget_message', limit=100)

        # Calcular fecha límite (últimos N días)
        now = datetime.now(timezone.utc)
        fecha_limite = now - timedelta(days=dias)

        asins_metadata = {}  # {asin: timestamp}

        for msg in mensajes:
            try:
                # Extraer timestamp del mensaje
                time_elem = msg.find('time')
                if not time_elem or 'datetime' not in time_elem.attrs:
                    continue

                timestamp_str = time_elem['datetime']
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

                # Filtrar solo mensajes recientes
                if timestamp < fecha_limite:
                    continue

                # Extraer enlaces
                enlaces = msg.find_all('a', href=True)

                for enlace in enlaces:
                    href = enlace['href']

                    # Filtrar solo enlaces de Amazon
                    if 'amazon' in href.lower() or 'amzn.to' in href.lower() or 'link.amazon' in href.lower():
                        # Resolver si es corto
                        if 'link.amazon' in href or 'amzn.to' in href:
                            href = resolver_enlace_corto(href)

                        asin = extraer_asin_de_url(href)
                        if asin:
                            # Guardar solo el timestamp más reciente para cada ASIN
                            if asin not in asins_metadata or timestamp > asins_metadata[asin]:
                                asins_metadata[asin] = timestamp_str

            except Exception as e:
                continue

        print(f"    ✅ {len(asins_metadata)} ASINs únicos de Telegram", flush=True)
        return asins_metadata  # Retorna dict {asin: timestamp}

    except Exception as e:
        print(f"    ⚠️  Error scrapeando Telegram: {e}", flush=True)
        return {}

def obtener_asins_de_telegram(perfil):
    """
    Obtiene ASINs de todos los canales de Telegram configurados en un perfil.
    Retorna dict {asin: timestamp} con el timestamp más reciente para cada ASIN.
    """
    telegram_sources = perfil.get('telegram_sources', [])
    if not telegram_sources:
        return {}

    todos_asins_metadata = {}
    for source in telegram_sources:
        url = source.get('url')
        dias = source.get('dias_historico', 5)  # Por defecto 5 días
        if url:
            asins_metadata = scrape_telegram_ultimos_dias(url, dias)
            # Merge manteniendo el timestamp más reciente
            for asin, timestamp in asins_metadata.items():
                if asin not in todos_asins_metadata:
                    todos_asins_metadata[asin] = timestamp
                else:
                    # Comparar timestamps y quedarse con el más reciente
                    if timestamp > todos_asins_metadata[asin]:
                        todos_asins_metadata[asin] = timestamp

    return todos_asins_metadata  # {asin: timestamp}
