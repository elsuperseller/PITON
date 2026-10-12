#!/usr/bin/env python3
import scraper_ml as ml

print("🔍 Probando scraper ML con tu sesión...")
print("Se abrirá Chrome - observa qué página carga...")
print()

url = 'https://www.mercadolibre.com.mx/ofertas'
items = ml.scrape_url(url, min_discount=10, pages=1)

print()
print("=" * 60)
print(f"✅ Resultado: {len(items)} productos")
print("=" * 60)

if len(items) > 0:
    print()
    print("Primeros productos encontrados:")
    for i in range(min(3, len(items))):
        print(f"{i+1}. {items[i].get('title', '')[:60]}")
        print(f"   💰 ${items[i].get('price_discounted', 0):.2f} ({items[i].get('descuento_pct', 0)}% OFF)")
else:
    print()
    print("⚠️  No se encontraron productos.")
    print("Observa la ventana de Chrome que se abrió:")
    print("- ¿Qué página muestra?")
    print("- ¿Dice 'suspicious traffic'?")
    print("- ¿Pide verificación?")
