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
