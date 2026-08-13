#!/usr/bin/env python3
"""
Servidor Landing de Cupones - Superseller
Servidor simple que lee cupones.json y genera la página dinámica
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from urllib.parse import urlparse

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CUPONES_FILE = os.path.join(BASE_DIR, "cupones.json")
TEMPLATE_FILE = os.path.join(BASE_DIR, "index.html")


def cargar_cupones():
    """Carga el archivo cupones.json"""
    with open(CUPONES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def esta_vigente(fecha_vencimiento):
    """Verifica si un cupón está vigente"""
    try:
        vence = datetime.strptime(fecha_vencimiento, "%Y-%m-%d")
        hoy = datetime.now()
        return vence.date() >= hoy.date()
    except:
        return True


def dias_restantes(fecha_vencimiento):
    """Calcula días restantes para vencer"""
    try:
        vence = datetime.strptime(fecha_vencimiento, "%Y-%m-%d")
        hoy = datetime.now()
        diferencia = (vence.date() - hoy.date()).days

        if diferencia == 0:
            return "Vence hoy"
        elif diferencia == 1:
            return "Vence mañana"
        elif diferencia < 0:
            return "Vencido"
        else:
            return f"Vence en {diferencia} días"
    except:
        return "Sin vencimiento"


def generar_html():
    """Genera el HTML con los cupones actuales"""
    data = cargar_cupones()
    cupones = data.get("cupones", [])
    config = data.get("configuracion", {})

    # Filtrar cupones activos y vigentes
    cupones_activos = [c for c in cupones if c.get("activo", True) and esta_vigente(c.get("vencimiento", ""))]

    # Separar destacados
    destacados = [c for c in cupones_activos if c.get("destacado", False)]
    normales = [c for c in cupones_activos if not c.get("destacado", False)]

    # Leer template
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()

    # Generar HTML de cupones destacados
    html_destacados = ""
    for cupon in destacados:
        html_destacados += generar_tarjeta_cupon(cupon, destacado=True)

    # Generar HTML de cupones normales
    html_normales = ""
    for cupon in normales:
        html_normales += generar_tarjeta_cupon(cupon, destacado=False)

    # Reemplazar en template
    html = template.replace("{{TITULO_SITIO}}", config.get("titulo_sitio", "Cupones Superseller"))
    html = html.replace("{{DESCRIPCION}}", config.get("descripcion", "Los mejores cupones"))
    html = html.replace("{{CUPONES_DESTACADOS}}", html_destacados)
    html = html.replace("{{CUPONES_NORMALES}}", html_normales)
    html = html.replace("{{WHATSAPP_URL}}", config.get("redes_sociales", {}).get("whatsapp", "#"))
    html = html.replace("{{TELEGRAM_URL}}", config.get("redes_sociales", {}).get("telegram", "#"))
    html = html.replace("{{FACEBOOK_URL}}", config.get("redes_sociales", {}).get("facebook", "#"))
    html = html.replace("{{YOUTUBE_URL}}", config.get("redes_sociales", {}).get("youtube", "#"))

    return html


def generar_tarjeta_cupon(cupon, destacado=False):
    """Genera HTML de una tarjeta de cupón"""

    # Determinar colores según el fondo
    colores = {
        "gold": "linear-gradient(135deg, #f6d365 0%, #fda085 100%)",
        "blue": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "purple": "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)",
        "green": "linear-gradient(135deg, #13547a 0%, #80d0c7 100%)",
        "red": "linear-gradient(135deg, #eb3349 0%, #f45c43 100%)"
    }

    color_bg = colores.get(cupon.get("color_fondo", "blue"), colores["blue"])
    codigo_oculto = cupon["codigo"][:4] + "●" * (len(cupon["codigo"]) - 4)
    vencimiento = dias_restantes(cupon.get("vencimiento", ""))

    badge_destacado = '⭐ CUPÓN TOP' if destacado else ''

    html = f'''
    <article class="cupon-card">
        <div class="cupon-header">
            <h3 class="cupon-titulo">{cupon["titulo"]}</h3>
            <div class="vencimiento">{vencimiento}</div>
        </div>
        {f'<div class="badge-destacado">{badge_destacado}</div>' if destacado else ''}
        <div class="cupon-contenido" style="background: {color_bg}">
            <div class="logo-seccion">
                <img src="{cupon.get("logo_url", "")}" alt="{cupon.get("plataforma", "Mercado Libre")}" class="logo-plataforma">
            </div>
            <div class="info-seccion">
                <div class="codigo-oculto">{codigo_oculto}</div>
                <div class="condiciones">
                    <div>COMPRA MÍNIMA ${cupon.get("compra_minima", 0):,}</div>
                    <div>DESCUENTO MAX: ${cupon.get("descuento_maximo", 0):,}</div>
                </div>
            </div>
        </div>
        <button class="btn-copiar" onclick="copiarCupon('{cupon["codigo"]}', '{cupon.get("plataforma", "Mercado Libre")}')">
            COPIAR Y CANJEAR
        </button>
    </article>
    '''

    return html


class RequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """Manejar peticiones GET"""

        path = urlparse(self.path).path

        if path == "/" or path == "/index.html":
            try:
                html = generar_html()
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"Error generando página: {str(e)}")

        elif path == "/api/cupones":
            # API endpoint para obtener cupones en JSON
            try:
                data = cargar_cupones()
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"Error cargando cupones: {str(e)}")

        else:
            self.send_error(404, "Página no encontrada")

    def log_message(self, format, *args):
        """Sobrescribir para logging personalizado"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {args[0]}")


def main():
    """Iniciar servidor"""
    print(f"🚀 Servidor Landing de Cupones - Superseller")
    print(f"📂 Directorio: {BASE_DIR}")
    print(f"📄 Cupones: {CUPONES_FILE}")
    print(f"🌐 Servidor corriendo en http://localhost:{PORT}")
    print(f"⏹️  Presiona Ctrl+C para detener\n")

    server = HTTPServer(("", PORT), RequestHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n⏹️  Servidor detenido")
        server.shutdown()


if __name__ == "__main__":
    main()
