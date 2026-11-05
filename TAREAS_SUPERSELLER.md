# 📋 TAREAS - SUPERSELLER

**Última actualización**: 2026-11-05

---

## ⏳ PENDIENTES

- [ ] **Configurar cron para limpieza automática de imágenes**
  - **Contexto**: Script `limpiar_imagenes_drive.py` elimina imágenes > 7 días de Google Drive
  - **Comando**: `python3 limpiar_imagenes_drive.py`
  - **Recomendado**: Ejecutar diariamente vía cron
  - **Prioridad**: BAJA (puede ejecutarse manualmente)

- [ ] **Optimizar headers de requests para evitar bloqueo Amazon**
  - **Contexto**: Sistema híbrido implementado pero Amazon bloquea requests simples (100% fallos en test)
  - **Estado actual**: Funciona con fallback a Playwright (circuit breaker activo)
  - **Mejoras posibles**:
    - Agregar sesión persistente con cookies
    - Incluir Referer headers
    - Simular navegación previa
    - Probar proxies rotativos
  - **Archivos**: `scraper_amazon.py` función `scrape_requests_rapido()` línea ~170
  - **Test**: `python3 test_hibrido.py`
  - **Prioridad**: BAJA (sistema funciona, esto es optimización)

---

## ✅ COMPLETADAS

- [x] **MercadoLibre: verificación vía API extendida también a URL fija** (2026-11-05)
  - **Pedido del usuario**: extender el enfoque híbrido (API) a todo lo que use el perfil de ML, no solo Telegram. Usuario aclaró que en la práctica solo usa Telegram y URL fija a diario.
  - **Límite confirmado**: la API de búsqueda de ML (`/sites/MLM/search`, usada para keywords/categorías) sigue bloqueada ("forbidden") incluso con el token autenticado — ML descontinuó ese endpoint público para la mayoría de apps. Esto NO es un tema de permisos resoluble; descubrir productos nuevos por keyword/categoría tiene que seguir siendo scraping.
  - **Lo que sí se logró**: nueva función `scraper_ml.verificar_via_api()` — toma productos ya encontrados por scraping (en URL fija) y refresca su precio/título/imagen vía `/products/{id}` + `/products/{id}/items`, más confiable que lo leído del DOM en ese instante. Si la API no puede resolver un producto, se conserva el dato scrapeado original sin romper nada.
  - **Conectado en**: el flujo de "URL fija" de ML en la feed de Ofertas (`servidor.py`, dentro de `/feeds/` → URLs fijas → rama MercadoLibre).
  - **Verificado**: probado con 3 productos reales scrapeados de `listado.mercadolibre.com.mx/ofertas` — los 3 se verificaron vía API, con precios más precisos (ej. $844.20 exacto vs $844 redondeado del scraping).
  - **Actualización**: usuario aclaró que el flujo que más usa es el cuadro **"🔗 URLs ML"** (pegar URL y buscar, ej. `mercadolibre.com.mx/ofertas`) — endpoint `/buscar-ml`. Se conectó `verificar_via_api()` ahí también (`servidor.py`, justo después de `_ml.scrape()`, antes del scoring de historial).
  - **Verificado con la URL real que usa el usuario** (`mercadolibre.com.mx/ofertas`): 42 productos scrapeados en 10.4s + 42/42 verificados vía API en 17.4s adicionales (~28s total). El navegador sigue abriéndose para descubrir qué productos hay en la página (inevitable, es la parte de scraping), pero el precio final que se muestra ya viene verificado por API.
  - **Pendiente, no usado a diario**: "pegar HTML manual" no tiene la verificación conectada todavía — se puede agregar después con la misma función si se necesita.

