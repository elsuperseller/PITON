# 📘 SUPERSELLER - Instrucciones para Claude

**Proyecto**: Superceller Creator App  
**Propietario**: Isaac (isaac@elsuperseller.com)  
**GitHub**: elsuperseller/PITON  
**Última actualización**: 2026-10-26

---

## 🏗️ ARQUITECTURA

### Stack Técnico
- **Backend**: `servidor.py` (Flask, Python)
  - Puerto: 8765
  - API: Amazon PA-API 5.0
  - Logs: `servidor.log`
- **Frontend**: `superseller.html` (Vanilla JS SPA)
- **Configuración**: 
  - Feeds: `feeds/perfiles_audiencia.json`
  - Historial: `feeds/*/historial.json`
- **Control de versiones**: Git → GitHub elsuperseller/PITON

### Comandos
```bash
# Iniciar servidor
./start.sh

# Detener servidor
./stop.sh

# Ver logs en tiempo real
tail -f servidor.log

# Verificar estado
ps aux | grep servidor.py
```

---

## 🔴 NUNCA HACER (Errores Críticos)

### 1. NO cambiar `searchResult` a `itemsResult`
```python
# ❌ INCORRECTO (error común)
items = data.get("itemsResult", {}).get("items", [])

# ✅ CORRECTO (Amazon PA-API 5.0)
items = data.get("searchResult", {}).get("items", [])
```
**Por qué**: Amazon PA-API 5.0 usa `searchResult`, no `itemsResult`

### 2. NO omitir `setFeedId()` antes de `setItems()`
```javascript
// ❌ INCORRECTO
ProductosState.setItems(allItems)

// ✅ CORRECTO
ProductosState.setFeedId(feedId)  // PRIMERO
ProductosState.setItems(allItems)  // DESPUÉS
```
**Por qué**: Export irá al Google Sheet incorrecto

### 3. NO correr desde Google Drive
- Nunca ejecutar servidor desde carpetas sincronizadas (Google Drive, Dropbox)
- Causa: ETIMEDOUT y errores de I/O
- Ver: `feedback_avoid_cloud_sync_for_dev_servers.md`

### 4. NO usar selector `.result-item`
```javascript
// ❌ INCORRECTO
document.querySelectorAll('.result-item:not([style*="display: none"]) .select-chk')

// ✅ CORRECTO
document.querySelectorAll('.product-card:not([style*="display: none"]) .select-chk')
```
**Por qué**: Los divs usan clase `.product-card`

---

## 🐛 PROBLEMAS CONOCIDOS Y SOLUCIONES

### Búsqueda por Keywords

**Problema**: Búsqueda no retorna productos
- **Causa**: Usar `itemsResult` en vez de `searchResult`
- **Solución**: `servidor.py` línea ~2751 usa `searchResult`

**Problema**: "Selecciona al menos un producto VISIBLE"
- **Causa**: `ProductosState.setItems()` no se ejecutaba
- **Solución**: Llamar directamente sin `if (window.ProductosState)` check

**Configuración actual**:
- Límite keywords: 200 (antes: 50)
- Páginas por keyword: 3
- Total requests: hasta 600 a Amazon PA-API
- Descuento mínimo: 1% (antes: 15%)

### Export a Google Sheets

**Feeds**:
- SUPERSELLER: `superseller_google_sheet.md`
- Coleccionistas: `coleccionistas_google_sheet.md`

**Flujo correcto**:
1. Usuario selecciona feed (audiencia)
2. Busca productos (keywords/telegram/urls)
3. `ProductosState.setFeedId(feedId)` ← CRÍTICO
4. `ProductosState.setItems(allItems)`
5. Usuario selecciona productos visibles
6. Export envía a URL correcta según `feedId`

**Problema**: Export va a Sheet incorrecto
- **Causa**: No se llamó `setFeedId()` antes de `setItems()`
- **Solución**: En `buscarKeywords()`, `buscarSoloTelegram()`, `buscarSoloURLs()` siempre llamar `setFeedId()` primero

### Filtro de Historial

**Propósito**: Evitar republicar productos recientes

**Reglas**:
- Productos publicados hace < 21 días → Filtrados
- Productos bloqueados (descartados) → Filtrados
- Archivo: `feeds/{audiencia_id}/historial.json`

**Ubicación en código**:
- Backend: `servidor.py` líneas ~2774-2816
- Función: `cargar_historial_feed(audiencia_id)`

### Badges en Productos

