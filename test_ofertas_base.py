#!/usr/bin/env python3
"""
Test: Probar URL base de ofertas (sin container_id)
"""

import scraper_ml_nuevo as ml

print("🔍 Probando URL BASE de ofertas (sin filtros)...")
print()

url = 'https://www.mercadolibre.com.mx/ofertas'
items = ml.extraer_productos_ml(url, min_discount=10, pages=3)

print()
print("=" * 60)
print(f"✅ RESULTADO: {len(items)} productos únicos")
print("=" * 60)

if len(items) > 0:
    print()
    print("Primeros 5 productos:")
    for i in range(min(5, len(items))):
        print(f"{i+1}. {items[i]['title'][:60]}")
        print(f"   💰 ${items[i]['price_discounted']:.0f} ({items[i]['descuento_pct']}% OFF)")
