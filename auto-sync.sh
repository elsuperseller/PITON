#!/bin/bash

# Auto-sync: Sube cambios a GitHub cada 60 minutos automáticamente
cd "$(dirname "$0")"

INTERVAL=3600  # 60 minutos en segundos

echo "🔄 Auto-sync iniciado (cada 60 minutos)"
echo "   Revisa: tail -f ~/Desktop/SUPERSELLER/auto-sync.log"

while true; do
    sleep $INTERVAL

    # Verificar si hay cambios
    if [[ -n $(git status --porcelain) ]]; then
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$TIMESTAMP] 🔄 Detectados cambios, subiendo a GitHub..." >> auto-sync.log

        git add -A
        git commit -m "Auto-sync: $TIMESTAMP" >> auto-sync.log 2>&1
        git push origin main >> auto-sync.log 2>&1

        if [ $? -eq 0 ]; then
            echo "[$TIMESTAMP] ✅ Sincronizado exitosamente" >> auto-sync.log
        else
            echo "[$TIMESTAMP] ❌ Error al sincronizar" >> auto-sync.log
        fi
    else
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$TIMESTAMP] ⏭️  Sin cambios, nada que subir" >> auto-sync.log
    fi
done
