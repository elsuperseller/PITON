---
name: project-superceller-setup
description: "Ubicación y configuración del proyecto Superceller Creator App"
type: project
originSessionId: 3c427a7a-6e2e-47b6-825f-95f257333752
---
El proyecto **Superceller Creator App** está ubicado en:
`/Users/isaac/Library/CloudStorage/GoogleDrive-isaac@elsuperseller.com/Mi unidad/BBQ/PITON/CREATOR APP`

**Why:** Es una aplicación Python para scraping y gestión de productos (Amazon, MercadoLibre), manejo de keywords, historial de variedad. El servidor principal está en `servidor.py` y tiene un script de inicio `iniciar_superseller.command`.

**How to apply:** Para continuar trabajando en este proyecto después de reiniciar:
```bash
cd "/Users/isaac/Library/CloudStorage/GoogleDrive-isaac@elsuperseller.com/Mi unidad/BBQ/PITON/CREATOR APP"
claude
```

**ADVERTENCIA:** Este proyecto actualmente corre desde Google Drive. Según experiencia previa con el proyecto mercadoads, correr servidores de desarrollo desde carpetas sincronizadas con Drive puede causar errores ETIMEDOUT porque Drive transmite archivos bajo demanda en lugar de mantenerlos completamente locales. Si experimentas problemas de estabilidad, considera clonar a una ubicación local (ej. `~/Desktop/superceller` o `~/dev/superceller`).
