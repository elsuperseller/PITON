# 📋 TAREAS - SUPERSELLER

**Última actualización**: 2026-11-24

---

## ⏳ PENDIENTES

- [ ] **Agregar pausas y freno de emergencia al scraping de respaldo de MercadoLibre (Playwright)**
  - **Problema**: `_enriquecer_via_playwright()` en `scraper_ml.py` navega una página de producto tras otra sin pausas, usando siempre el mismo perfil de navegador. Esto disparó una advertencia real de "¿eres humano?" de MercadoLibre (2026-11-24) por volumen de búsquedas.
  - **Mejoras propuestas, aún no implementadas**: pausas aleatorias (3-7s) entre cada página, freno de emergencia si detecta el muro de verificación (para no seguir intentando el resto del lote), y un tope máximo de productos por corrida (ej. 15).
  - **Prioridad**: ALTA (riesgo de bloqueo de cuenta de MercadoLibre)

- [ ] **Borrar filas de prueba en el Sheet de Collector Secret Society**
  - 4 filas con título "TEST BORRAR - Producto ML" / "TEST BORRAR - Producto Amazon" quedaron de la verificación del fix de CANAL (2026-11-24).

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

- [x] **Fix: CANAL mostraba "Amazon" para todo en el export a Google Sheets (Collector Secret Society)** (2026-11-24)
  - **Causa**: el Apps Script real (`doPost`) solo revisaba `item.source === "ml"`, pero muchos productos de MercadoLibre llegan con `source: null` y solo `platform: "mercadolibre"` seteado — por eso siempre caían en "Amazon".
  - **Fix**: se corrigió la lógica del script para revisar `item.platform` también, no solo `item.source`. Se creó una implementación nueva en Apps Script (URL distinta a la anterior) y se actualizó `sheets_export_url` del feed `coleccionistas` en `perfiles_audiencia.json` para apuntar a la nueva URL.
  - **Verificado**: prueba real enviada al nuevo endpoint — un producto de ML salió con CANAL "Mercado Libre" y uno de Amazon salió "Amazon", correctamente. Quedaron 4 filas de prueba por borrar en el Sheet (ver pendientes).
  - **Nota importante descubierta en el camino**: el script de Collector Secret Society resultó ser una copia casi idéntica del script de Superseller (mismo bug) — probablemente se duplicó como plantilla al crear el proyecto. El de Superseller NO se tocó (no era el reportado).

- [x] **Fix: "Ver en Amazon →" se mostraba para productos de MercadoLibre en localhost** (2026-11-24)
  - **Causa**: el texto del botón "Ver en..." estaba fijo en "Amazon" en el template de la tarjeta de producto (`superseller.html`), sin revisar la plataforma real del producto.
  - **Fix**: ahora el texto es condicional — revisa `p.platform === 'mercadolibre'`, `p.source === 'ml'`, o si `p.asin` empieza con `MLM`, y muestra "Ver en MercadoLibre →" en esos casos.
  - **Verificado**: se confirmó que todo el caché de productos en disco (`feeds/feeds_cache.json`) tiene el campo `platform`/`source` correctamente seteado para ML — cero productos mal etiquetados.

- [x] **Aclaración: por qué MercadoLibre mostró advertencia de "¿eres humano?"** (2026-11-24)
  - **Causa raíz identificada**: `_enriquecer_via_playwright()` (respaldo cuando la API no reconoce un producto como "de catálogo") abre muchas páginas de producto seguidas sin pausas, con el mismo perfil de navegador — patrón típico de detección de bots. Pendiente implementar mitigación (ver PENDIENTES).

- [x] **Aclaración: por qué una búsqueda de MercadoLibre se disparó sin que el usuario apretara ningún botón** (2026-11-24)
  - **Causa real #1**: la caché de resultados expira por tiempo (ej. "cada_3_horas" en el feed Coleccionistas en realidad vence en **1 hora** reales, no 3 — reducción intencional hecha en una sesión anterior). Al reabrir la vista de Ofertas/Novedades después de ese tiempo, el sistema busca todo de nuevo automáticamente, sin que el usuario pida un "refresh" explícito.
  - **Causa real #2**: los canales de Telegram están exentos a propósito del selector de canal Amazon/MercadoLibre (decisión explícita de una sesión anterior, confirmada de nuevo en esta) — así que aunque el usuario desactive MercadoLibre, los links de ML que vengan de Telegram se siguen procesando igual.
  - **No se encontró ningún proceso en segundo plano, cron, ni temporizador** que dispare búsquedas por sí solo — se confirmó revisando el código (no hay `setInterval`, `Timer`, ni hilos que repitan búsquedas).
  - **Sin cambios de código**: el usuario decidió dejar ambos comportamientos como están.

- [x] **Seguridad: `.ml_browser_profile/` (perfil de navegador con cookies de MercadoLibre) se estaba subiendo a GitHub automáticamente** (2026-11-24)
  - **Causa**: `auto-sync.sh` corre `git add -A` cada hora sin exclusiones, y esa carpeta nunca estuvo en `.gitignore`. El repo `elsuperseller/PITON` es **público**.
  - **Fix**: se agregó al `.gitignore`, se dejó de rastrear, y se limpió del historial de git (ver commit de limpieza). Se recomendó además cerrar sesión/rotar la sesión de MercadoLibre por si alguna cookie quedó expuesta públicamente.

