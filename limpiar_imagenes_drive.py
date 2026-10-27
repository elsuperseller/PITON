#!/usr/bin/env python3
"""
Limpia imágenes antiguas de Google Drive (> 7 días)
Ejecutar manualmente o con cron diario
"""

import google_drive_images

AUDIENCIAS = ["superseller", "coleccionistas"]

print("=" * 70)
print("🗑️  LIMPIEZA DE IMÁGENES ANTIGUAS EN GOOGLE DRIVE")
print("=" * 70)
print()
print(f"Política de retención: {google_drive_images.DIAS_RETENCION} días")
print()

total_eliminados = 0

for audiencia in AUDIENCIAS:
    print(f"📁 Audiencia: {audiencia}")
    eliminados = google_drive_images.limpiar_imagenes_antiguas(audiencia)
    total_eliminados += eliminados
    print()

print("=" * 70)
print(f"✅ LIMPIEZA COMPLETADA - {total_eliminados} archivos eliminados")
print("=" * 70)
