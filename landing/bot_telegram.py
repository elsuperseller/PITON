#!/usr/bin/env python3
"""
Bot de Telegram - Superseller Cupones
Permite agregar cupones enviando mensajes al bot
"""

import os
import json
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Token del bot (lo configuraremos después)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "TU_TOKEN_AQUI")

# Archivo de cupones
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CUPONES_FILE = os.path.join(BASE_DIR, "cupones.json")

# IDs de usuarios autorizados (por seguridad)
USUARIOS_AUTORIZADOS = []  # Se llena desde variable de entorno


def cargar_cupones():
    """Carga cupones desde el archivo JSON"""
    try:
        with open(CUPONES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"cupones": [], "configuracion": {}}


def guardar_cupones(data):
    """Guarda cupones en el archivo JSON"""
    with open(CUPONES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generar_id():
    """Genera ID único para cupón"""
    data = cargar_cupones()
    cupones = data.get("cupones", [])

    if not cupones:
        return "cup001"

    # Obtener el último ID
    ids = [int(c["id"].replace("cup", "")) for c in cupones if c["id"].startswith("cup")]
    nuevo_id = max(ids) + 1 if ids else 1

    return f"cup{str(nuevo_id).zfill(3)}"


def parsear_mensaje(texto):
    """
    Parsea un mensaje de texto y extrae datos del cupón

    Formatos soportados:
    1. "15% desc SUPER15 min $500 max $150 vence 20/08"
    2. "15% de descuento / SUPER15 / min 500 / max 150 / 20-08-2026"
    3. Formato libre que contenga los datos clave
    """

    cupon = {
        "titulo": "",
        "codigo": "",
        "categoria": "regular",
        "tipo": "porcentaje",
        "descuento": 0,
        "compra_minima": 0,
        "descuento_maximo": 0,
        "vencimiento": "",
        "color_fondo": "blue",
        "destacado": False
    }

    texto_lower = texto.lower()

    # Detectar categoría
    if "bancario" in texto_lower or "banco" in texto_lower or "tarjeta" in texto_lower:
        cupon["categoria"] = "bancario"

    # Detectar si es destacado
    if "destacado" in texto_lower or "top" in texto_lower or "⭐" in texto:
        cupon["destacado"] = True

    # Extraer código (texto en mayúsculas sin espacios)
    codigos = re.findall(r'\b[A-Z]{4,}[0-9]*\b', texto)
    if codigos:
        cupon["codigo"] = codigos[0]

    # Extraer porcentaje de descuento
    porcentajes = re.findall(r'(\d+)\s*%', texto)
    if porcentajes:
        cupon["descuento"] = int(porcentajes[0])
        cupon["tipo"] = "porcentaje"
        cupon["titulo"] = f"{porcentajes[0]}% de descuento"

    # Extraer monto de descuento (si no hay porcentaje)
    if not porcentajes:
        montos = re.findall(r'\$\s*(\d+(?:,\d{3})*)', texto)
        if montos:
            monto = int(montos[0].replace(',', ''))
            cupon["descuento"] = monto
            cupon["tipo"] = "monto"
            cupon["titulo"] = f"${monto:,} de descuento"

    # Extraer compra mínima
    min_patterns = [
        r'min[ií]m[ao]\s*:?\s*\$?\s*(\d+(?:,\d{3})*)',
        r'compra\s+m[ií]n[ií]m[ao]\s*:?\s*\$?\s*(\d+(?:,\d{3})*)',
        r'min\s*\$?\s*(\d+(?:,\d{3})*)'
    ]
    for pattern in min_patterns:
        matches = re.findall(pattern, texto_lower)
        if matches:
            cupon["compra_minima"] = int(matches[0].replace(',', ''))
            break

    # Extraer descuento máximo
    max_patterns = [
        r'max[ií]m[ao]\s*:?\s*\$?\s*(\d+(?:,\d{3})*)',
        r'descuento\s+m[aá]x[ií]m[ao]\s*:?\s*\$?\s*(\d+(?:,\d{3})*)',
        r'max\s*\$?\s*(\d+(?:,\d{3})*)',
        r'tope\s*:?\s*\$?\s*(\d+(?:,\d{3})*)'
    ]
    for pattern in max_patterns:
        matches = re.findall(pattern, texto_lower)
        if matches:
            cupon["descuento_maximo"] = int(matches[0].replace(',', ''))
            break

    # Extraer fecha de vencimiento
    fecha_patterns = [
        r'venc[ei]\s*:?\s*(\d{1,2})[/-](\d{1,2})[/-]?(\d{2,4})?',
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
        r'hasta\s+(\d{1,2})[/-](\d{1,2})[/-]?(\d{2,4})?'
    ]
    for pattern in fecha_patterns:
        matches = re.findall(pattern, texto)
        if matches:
            dia, mes, año = matches[0]
            dia = int(dia)
            mes = int(mes)
            año = int(año) if año else datetime.now().year

            # Corregir año de 2 dígitos
            if año < 100:
                año = 2000 + año

            try:
                fecha = datetime(año, mes, dia)
                cupon["vencimiento"] = fecha.strftime("%Y-%m-%d")
            except:
                # Si falla, usar fecha de hoy + 7 días
                cupon["vencimiento"] = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            break

    # Si no se encontró fecha, usar hoy + 7 días
    if not cupon["vencimiento"]:
        cupon["vencimiento"] = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    # Detectar color
    colores_map = {
        "dorado": "gold",
        "gold": "gold",
        "oro": "gold",
        "azul": "blue",
        "blue": "blue",
        "morado": "purple",
        "purple": "purple",
        "rosa": "purple",
        "verde": "green",
        "green": "green",
        "rojo": "red",
        "red": "red"
    }
    for palabra, color in colores_map.items():
        if palabra in texto_lower:
            cupon["color_fondo"] = color
            break

    # Color por defecto según categoría
    if cupon["categoria"] == "bancario" and cupon["color_fondo"] == "blue":
        cupon["color_fondo"] = "green"

    return cupon


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    mensaje = """
🎯 *Bot de Cupones Superseller*

Envíame un mensaje con los datos del cupón y yo lo agregaré automáticamente.

*Formatos aceptados:*

📝 *Formato simple:*
`15% desc SUPER15 min $500 max $150 vence 20/08`

📝 *Formato detallado:*
```
15% de descuento
Código: SUPER15
Regular/Bancario
Compra mínima: $500
Descuento máximo: $150
Vence: 20/08/2026
Color: dorado
Destacado
```

*Comandos disponibles:*
/start - Este mensaje
/listar - Ver cupones activos
/ayuda - Ejemplos de uso

Simplemente envía el mensaje y yo haré el resto ✨
"""
    await update.message.reply_text(mensaje, parse_mode='Markdown')


async def listar_cupones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /listar - muestra cupones activos"""
    data = cargar_cupones()
    cupones = data.get("cupones", [])

    if not cupones:
        await update.message.reply_text("📭 No hay cupones registrados todavía.")
        return

    # Filtrar activos
    activos = [c for c in cupones if c.get("activo", True)]

    if not activos:
        await update.message.reply_text("📭 No hay cupones activos.")
        return

    mensaje = "📋 *Cupones activos:*\n\n"

    for cupon in activos:
        emoji = "⭐" if cupon.get("destacado") else ("🏦" if cupon.get("categoria") == "bancario" else "📦")
        mensaje += f"{emoji} *{cupon['titulo']}*\n"
        mensaje += f"   Código: `{cupon['codigo']}`\n"
        mensaje += f"   Min: ${cupon['compra_minima']:,} | Max: ${cupon['descuento_maximo']:,}\n"
        mensaje += f"   Vence: {cupon['vencimiento']}\n\n"

    await update.message.reply_text(mensaje, parse_mode='Markdown')


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ayuda"""
    mensaje = """
📚 *Ejemplos de uso:*

*Ejemplo 1 - Súper simple:*
`15% SUPER15 min 500 max 150 vence 20/08`

*Ejemplo 2 - Con formato:*
```
20% de descuento
MEGA20
Bancario
Min: $1000
Max: $200
Vence: 25/08/2026
Dorado
Destacado
```

*Ejemplo 3 - Cupón de monto fijo:*
`$500 descuento AHORRA500 min $2000 max $500 vence 30/08`

*Palabras clave:*
• *Categoría:* "bancario" o "regular"
• *Destacado:* "destacado" o "top"
• *Color:* dorado, azul, morado, verde, rojo
• *Mínimo:* "min", "mínimo", "compra mínima"
• *Máximo:* "max", "máximo", "tope"
• *Fecha:* "vence", "hasta"

¡El bot es inteligente! 🤖 Entiende muchas variaciones.
"""
    await update.message.reply_text(mensaje, parse_mode='Markdown')


async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa mensajes de texto y crea cupones"""

    # Verificar usuario autorizado (opcional, comentado por ahora)
    # if USUARIOS_AUTORIZADOS and update.effective_user.id not in USUARIOS_AUTORIZADOS:
    #     await update.message.reply_text("⛔ No tienes permiso para usar este bot.")
    #     return

    texto = update.message.text

    # Parsear mensaje
    try:
        cupon_data = parsear_mensaje(texto)

        # Validar datos mínimos
        if not cupon_data["codigo"]:
            await update.message.reply_text(
                "❌ No pude encontrar el código del cupón.\n"
                "Asegúrate de incluir un código en MAYÚSCULAS (ej: SUPER15)"
            )
            return

        if cupon_data["descuento"] == 0:
            await update.message.reply_text(
                "❌ No pude encontrar el descuento.\n"
                "Incluye algo como '15%' o '$500'"
            )
            return

        # Cargar cupones existentes
        data = cargar_cupones()

        # Agregar datos adicionales
        cupon_completo = {
            "id": generar_id(),
            "titulo": cupon_data["titulo"],
            "codigo": cupon_data["codigo"],
            "categoria": cupon_data["categoria"],
            "tipo": cupon_data["tipo"],
            "descuento": cupon_data["descuento"],
            "compra_minima": cupon_data["compra_minima"],
            "descuento_maximo": cupon_data["descuento_maximo"],
            "plataforma": "Mercado Libre",
            "logo_url": "https://http2.mlstatic.com/frontend-assets/ml-web-navigation/ui-navigation/5.21.22/mercadolibre/logo__large_plus.png",
            "vencimiento": cupon_data["vencimiento"],
            "destacado": cupon_data["destacado"],
            "color_fondo": cupon_data["color_fondo"],
            "activo": True
        }

        # Agregar cupón
        data["cupones"].append(cupon_completo)

        # Guardar
        guardar_cupones(data)

        # Confirmar
        emoji_cat = "🏦" if cupon_data["categoria"] == "bancario" else "📦"
        emoji_dest = "⭐ " if cupon_data["destacado"] else ""

        respuesta = f"""
✅ *Cupón agregado exitosamente!*

{emoji_dest}{emoji_cat} *{cupon_completo['titulo']}*
Código: `{cupon_completo['codigo']}`
Categoría: {cupon_completo['categoria'].title()}
Compra mínima: ${cupon_completo['compra_minima']:,}
Descuento máximo: ${cupon_completo['descuento_maximo']:,}
Vence: {cupon_completo['vencimiento']}
Color: {cupon_completo['color_fondo']}

🌐 Ya está visible en la landing!
"""

        await update.message.reply_text(respuesta, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error al procesar el cupón:\n{str(e)}\n\n"
            "Envía /ayuda para ver ejemplos de formato."
        )


def main():
    """Inicia el bot"""
    if BOT_TOKEN == "TU_TOKEN_AQUI":
        print("❌ Error: Configura el token del bot en la variable de entorno TELEGRAM_BOT_TOKEN")
        return

    # Crear aplicación
    application = Application.builder().token(BOT_TOKEN).build()

    # Registrar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("listar", listar_cupones))
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))

    # Iniciar bot
    print("🤖 Bot de Telegram iniciado...")
    print(f"📂 Archivo de cupones: {CUPONES_FILE}")
    application.run_polling()


if __name__ == "__main__":
    main()
