#!/usr/bin/env python3
"""
Crear carpetas en Shared Drive usando Service Account
"""

from google_drive_images import get_drive_service

# ID del Shared Drive
SHARED_DRIVE_ID = "0ALCl4wu6e7kbUk9PVA"

print("=" * 70)
print("📁 Creando carpetas en Shared Drive")
print("=" * 70)
print()

try:
    # Obtener servicio
    service = get_drive_service()

    # Crear carpeta "Superseller"
    print("Creando carpeta 'Superseller'...")
    folder1_metadata = {
        'name': 'Superseller',
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [SHARED_DRIVE_ID]
    }

    folder1 = service.files().create(
        body=folder1_metadata,
        fields='id, name',
        supportsAllDrives=True
    ).execute()

    print(f"✅ Superseller creada: {folder1.get('id')}")

    # Crear carpeta "Collector Secret Society"
    print("Creando carpeta 'Collector Secret Society'...")
    folder2_metadata = {
        'name': 'Collector Secret Society',
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [SHARED_DRIVE_ID]
    }

    folder2 = service.files().create(
        body=folder2_metadata,
        fields='id, name',
        supportsAllDrives=True
    ).execute()

    print(f"✅ Collector Secret Society creada: {folder2.get('id')}")

    print()
    print("=" * 70)
    print("✅ CARPETAS CREADAS")
    print("=" * 70)
    print()
    print("IDs de las carpetas:")
    print(f"  Superseller: {folder1.get('id')}")
    print(f"  Collector Secret Society: {folder2.get('id')}")
    print()
    print("Actualiza google_drive_images.py con estos IDs")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
