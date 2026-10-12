#!/usr/bin/env python3
"""
Scraper ML usando DOM directo - VERSIÓN CORREGIDA
"""

import os
from playwright.sync_api import sync_playwright

ML_BROWSER_PROFILE = os.path.expanduser('~/Desktop/SUPERSELLER/.ml_browser_profile')

def extraer_productos_ml(url, min_discount=0, pages=1):
    """
    Extrae productos directamente del DOM usando Playwright.
    """
    productos = []

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            ML_BROWSER_PROFILE,
            headless=False,  # Modo visible - ML detecta headless
            channel='chrome',
            viewport={'width': 1280, 'height': 800},
            locale='es-MX',
            args=['--disable-blink-features=AutomationControlled'],
        )

        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print(f"  🎭 Playwright ML: {url[:80]}", flush=True)

        page.goto(url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(3000)

        # Extraer productos del DOM
        productos_raw = page.evaluate("""() => {
            const productos = [];
            const cards = document.querySelectorAll('.poly-card, [class*="poly-card"]');

            cards.forEach(card => {
                try {
                    // Link (contiene el ID)
                    const linkElem = card.querySelector('a[href*="/p/"]');
                    if (!linkElem) return;

                    const link = linkElem.href;
                    const idMatch = link.match(/MLM\\d+/);
                    if (!idMatch) return;
                    const id = idMatch[0];

                    // Título
                    const titleElem = card.querySelector('.poly-component__title, [class*="title"]');
                    const title = titleElem ? titleElem.textContent.trim() : '';
                    if (!title) return;

                    // Precio actual (con descuento)
                    const precioElems = card.querySelectorAll('.andes-money-amount__fraction');
                    if (precioElems.length === 0) return;

                    let precio = 0;
                    let precioOrig = 0;

                    // Si hay 2 precios, el primero es el original, el segundo es el con descuento
                    if (precioElems.length >= 2) {
                        precioOrig = parseFloat(precioElems[0].textContent.replace(/[^0-9]/g, ''));
                        precio = parseFloat(precioElems[1].textContent.replace(/[^0-9]/g, ''));
                    } else {
                        // Solo hay 1 precio
                        precio = parseFloat(precioElems[0].textContent.replace(/[^0-9]/g, ''));
                        precioOrig = precio;
                    }

                    if (precio === 0) return;

                    // Calcular descuento
                    let descuento = 0;
                    if (precioOrig > precio) {
                        descuento = Math.round(((precioOrig - precio) / precioOrig) * 100);
                    }

                    // Buscar descuento explícito
                    const descuentoElem = card.querySelector('[class*="discount"], [class*="off"]');
                    if (descuentoElem) {
                        const match = descuentoElem.textContent.match(/(\\d+)%/);
                        if (match) {
                            descuento = parseInt(match[1]);
                        }
                    }

                    // Imagen
                    const imgElem = card.querySelector('img');
                    const img = imgElem ? (imgElem.src || imgElem.dataset.src || imgElem.getAttribute('data-src') || '') : '';

                    productos.push({
                        id: id,
                        title: title,
                        link: link,
                        price_discounted: precio,
                        price_original: precioOrig,
                        descuento_pct: descuento,
                        img: img
                    });

                } catch (e) {
                    // Ignorar errores en cards individuales
                }
            });

            return productos;
        }""")

        print(f"  ✅ {len(productos_raw)} productos extraídos", flush=True)

        # Filtrar por descuento mínimo
        for p in productos_raw:
            if p['descuento_pct'] >= min_discount:
                productos.append(p)

        print(f"  📊 {len(productos)} con ≥{min_discount}% descuento", flush=True)

        ctx.close()

    return productos


if __name__ == "__main__":
    print("🔍 Probando scraper ML nuevo...")
    print()

    items = extraer_productos_ml('https://www.mercadolibre.com.mx/ofertas', min_discount=10, pages=1)

    print()
    print("=" * 60)
    print(f"✅ RESULTADO: {len(items)} productos")
    print("=" * 60)

    if len(items) > 0:
        print()
        for i in range(min(5, len(items))):
            print(f"{i+1}. {items[i]['title'][:60]}")
            print(f"   💰 ${items[i]['price_discounted']:.0f} (antes ${items[i]['price_original']:.0f})")
            print(f"   🔥 {items[i]['descuento_pct']}% OFF")
            print(f"   🔗 {items[i]['id']}")
            print()
    else:
        print("\n⚠️  No se encontraron productos con descuento ≥10%")
