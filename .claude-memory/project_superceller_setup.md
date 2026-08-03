---
name: project-superceller-setup
description: "Ubicación y configuración del proyecto Superceller Creator App en Desktop con GitHub"
type: project
originSessionId: 3c427a7a-6e2e-47b6-825f-95f257333752
---

El proyecto **Superceller Creator App** ahora corre desde una ubicación local:
`/Users/isaac/Desktop/SUPERSELLER`

**Why:** Es una aplicación Python para scraping y gestión de productos (Amazon, MercadoLibre), manejo de keywords, historial de variedad. Se movió de Google Drive a Desktop para evitar problemas de ETIMEDOUT y sincronización. El servidor principal está en `servidor.py`.

**Repositorio GitHub:** https://github.com/elsuperseller/PITON

**How to apply:** Para continuar trabajando en este proyecto:
```bash
cd ~/Desktop/SUPERSELLER
claude
```

**Scripts de control:**
- Iniciar servidor: `./start.sh` (corre en background, puerto 8765)
- Detener servidor: `./stop.sh`
- Ver logs: `tail -f ~/Desktop/SUPERSELLER/servidor.log`

**Flujo de trabajo con GitHub:**
1. Trabajar en `~/Desktop/SUPERSELLER` (desarrollo local)
2. Hacer commits frecuentes
3. Push a GitHub: `git push origin main`
4. Google Drive es SOLO respaldo (no correr servidor desde ahí)

**Nota:** La versión original en Google Drive (`Mi unidad/BBQ/PITON/CREATOR APP`) se mantiene como respaldo pero NO debe usarse para desarrollo.
