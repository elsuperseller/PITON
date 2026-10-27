#!/usr/bin/env python3
"""
Test del sistema de cache mapping
Verifica que no se re-suban imágenes duplicadas
"""

import google_drive_images

TEST_URL = "https://m.media-amazon.com/images/I/71QKQ9mwV7L._AC_SL1500_.jpg"
TEST_AUDIENCIA = "superseller"

print("=" * 70)
print("🧪 TEST: Cache Mapping (evitar duplicados)")
print("=" * 70)
print()

# Primera subida
print("📤 PRIMERA SUBIDA (debe procesar y subir):")
print("-" * 70)
url1 = google_drive_images.subir_imagen_procesada(TEST_URL, TEST_AUDIENCIA)
print()

# Segunda subida (debe usar cache)
print("📤 SEGUNDA SUBIDA (debe usar cache, NO re-subir):")
print("-" * 70)
url2 = google_drive_images.subir_imagen_procesada(TEST_URL, TEST_AUDIENCIA)
print()

# Verificar
print("=" * 70)
print("📊 RESULTADO")
print("=" * 70)

if url1 and url2:
    if url1 == url2:
        print("✅ TEST EXITOSO")
        print()
        print("URL 1:", url1)
        print("URL 2:", url2)
        print()
        print("✅ URLs idénticas (no se creó duplicado)")
    else:
        print("⚠️ URLs diferentes (posible duplicado)")
        print()
        print("URL 1:", url1)
        print("URL 2:", url2)
else:
    print("❌ TEST FALLÓ - Error en upload")

print()
print("Verifica drive_image_cache.json para ver el mapping guardado")
print()
