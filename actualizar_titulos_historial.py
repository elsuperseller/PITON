#!/usr/bin/env python3
"""
Actualiza los títulos faltantes en el historial del feed usando Amazon API.
"""

import json
import os
import sys
import time
import requests
from datetime import datetime, timezone, timedelta

# Importar funciones del servidor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from servidor import cargar_historial_feed, guardar_historial_feed, get_token, CREDS

def actualizar_titulos_feed(feed_id):
    """Actualiza títulos faltantes en el historial del feed"""

    print(f"🔄 Actualizando títulos del feed '{feed_id}'...\n")

    # Cargar historial
    historial = cargar_historial_feed(feed_id)
    print(f"📋 Total productos en historial: {len(historial)}")

    # Filtrar solo últimos 30 días sin título
    ahora = datetime.now(timezone.utc)
    hace_30_dias = ahora - timedelta(days=30)

    asins_sin_titulo = []
    for asin, data in historial.items():
        ultima_vez = data.get('ultima_vez', '')
        title = data.get('title', '')

        if not ultima_vez:
            continue

        try:
            if '+' in ultima_vez or ultima_vez.endswith('Z'):
                fecha = datetime.fromisoformat(ultima_vez.replace('Z', '+00:00'))
            else:
                fecha = datetime.fromisoformat(ultima_vez).replace(tzinfo=timezone.utc)

            # Solo últimos 30 días sin título
            if fecha >= hace_30_dias and (not title or title == 'N/A'):
                asins_sin_titulo.append(asin)
        except:
            pass

    print(f"⚠️  Productos últimos 30 días sin título: {len(asins_sin_titulo)}")

    if not asins_sin_titulo:
        print("✅ Todos los productos recientes ya tienen título")
        return

    print(f"\n🔍 Obteniendo títulos de Amazon API...")

    # Obtener token
    token = get_token()
    api_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-marketplace": "www.amazon.com.mx"
    }

    actualizados = 0
    errores = 0

    # Procesar en batches de 10
    for i in range(0, len(asins_sin_titulo), 10):
        batch = asins_sin_titulo[i:i+10]

        try:
            r = requests.post(
                "https://creatorsapi.amazon/catalog/v1/getItems",
                headers=api_headers,
                json={
                    "partnerTag": CREDS["partner_tag"],
                    "marketplace": "www.amazon.com.mx",
                    "itemIds": batch,
                    "languagesOfPreference": ["es_MX"],
                    "currencyOfPreference": "MXN",
                    "resources": ["itemInfo.title"]
                },
                timeout=30
            )

            if r.status_code != 200:
                print(f"  ⚠️  Batch {i//10 + 1}: HTTP {r.status_code}")
                errores += len(batch)
                continue

            items = r.json().get("itemsResult", {}).get("items", [])

            for item in items:
                asin = item.get("asin", "")
                title = item.get("itemInfo", {}).get("title", {}).get("displayValue", "")

                if asin and title and asin in historial:
                    historial[asin]["title"] = title
                    actualizados += 1
                    print(f"  ✅ {asin}: {title[:60]}")

            # Guardar cada batch
            if actualizados % 10 == 0:
                guardar_historial_feed(feed_id, historial)

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"  ❌ Batch {i//10 + 1}: {e}")
            errores += len(batch)

    # Guardar final
    guardar_historial_feed(feed_id, historial)

    print(f"\n📊 Resumen:")
    print(f"   Actualizados: {actualizados}")
    print(f"   Errores: {errores}")
    print(f"   Total procesados: {len(asins_sin_titulo)}")
    print(f"\n✅ Historial actualizado!")

if __name__ == "__main__":
    try:
        actualizar_titulos_feed("coleccionistas")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
