#!/usr/bin/env python3
"""
Encuentra la estructura real de productos en ML
"""

import os
from playwright.sync_api import sync_playwright

ML_PROFILE = os.path.expanduser('~/Desktop/SUPERSELLER/.ml_browser_profile')

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        ML_PROFILE,
        headless=False,
        channel='chrome',
        viewport={'width': 1280, 'height': 800},
        locale='es-MX',
    )

    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("📄 Cargando ofertas...")
    page.goto('https://www.mercadolibre.com.mx/ofertas', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(5000)

    print("\n🔍 Buscando estructura de productos...\n")

    # Probar diferentes selectores
    selectores = [
        '.poly-card',
        '[class*="poly-card"]',
        '[data-testid="items-list"] > div',
        '.andes-card',
        '[class*="item"]',
        'article',
        '[role="listitem"]',
        '.ui-search-result',
        '.shops__item',
    ]

    for selector in selectores:
        count = page.evaluate(f"""() => {{
            return document.querySelectorAll('{selector}').length;
        }}""")
        print(f"  {selector:40} → {count} elementos")

    print("\n🔍 Intentando extraer primer producto visible...\n")

    primer_producto = page.evaluate("""() => {
        // Buscar cualquier elemento que parezca un producto
        const posibles = [
            ...document.querySelectorAll('[class*="poly"]'),
            ...document.querySelectorAll('[class*="card"]'),
            ...document.querySelectorAll('[class*="item"]'),
            ...document.querySelectorAll('article'),
        ];

        for (let elem of posibles) {
            const texto = elem.textContent || '';
            const tieneLink = elem.querySelector('a[href*="/p/"]');
            const tienePrecio = texto.match(/\\$[\\d,]+/);

            if (tieneLink && tienePrecio && texto.length > 50 && texto.length < 1000) {
                return {
                    tagName: elem.tagName,
                    className: elem.className,
                    texto: texto.substring(0, 200),
                    html: elem.outerHTML.substring(0, 500)
                };
            }
        }

        return null;
    }""")

    if primer_producto:
        print("✅ Encontrado:")
        print(f"  Tag: {primer_producto['tagName']}")
        print(f"  Class: {primer_producto['className'][:100]}")
        print(f"  Texto: {primer_producto['texto'][:100]}...")
        print(f"\n  HTML:\n{primer_producto['html'][:300]}...")
    else:
        print("❌ No se encontró estructura")

    input("\n>>> Presiona ENTER para cerrar...")
    ctx.close()
