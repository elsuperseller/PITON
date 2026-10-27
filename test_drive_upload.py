#!/usr/bin/env python3
"""
Test de subida de imágenes a Google Drive
Verifica que las credenciales y permisos estén correctos
"""

import google_drive_images

# URL de prueba (imagen de Amazon)
TEST_URL = "https://m.media-amazon.com/images/I/71QKQ9mwV7L._AC_SL1500_.jpg"
TEST_AUDIENCIA = "superseller"

print("=" * 70)
print("🧪 TEST: Upload de Imagen a Google Drive")
print("=" * 70)
print()
print(f"URL de prueba: {TEST_URL[:60]}...")
print(f"Audiencia: {TEST_AUDIENCIA}")
print(f"Carpeta Drive: {google_drive_images.CARPETAS_DRIVE[TEST_AUDIENCIA]}")
print()
print("Procesando...")
print()

# Probar upload
url_publica = google_drive_images.subir_imagen_procesada(TEST_URL, TEST_AUDIENCIA)

print()
print("=" * 70)
print("📊 RESULTADO")
print("=" * 70)

if url_publica:
    print("✅ TEST EXITOSO")
    print()
    print(f"URL pública: {url_publica}")
    print()
    print("Verifica en:")
    print("https://drive.google.com/drive/folders/1JF34AY239xKShd7RDm6NkXSpYcgz-sb8")
else:
    print("❌ TEST FALLÓ")
    print()
    print("Posibles causas:")
    print("  1. Credenciales incorrectas o faltantes")
    print("  2. Carpeta no compartida con Service Account")
    print("  3. Error de red o procesamiento")

print()
