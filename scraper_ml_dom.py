#!/usr/bin/env python3
"""
Scraper ML usando DOM directo (sin JSON embebido)
Mercado Libre cambió a renderizar productos en HTML.
"""

import os
import re
from playwright.sync_api import sync_playwright

ML_BROWSER_PROFILE = os.path.expanduser('~/Desktop/SUPERSELLER/.ml_browser_profile')

def extraer_productos_dom(url, min_discount=0, pages=1):
    """
    Extrae productos directamente del DOM usando Playwright.
    """
    productos = []

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            ML_BROWSER_PROFILE,
            headless=True,
            channel='chrome',
            viewport={'width': 1280, 'height': 800},
            locale='es-MX',
            args=['--disable-blink-features=AutomationControlled'],
        )

        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print(f"  🎭 Playwright ML DOM: {url[:80]}", flush=True)

        page.goto(url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(3000)  # Esperar que cargue todo

        # Extraer productos del DOM usando JavaScript
        productos_raw = page.evaluate("""() => {
            const productos = [];
            const cards = document.querySelectorAll('.poly-card');

            cards.forEach(card => {
                try {
                    // Título
                    const titleElem = card.querySelector('.poly-component__title');
                    const title = titleElem ? titleElem.textContent.trim() : '';

                    // Link y ID
                    const linkElem = card.querySelector('a[href*="/p/"]');
                    const link = linkElem ? linkElem.href : '';
                    const id = link ? link.match(/MLM\\d+/)?.[0] || '' : '';

                    // Precio con descuento (actual)
                    const precioElem = card.querySelector('.poly-price__amount .andes-money-amount__fraction');
                    const precio = precioElem ? parseFloat(precioElem.textContent.replace(/,/g, '')) : 0;

                    // Precio original
                    const precioOrigElem = card.querySelector('.andes-money-amount--previous .andes-money-amount__fraction');
                    const precioOrig = precioOrigElem ? parseFloat(precioOrigElem.textContent.replace(/,/g, '')) : precio;

                    // Descuento
                    const descuentoElem = card.querySelector('.poly-price__discount-polylabel');
                    let descuento = 0;
                    if (descuentoElem) {
                        const match = descuentoElem.textContent.match(/(\\d+)%/);
                        descuento = match ? parseInt(match[1]) : 0;
                    } else if (precioOrig > precio) {
                        descuento = Math.round(((precioOrig - precio) / precioOrig) * 100);
                    }

                    // Imagen
                    const imgElem = card.querySelector('.poly-component__picture img');
                    const img = imgElem ? (imgElem.src || imgElem.dataset.src || '') : '';

                    if (id && title && precio > 0) {
                        productos.push({
                            id: id,
                            title: title,
                            link: link,
                            price_discounted: precio,
                            price_original: precioOrig,
                            descuento_pct: descuento,
                            img: img
                        });
                    }
                } catch (e) {
                    console.error('Error extrayendo card:', e);
                }
            });

            return productos;
        }""")

        print(f"  ✅ {len(productos_raw)} productos extraídos del DOM", flush=True)

        # Filtrar por descuento mínimo
        for p in productos_raw:
            if p['descuento_pct'] >= min_discount:
                productos.append(p)

        print(f"  📊 {len(productos)} productos con ≥{min_discount}% descuento", flush=True)

        ctx.close()

    return productos


if __name__ == "__main__":
    print("🔍 Probando scraper DOM...")
    items = extraer_productos_dom('https://www.mercadolibre.com.mx/ofertas', min_discount=10, pages=1)

    print()
    print("=" * 60)
    print(f"✅ {len(items)} productos encontrados")
    print("=" * 60)

    if len(items) > 0:
        print()
        for i in range(min(5, len(items))):
            print(f"{i+1}. {items[i]['title'][:60]}")
            print(f"   💰 ${items[i]['price_discounted']:.2f} (antes ${items[i]['price_original']:.2f})")
            print(f"   🔥 {items[i]['descuento_pct']}% OFF")
            print(f"   🔗 {items[i]['id']}")
            print()