- [x] **MercadoLibre: enfoque híbrido API + scraping (igual que Amazon), en vez de solo scraping** (2026-11-05)
  - **Pedido del usuario**: no le gusta depender solo de scraping para ML; quería que, dado un link, se busque el ID de producto y se baje la info vía API, igual que con Amazon.
  - **Hallazgo clave**: un link de producto de ML da un "ID de catálogo" (ej. `MLM60359404`), que hay que resolver a un "ID de artículo" real (ej. `MLM4238306650`) vía `/products/{id}/items` para obtener el precio — `/products/{id}` solo da título e imágenes.
  - **Credenciales**: se reutiliza el mismo access_token/refresh_token que ya usa el proyecto Mercado Ads Manager (`~/Desktop/mercadoads`), vía nuevo módulo `mercadolibre_auth.py`. Ambos proyectos leen y escriben la MISMA base de datos (`database.sqlite`, tabla `auth_tokens`) — nunca credenciales duplicadas — porque el `refresh_token` de ML es de un solo uso y refrescarlo por separado en cada proyecto invalidaría al otro.
  - **Solución**: `scraper_ml.py` ahora intenta primero `_enriquecer_via_api()` (sin abrir navegador); solo si la API no puede resolver el producto (ej. no es un producto de catálogo, es un listado individual de otro vendedor) cae a Playwright como respaldo — y en ese caso abre el navegador una sola vez para todos los pendientes, no uno por uno.
  - **Verificado**: probado en vivo — resolvió un producto real 100% vía API (título, imagen, $390 vs $640 original, 39% descuento) sin abrir Chrome; y confirmé que un ID inexistente retorna `None` limpiamente para activar el respaldo por scraping.

- [x] **Canales de Telegram ahora extraen productos de MercadoLibre, no solo Amazon** (2026-11-05)
  - **Problema**: `telegram_utils.py` solo detectaba y enriquecía links de Amazon en los mensajes de los canales. Los links de MercadoLibre (ej. `meli.la/...`) se ignoraban por completo.
  - **Solución**: `scrape_telegram_ultimos_dias()` ahora detecta también links de MercadoLibre, resuelve los acortados (meli.la, etc.) y extrae el ID de producto (MLM...) de la URL final. Se agregó `scraper_ml.enriquecer_urls_productos()` que abre cada página de producto con Playwright (requests simples son bloqueados por ML con un muro de "verificación de cuenta") y extrae título/precio/imagen. Se actualizaron los 4 puntos de `servidor.py` que usan Telegram (`/feeds/buscar`, el feed de Ofertas, el feed de Novedades, y `/feeds/telegram-extract`) para procesar también los productos de ML encontrados.
  - **Nota técnica**: links de ML que no apuntan a un producto específico (ej. páginas de perfil/afiliado) se descartan automáticamente, ya que no se les puede extraer un ID de producto.
  - **Fix adicional (drive-by)**: en `/feeds/telegram-extract` había un bug preexistente que pasaba el dict de ASINs directo a `enriquecer_asins()` sin convertirlo a lista (hubiera fallado con TypeError al usar slicing sobre un dict). Corregido en el mismo cambio.
  - **Verificado**: probado en vivo contra el canal real "The Geek Chronicles" — detectó correctamente el único link de ML presente, lo resolvió, y lo descartó apropiadamente porque apuntaba a una página de afiliado, no a un producto. También se probó `enriquecer_urls_productos()` con un link de producto real de ML, extrayendo título/precio/descuento/imagen correctamente.

- [x] **Agregado canal de Telegram "goeyGEEKS.bot" como competencia en feed coleccionistas** (2026-11-05)
  - Canal con 3,509 suscriptores que rastrea ofertas de Pokémon TCG, Magic: The Gathering y coleccionables en Amazon. Agregado a `telegram_sources` con 2 días de histórico, igual que "The Geek Chronicles".

- [x] **Fix: "Selecciona al menos un producto VISIBLE" al exportar desde URL temporal** (2026-11-05)
  - **Problema**: la función `buscarAmazonUrlTemporal()` en `superseller.html` pintaba los productos en pantalla pero nunca actualizaba `ProductosState` (el estado que usa el botón de exportar para saber qué está seleccionado y visible). Por eso, aunque se vieran y marcaran productos, exportar siempre fallaba con ese mensaje.
  - **Solución**: se agregó `ProductosState.setFeedId()` y `ProductosState.setItems()` después de recibir los productos, igual que hacen todas las demás funciones de búsqueda del archivo.

