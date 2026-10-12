def _scrape_listado_playwright(url, pages=3, min_discount=0, precio_min=0, precio_max=0):
    """
    Renderiza URLs de ML con Playwright extrayendo productos del DOM.
    ML cambió su estructura - ahora renderiza productos client-side en HTML.
    IMPORTANTE: Corre en modo visible (headless=False) porque ML detecta headless.
    """
    if not _PLAYWRIGHT_OK:
        print("  ⚠️  Playwright no disponible — pip install playwright && playwright install chrome", flush=True)
        return []

    productos = []

    try:
        with _sync_playwright() as pw:
            # Usar perfil persistente con sesión de ML guardada
            # IMPORTANTE: headless=False porque ML detecta headless y no carga productos
            ctx = pw.chromium.launch_persistent_context(
                ML_BROWSER_PROFILE,
                headless=False,  # ML no carga productos en headless
                channel='chrome',
                viewport={'width': 1280, 'height': 800},
                locale='es-MX',
                args=['--disable-blink-features=AutomationControlled'],
            )

            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            print(f"  🎭 Playwright ML: {url[:80]}", flush=True)

            page.goto(url, wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(3000)

            # Extraer productos del DOM (ML ya no usa JSON embebido)
            productos_raw = page.evaluate("""() => {
                const productos = [];
                const cards = document.querySelectorAll('.poly-card, [class*="poly-card"]');

                cards.forEach(card => {
                    try {
                        const linkElem = card.querySelector('a[href*="/p/"]');
                        if (!linkElem) return;

                        const link = linkElem.href;
                        const idMatch = link.match(/MLM\\d+/);
                        if (!idMatch) return;
                        const id = idMatch[0];

                        const titleElem = card.querySelector('.poly-component__title, [class*="title"]');
                        const title = titleElem ? titleElem.textContent.trim() : '';
                        if (!title) return;

                        const precioElems = card.querySelectorAll('.andes-money-amount__fraction');
                        if (precioElems.length === 0) return;

                        let precio = 0;
                        let precioOrig = 0;

                        if (precioElems.length >= 2) {
                            precioOrig = parseFloat(precioElems[0].textContent.replace(/[^0-9]/g, ''));
                            precio = parseFloat(precioElems[1].textContent.replace(/[^0-9]/g, ''));
                        } else {
                            precio = parseFloat(precioElems[0].textContent.replace(/[^0-9]/g, ''));
                            precioOrig = precio;
                        }

                        if (precio === 0) return;

                        let descuento = 0;
                        if (precioOrig > precio) {
                            descuento = Math.round(((precioOrig - precio) / precioOrig) * 100);
                        }

                        const descuentoElem = card.querySelector('[class*="discount"], [class*="off"]');
                        if (descuentoElem) {
                            const match = descuentoElem.textContent.match(/(\\d+)%/);
                            if (match) descuento = parseInt(match[1]);
                        }

                        const imgElem = card.querySelector('img');
                        const img = imgElem ? (imgElem.src || imgElem.dataset.src || '') : '';

                        productos.push({
                            id: id,
                            title: title,
                            link: link,
                            price_discounted: precio,
                            price_original: precioOrig,
                            descuento_pct: descuento,
                            img: img
                        });
                    } catch (e) {}
                });

                return productos;
            }""")

            print(f"  ✅ {len(productos_raw)} productos extraídos del DOM", flush=True)

            # Normalizar al formato común y aplicar filtros
            for p_raw in productos_raw:
                # Filtro de descuento mínimo
                if p_raw['descuento_pct'] < min_discount:
                    continue

                # Filtro de precio
                precio = p_raw['price_discounted']
                if precio_min > 0 and precio < precio_min:
                    continue
                if precio_max > 0 and precio > precio_max:
                    continue

                # Normalizar al formato común de ML
                productos.append({
                    'id': p_raw['id'],
                    'title': p_raw['title'],
                    'link': p_raw['link'],
                    'img': p_raw['img'],
                    'price_discounted': p_raw['price_discounted'],
                    'price_original': p_raw['price_original'],
                    'descuento_pct': p_raw['descuento_pct'],
                })

            print(f"  📊 {len(productos)} con descuento≥{min_discount}%", flush=True)

            ctx.close()
    except Exception as e:
        print(f"  ❌ Playwright ML error: {e}", flush=True)

    return productos
