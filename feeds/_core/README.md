# 📊 Sistema de Feeds por Audiencia

## Estructura

```
feeds/
├── perfiles_audiencia.json       # Configuración de cada feed (keywords, filtros, URLs)
├── feeds_cache.json               # Cache temporal de feeds generados
├── historial_coleccionistas.json # Tracking adicional feed Collector Secret Society
└── README.md                      # Este archivo
```

## Cómo funciona

### 1. LÓGICA CENTRALIZADA (Core Superseller)
- **`../historial_variedad.py`** - Algoritmos de scoring, detección de modelos, lógica de novedad
- **IMPORTANTE:** La lógica es compartida, pero cada sistema tiene su propio historial

### 2. HISTORIALES SEPARADOS
- **`../historial.json`** - Historial SOLO de Superseller regular
- **`historial_coleccionistas.json`** - Historial SOLO del feed Collector Secret Society
- **`historial_gamers.json`** - Historial SOLO del feed Gamers (cuando se cree)
- Cada feed es independiente

### 2. Configuración POR NICHO
- **`perfiles_audiencia.json`** - Define cada feed:
  - Keywords específicas del nicho
  - Filtros (precio, descuento, etc.)
  - URLs fijas (páginas curadas de Amazon)
  - Google Sheets export URL

### 3. Tracking ADICIONAL por feed
- **`historial_coleccionistas.json`** - Tracking específico del feed
- Se combina con el historial core para mejor precisión

## Agregar un nuevo feed

1. Editar `perfiles_audiencia.json`
2. Agregar nuevo objeto con estructura similar a "coleccionistas"
3. El sistema creará automáticamente `historial_[nombre].json`

## Validación de productos

### Para URLs fijas (ofertas del día):
1. ✅ Valida categoría de Amazon (es_categoria_coleccionable)
2. ✅ Aplica excludeKeywords
3. ✅ Scoring de novedad del CORE
4. ✅ Filtros de precio/descuento

### Para keywords:
1. ✅ Búsqueda por API de Amazon
2. ✅ Aplica excludeKeywords
3. ✅ Scoring de novedad del CORE
4. ✅ Filtros de precio/descuento

## Exportación

Al exportar a Google Sheets:
- ✅ Marca productos en **historial CORE** (../historial.json)
- ✅ Marca productos en **historial del feed**
- ✅ Ambos se usan para detectar repetidos
