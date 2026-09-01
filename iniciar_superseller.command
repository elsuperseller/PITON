#!/bin/bash

# Abrir una nueva ventana de Terminal que ejecute start.sh y se quede abierta
osascript -e 'tell application "Terminal"
    do script "cd ~/Desktop/SUPERSELLER && ./start.sh && exec $SHELL"
    activate
end tell'
