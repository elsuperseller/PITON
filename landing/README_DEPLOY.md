# 🎯 Landing de Cupones Superseller

Landing page dinámica para mostrar cupones de Mercado Libre con actualización automática vía Telegram Bot.

## ✨ Características

- 📱 **Panel Admin web** para agregar cupones
- 🤖 **Bot de Telegram** para agregar cupones desde WhatsApp/Telegram
- 🎨 **Diseño moderno** inspirado en Rep Joe
- 📊 **Categorías:** Destacados, Regulares, Bancarios
- ⏰ **Temporizadores automáticos** de vencimiento
- 🌐 **Responsive** (mobile, tablet, desktop)
- ☁️ **Cloud-ready** (Railway, Render, Vercel)

## 🚀 Deploy Rápido

### Opción 1: Railway (Recomendado)

```bash
# 1. Subir a GitHub
git init
git add .
git commit -m "Initial commit"
gh repo create superseller-landing --public --source=. --push

# 2. Deploy en Railway
# - Ve a railway.app
# - New Project → Deploy from GitHub
# - Selecciona el repo
# - Agrega variable: TELEGRAM_BOT_TOKEN

# 3. ¡Listo!
```

### Opción 2: Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
python3 servidor_landing.py

# En otra terminal, iniciar bot
export TELEGRAM_BOT_TOKEN="tu_token_aqui"
python3 bot_telegram.py
```

## 🤖 Configurar Bot de Telegram

1. Habla con @BotFather en Telegram
2. Envía `/newbot`
3. Sigue las instrucciones
4. Copia el token
5. Agrégalo como variable de entorno `TELEGRAM_BOT_TOKEN`

## 📝 Uso

### Desde el Panel Admin:
```
http://tu-url.railway.app/admin
```
Llena el formulario y guarda.

### Desde Telegram:
Envía al bot:
```
15% desc SUPER15 min 500 max 150 vence 20/08 dorado destacado
```

## 📂 Estructura

```
landing/
├── servidor_landing.py    # Servidor web
├── bot_telegram.py        # Bot de Telegram
├── index.html            # Template principal
├── admin.html            # Panel admin
├── cupones.json          # Base de datos
├── requirements.txt      # Dependencias
├── Procfile             # Config para Railway/Heroku
└── DEPLOY_GUIDE.md      # Guía completa de deploy
```

## 🌐 URLs

- **Landing pública:** `/`
- **Panel Admin:** `/admin`
- **API cupones:** `/api/cupones`

## 📱 Workflow Diario

1. Recibes cupón por WhatsApp
2. Lo reenvías al bot de Telegram
3. Bot lo procesa y guarda
4. Cupón aparece en la landing automáticamente

**Tiempo: 5-10 segundos**

## 🔧 Variables de Entorno

```bash
PORT=8080                          # Puerto (Railway lo asigna auto)
TELEGRAM_BOT_TOKEN=123456:ABC...  # Token del bot
USUARIOS_AUTORIZADOS=123456789    # IDs de Telegram autorizados (opcional)
```

## 📄 Licencia

Uso privado - Superseller

## 🆘 Soporte

Lee `DEPLOY_GUIDE.md` para guía completa de deploy y troubleshooting.
