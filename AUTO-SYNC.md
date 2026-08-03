# 🔄 Auto-Sync a GitHub

## ✅ Configuración completada

Tu proyecto ahora sube cambios a GitHub **automáticamente cada 60 minutos**.

---

## 🚀 Cómo usar:

### Iniciar (una sola vez al día)
```bash
cd ~/Desktop/SUPERSELLER
./start.sh
```

**Qué hace:**
- ✅ Inicia el servidor en http://localhost:8765
- ✅ Activa auto-sync (cada 60 minutos)
- ✅ Todo corre en background

### Trabajar normal
- Editas código
- Haces cambios
- Pruebas features
- **NO haces nada con git** 👍

### Detener (al terminar el día)
```bash
./stop.sh
```

**Qué hace:**
- ✅ Detiene el servidor
- ✅ Detiene auto-sync
- ✅ Todo limpio

---

## 🔄 ¿Cómo funciona el auto-sync?

**Cada 60 minutos:**
1. Revisa si hay cambios
2. Si hay cambios → sube a GitHub automáticamente
3. Si no hay cambios → espera otros 60 minutos

**No importa cómo detengas el servidor:**
- Ctrl+C ✅ (ya está respaldado cada hora)
- ./stop.sh ✅ (ya está respaldado cada hora)
- Se cae la compu ✅ (perdiste máximo 1 hora de trabajo)

---

## 📋 Ver qué está pasando:

### Logs del servidor:
```bash
tail -f ~/Desktop/SUPERSELLER/servidor.log
```

### Logs del auto-sync:
```bash
tail -f ~/Desktop/SUPERSELLER/auto-sync.log
```

Aquí ves:
- Cuándo se subió a GitHub
- Si hubo cambios o no
- Si hubo algún error

---

## 🎯 Ejemplo de un día normal:

```
09:00 → ./start.sh
        (Servidor + Auto-sync iniciados)

10:00 → 🔄 Auto-sync: Subido a GitHub
11:00 → ⏭️  Sin cambios
12:00 → 🔄 Auto-sync: Subido a GitHub
13:00 → ⏭️  Sin cambios
...

18:00 → ./stop.sh
        (Todo detenido, última versión en GitHub)
```

---

## ❓ Preguntas frecuentes:

**P: ¿Tengo que hacer git add/commit/push?**
R: NO. El auto-sync lo hace todo automáticamente.

**P: ¿Puedo seguir usando Ctrl+C?**
R: SÍ. Los cambios ya están en GitHub (se suben cada hora).

**P: ¿Cómo sé si se subió a GitHub?**
R: Revisa `tail -f auto-sync.log` o ve a GitHub.com

**P: ¿Puedo cambiar los 60 minutos?**
R: SÍ. Edita `auto-sync.sh` y cambia `INTERVAL=3600` (en segundos).

**P: ¿Se puede desactivar?**
R: SÍ. Comenta la línea del auto-sync en `start.sh`.

---

## ✅ Ventajas:

1. **Cero esfuerzo** - No piensas en git nunca más
2. **Siempre respaldado** - Máximo pierdes 1 hora de trabajo
3. **Funciona siempre** - No importa cómo cierres el servidor
4. **GitHub actualizado** - Siempre tienes la última versión
