#!/usr/bin/env python3
"""
Extrae ofertas de canales de Telegram de días anteriores y las publica en tu canal.

Uso:
    python telegram_publisher.py --dias 1                    # Ayer
    python telegram_publisher.py --dias 2                    # Últimos 2 días
    python telegram_publisher.py --fecha 2026-10-08          # Día específico
    python telegram_publisher.py --dias 1 --publicar         # Extraer Y publicar
"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from telegram_utils import scrape_telegram_ultimos_dias, extraer_asin_de_url
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def cargar_canales_telegram():
    """Carga todos los canales configurados en perfiles_audiencia.json"""
    perfiles_path = os.path.join(BASE_DIR, 'feeds/perfiles_audiencia.json')

    with open(perfiles_path, 'r', encoding='utf-8') as f:
        perfiles = json.load(f)

    canales = []
    for feed_id, perfil in perfiles.items():
        telegram_sources = perfil.get('telegram_sources', [])
        for source in telegram_sources:
            canales.append({
                'feed_id': feed_id,
                'feed_nombre': perfil.get('nombre', feed_id),
                'url': source.get('url'),
                'nombre': source.get('nombre', 'Sin nombre'),
            })

    return canales

def scrape_telegram_con_fecha(channel_url, fecha_inicio, fecha_fin):
    """
    Scrape mensajes de Telegram en un rango de fechas específico.
    Retorna lista de ofertas con ASIN, texto, timestamp.
    """
    print(f"\n📡 Scrapeando: {channel_url.split('/')[-1]}")
    print(f"   📅 Desde: {fecha_inicio.strftime('%Y-%m-%d')} hasta {fecha_fin.strftime('%Y-%m-%d')}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(channel_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        mensajes = soup.find_all('div', class_='tgme_widget_message', limit=200)

        ofertas = []

        for msg in mensajes:
            try:
                # Extraer timestamp
                time_elem = msg.find('time')
                if not time_elem or 'datetime' not in time_elem.attrs:
                    continue

                timestamp_str = time_elem['datetime']
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

                # Filtrar por rango de fechas
                if not (fecha_inicio <= timestamp <= fecha_fin):
                    continue

                # Extraer texto
                texto_elem = msg.find('div', class_='tgme_widget_message_text')
                texto = texto_elem.get_text(strip=True) if texto_elem else ""

                # Extraer enlaces de Amazon
                enlaces = msg.find_all('a', href=True)

                for enlace in enlaces:
                    href = enlace['href']

                    if 'amazon' in href.lower() or 'amzn.to' in href.lower() or 'link.amazon' in href.lower():
                        # Resolver enlaces cortos
                        if 'link.amazon' in href or 'amzn.to' in href:
                            try:
                                r = requests.get(href, allow_redirects=True, timeout=10,
                                               headers={'User-Agent': 'Mozilla/5.0'})
                                href = r.url
                            except:
                                pass

                        asin = extraer_asin_de_url(href)

                        if asin:
                            ofertas.append({
                                'asin': asin,
                                'url': href,
                                'texto': texto[:300],
                                'timestamp': timestamp_str,
                                'fecha': timestamp.strftime('%Y-%m-%d %H:%M'),
                            })

            except Exception as e:
                continue

        print(f"   ✅ {len(ofertas)} ofertas encontradas")
        return ofertas

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

def enriquecer_ofertas_con_api(ofertas):
    """
    Enriquece ofertas con datos de Amazon API.
    Retorna lista de productos con precio, descuento, etc.
    """
    if not ofertas:
        return []

    asins = list(set(o['asin'] for o in ofertas))

    print(f"\n🔍 Enriqueciendo {len(asins)} ASINs únicos con Amazon API...")

    try:
        # Importar función de servidor
        import sys
        sys.path.insert(0, BASE_DIR)
        from servidor import enriquecer_asins, parsear_item

        items_api = enriquecer_asins(asins, minSavingPercent=1)

        productos = []
        for item in items_api:
            p = parsear_item(item)
            if p:
                # Agregar info del mensaje original de Telegram
                oferta_original = next((o for o in ofertas if o['asin'] == p['asin']), None)
                if oferta_original:
                    p['telegram_texto'] = oferta_original['texto']
                    p['telegram_fecha'] = oferta_original['fecha']

                productos.append(p)

        print(f"   ✅ {len(productos)} productos enriquecidos")
        return productos

    except Exception as e:
        print(f"   ❌ Error enriqueciendo: {e}")
        return []

def publicar_a_telegram(productos, bot_token, chat_id):
    """
    Publica productos a un canal de Telegram usando bot.

    Configuración:
    1. Crea un bot: @BotFather en Telegram
    2. Agrega el bot a tu canal como administrador
    3. Obtén el chat_id de tu canal
    """
    if not productos:
        print("\n⚠️  Sin productos para publicar")
        return

    print(f"\n📤 Publicando {len(productos)} productos a Telegram...")

    publicados = 0
    errores = 0

    for p in productos:
        try:
            # Formatear mensaje
            titulo = p['title'][:100]
            precio = f"${p['price_discounted']:.2f}"
            descuento = f"{p['descuento_pct']}%"
            link = p['link']

            mensaje = f"""🔥 <b>{titulo}</b>

💰 Precio: <b>{precio}</b> ({descuento} OFF)
🔗 <a href="{link}">Ver en Amazon</a>

