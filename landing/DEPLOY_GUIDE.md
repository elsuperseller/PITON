# 🚀 Guía de Deploy a la Nube

## 📋 Resumen

Vamos a subir tu landing de cupones a la nube para que funcione 24/7 sin necesidad de que tu computadora esté encendida.

**Lo que lograremos:**
- ✅ URL pública (ej: `superseller-cupones.up.railway.app`)
- ✅ Bot de Telegram funcionando 24/7
- ✅ Agregar cupones desde cualquier lugar del mundo
- ✅ Sin costos (plan gratuito)

---

## 🎯 Opción 1: Railway (RECOMENDADA - MÁS FÁCIL)

### Ventajas:
- ✅ **Gratis** (hasta $5/mes de crédito)
- ✅ **Súper fácil** de configurar
- ✅ **Deploy automático** desde GitHub
- ✅ **Base de datos** incluida si la necesitas después

### Pasos:

#### 1️⃣ Crear cuenta en Railway
1. Ve a https://railway.app
2. Haz clic en "Start a New Project"
3. Conecta con GitHub

#### 2️⃣ Subir código a GitHub
```bash
cd ~/Desktop/SUPERSELLER/landing

# Inicializar git
git init
git add .
git commit -m "Landing de cupones Superseller"

# Crear repositorio en GitHub (desde la web o CLI)
gh repo create superseller-landing --public --source=. --remote=origin --push

# O manualmente:
# 1. Crea repo en github.com
# 2. git remote add origin https://github.com/TU_USUARIO/superseller-landing.git
# 3. git push -u origin main
```

#### 3️⃣ Deploy en Railway
1. En Railway, click "New Project"
2. Selecciona "Deploy from GitHub repo"
3. Elige tu repositorio `superseller-landing`
4. Railway detectará automáticamente Python
5. ¡Listo! Se deployará automáticamente

#### 4️⃣ Configurar variables de entorno
En Railway:
1. Ve a tu proyecto
2. Click en "Variables"
3. Agrega:
   - `TELEGRAM_BOT_TOKEN` = (el token que te dará BotFather)
   - `PORT` = `8080` (opcional, Railway lo asigna automáticamente)

#### 5️⃣ Obtener URL pública
1. Railway te dará una URL como: `superseller-cupones.up.railway.app`
2. Esa es tu landing pública ✨

---

## 🤖 Configurar el Bot de Telegram

### 1️⃣ Crear el bot

1. Abre Telegram
2. Busca **@BotFather**
3. Envía `/newbot`
4. Elige un nombre: `Superseller Cupones`
5. Elige un username: `SupersellerCuponesBot` (debe terminar en "bot")
6. BotFather te dará un **TOKEN** como:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
7. **GUARDA ESE TOKEN** (lo necesitarás)

### 2️⃣ Agregar el token a Railway

1. En Railway → Variables
2. Agrega:
   - **Nombre:** `TELEGRAM_BOT_TOKEN`
   - **Valor:** `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` (tu token)

### 3️⃣ Reiniciar el servicio

Railway reiniciará automáticamente. Espera 1-2 minutos.

### 4️⃣ Probar el bot

1. Abre Telegram
2. Busca tu bot: `@SupersellerCuponesBot`
3. Envía `/start`
4. Deberías ver el mensaje de bienvenida

### 5️⃣ Agregar tu primer cupón

Envía al bot:
```
15% desc SUPER15 min 500 max 150 vence 20/08 dorado destacado
```

El bot responderá:
```
✅ Cupón agregado exitosamente!
⭐📦 15% de descuento
Código: SUPER15
...
🌐 Ya está visible en la landing!
```

Visita tu URL y verás el cupón ✨

---

## 🌐 Opción 2: Render

### Si prefieres Render en vez de Railway:

