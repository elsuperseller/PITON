#!/usr/bin/env python3
"""
Test: Verificar cómo funciona la paginación de ML
"""

import os
from playwright.sync_api import sync_playwright

ML_PROFILE = os.path.expanduser('~/Desktop/SUPERSELLER/.ml_browser_profile')

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        ML_PROFILE,
        headless=False,
        channel='chrome',
    )

    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Ir a ofertas
    url = 'https://www.mercadolibre.com.mx/ofertas?container_id=MLM1321208-1'
    print(f"Página 1: {url}")
    page.goto(url, wait_until='networkidle')
    page.wait_for_timeout(3000)

    # Contar productos página 1
    count1 = page.evaluate("document.querySelectorAll('.poly-card').length")
    print(f"  Productos página 1: {count1}")

    # Buscar botón de siguiente página
    btn_siguiente = page.evaluate("""() => {
        const botones = Array.from(document.querySelectorAll('button, a'));
        const siguiente = botones.find(b =>
            b.textContent.toLowerCase().includes('siguiente') ||
            b.textContent.includes('›') ||
            b.textContent.includes('→') ||
            b.getAttribute('aria-label')?.toLowerCase().includes('siguiente')
        );
        return siguiente ? siguiente.textContent : null;
    }""")

    print(f"  Botón siguiente: {btn_siguiente}")

    # Probar con page=2
    url2 = url + '&page=2'
    print(f"\nProbando: {url2}")
    page.goto(url2, wait_until='networkidle')
    page.wait_for_timeout(3000)
    count2 = page.evaluate("document.querySelectorAll('.poly-card').length")
    print(f"  Productos: {count2}")

    # Extraer primer producto de cada página para comparar
    primer_id_p1 = page.evaluate("""() => {
        const link = document.querySelector('a[href*="/p/"]');
        return link ? link.href.match(/MLM\\d+/)?.[0] : null;
    }""")

    # Volver a página 1
    page.goto(url, wait_until='networkidle')
    page.wait_for_timeout(2000)
    primer_id_p2 = page.evaluate("""() => {
        const link = document.querySelector('a[href*="/p/"]');
        return link ? link.href.match(/MLM\\d+/)?.[0] : null;
    }""")

    print(f"\nPrimer producto página 1: {primer_id_p2}")
    print(f"Primer producto página 2 (page=2): {primer_id_p1}")
    print(f"¿Son diferentes? {'✅ Sí' if primer_id_p1 != primer_id_p2 else '❌ No, son iguales'}")

    input("\nPresiona ENTER para cerrar...")
    ctx.close()