**Sistema de badges**:
- `🎯 keyword` → Muestra qué keyword encontró el producto
- Permite identificar keywords que traen productos no deseados

**Implementación**:
- Backend marca: `item['_keyword_match'] = keyword`
- Backend parsea: `p['badge'] = f'🎯 {keyword_match}'`
- Frontend muestra: Badge visible en card de producto

---

## 🎯 WORKFLOWS IMPORTANTES

### Agregar Nueva Keyword
1. Frontend: Usuario selecciona feed
2. Frontend: Ingresa keywords en textarea
3. Frontend: Click "Buscar"
4. Backend: `/feeds/buscar-keywords`
   - Itera por cada keyword (máx 200)
   - Por cada keyword: 3 páginas Amazon API
   - Marca cada item con `_keyword_match`
5. Backend: Filtra historial (21 días + bloqueados)
6. Backend: Parsea y agrega badge `🎯 keyword`
7. Frontend: Muestra productos con badge visible

### Export de Productos a Google Sheets
1. Frontend: Usuario selecciona productos (checkboxes)
2. Frontend: Click botón "Exportar a Google Sheets"
3. Frontend: Obtiene `feedId` de `ProductosState`
4. Frontend: Lee `sheets_export_url` del perfil
5. Frontend: POST a Google Apps Script webhook
6. Backend (Google): Inserta filas en spreadsheet
7. Frontend: Muestra confirmación

### Agregar Producto al Historial
- Al publicar producto → se agrega a `historial.json`
- Campos: `asin`, `ultima_vez` (timestamp), `blocked` (bool)
- Al buscar de nuevo → se filtra si `ultima_vez` < 21 días

---

## 📂 ESTRUCTURA DE ARCHIVOS CLAVE

```
SUPERSELLER/
├── servidor.py           # Backend Flask
├── superseller.html      # Frontend SPA
├── start.sh             # Inicia servidor
├── stop.sh              # Detiene servidor
├── servidor.log         # Logs del servidor
├── TAREAS.md            # Pendientes y completadas
├── CLAUDE.md            # Este archivo
├── feeds/
│   ├── perfiles_audiencia.json    # Config de feeds
│   ├── coleccionistas/
│   │   └── historial.json         # Historial feed coleccionistas
│   └── superseller/
│       └── historial.json         # Historial feed superseller
└── imagenes.py          # Procesamiento de imágenes
```

---

## 🔧 CONFIGURACIÓN

### Amazon PA-API 5.0
- Endpoint: SearchItems
- Response: `data.searchResult.items[]`
- Cada item contiene: `ASIN`, `ItemInfo`, `Images`, `Offers`

### Google Sheets Export
- Método: POST a Google Apps Script webhook
- URLs configuradas en `perfiles_audiencia.json`
- Campo: `sheets_export_url`

### Feeds (Audiencias)
- Coleccionistas: ID en `perfiles_audiencia.json`
- SUPERSELLER: ID en `perfiles_audiencia.json`
- Cada feed tiene su propio historial

---

## 📝 NOTAS IMPORTANTES

### Al Hacer Cambios en Código
1. Leer archivo completo antes de modificar
2. Hacer cambio mínimo necesario
3. Preguntar al usuario antes si no estás seguro
4. Verificar antes y después del cambio
5. Ver: `feedback_verificar_antes_modificar.md`

### Al Trabajar con Git
1. Commits descriptivos
2. No forzar push a main
3. Siempre revisar `git status` antes de commit
4. Co-authored: Claude Sonnet 4.5

### Performance
- Búsqueda de 200 keywords puede tardar varios minutos
- Amazon API tiene rate limits
- Timeout común si API lenta → reintentar

---

## 🔗 REFERENCIAS

- Memoria proyecto: `~/.claude/projects/-Users-isaac/memory/project_superceller_setup.md`
- Tareas: `/Users/isaac/Desktop/SUPERSELLER/TAREAS.md`
- Google Sheet SUPERSELLER: Ver `superseller_google_sheet.md`
- Google Sheet Coleccionistas: Ver `coleccionistas_google_sheet.md`
- ML Lightning API: Ver `ml_lightning_api_endpoint.md`

---

## 📊 MÉTRICAS Y LÍMITES ACTUALES

- Keywords por búsqueda: 200
- Páginas por keyword: 3
- Total API calls: ~600 (200 × 3)
- Descuento mínimo: 1%
- Filtro historial: 21 días
- Timeout API: ~10 segundos por request

---

**Última sesión**: 2026-10-23 - Fix búsqueda keywords, export Google Sheets, filtro historial, badges
