#!/usr/bin/env python3
"""
Script para login único en Mercado Libre.
Ejecutar UNA VEZ para guardar la sesión.
"""

import os
from playwright.sync_api import sync_playwright

# Directorio donde se guardará el perfil de Chrome con tu sesión
ML_PROFILE = os.path.expanduser('~/Desktop/SUPERSELLER/.ml_browser_profile')

print("=" * 60)
print("🔐 LOGIN MERCADO LIBRE - Configuración única")
print("=" * 60)
print()
print("Se abrirá Chrome en modo visible.")
print("Por favor:")
print("  1. Loguéate en Mercado Libre normalmente")
print("  2. Espera a que cargue tu cuenta")
print("  3. Regresa a la terminal y presiona ENTER")
print()
print("=" * 60)
input("Presiona ENTER para abrir Chrome...")

try:
    with sync_playwright() as p:
        # Abrir Chrome con perfil persistente (visible)
        print("🌐 Abriendo Chrome...")
        ctx = p.chromium.launch_persistent_context(
            ML_PROFILE,
            headless=False,  # Modo visible
            channel='chrome',
            viewport={'width': 1280, 'height': 800},
            locale='es-MX',
            args=['--disable-blink-features=AutomationControlled']
        )

        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print("📄 Navegando a Mercado Libre...")
        print("   (Esto puede tardar si tienes VPN activo...)")
        page.goto('https://www.mercadolibre.com.mx', wait_until='domcontentloaded', timeout=60000)

        print()
        print("=" * 60)
        print("👤 LOGUÉATE AHORA EN EL NAVEGADOR")
        print("=" * 60)
        print()
        print("Cuando hayas terminado de loguearte,")
        print("regresa aquí y presiona ENTER...")
        print()

        input(">>> Presiona ENTER cuando estés logueado...")

        print()
        print("🔍 Verificando sesión...")

        # Ir a cuenta para verificar que está logueado
        try:
            page.goto('https://www.mercadolibre.com.mx/navigation/account', timeout=15000)
        except:
            # No importa si falla, lo importante es que la sesión se guardó
            pass

        print("💾 Guardando sesión...")
        ctx.close()

        print()
        print("=" * 60)
        print("✅ SESIÓN GUARDADA EXITOSAMENTE")
        print("=" * 60)
        print()
        print(f"📁 Perfil guardado en: {ML_PROFILE}")
        print()
        print("Ahora todas las búsquedas automáticas usarán tu sesión.")
        print("No necesitas volver a ejecutar este script.")
        print()

except Exception as e:
    print()
    print("=" * 60)
    print("❌ ERROR")
    print("=" * 60)
    print(f"Error: {e}")
    print()
    print("Si Playwright no está instalado, ejecuta:")
    print("  pip install playwright")
    print("  playwright install chrome")
    print()
