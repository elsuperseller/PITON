# Amazon México - BrowseNodeIds Oficiales

**Actualizado:** 2026-10-08  
**Método:** GetBrowseNodes API  
**Marketplace:** www.amazon.com.mx

## Resumen

Este catálogo contiene los **browseNodeIds correctos** para Amazon México, obtenidos directamente usando la API GetBrowseNodes.

### ❌ Problema Anterior

Los nodeIds anteriores (ej: `9482662011`, `9482666011`, `9482676011`) **NO correspondían a las categorías correctas**. Por ejemplo:
- `9482676011` (se pensaba que era "Juguetes__Coleccionables") → en realidad era "Custom Stores" bajo "Herramientas"
- Esto causaba que búsquedas de Juguetes trajeran Caladoras y otros productos de Herramientas

### ✅ Solución

Mapeamos la jerarquía completa usando GetBrowseNodes API y actualizamos todos los nodeIds.

---

## Estructura de BrowseNodeIds en Amazon

```
Nodo Raíz (ej: 11260442011 "Juguetes y Juegos")
  ├─ Arborist Merchandising Root (interno, no usar)
  ├─ Categorías (11260443011) ← ESTE es el que queremos
  │   ├─ Figuras de Acción (11337634011)
  │   ├─ Muñecas y Accesorios (11337428011)
  │   └─ ...
  └─ Specialty Stores (interno, no usar)
```

**Importante:** El nodo que contiene las subcategorías reales se llama **"Categorías"** y está un nivel debajo de la raíz.

---

## Catálogo de Nodos

### Nodos Raíz
| Categoría Principal | Node ID | Nodo "Categorías" |
|---------------------|---------|-------------------|
| Juguetes y Juegos | `11260442011` | `11260443011` |
| Electrónicos | `9482558011` | `9482559011` |
| Hogar y Cocina | `9482593011` | `9482594011` |
| Deportes y Aire Libre | `9482660011` | `9482661011` |
| Ropa, Zapatos y Accesorios | `9482610011` | - |
| Libros | `9298576011` | - |

---

## Juguetes y Juegos

**Root:** `11260442011`  
**Categorías Node:** `11260443011`

| Subcategoría | Node ID |
|--------------|---------|
| **Figuras de Acción** | `11337634011` |
| **Muñecas y Accesorios** | `11337428011` |
| **Coleccionables** | `20940159011` |
| Muñecos, Figuras y Sets de Juego | `11337429011` |
| Juegos y Accesorios para Juegos | `11337420011` |
| Juguetes Educativos | `11337424011` |
| Juegos de Construcción | `11337421011` |
| Vehículos de Juguete | `11337433011` |
| Aire Libre y Deportes | `11337412011` |
| Peluches | `11337430011` |
| Rompecabezas | `11337431011` |
| Radiocontrol | `11337504011` |
| Juguetes Electrónicos | `11337425011` |
| Artes y Manualidades | `11337413011` |
| Artículos para Fiesta | `11337414011` |
| Instrumentos Musicales de Juguete | `11337418011` |
| Juegos de Imitación | `11337422011` |
| Juguetes Novedosos y de Broma | `11337426011` |
| Juguetes para Bebés y Niños Pequeños | `11337427011` |
| Títeres y Escenarios para Títeres | `11337432011` |

---

## Electrónicos

**Root:** `9482558011`  
**Categorías Node:** `9482559011`

| Subcategoría | Node ID |
|--------------|---------|
| Computadoras, Componentes y Accesorios | `9687880011` |
| Celulares y Accesorios | `9687422011` |
| Televisión y Vídeo | `9687925011` |
| Cámaras y Fotografía | `9687605011` |
| Equipos de Audio y Hi-Fi | `9687565011` |
| Audio y Video Portátil | `9687392011` |
| Audífonos, auriculares y accesorios | `24035342011` |
| Tabletas | `10189676011` |
| Tecnología para Vestir | `15144312011` |
| Teléfonos, VoIP y Accesorios | `9687911011` |
| Lectores de Libros Electrónicos | `9687881011` |
| Electrónica para Autos | `9687471011` |
| Navegación Satelital, GPS | `9687860011` |
| Electrónicos de Oficina | `9705965011` |
| Pilas y Cargadores | `9687374011` |
| Accesorios de Alimentación | `9687281011` |
| Radiocomunicación | `9687892011` |

