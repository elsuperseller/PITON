# 📋 TAREAS - SUPERSELLER

**Última actualización**: 2026-10-29

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
