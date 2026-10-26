#!/usr/bin/env python3
"""
Test del scraping con comportamiento HUMANO
Simula exactamente lo que hace Asin Crawler manualmente
"""

import sys
from scraper_amazon import _scrape_zg_batch_playwright

# URL de prueba
TEST_URL = "https://www.amazon.com.mx/gp/bestsellers/electronics/"

def main():
    print("=" * 70)
    print("🧪 TEST: Scraping con Comportamiento Humano")
    print("=" * 70)
    print()
    print("Simulando Asin Crawler:")
    print("  - Scroll variable (60-90% cada vez)")
    print("  - Pausas irregulares (800-2000ms)")
    print("  - Movimientos de mouse ocasionales")
    print("  - Detección de fin (sin productos nuevos)")
    print()
    print(f"URL: {TEST_URL}")
    print()

    # Probar con Playwright mejorado
    asins, estado = _scrape_zg_batch_playwright(
        [TEST_URL],
        pages=1,  # Solo primera página
        per_url_limit=50  # Top 50
    )

    print()
    print("=" * 70)
    print("📊 RESULTADOS")
    print("=" * 70)
    print(f"Total ASINs extraídos: {len(asins)}")
    print(f"Estado: {estado}")
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
    print("Revisa los logs arriba:")
    print("  - ¿Cuántos scrolls se hicieron?")
    print("  - ¿Detectó el fin automáticamente?")
    print("  - ¿Amazon bloqueó?")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
