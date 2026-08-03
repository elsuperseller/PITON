#!/bin/bash

# Script para detener Superseller
cd "$(dirname "$0")"

echo "🛑 Deteniendo Superseller..."

# Buscar proceso en puerto 8765
PID=$(lsof -ti:8765 2>/dev/null)

if [ -z "$PID" ]; then
    echo "⚠️  Superseller no está corriendo"
    exit 0
fi

# Detener proceso
kill $PID 2>/dev/null

# Esperar a que termine
sleep 1

# Verificar que se detuvo
if ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  El proceso no se detuvo, forzando..."
    kill -9 $PID 2>/dev/null
    sleep 1
fi

if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "❌ No se pudo detener el servidor"
    exit 1
else
    echo "✅ Superseller detenido correctamente"
fi
