#!/usr/bin/env python3
"""
Scraper de canales de Telegram para alimentar feeds de audiencia.
Lee canales públicos, extrae ofertas de Amazon/ML y las valida con la API.
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime, timezone
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuración de canales por feed
TELEGRAM_SOURCES = {
    "coleccionistas": [
        {
            "url": "https://t.me/s/TheGeekChroniclesOfertas",
            "nombre": "The Geek Chronicles"
        }
    ]
}

def extraer_asin_de_url(url):
    """
    Extrae ASIN de URLs de Amazon (completas o cortas).
    Soporta: amazon.com.mx/dp/ASIN, /gp/product/ASIN, link.amazon/short
    """
    if not url:
        return None

    # URLs normales de Amazon
    if 'amazon' in url.lower():
        # Buscar patrón /dp/ASIN o /gp/product/ASIN
        match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url, re.IGNORECASE)
        if match:
            return match.group(1)

        # Intentar desde query params
        parsed = urlparse(url)
        if parsed.path:
            parts = parsed.path.strip('/').split('/')
            for i, part in enumerate(parts):
                if part.lower() in ['dp', 'product'] and i + 1 < len(parts):
                    candidate = parts[i + 1].split('?')[0]
                    if len(candidate) == 10 and candidate.isalnum():
                        return candidate

    return None

def resolver_enlace_corto(short_url):
    """
    Resuelve enlaces cortos (link.amazon, amzn.to) siguiendo redirects.
    Retorna la URL final de Amazon.
    """
    try:
        response = requests.head(short_url, allow_redirects=True, timeout=10)
        return response.url
    except:
        return short_url

def scrape_telegram_channel(channel_url, max_mensajes=50):
    """
    Scrape de canal público de Telegram.
    Retorna lista de ofertas encontradas con ASINs.
    """
    print(f"\n📡 Scrapeando: {channel_url}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(channel_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        mensajes = soup.find_all('div', class_='tgme_widget_message', limit=max_mensajes)

        ofertas = []

        for msg in mensajes:
            try:
                # Extraer texto del mensaje
                texto_elem = msg.find('div', class_='tgme_widget_message_text')
                if not texto_elem:
                    continue

                texto = texto_elem.get_text(strip=True)

                # Extraer enlaces
                enlaces = msg.find_all('a', href=True)

                for enlace in enlaces:
                    href = enlace['href']

                    # Filtrar solo enlaces de Amazon
                    if 'amazon' in href.lower() or 'amzn.to' in href.lower() or 'link.amazon' in href.lower():
                        # Resolver si es corto
                        if 'link.amazon' in href or 'amzn.to' in href:
                            print(f"  🔗 Resolviendo enlace corto: {href[:50]}...")
                            href = resolver_enlace_corto(href)

                        asin = extraer_asin_de_url(href)

                        if asin:
                            # Extraer timestamp si está disponible
                            time_elem = msg.find('time')
                            timestamp = time_elem['datetime'] if time_elem and 'datetime' in time_elem.attrs else None

                            ofertas.append({
                                'asin': asin,
                                'url': href,
                                'texto': texto[:200],  # Primeros 200 chars
                                'timestamp': timestamp,
                                'fuente': 'telegram'
                            })
                            print(f"  ✅ ASIN encontrado: {asin}")

            except Exception as e:
                print(f"  ⚠️  Error procesando mensaje: {e}")
                continue

        print(f"  📦 Total ASINs extraídos: {len(ofertas)}")
        return ofertas

    except Exception as e:
        print(f"  ❌ Error scrapeando canal: {e}")
        return []

def validar_con_amazon_api(asins, feed_id):
    """
    Valida ASINs con Amazon Creators API aplicando filtros del feed.
    """
    print(f"\n🔍 Validando {len(asins)} ASINs con Amazon API...")

    try:
        # Llamar al endpoint local de feeds que ya tiene toda la lógica
        response = requests.post(
            'http://localhost:8000/feeds/buscar',
            json={
                'audiencia_id': feed_id,
                'asins_telegram': asins  # Nueva forma de pasar ASINs directos
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            print(f"  ✅ {len(items)} productos válidos después de filtros")
            return items
        else:
            print(f"  ❌ Error API: {response.status_code}")
            return []

    except Exception as e:
        print(f"  ❌ Error validando: {e}")
        return []

def exportar_a_sheets(items, feed_id):
    """
    Exporta items validados a Google Sheets del feed.
    """
    if not items:
        return

    print(f"\n📊 Exportando {len(items)} items a Google Sheets...")

    try:
        # Llamar al endpoint de export del feed
        response = requests.post(
            f'http://localhost:8000/feeds/export-sheets',
            json={
                'audiencia_id': feed_id,
                'items': items
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Exportado exitosamente: {result.get('rows', 0)} filas")
        else:
            print(f"  ❌ Error exportando: {response.status_code}")

    except Exception as e:
        print(f"  ❌ Error en export: {e}")

def procesar_feed_desde_telegram(feed_id):
    """
    Proceso completo: scrape → validar → exportar para un feed específico.
    """
    print(f"\n{'='*60}")
    print(f"🎯 Procesando feed: {feed_id}")
    print(f"{'='*60}")

    if feed_id not in TELEGRAM_SOURCES:
        print(f"❌ No hay fuentes de Telegram configuradas para '{feed_id}'")
        return

    todas_ofertas = []

    # Scrape todos los canales configurados para este feed
    for source in TELEGRAM_SOURCES[feed_id]:
        ofertas = scrape_telegram_channel(source['url'])
        todas_ofertas.extend(ofertas)

    if not todas_ofertas:
        print("\n⚠️  No se encontraron ofertas")
        return

    # Deduplicar por ASIN
    asins_unicos = list(set(o['asin'] for o in todas_ofertas))
    print(f"\n📋 ASINs únicos a validar: {len(asins_unicos)}")

    # Validar con API y aplicar filtros
    items_validados = validar_con_amazon_api(asins_unicos, feed_id)

    if items_validados:
        # Exportar a Sheets
        exportar_a_sheets(items_validados, feed_id)

        # Guardar en archivo local para debug
        output_file = os.path.join(BASE_DIR, f'feeds/{feed_id}/telegram_import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(items_validados, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Guardado en: {output_file}")

    print(f"\n{'='*60}")
    print(f"✅ Proceso completado")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    import sys

    # Usar argumento o default a coleccionistas
    feed_id = sys.argv[1] if len(sys.argv) > 1 else 'coleccionistas'

    procesar_feed_desde_telegram(feed_id)
