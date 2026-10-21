#!/usr/bin/env python3
"""
Limpia archivos de historial eliminando productos no publicados en los últimos 3 meses.
Crea backups automáticamente antes de limpiar.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

def limpiar_historial(archivo_path):
    """Limpia un archivo de historial eliminando entradas antiguas."""

    if not os.path.exists(archivo_path):
        print(f"  ⚠️  No existe: {archivo_path}")
        return

    # Backup
    backup_path = f"{archivo_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.system(f'cp "{archivo_path}" "{backup_path}"')
    print(f"  💾 Backup: {os.path.basename(backup_path)}")

    # Cargar historial
    with open(archivo_path, 'r', encoding='utf-8') as f:
        historial = json.load(f)

    total_antes = len(historial)

    # Filtrar últimos 3 meses
    hace_3_meses = datetime.now(timezone.utc) - timedelta(days=90)

    historial_limpio = {}
    for key, entry in historial.items():
        # Usar last_published para determinar si mantener la entrada
        last_pub = entry.get("last_published")
        if not last_pub:
            # Si no tiene last_published, skip (muy antiguo)
            continue

        try:
            dt = datetime.fromisoformat(last_pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # Mantener solo si fue publicado en los últimos 3 meses
            if dt >= hace_3_meses:
                historial_limpio[key] = entry
        except:
            # Si hay error parseando fecha, skip
            continue

    total_despues = len(historial_limpio)
    eliminados = total_antes - total_despues

    # Guardar historial limpio
    with open(archivo_path, 'w', encoding='utf-8') as f:
        json.dump(historial_limpio, f, ensure_ascii=False, indent=2)

    # Calcular tamaño
    tamaño_mb = os.path.getsize(archivo_path) / (1024 * 1024)

    print(f"  ✅ {total_antes} → {total_despues} entradas ({eliminados} eliminadas)")
    print(f"  📦 Tamaño: {tamaño_mb:.1f} MB")
    print()

    return total_antes, total_despues, eliminados


def main():
    print("🧹 LIMPIANDO ARCHIVOS DE HISTORIAL")
    print("=" * 60)
    print()

    # Lista de archivos de historial
    archivos = [
        "/Users/isaac/Desktop/SUPERSELLER/historial.json",
        "/Users/isaac/Desktop/SUPERSELLER/feeds/coleccionistas/historial.json",
        "/Users/isaac/Desktop/SUPERSELLER/feeds/superseller/historial.json",
        "/Users/isaac/Desktop/SUPERSELLER/feeds/melomanos/historial.json",
    ]

    total_antes_global = 0
    total_despues_global = 0
    total_eliminados = 0

    for archivo in archivos:
        nombre = os.path.basename(os.path.dirname(archivo)) if "feeds/" in archivo else "GLOBAL"
        print(f"📂 {nombre}")

        resultado = limpiar_historial(archivo)
        if resultado:
            antes, despues, eliminados = resultado
            total_antes_global += antes
            total_despues_global += despues
            total_eliminados += eliminados

    print("=" * 60)
    print(f"🎉 TOTALES:")
    print(f"   Antes: {total_antes_global} entradas")
    print(f"   Después: {total_despues_global} entradas")
    print(f"   Eliminadas: {total_eliminados} entradas ({total_eliminados/total_antes_global*100:.1f}%)")
    print()
    print("✅ Limpieza completada. Las exportaciones deberían ser mucho más rápidas ahora.")


if __name__ == "__main__":
    main()
