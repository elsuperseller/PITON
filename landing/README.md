# 🎯 Landing de Cupones - Superseller

Landing page dinámica para mostrar cupones de descuento, inspirada en Rep Joe.

## 📁 Archivos

```
landing/
├── cupones.json           # Base de datos de cupones (EDITAR AQUÍ)
├── servidor_landing.py    # Servidor Python
├── index.html            # Template HTML
├── iniciar.sh            # Script para iniciar servidor
└── README.md             # Este archivo
```

## 🚀 Cómo usar

### 1. Iniciar el servidor

```bash
cd ~/Desktop/SUPERSELLER/landing
python3 servidor_landing.py
```

O usa el script:
```bash
./iniciar.sh
```

### 2. Abrir en navegador

Abre tu navegador en: **http://localhost:8080**

### 3. Actualizar cupones

Edita el archivo `cupones.json` y recarga la página. ¡Así de simple!

---

## 📝 Cómo editar cupones

### Estructura de un cupón en `cupones.json`:

```json
{
  "id": "cup001",                    // ID único
  "titulo": "15% de descuento",      // Título visible
  "codigo": "SUPERSELLER15",         // Código del cupón
  "tipo": "porcentaje",              // "porcentaje" o "monto"
  "descuento": 15,                   // Valor del descuento
  "compra_minima": 500,              // Compra mínima requerida
  "descuento_maximo": 150,           // Tope máximo de descuento
  "plataforma": "Mercado Libre",     // Nombre de la plataforma
  "logo_url": "https://...",         // URL del logo
  "vencimiento": "2026-08-13",       // Fecha YYYY-MM-DD
  "destacado": true,                 // true = aparece en sección destacada
  "color_fondo": "gold",             // gold, blue, purple, green, red
  "activo": true                     // true = se muestra, false = oculto
}
```

### Colores disponibles:

- `"gold"` - Dorado (para cupones TOP)
- `"blue"` - Azul/Morado
- `"purple"` - Rosa/Morado claro
- `"green"` - Verde azulado
- `"red"` - Rojo

### Ejemplo: Agregar un nuevo cupón

1. Abre `cupones.json`
2. Agrega un nuevo objeto al array `"cupones"`:

```json
{
  "id": "cup004",
  "titulo": "$1000 de descuento",
  "codigo": "MEGA1000",
  "tipo": "monto",
  "descuento": 1000,
  "compra_minima": 5000,
  "descuento_maximo": 1000,
  "plataforma": "Mercado Libre",
  "logo_url": "https://http2.mlstatic.com/frontend-assets/ml-web-navigation/ui-navigation/5.21.22/mercadolibre/logo__large_plus.png",
  "vencimiento": "2026-08-20",
  "destacado": true,
  "color_fondo": "red",
  "activo": true
}
```

3. Guarda el archivo
4. Recarga la página en el navegador

---

## ⚙️ Configuración del sitio

En `cupones.json`, sección `"configuracion"`:

```json
"configuracion": {
  "titulo_sitio": "Cupones Superseller",
  "descripcion": "Los mejores cupones de descuento",
  "redes_sociales": {
    "whatsapp": "https://wa.me/1234567890",
    "telegram": "https://t.me/superseller",
    "facebook": "https://facebook.com/superseller",
    "youtube": "https://youtube.com/@superseller"
  },
  "logo_url": "",
  "actualizado": "2026-08-13"
}
```

---

## 🔧 Mantenimiento diario

### Workflow recomendado:

1. **Cada día:**
   - Abre `cupones.json`
   - Actualiza las fechas de vencimiento
   - Agrega nuevos cupones
   - Marca cupones viejos como `"activo": false`
   - Guarda

2. **La página se actualiza automáticamente** al recargar

3. **No necesitas tocar HTML ni código Python**

---

## 🌐 API Endpoint

El servidor también expone un endpoint JSON:

**GET** `http://localhost:8080/api/cupones`

Retorna todos los cupones en formato JSON. Útil para integraciones futuras.

---

## 🎨 Personalización

### Cambiar colores del sitio

Edita `index.html`, sección `:root`:

```css
:root {
    --bg-primary: #0a0a0a;        /* Fondo principal */
    --bg-card: #1a1a1a;           /* Fondo de tarjetas */
    --text-primary: #ffffff;      /* Texto principal */
    --accent-green: #4ade80;      /* Botón "Copiar" */
    --accent-gold: #fbbf24;       /* Badges destacados */
}
```

---

## 📱 Responsive

La página está optimizada para:
- Desktop
- Tablet
- Mobile

Se adapta automáticamente al tamaño de pantalla.

---

## 🚨 Troubleshooting

### El servidor no arranca
- Verifica que el puerto 8080 esté libre
- Cambia `PORT = 8080` en `servidor_landing.py`

### Los cupones no se muestran
- Verifica que `cupones.json` sea JSON válido
- Usa un validador JSON online

### Error al copiar cupones
- Requiere HTTPS o localhost
- Funciona en localhost sin problemas

---

## 📦 Deploy a producción

Para subir a un servidor:

1. **Opción 1: Servidor Python simple**
   - Sube toda la carpeta `landing/`
   - Ejecuta `python3 servidor_landing.py`
   - Usa un proceso manager (PM2, systemd)

2. **Opción 2: Servidor web (nginx/apache)**
   - Genera el HTML estático una vez
   - Sírvelo como archivo estático
   - Regenera cuando actualices cupones

3. **Opción 3: Integrar con servidor principal**
   - Agrega la ruta al `servidor.py` principal
   - Usa el mismo puerto que Superseller

---

## ✨ Próximas mejoras

- [ ] Panel admin para editar cupones desde la web
- [ ] Analytics de clicks en cupones
- [ ] Notificaciones push de nuevos cupones
- [ ] Integración con API de Mercado Libre
- [ ] Cupones por categorías
- [ ] Búsqueda de cupones

---

**¿Dudas?** Contacta al equipo de Superseller.