- [x] **Fix: links de MercadoLibre tipo "perfil social" no traían ningún producto** (2026-11-20)
  - **Problema**: la mayoría de los links de ML compartidos en Telegram son del tipo `/social/tienda?matt_word=...` (página de perfil de afiliado), no un link directo a producto — por eso salían "0 productos de MercadoLibre" en casi todas las búsquedas, aunque el canal sí compartiera ofertas de ML.
  - **Aclaración del usuario**: esas páginas muestran el producto promocionado como el primero/destacado de la lista — hay que entrar y tomar ese primero, no un link cualquiera de recomendaciones genéricas.
  - **Fix**: nueva función `scraper_ml.resolver_producto_destacado_social()` — visita la página `/social/` y extrae el producto marcado internamente por ML como `card-featured` (el destacado real), en vez de ignorar el link por completo.
  - **Verificado de punta a punta**: con el link real que compartió el usuario, extrajo `MLM75329393` y lo enriqueció correctamente vía API (título, $914.54 vs $1,299 original, 30% descuento, imagen).

- [x] **Fix paginación de MercadoLibre: clic real en "Siguiente" en vez de adivinar la URL** (2026-11-20)
  - **Problema**: el scraper de listados ML (`_scrape_listado_playwright`) construía la URL de la página 2/3 adivinando el esquema de paginación (`_Desde_N_` insertado antes de `_NoIndex_True`). El usuario confirmó que seguía fallando (repetía la página 1).
  - **Causa real**: el botón "Siguiente" real de ML inserta `_Desde_N_` en una posición DISTINTA de la ruta (justo después del dominio, no antes de `_NoIndex_True`). Confirmado comparando ambas URLs directamente.
  - **Solución**: se abandonó el intento de adivinar la URL. Ahora el scraper navega a la página 1 normalmente y para las siguientes páginas busca y hace **clic real** en el link `a.andes-pagination__link` con texto "Siguiente" — así nunca depende de adivinar el esquema correcto.
  - **Verificado**: 94 productos únicos de 96 en 3 páginas (antes repetía los mismos ~28 tres veces).

- [x] **Fix: productos de MercadoLibre por keyword no tenían link (abrían localhost)** (2026-11-20)
  - **Causa**: `_enriquecer_via_api()` dejaba `link: ""` esperando que el caller lo llenara; `buscar_por_keywords()` nunca lo hacía (a diferencia de Telegram/URL fija, aquí no hay URL de origen, solo un ID de catálogo).
  - **Fix**: se construye `https://www.mercadolibre.com.mx/p/{ID}` como link canónico — verificado con Playwright que carga la página real del producto sin necesitar el slug de título.

- [x] **Fix: Telegram solo traía ~20 mensajes por canal (unas horas, no los días configurados)** (2026-11-20)
  - **Causa**: `scrape_telegram_ultimos_dias()` hacía una sola petición a `t.me/s/canal`, que solo devuelve los últimos ~20 mensajes de Telegram (confirmado: cubría 8 horas, no 5 días). Explica por qué solo salían 12-16 ofertas de canales activos en "5 días".
  - **Fix**: se agregó paginación real usando el parámetro `?before={id_mensaje}` que soporta la vista pública de Telegram, con tope de seguridad de 30 páginas (~600 mensajes) para no pedir infinito.
  - **Verificado**: mismo canal pasó de 12 a **203 ASINs de Amazon** encontrados en una prueba real. Nota: canales muy activos pueden llegar al tope de 30 páginas sin cubrir el 100% de los días pedidos — subir el tope da más cobertura a cambio de más tiempo (cada página resuelve varios links cortos con peticiones HTTP reales).

- [x] **Fix: todos los productos de Telegram mostraban el nombre del primer canal configurado** (2026-11-20)
  - **Causa**: el código usaba `telegram_sources[0].get('nombre', ...)` fijo, sin importar cuál canal real trajo cada producto (relevante ahora que varios feeds tienen 2-3 canales de Telegram).
  - **Fix**: `telegram_utils.py` ahora rastrea el canal de origen por cada ASIN/producto ML individualmente. Se actualizaron los 4 puntos de `servidor.py` que consumen esto (`/feeds/buscar`, Ofertas, Novedades, `/feeds/telegram-extract`) para mostrar el canal real por producto.

- [x] **Confirmado: "Buscar por fuente → Telegram" se mantiene sin filtros de Ofertas/Novedades a propósito** (2026-11-20)
  - Usuario preguntó por qué ese botón no respeta los filtros de descuento/precio de Ofertas o Novedades. Se confirmó que es diseño intencional ("modo aprendizaje": el canal ya fue curado a mano, se confía en él). Usuario confirmó dejarlo así, sin cambios.

- [x] **Selector de canal (Amazon/MercadoLibre) agregado para Ofertas y Novedades** (2026-11-12/13)
  - Checkboxes visibles junto a los botones "Ofertas"/"Novedades" en la barra principal (no en un modal escondido), mutuamente excluyentes (marcar uno desmarca el otro) para evitar que se sumen los tiempos de espera de ambos canales.
  - Aplica a **Keywords** y **URLs fijas** (gatea cuál se busca). **Telegram queda exento a propósito**: es contenido curado a mano, siempre trae ambas plataformas sin importar el canal seleccionado.
  - Fix de bug real en el camino: `do_GET` calculaba `path = urlparse(self.path).path` (sin query string) pero el código seguía buscando `?parámetros` dentro de esa misma variable — rompía silenciosamente `refresh`, `fuente`, `sort_by` y el nuevo selector de canal. Corregido usando `self.path` para leer la query string.

- [x] **MercadoLibre por keyword paralelizado (5 a la vez) + botón Detener real** (2026-11-12)
  - `buscar_por_keywords()` ahora verifica hasta 5 productos en paralelo (`ThreadPoolExecutor`) en vez de uno por uno — de ~20-26s/keyword a ~2.5s/keyword.
  - Servidor migrado a multi-hilo (`ThreadingMixIn`) y nuevo endpoint `/detener` que activa una bandera global (`CANCELAR_BUSQUEDA`) revisada entre keywords — corta la búsqueda en curso sin apagar el servidor.

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
