# Cambio de Google Drive a Desktop

## 🎯 Objetivo
Dejar de correr Superseller desde Google Drive y usar la versión local en Desktop.

## 📋 Pasos para hacer el cambio:

### 1. Detener servidor viejo (Google Drive)
```bash
# Encontrar el proceso
lsof -ti:8765

# Detenerlo (reemplaza XXXXX con el PID del comando anterior)
kill XXXXX
```

**O más directo:**
```bash
kill $(lsof -ti:8765)
```

### 2. Iniciar servidor nuevo (Desktop)
```bash
cd ~/Desktop/superceller
./start.sh
```

### 3. Verificar que funciona
Abre en Chrome: http://localhost:8765

### 4. Verificar que puedes hacer cambios y pushear a GitHub
```bash
cd ~/Desktop/superceller

# Hacer algún cambio de prueba
echo "# Test" >> test.txt

# Ver cambios
git status

# Agregar, commit y push
git add test.txt
git commit -m "Test desde Desktop"
git push origin main

# Limpiar
rm test.txt
git add test.txt
git commit -m "Remove test file"
git push origin main
```

## 🔄 Comandos útiles

**Iniciar servidor:**
```bash
cd ~/Desktop/superceller && ./start.sh
```

**Detener servidor:**
```bash
cd ~/Desktop/superceller && ./stop.sh
```

**Ver logs:**
```bash
tail -f ~/Desktop/superceller/servidor.log
```

**Ver qué está usando el puerto 8765:**
```bash
lsof -i:8765
```

## 📝 Notas importantes

- ✅ Google Drive ahora es SOLO respaldo
- ✅ Desktop es tu versión de desarrollo
- ✅ GitHub es la fuente de verdad
- ⚠️ Recuerda hacer `git push` después de cambios importantes
- 💡 Los archivos .gitignore (como historial.json) NO están en el repo, solo local
