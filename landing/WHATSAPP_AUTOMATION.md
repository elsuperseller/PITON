# 📱 Automatización de Cupones vía WhatsApp

## 🎯 Objetivo
Recibir cupones por WhatsApp y que se agreguen automáticamente a la landing sin necesidad de llenar el formulario manualmente.

---

## 🔧 Soluciones posibles

### ✅ **OPCIÓN 1: WhatsApp Business API + Webhook (RECOMENDADA)**

#### Cómo funciona:
1. Te llega un mensaje a WhatsApp con el cupón
2. Lo reenvías a un número/chatbot configurado
3. El sistema lee el mensaje, extrae la info del cupón
4. Lo agrega automáticamente a `cupones.json`
5. El cupón aparece en la landing al instante

#### Qué necesitas:
- **WhatsApp Business API** (gratuita para volumen bajo)
- **Webhook en tu servidor** que reciba los mensajes
- **Parser de texto** que extraiga: código, descuento, compra mínima, etc.

#### Formato del mensaje que enviarías:
```
CUPÓN REGULAR
15% de descuento
Código: SUPER15
Compra mínima: $500
Descuento max: $150
Vence: 2026-08-20
Color: gold
Destacado: si
```

O simplemente reenviar el mensaje tal cual lo recibes y el sistema lo interpreta.

---

### ✅ **OPCIÓN 2: Telegram Bot (MÁS FÁCIL)**

#### Cómo funciona:
1. Creas un bot de Telegram
2. Le reenvías (o escribes) el cupón al bot
3. El bot lo parsea y actualiza `cupones.json`
4. Listo

#### Ventajas:
- ✅ **Más fácil de configurar** que WhatsApp API
- ✅ **API gratis** y sin límites
- ✅ **Telegram tiene mejor API** para bots
- ✅ **Puedes reenviar mensajes de WhatsApp a Telegram**

#### Workflow:
```
WhatsApp → Recibes cupón
  ↓
Telegram → Lo reenvías al bot
  ↓
Servidor → Bot actualiza cupones.json
  ↓
Landing → Cupón visible al instante
```

---

### ✅ **OPCIÓN 3: Email → Cupones (INTERMEDIA)**

#### Cómo funciona:
1. Configuras un email específico (cupones@superseller.com)
2. Reenvías el WhatsApp como email
3. Un script lee el email y extrae el cupón
4. Actualiza la landing

---

### ✅ **OPCIÓN 4: Formulario web ultra-rápido (YA EXISTE)**

Ya tienes el panel admin en:
```
http://localhost:8080/admin
```

Puedes:
1. Copiar el texto del WhatsApp
2. Pegarlo en un campo del formulario
3. El sistema lo parsea automáticamente
4. Solo das click en "Guardar"

**Tiempo: 10 segundos**

---

## 🚀 Mi recomendación: **TELEGRAM BOT**

### Por qué Telegram Bot es la mejor opción:

1. **Fácil de configurar** (15 minutos)
2. **API gratuita** (sin límites)
3. **Puedes usarlo desde el celular**
4. **Solo reenvías el mensaje** y ya
5. **No necesitas WhatsApp Business API** (que es más complejo)

### Cómo funcionaría:

```
📱 WhatsApp
Te llega: "15% descuento código SUPER15 compra mín $500 max $150 vence 20/08"

📲 Telegram
Reenvías al bot: @SupersellerCuponesBot

🤖 Bot te responde:
"✅ Cupón agregado:
- Título: 15% de descuento
- Código: SUPER15
- Compra mín: $500
- Descuento max: $150
- Vence: 2026-08-20"

🌐 Landing
El cupón ya está visible en http://localhost:8080
```

---

## 📋 Implementación Telegram Bot

Te crearía:

1. **Bot de Telegram** (@SupersellerCuponesBot)
2. **Script Python** que escucha mensajes
3. **Parser inteligente** que entiende diferentes formatos
4. **Comandos**:
   - `/agregar` - Agregar cupón desde texto
   - `/listar` - Ver cupones actuales
   - `/eliminar [código]` - Eliminar cupón
   - `/activar [código]` - Activar/desactivar

### Ejemplo de uso:

```
Tú → Bot:
/agregar
15% de descuento
SUPER15
Regular
Compra mín: 500
Max: 150
Vence: 20/08/2026
Dorado
Destacado

Bot → Tú:
✅ Cupón creado exitosamente!
🔗 Ver en: http://localhost:8080
```

O más simple:

```
Tú → Bot:
15% desc SUPER15 min $500 max $150 vence 20/08 gold

Bot → Tú:
✅ Cupón agregado!
```

---

## 🛠️ ¿Quieres que te implemente el bot de Telegram?

Puedo crearte:
- ✅ El bot completo
- ✅ Parser inteligente de texto
- ✅ Comandos fáciles
- ✅ Actualización automática de cupones.json
- ✅ Notificaciones cuando se agrega un cupón

**Tiempo de implementación: 30-45 minutos**

---

## 💡 O también puedo...

### Opción híbrida:
1. **Panel Admin mejorado** con campo de "pegado rápido"
2. Pegas el texto del WhatsApp
3. El sistema lo parsea automáticamente
4. Solo confirmas y guardas

**Esto lo puedo hacer en 10 minutos**

---

## ❓ ¿Qué prefieres?

1. **Telegram Bot** (automatización total)
2. **Panel Admin con parser** (rápido de implementar)
3. **WhatsApp Business API** (más complejo)
4. **Email automation** (intermedio)

Dime cuál te interesa más y lo implemento ahora mismo.