1. Ve a https://render.com
2. Crea cuenta (gratis)
3. "New Web Service"
4. Conecta GitHub
5. Selecciona el repo
6. Configura:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python servidor_landing.py`
7. Agrega variables de entorno
8. Deploy

Para el bot, crea otro servicio:
- **Start Command:** `python bot_telegram.py`
- Agrega el mismo `TELEGRAM_BOT_TOKEN`

---

## 🎯 Opción 3: Vercel + Bot separado

### Landing en Vercel (estática)
1. Convierte a estática (generar HTML una vez)
2. Deploy en Vercel (súper rápido)

### Bot en Railway
1. Solo el bot en Railway
2. Actualiza un JSON en GitHub
3. Vercel redeploya automáticamente

---

## 📱 Uso Diario (después del deploy)

### Desde cualquier lugar:

1. **Recibes cupón por WhatsApp**
2. **Abres Telegram** (desde el celular)
3. **Envías al bot:**
   ```
   20% MEGA20 min 800 max 200 vence 25/08
   ```
4. **Bot responde:** ✅ Cupón agregado!
5. **La página se actualiza** automáticamente

**Tiempo total: 10 segundos**

---

## 🔒 Seguridad

### Restringir el bot solo a ti:

1. Busca tu ID de Telegram:
   - Envía mensaje a @userinfobot
   - Te dirá tu ID (ej: `123456789`)

2. En Railway, agrega variable:
   - **Nombre:** `USUARIOS_AUTORIZADOS`
   - **Valor:** `123456789` (tu ID)

3. Edita `bot_telegram.py` y descomenta las líneas 183-185:
   ```python
   if USUARIOS_AUTORIZADOS and update.effective_user.id not in USUARIOS_AUTORIZADOS:
       await update.message.reply_text("⛔ No tienes permiso para usar este bot.")
       return
   ```

Ahora solo tú puedes agregar cupones ✅

---

## 💰 Costos

### Railway (Plan Gratuito):
- ✅ $5 USD de crédito mensual gratis
- ✅ Suficiente para este proyecto
- ✅ ~500 horas de servidor/mes
- ⚠️ Después de agotar crédito, se pausa

### Render (Plan Gratuito):
- ✅ Gratis para siempre
- ⚠️ Se "duerme" después de 15 min sin actividad
- ⚠️ Tarda ~30s en "despertar"

### Mi recomendación:
**Railway** para empezar (más rápido), luego migrar a servidor propio si crece.

---

## 🆘 Troubleshooting

### El bot no responde:
1. Verifica que Railway esté corriendo
2. Checa los logs en Railway
3. Verifica el token en variables de entorno

### La landing no carga:
1. Verifica la URL en Railway
2. Checa los logs
3. Asegúrate que `PORT` esté bien configurado

### Los cupones no se guardan:
1. Railway puede necesitar un volumen persistente
2. O usar PostgreSQL para guardar cupones
3. (Te ayudo con esto si es necesario)

---

## 🎁 Bonus: Dominio Personalizado

### Si quieres `cupones.superseller.com`:

1. Compra dominio (ej: en Namecheap)
2. En Railway:
   - Settings → Custom Domain
   - Agrega `cupones.superseller.com`
3. En tu proveedor de dominio:
   - Agrega registro CNAME:
   - `cupones` → `tu-app.up.railway.app`
4. ¡Listo! En 5 minutos estará activo

---

## ✅ Checklist de Deploy

- [ ] Cuenta en Railway creada
- [ ] Código subido a GitHub
- [ ] Proyecto deployado en Railway
- [ ] Bot de Telegram creado con BotFather
- [ ] Token agregado a variables de entorno
- [ ] Bot probado y funcionando
- [ ] Primer cupón agregado exitosamente
- [ ] URL pública funcionando

---

## 📞 Siguiente paso

**¿Listo para deployar?**

Te ayudo paso a paso con:
1. Subir a GitHub
2. Configurar Railway
3. Crear el bot de Telegram
4. Hacer la primera prueba

¿Empezamos? 🚀
