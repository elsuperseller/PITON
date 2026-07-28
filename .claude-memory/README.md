# Claude Code Memory Backup

Este directorio contiene un respaldo de la memoria de Claude Code para el proyecto **Superceller Creator App**.

## ¿Qué es esto?

Claude Code guarda memoria sobre los proyectos en `~/.claude/projects/` para mantener contexto entre conversaciones. Este directorio `.claude-memory/` es un respaldo versionado en Git de esa memoria, específicamente para este proyecto.

## Archivos

- `MEMORY.md` - Índice de todos los archivos de memoria
- `project_superceller_setup.md` - Configuración y ubicación del proyecto Superceller

## Uso

Para restaurar esta memoria en una nueva máquina o después de reinstalar:

1. Copia estos archivos a `~/.claude/projects/-Users-isaac/memory/`
2. Navega al directorio del proyecto
3. Inicia Claude Code con `claude`

## Nota

Esta memoria contiene **solo** información del proyecto Super Seller. No incluye memoria de otros proyectos para evitar mezclar contextos.
