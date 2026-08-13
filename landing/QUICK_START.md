# 🚀 Quick Start - Landing de Cupones

## ⚡ Inicio Rápido (3 pasos)

### 1️⃣ Iniciar servidor
```bash
cd ~/Desktop/SUPERSELLER/landing
./iniciar.sh
```

O manualmente:
```bash
python3 servidor_landing.py
```

### 2️⃣ Abrir navegador
```
http://localhost:8080
```

### 3️⃣ Editar cupones
Abre `cupones.json` en tu editor favorito y modifica los cupones.

---

## 📝 Edición diaria de cupones

### Agregar un cupón nuevo

Copia esto en el array `"cupones"` dentro de `cupones.json`:

```json
{
  "id": "cup004",
  "titulo": "$500 de descuento",
  "codigo": "AHORRA500",
  "tipo": "monto",
  "descuento": 500,
  "compra_minima": 2000,
  "descuento_maximo": 500,
  "plataforma": "Mercado Libre",
  "logo_url": "https://http2.mlstatic.com/frontend-assets/ml-web-navigation/ui-navigation/5.21.22/mercadolibre/logo__large_plus.png",
  "vencimiento": "2026-08-20",
  "destacado": false,
  "color_fondo": "blue",
  "activo": true
}
```

### Desactivar cupón vencido

Cambia:
```json
"activo": true
```
Por:
```json
"activo": false
```

### Marcar como destacado (⭐ Cupón TOP)

Cambia:
```json
"destacado": false
```
Por:
```json
"destacado": true
```

---

## 🎨 Colores disponibles

Cambiar `"color_fondo"` a:

- `"gold"` → 🟡 Dorado (recomendado para TOP)
- `"blue"` → 🔵 Azul/Morado
- `"purple"` → 🟣 Rosa/Morado claro  
- `"green"` → 🟢 Verde azulado
- `"red"` → 🔴 Rojo

---

## ✅ Checklist diario

- [ ] Abrir `cupones.json`
- [ ] Actualizar fechas de vencimiento
- [ ] Desactivar cupones vencidos (`"activo": false`)
- [ ] Agregar nuevos cupones del día
- [ ] Marcar el mejor cupón como destacado
- [ ] Guardar archivo
- [ ] Recargar navegador (F5)
- [ ] ✨ ¡Listo!

---

## 🔗 Redes sociales

Actualiza los links en `cupones.json` → `"configuracion"` → `"redes_sociales"`:

```json
"redes_sociales": {
  "whatsapp": "https://wa.me/521234567890",
  "telegram": "https://t.me/tuperfil",
  "facebook": "https://facebook.com/tupagina",
  "youtube": "https://youtube.com/@tucanal"
}
```

---

## 💡 Tips

✅ **Siempre válida el JSON** antes de guardar (usa un validador online)  
✅ **Mantén IDs únicos** (cup001, cup002, cup003...)  
✅ **Fechas formato YYYY-MM-DD** (2026-08-13)  
✅ **Un solo cupón destacado** a la vez para mayor impacto  
✅ **Códigos cortos** se ven mejor (max 12 caracteres)  

❌ **No edites** `index.html` ni `servidor_landing.py` (a menos que sepas lo que haces)  
❌ **No borres cupones**, mejor marca como `"activo": false`  

---

## 🆘 Ayuda rápida

**¿El servidor no arranca?**
```bash
# Ver si el puerto está ocupado
lsof -i :8080

# Cambiar puerto (edita servidor_landing.py, línea 10)
PORT = 8081
```

**¿Los cupones no aparecen?**
- Verifica que el JSON sea válido
- Revisa que `"activo": true`
- Verifica que la fecha no esté vencida

**¿Error al copiar cupón?**
- Solo funciona en localhost o HTTPS
- Requiere navegador moderno

---

## 📞 Soporte

Lee el `README.md` completo para más detalles.

---

**¡Actualiza cupones en segundos, no en horas! 🚀**