---

## Hogar y Cocina

**Root:** `9482593011`  
**Categorías Node:** `9482594011`

| Subcategoría | Node ID |
|--------------|---------|
| Cocina | `9721682011` |
| Muebles | `9757251011` |
| Decoración del Hogar | `9757037011` |
| Iluminación | `9939347011` |
| Blancos para el Hogar | `9757431011` |
| Baño | `9756950011` |
| Climatización y Calefacción | `9725442011` |
| Almacenamiento y Organización | `9756857011` |
| Aspiración, Limpieza y Planchado | `9725297011` |
| Cuidado del Hogar y Limpieza | `11525771011` |
| Obras de Arte y Material Decorativo | `9757416011` |
| Arte y Manualidades | `10201738011` |

---

## Deportes y Aire Libre

**Root:** `9482660011`  
**Categorías Node:** `9482661011`

| Subcategoría | Node ID |
|--------------|---------|
| Fútbol | `9786709011` |
| Basquetbol | `9784119011` |
| Béisbol | `9784206011` |
| Ciclismo | `9784530011` |
| Correr | `9790484011` |
| Atletismo | `9784025011` |
| Gimnasia | `9789894011` |
| Tenis | `9789598011` |
| Golf | `9789827011` |
| Deportes Acuáticos | `9785900011` |
| Deportes de Invierno | `9786306011` |
| Campismo y Senderismo | `9783688011` |
| Caza | `9784387011` |
| Pesca | `9786633011` |
| Artes Marciales | `9783947011` |
| Box | `9784332011` |
| Bádminton | `9784072011` |
| Balonmano | `9784163011` |
| Billar | `9784285011` |
| Boliche | `9784303011` |
| Danza | `9785852011` |
| Airsoft | `9783917011` |
| Animación | `9784513011` |

---

## Cómo Usar

### En búsquedas de searchItems:

```python
body = {
    "partnerTag": PARTNER_TAG,
    "marketplace": "www.amazon.com.mx",
    "browseNodeId": "11337634011",  # Figuras de Acción
    "searchIndex": "ToysAndGames",
    # ...
}
```

**Importante:** Usar el ID de la **subcategoría específica**, NO el nodo raíz ni el nodo "Categorías".

### Para explorar más subcategorías:

```python
# Usar GetBrowseNodes con el nodo "Categorías"
body = {
    "partnerTag": PARTNER_TAG,
    "marketplace": "www.amazon.com.mx",
    "browseNodeIds": ["11260443011"],  # Nodo "Categorías" de Juguetes
    "resources": ["browseNodes.children"]
}
```

---

## Archivos Generados

- `amazon_roots.json` - Nodos raíz de categorías principales
- `amazon_catalog.json` - Catálogo completo con todas las subcategorías
- `amazon_browse_nodes.py` - Funciones helper para obtener nodeIds por nombre
- `browse_nodes_juguetes.json` - Estructura completa de Juguetes
- `juguetes_categorias.json` - Subcategorías de Juguetes (plano)
- `figuras_categorias.json` - Subcategorías de "Muñecos, Figuras y Sets"

---

## Verificación

Para verificar que un nodeId es correcto:

```python
body = {
    "partnerTag": PARTNER_TAG,
    "marketplace": "www.amazon.com.mx",
    "browseNodeIds": ["11337634011"],
    "resources": ["browseNodes.ancestor"]
}

# Revisar la jerarquía completa hasta la raíz
# Debe mostrar: Figuras de Acción → Muñecos, Figuras... → Categorías → Juguetes y Juegos
```

---

## Changelog

### 2026-10-08
- ✅ Mapeadas todas las categorías principales usando GetBrowseNodes API
- ✅ Actualizados nodeIds en `servidor.py` para Juguetes, Electrónicos, Hogar, Deportes
- ✅ Descubierto y corregido error: nodeIds anteriores apuntaban a categorías incorrectas
- ✅ Verificado que Juguetes__Coleccionables ahora trae juguetes, no herramientas
