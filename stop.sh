#!/bin/bash

# Script para detener Superseller
cd "$(dirname "$0")"

echo "🛑 Deteniendo Superseller..."

# Detener servidor
PID=$(lsof -ti:8765 2>/dev/null)

if [ -n "$PID" ]; then
    kill $PID 2>/dev/null
    sleep 1

    if ps -p $PID > /dev/null 2>&1; then
        kill -9 $PID 2>/dev/null
        sleep 1
    fi

    if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "❌ No se pudo detener el servidor"
    else
        echo "✅ Servidor detenido"
    fi
else
    echo "⚠️  Servidor no estaba corriendo"
fi

# Detener auto-sync
if [ -f .sync.pid ]; then
    SYNC_PID=$(cat .sync.pid)
    if ps -p $SYNC_PID > /dev/null 2>&1; then
        kill $SYNC_PID 2>/dev/null
        echo "✅ Auto-sync detenido"
    fi
    rm .sync.pid
fi

# Limpiar archivo de PID del servidor
if [ -f .server.pid ]; then
    rm .server.pid
fi

echo "✅ Todo detenido correctamente"
