#!/bin/bash

# Script para iniciar Superseller desde Desktop
cd "$(dirname "$0")"

# Verificar si ya está corriendo
if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Superseller ya está corriendo en el puerto 8765"
    echo "   Para detenerlo: ./stop.sh"
    exit 1
fi

echo "🚀 Iniciando Superseller..."
echo "   📁 Ubicación: ~/Desktop/SUPERSELLER"
echo "   🌐 URL: http://localhost:8765"
echo ""

# Iniciar servidor en background
nohup python3 servidor.py > servidor.log 2>&1 &
PID=$!

# Esperar un momento para verificar que inició
sleep 2

# Verificar que el proceso sigue corriendo
if ps -p $PID > /dev/null 2>&1; then
    echo "✅ Superseller iniciado correctamente (PID: $PID)"
    echo "   👉 Abre: http://localhost:8765"
    echo "   📋 Logs: tail -f ~/Desktop/SUPERSELLER/servidor.log"
    echo "   🛑 Detener: ./stop.sh"
else
    echo "❌ Error al iniciar Superseller"
    echo "   Revisa: cat ~/Desktop/SUPERSELLER/servidor.log"
    exit 1
fi