{p.get('telegram_texto', '')[:100]}
"""

            # Enviar a Telegram
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': mensaje,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }

            r = requests.post(url, json=data, timeout=10)

            if r.status_code == 200:
                publicados += 1
            else:
                errores += 1
                print(f"   ⚠️  Error publicando {p['asin']}: {r.status_code}")

        except Exception as e:
            errores += 1
            print(f"   ❌ Error: {e}")

    print(f"\n✅ Publicados: {publicados}")
    if errores:
        print(f"⚠️  Errores: {errores}")

def main():
    parser = argparse.ArgumentParser(description='Extrae ofertas de Telegram de días anteriores')
    parser.add_argument('--dias', type=int, help='Número de días hacia atrás (ej: 1 para ayer)')
    parser.add_argument('--fecha', type=str, help='Fecha específica YYYY-MM-DD')
    parser.add_argument('--publicar', action='store_true', help='Publicar a tu canal de Telegram')
    parser.add_argument('--bot-token', type=str, help='Token del bot de Telegram')
    parser.add_argument('--chat-id', type=str, help='Chat ID de tu canal')
    parser.add_argument('--output', type=str, default='telegram_extraido.json', help='Archivo de salida')

    args = parser.parse_args()

    # Determinar rango de fechas
    if args.fecha:
        fecha_especifica = datetime.strptime(args.fecha, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        fecha_inicio = fecha_especifica
        fecha_fin = fecha_especifica + timedelta(days=1)
        print(f"📅 Extrayendo ofertas del: {args.fecha}")
    elif args.dias:
        ahora = datetime.now(timezone.utc)
        fecha_fin = ahora - timedelta(days=args.dias - 1)
        fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
        fecha_inicio = fecha_fin - timedelta(days=1)
        fecha_inicio = fecha_inicio.replace(hour=0, minute=0, second=0)
        print(f"📅 Extrayendo ofertas de hace {args.dias} día(s)")
    else:
        # Por defecto: ayer
        ahora = datetime.now(timezone.utc)
        fecha_fin = ahora - timedelta(days=0)
        fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
        fecha_inicio = fecha_fin - timedelta(days=1)
        fecha_inicio = fecha_inicio.replace(hour=0, minute=0, second=0)
        print(f"📅 Extrayendo ofertas de ayer (sin --dias ni --fecha)")

    # Cargar canales
    canales = cargar_canales_telegram()

    if not canales:
        print("❌ No hay canales de Telegram configurados")
        return

    print(f"\n📱 Canales configurados: {len(canales)}")
    for canal in canales:
        print(f"   • {canal['nombre']} ({canal['feed_nombre']})")

    # Scrape todos los canales
    todas_ofertas = []

    for canal in canales:
        ofertas = scrape_telegram_con_fecha(canal['url'], fecha_inicio, fecha_fin)
        for o in ofertas:
            o['canal_nombre'] = canal['nombre']
            o['feed'] = canal['feed_nombre']
        todas_ofertas.extend(ofertas)

    if not todas_ofertas:
        print("\n⚠️  No se encontraron ofertas en el rango de fechas")
        return

    # Deduplicar
    asins_vistos = set()
    ofertas_unicas = []
    for o in todas_ofertas:
        if o['asin'] not in asins_vistos:
            asins_vistos.add(o['asin'])
            ofertas_unicas.append(o)

    print(f"\n📦 Total ofertas únicas: {len(ofertas_unicas)}")

    # Enriquecer con API
    productos_raw = enriquecer_ofertas_con_api(ofertas_unicas)

    # ========== FILTROS PERSONALIZADOS ==========
    productos = []
    for p in productos_raw:
        # FILTRO 1: Descuento mínimo
        if p.get('descuento_pct', 0) < 20:  # ⚙️ Cambiar aquí: descuento mínimo
            continue

        # FILTRO 2: Precio máximo
        if p.get('price_discounted', 999999) > 2000:  # ⚙️ Cambiar aquí: precio máx
            continue

        # FILTRO 3: Palabras clave en título
        titulo_lower = p.get('title', '').lower()
        palabras_excluir = ['usado', 'refurbished', 'renewed']  # ⚙️ Agregar palabras
        if any(palabra in titulo_lower for palabra in palabras_excluir):
            continue

        # FILTRO 4: Solo ciertas categorías (opcional)
        # browse_nodes = p.get('browse_nodes', [])
        # if not any('Juguetes' in node for node in browse_nodes):
        #     continue

        productos.append(p)

    print(f"\n🔍 Después de filtros personalizados: {len(productos)} productos")
    # ============================================

    # Guardar resultado
    output_path = os.path.join(BASE_DIR, args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(productos, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Guardado en: {output_path}")

    # Mostrar muestra
    print(f"\n📋 Muestra de productos extraídos:")
    for i, p in enumerate(productos[:5], 1):
        print(f"{i}. {p['title'][:60]}")
        print(f"   {p['descuento_pct']}% | ${p['price_discounted']:.2f} | {p.get('telegram_fecha', 'N/A')}")

    # Publicar si se pidió
    if args.publicar:
        if not args.bot_token or not args.chat_id:
            print("\n⚠️  Para publicar necesitas --bot-token y --chat-id")
            print("\nEjemplo:")
            print("  python telegram_publisher.py --dias 1 --publicar \\")
            print("    --bot-token 123456:ABC-DEF... \\")
            print("    --chat-id @tu_canal")
        else:
            publicar_a_telegram(productos, args.bot_token, args.chat_id)
    else:
        print("\n💡 Para publicar a tu canal, agrega: --publicar --bot-token TU_TOKEN --chat-id @tu_canal")

if __name__ == '__main__':
    main()
