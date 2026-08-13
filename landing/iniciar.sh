#!/bin/bash
# Script para iniciar la landing de cupones Superseller

cd "$(dirname "$0")"

echo "🚀 Iniciando Landing de Cupones - Superseller"
echo ""

# Verificar que existen los archivos necesarios
if [ ! -f "cupones.json" ]; then
    echo "❌ Error: No se encuentra cupones.json"
    exit 1
fi

if [ ! -f "index.html" ]; then
    echo "❌ Error: No se encuentra index.html"
    exit 1
fi

if [ ! -f "servidor_landing.py" ]; then
    echo "❌ Error: No se encuentra servidor_landing.py"
    exit 1
fi

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado"
    exit 1
fi

echo "✅ Todos los archivos encontrados"
echo ""
echo "📂 Directorio: $(pwd)"
echo "🌐 Abriendo en http://localhost:8080"
echo ""
echo "⏹️  Presiona Ctrl+C para detener el servidor"
echo ""

# Abrir navegador automáticamente después de 2 segundos
(sleep 2 && open http://localhost:8080) &

# Iniciar servidor
python3 servidor_landing.py
