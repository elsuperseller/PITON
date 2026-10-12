# 🔐 Login Mercado Libre - Guía de Uso

## ¿Por qué es necesario?

Mercado Libre bloquea navegadores automatizados sin sesión. Al usar tu sesión real de usuario:
- ✅ ML te reconoce como usuario legítimo
- ✅ Sin bloqueos de IP
- ✅ Sin CAPTCHAs
- ✅ Acceso completo a ofertas

---

## 📋 Paso 1: Login único (solo UNA vez)

Ejecuta:

```bash
cd ~/Desktop/SUPERSELLER
python3 ml_login.py
```

**¿Qué va a pasar?**

1. Se abrirá Chrome en modo visible
2. Irá a mercadolibre.com.mx
3. **TÚ te logueas** con tu usuario/contraseña
4. Regresas a la terminal y presionas ENTER
5. ✅ Sesión guardada

**Tiempo estimado:** 30 segundos

---

## 🚀 Paso 2: Usar la automatización

Después del login, TODO funciona automático:

```bash
./start.sh  # Inicia el servidor normalmente
```

Ahora cuando busques ofertas de Mercado Libre:
- El scraper usará TU sesión guardada
- ML verá navegador legítimo con historial
- Sin bloqueos

---

## ❓ Preguntas frecuentes

### ¿Necesito repetir el login?

**NO.** Solo una vez. La sesión se guarda en:
```
~/Desktop/SUPERSELLER/.ml_browser_profile/
```

### ¿Y si cierro sesión en ML desde mi navegador normal?

El scraper seguirá usando su propia sesión (guardada en el perfil dedicado).
Son sesiones independientes.

### ¿Y si ML me pide login de nuevo al scraper?

Ejecuta `ml_login.py` otra vez para refrescar la sesión.

### ¿Puedo usar diferentes cuentas de ML?

Sí. Puedes crear múltiples perfiles:

```python
# En scraper_ml.py cambiar:
ML_BROWSER_PROFILE = '~/.ml_profile_cuenta1'
ML_BROWSER_PROFILE = '~/.ml_profile_cuenta2'
```

---

## 🔧 Troubleshooting

### Error: "Playwright no disponible"

```bash
pip install playwright
playwright install chrome
```

### Error: "Browser closed"

Asegúrate de que Chrome normal NO esté usando el mismo perfil.
El perfil dedicado (`. ml_browser_profile`) es solo para el scraper.

### Sigue sin funcionar

1. Borra el perfil: `rm -rf ~/Desktop/SUPERSELLER/.ml_browser_profile`
2. Ejecuta `ml_login.py` de nuevo
3. Asegúrate de loguearte completamente antes de presionar ENTER

---

## ✅ Resultado esperado

Después del login, cuando ejecutes búsquedas de ML:

```
🎭 Playwright ML p1: https://www.mercadolibre.com.mx/ofertas
📋 Título: 'Ofertas del día en Mercado Libre México'
📡 Respuestas >5KB capturadas: 5
  2847392 bytes ✅initialState 🃏polycards   https://...
✅ Playwright listado → 48 productos total
```

**Sin "suspicious-traffic" = ✅ Funcionando**

