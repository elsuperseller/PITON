#!/usr/bin/env python3
"""
Test del sistema híbrido de scraping
Prueba con 5-10 URLs de Best Sellers para validar:
1. Requests rápido funciona
2. Fallback a Playwright cuando necesario
3. Circuit breaker se activa correctamente
"""

import sys
from scraper_amazon import scrape_zg_batch

# URLs de prueba (Best Sellers en diferentes categorías)
TEST_URLS = [
    # Best Sellers - Electrónicos
    "https://www.amazon.com.mx/gp/bestsellers/electronics/",

    # Best Sellers - Libros
    "https://www.amazon.com.mx/gp/bestsellers/books/",

    # Best Sellers - Deportes
    "https://www.amazon.com.mx/gp/bestsellers/sporting-goods/",

    # Best Sellers - Hogar
    "https://www.amazon.com.mx/gp/bestsellers/home-garden/",

    # Best Sellers - Juguetes
    "https://www.amazon.com.mx/gp/bestsellers/toys/",
]

def main():
    print("=" * 70)
    print("🧪 TEST: Sistema Híbrido de Scraping")
    print("=" * 70)
    print()
    print(f"Probando con {len(TEST_URLS)} URLs de Best Sellers")
    print()

    # Probar con todas las URLs
    asins, estado = scrape_zg_batch(TEST_URLS, pages=1, per_url_limit=20)

    print()
    print("=" * 70)
    print("📊 RESULTADOS")
    print("=" * 70)
    print(f"Total ASINs extraídos: {len(asins)}")
    print(f"Estado final: {estado}")
    print()

    if asins:
        print("✅ TEST EXITOSO")
        print()
        print("Primeros 10 ASINs:")
        for i, asin in enumerate(asins[:10], 1):
            print(f"  {i}. {asin}")

        if len(asins) > 10:
            print(f"  ... y {len(asins) - 10} más")
    else:
        print("❌ TEST FALLÓ - No se extrajeron ASINs")
        return 1

    print()
    print("=" * 70)
    print("💡 OBSERVACIONES")
    print("=" * 70)
    print("Revisa los logs arriba para ver:")
    print("  - Cuántas URLs usaron requests (⚡)")
    print("  - Cuántas usaron Playwright (🌐)")
    print("  - Si se activó el circuit breaker (🔴)")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
