# 📋 TAREAS - SUPERSELLER

**Última actualización**: 2026-10-26

---

## ⏳ PENDIENTES

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

- [x] Fix búsqueda keywords - API response `searchResult` vs `itemsResult` (2026-10-23)
- [x] Fix export Google Sheets - ProductosState y selector CSS (2026-10-23)
- [x] Filtro historial - Productos publicados últimos 21 días (2026-10-23)
- [x] Aumento límite keywords - 50 → 200 (2026-10-23)
- [x] Reducción descuento mínimo - 15% → 1% (2026-10-23)
- [x] Badge keyword específica - Mostrar `🎯 keyword` en cada producto (2026-10-23)
- [x] Sincronización GitHub - Todos los cambios pusheados (2026-10-23)
