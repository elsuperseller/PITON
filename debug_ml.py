#!/usr/bin/env python3
"""
Debug: Guardar HTML de ML para analizar estructura
"""

import os
from playwright.sync_api import sync_playwright

ML_PROFILE = os.path.expanduser('~/Desktop/SUPERSELLER/.ml_browser_profile')

print("🔍 Abriendo ML y guardando HTML...")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        ML_PROFILE,
        headless=False,
        channel='chrome',
        viewport={'width': 1280, 'height': 800},
        locale='es-MX',
    )

    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("📄 Navegando a ofertas...")
    page.goto('https://www.mercadolibre.com.mx/ofertas', wait_until='networkidle', timeout=60000)

    print("⏳ Esperando 5 segundos para que cargue todo...")
    page.wait_for_timeout(5000)

    # Guardar HTML
    html = page.content()
    with open('/Users/isaac/Desktop/SUPERSELLER/ml_debug.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ HTML guardado en: ml_debug.html ({len(html)} bytes)")

    # Buscar __PRELOADED_STATE__ o initialState en el JavaScript
    print("\n🔍 Buscando variables de estado en la página...")

    state = page.evaluate("""() => {
        if (window.__PRELOADED_STATE__) return 'Found: __PRELOADED_STATE__';
        if (window.__INITIAL_STATE__) return 'Found: __INITIAL_STATE__';
        if (window.__NEXT_DATA__) return 'Found: __NEXT_DATA__';

        // Buscar en scripts
        const scripts = Array.from(document.querySelectorAll('script'));
        for (let script of scripts) {
            if (script.textContent.includes('initialState')) return 'Found: initialState in script';
            if (script.textContent.includes('__PRELOADED_STATE__')) return 'Found: __PRELOADED_STATE__ in script';
        }
        return 'Not found';
    }""")

    print(f"   Estado: {state}")

    # Contar productos visibles
    productos_visibles = page.evaluate("""() => {
        const cards = document.querySelectorAll('[class*="poly-card"], [class*="ui-search-result"], .shops__item');
        return cards.length;
    }""")

    print(f"   Productos visibles en DOM: {productos_visibles}")

    input("\n>>> Presiona ENTER para cerrar...")
    ctx.close()

print("\n✅ Listo. Revisa ml_debug.html")
