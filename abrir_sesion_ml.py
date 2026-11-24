"""
Abre el navegador con el mismo perfil persistente que usa el scraper de
MercadoLibre, para resolver manualmente el muro de verificación ("¿eres
humano?" / login de cuenta) que apareció tras muchas búsquedas seguidas.

Uso: python3 abrir_sesion_ml.py
Deja el navegador abierto — resuelve la verificación/login y luego cierra
la ventana tú mismo. El script se cierra solo al detectar que ya no hay
páginas abiertas (no depende de que presiones nada aquí).
"""
import time
from playwright.sync_api import sync_playwright
from scraper_ml import ML_BROWSER_PROFILE

with sync_playwright() as pw:
    ctx = pw.chromium.launch_persistent_context(
        ML_BROWSER_PROFILE,
        headless=False,
        channel='chrome',
        viewport={'width': 1280, 'height': 800},
        locale='es-MX',
        args=['--disable-blink-features=AutomationControlled'],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto('https://www.mercadolibre.com.mx', wait_until='domcontentloaded', timeout=60000)
    print("\n✅ Navegador abierto. Resuelve la verificación/login en la ventana.", flush=True)
    print("Cuando termines, cierra la ventana del navegador para terminar este script.", flush=True)

    while ctx.pages:
        time.sleep(2)

    print("Ventana cerrada, terminando.", flush=True)