- [x] **Fix: historial no ocultaba ofertas ya publicadas (sin importar el método de búsqueda)** (2026-10-29)
  - **Problema**: `aplicar_novedad_score_feed()` solo le ponía un badge gris chiquito a los productos ya publicados, pero nunca los ocultaba de los resultados. Por eso en el feed de coleccionables (y en general) seguían apareciendo ofertas ya publicadas sin importar si se buscaban por keyword, Telegram o URL.
  - **Solución**: la función ahora oculta (filtra) los productos publicados hace <21 días o bloqueados, con un parámetro `ocultar=True` por default. Se desactiva explícitamente (`ocultar=False`) solo en el endpoint genérico `/historial` (acciones `score`/`filtrar`) para no romper su lógica propia de `min_score`.
  - **Verificación**: probado con el historial real de `coleccionistas` — un ASIN publicado hoy se ocultó, uno nunca visto se mantuvo visible.

- [x] **Fix: keywords de Novedades vacías (feed coleccionables)** (2026-10-29)
  - **Problema**: la búsqueda de Novedades por keywords (combinada con Telegram y URLs) traía siempre 0 resultados. Causa real: `obtener_asins_keyword()` llamaba a la API de Amazon con `minSavingPercent=0`, y Amazon rechaza ese valor con error 400 ("debe ser ≥1"). El error se tragaba silenciosamente y cortaba la búsqueda en la primera página de cada keyword.
  - **Solución**: `buscar()` ahora omite el parámetro `minSavingPercent` del todo cuando `min_saving<=0`, en vez de mandarlo inválido. Así Novedades puede pedir productos sin exigir ningún descuento (correcto, porque lo nuevo no siempre tiene oferta), sin que Amazon rechace la petición.
  - **Keywords de Novedades**: se igualaron a las 100 keywords de Ofertas en el feed `coleccionistas` (antes solo tenía 2: "Street Fighter" y "PROJECT PUNCH").
  - **Nota**: también se corrigió `/feeds/buscar-keywords` (botón manual "Buscar por fuente → Keywords") para que respete el modo activo (Ofertas/Novedades) en vez de usar siempre `keywords_ofertas`.
  - **Verificación**: probado en vivo con `obtener_asins_keyword('Funko Pop')` — antes 0 ASINs, después 20. Se limpió la caché vieja de `coleccionistas_novedades_Featured` para forzar la regeneración. Confirmado funcionando por el usuario.

- [x] **Fix timeout de exportación a Google Sheets** (2026-10-29)
  - **Problema**: Al exportar lotes grandes (75 productos), el frontend cancelaba la petición a los 5 minutos con error, aunque el backend seguía procesando. El servidor terminaba el export correctamente pero el navegador ya había abortado la conexión (`Broken pipe` en servidor.log).
  - **Solución**: Aumentado el timeout del fetch en `superseller.html` de 5 a 15 minutos (300000 → 900000 ms), en `exportarSheetsFeed()` y `exportarSheetsDirecto()`.
  - **Verificación**: Se confirmó que la exportación que disparó el error sí llegó al Google Sheet (75 filas, `modifiedTime` del spreadsheet coincide con la hora del export).
  - **Pendiente**: Ninguno. Si en el futuro los lotes crecen mucho más (200+ productos), puede que 15 min tampoco alcance — en ese caso conviene hacer el export asíncrono (responder de inmediato y que el frontend haga polling de estado) en lugar de seguir subiendo el timeout.

- [x] **Sistema de imágenes procesadas con upload a Google Drive** (2026-10-26)
  - Creado módulo `google_drive_images.py` con Google Drive API
  - Configurado Service Account en Google Cloud (imagenes-superseller)
  - Creadas carpetas en Shared Drive de Superseller
  - Integrado en `servidor.py` para procesar automáticamente al exportar
  - Imágenes cuadradas 1000×1000 subidas a Drive con URLs públicas
  - Script de limpieza `limpiar_imagenes_drive.py` (retención 7 días)
  - Actualizado CLAUDE.md con documentación completa
- [x] Fix búsqueda keywords - API response `searchResult` vs `itemsResult` (2026-10-23)
- [x] Fix export Google Sheets - ProductosState y selector CSS (2026-10-23)
- [x] Filtro historial - Productos publicados últimos 21 días (2026-10-23)
- [x] Aumento límite keywords - 50 → 200 (2026-10-23)
- [x] Reducción descuento mínimo - 15% → 1% (2026-10-23)
- [x] Badge keyword específica - Mostrar `🎯 keyword` en cada producto (2026-10-23)
- [x] Sincronización GitHub - Todos los cambios pusheados (2026-10-23)
