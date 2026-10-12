# 🛒 Guía: Scraping de Mercado Libre

## ✅ Configuración completada

Ya está todo listo para usar. Solo necesitas saber cómo funciona.

---

## 🚀 Cómo usar desde la interfaz web

### **Paso 1: Abrir interfaz**

```
http://localhost:8765
```

### **Paso 2: Configurar URLs de ML en un feed**

1. Ve a tu feed/audiencia
2. En la sección "URLs Fijas" agrega:
   - **URL:** `https://www.mercadolibre.com.mx/ofertas`
   - **Descripción:** `Ofertas del día`

3. Guarda

### **Paso 3: Buscar productos**

1. Haz clic en **"Buscar URLs"** o **"Buscar Ofertas ML"**
2. ⏳ **Espera 5-10 segundos**
3. 👀 **Verás una ventana de Chrome abrirse brevemente** (es normal)
4. ✅ **Productos aparecen en la interfaz**

---

## 👀 ¿Qué verás?

### **Durante la búsqueda:**

```
Tu navegador (localhost:8765)     Segunda ventana Chrome
┌─────────────────────┐           ┌─────────────────────┐
│ [Buscar Ofertas]    │           │                     │
│ ⏳ Buscando...      │    →→→    │ ML ofertas (5 seg)  │
│                     │           │ ✅ Se cierra sola   │
│ ✅ 66 productos     │           └─────────────────────┘
└─────────────────────┘
```

**Esto es NORMAL y NECESARIO:**
- La ventana de Chrome se abre porque Mercado Libre detecta navegadores "invisibles" (headless)
- Se cierra automáticamente cuando termina
- Dura solo 5-10 segundos

---

## ⚙️ Configuración actual

### **✅ Lo que YA está funcionando:**

1. **Sesión guardada:**
   - Tu login de ML está en: `~/Desktop/SUPERSELLER/.ml_browser_profile/`
   - El scraper usa tu sesión para evitar bloqueos
   - No necesitas volver a loguearte

2. **Scraper integrado:**
   - Función: `_scrape_listado_playwright()` en `scraper_ml.py`
   - Método: Extrae productos del DOM (HTML)
   - Modo: Visible (headless=False)

3. **Endpoints funcionando:**
   - `/buscar-ml` → Scraper ML directo
   - `/feeds/buscar-urls` → Detecta ML y usa scraper apropiado
   - `/feeds/buscar` → Búsquedas generales

---

## 🔧 Mantenimiento

### **Si ML pide login de nuevo:**

Ejecuta:
```bash
cd ~/Desktop/SUPERSELLER
python3 ml_login.py
```

Loguéate y listo. No necesitas hacer nada más.

### **Si quieres desactivar la ventana visible:**

**NO RECOMENDADO** - ML no cargará productos.

Pero si quieres intentar:
1. Edita `scraper_ml.py`
2. Busca: `headless=False`
3. Cambia a: `headless=True`
4. Reinicia: `./stop.sh && ./start.sh`
5. **Resultado esperado:** 0 productos (ML detecta headless)

---

## 📊 URLs compatibles

### **✅ Funcionan:**
- `https://www.mercadolibre.com.mx/ofertas`
- `https://www.mercadolibre.com.mx/ofertas?container_id=XXX`
- URLs de categorías con ofertas

### **❌ Posibles problemas:**
- URLs de búsqueda específicas (pueden o no funcionar)
- URLs que requieren scroll infinito (solo carga primera página)

---

## 🎯 Próximas mejoras (opcionales)

### **Opción A: Modo headless con anti-detección avanzada**
- Usar `playwright-stealth`
- Más complejo
- Puede funcionar o no

### **Opción B: Proxies rotatorios**
- Servicio pago (~$50/mes)
- Permite headless
- Más escalable

### **Opción C: Dejar como está**
- **RECOMENDADO POR AHORA**
- Funciona bien
- Solo "molestia visual" de la ventana

---

## ✅ Resumen

**Estado actual: FUNCIONANDO** ✅

- Scraper: ✅ Extrae productos
- Sesión: ✅ Guardada
- Bloqueos: ✅ Evitados
- Limitación: ⚠️ Ventana visible 5 segundos

**Próximo paso:** Úsalo normalmente desde localhost:8765

