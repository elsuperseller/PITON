#!/usr/bin/env python3
"""
Debug: Verificar qué URLs se están generando y qué productos extrae cada página
"""

import os
from playwright.sync_api import sync_playwright

ML_PROFILE = os.path.expanduser('~/Desktop/SUPERSELLER/.ml_browser_profile')

url_base = 'https://www.mercadolibre.com.mx/ofertas?container_id=MLM1321208-1&deal_ids=MLM1321208'
pages = 3

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        ML_PROFILE,
        headless=False,
        channel='chrome',
    )

    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    todos_ids = []

    for page_num in range(1, pages + 1):
        # Construir URL igual que el scraper
        if page_num == 1:
            page_url = url_base
        else:
            separator = '&' if '?' in url_base else '?'
            page_url = f"{url_base}{separator}page={page_num}"

        print(f"\n{'='*60}")
        print(f"PÁGINA {page_num}/{pages}")
        print(f"{'='*60}")
        print(f"URL: {page_url}")

        page.goto(page_url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(3000)

        # Extraer IDs de esta página
        ids = page.evaluate("""() => {
            const links = document.querySelectorAll('a[href*="/p/"]');
            const ids = new Set();
            links.forEach(link => {
                const match = link.href.match(/MLM\\d+/);
                if (match) ids.add(match[0]);
            });
            return Array.from(ids);
        }""")

        print(f"Productos encontrados: {len(ids)}")
        print(f"Primeros 5 IDs: {ids[:5]}")

        # Guardar todos
        todos_ids.extend(ids)

    print(f"\n{'='*60}")
    print(f"RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"Total productos extraídos: {len(todos_ids)}")
    print(f"Productos ÚNICOS: {len(set(todos_ids))}")
    print(f"Duplicados: {len(todos_ids) - len(set(todos_ids))}")

    input("\nPresiona ENTER para cerrar...")
    ctx.close()
