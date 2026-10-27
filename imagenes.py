"""
Módulo de procesamiento de imágenes
Gestiona transformaciones de URLs de imágenes de Amazon y Mercado Libre
Incluye procesamiento inteligente para crear imágenes cuadradas optimizadas
"""

import re
import os
import hashlib
import requests
from PIL import Image, ImageChops
from io import BytesIO

# ==================== CONFIGURACIÓN ====================

# Formato de imagen para Amazon (máxima calidad, no fuerza cuadrado)
FORMATO_AMAZON = '._SS1000_'  # Square Scale 1000×1000 - imagen cuadrada

# Formato de imagen para Mercado Libre
FORMATO_ML = '-2X.webp'  # Imagen cuadrada ~1000x1000

# ==================== FUNCIONES ====================

def transformar_imagen_amazon(url):
    """
    Transforma URL de imagen de Amazon al formato óptimo

    Formato actual: _SL1500_
    - Scale Longest: Escala lado más largo a 1500px
    - Mantiene aspect ratio original (no fuerza cuadrado)
    - Resultado: Máxima calidad para posterior procesamiento

    Args:
        url (str): URL original de imagen de Amazon

    Returns:
        str: URL transformada al formato óptimo

    Ejemplo:
        Input:  "https://m.media-amazon.com/images/I/41abc._SS1000_.jpg"
        Output: "https://m.media-amazon.com/images/I/41abc._SL1500_.jpg"
    """
    if not url:
        return ""

    # Reemplazar cualquier formato existente (_XX123_, _AC_UL1000_, etc.)
    # Patrón mejorado: captura formatos complejos como _AC_UL1000_, _SS1000_, etc.
    return re.sub(r'\._[A-Z0-9_,]+_\.', FORMATO_AMAZON + '.', url)


def transformar_imagen_ml(url):
    """
    Transforma URL de imagen de Mercado Libre al formato óptimo

    Formato actual: -2X.webp
    - Imagen cuadrada ~1000x1000
    - Formato WebP (mejor compresión)

    Args:
        url (str): URL original de imagen de ML

    Returns:
        str: URL transformada al formato óptimo

    Ejemplo:
        Input:  "https://http2.mlstatic.com/D_NQ_NP_123-O.jpg"
        Output: "https://http2.mlstatic.com/D_NQ_NP_123-2X.webp"
    """
    if not url:
        return ""

    # Reemplazar sufijo de formato (-O, -V, -F, etc.) + extensión
    return re.sub(r'-[A-Z0-9]+\.(jpg|webp|png)', FORMATO_ML, url, flags=re.IGNORECASE)


def cambiar_formato_amazon(nuevo_formato):
    """
    Cambia el formato de imagen de Amazon globalmente

    Args:
        nuevo_formato (str): Nuevo formato (ej: '._SS1000_', '._AC_UL1000_')

    Formatos disponibles:
        ._SS1000_    = Square Scale (cuadrado con espacios blancos)
        ._AC_UL1000_ = Auto Crop Uniform Large (zoom agresivo, puede pixelar)
        ._AC_SL1000_ = Auto Crop Scale Longest (punto medio: calidad + tamaño) ← ACTUAL
        ._SL1000_    = Scale Longest (máxima calidad, puede tener márgenes)

    Returns:
        str: Formato anterior (para rollback)
    """
    global FORMATO_AMAZON
    formato_anterior = FORMATO_AMAZON
    FORMATO_AMAZON = nuevo_formato
    print(f"  🖼️  Formato Amazon cambiado: {formato_anterior} → {nuevo_formato}", flush=True)
    return formato_anterior


# ==================== PROCESAMIENTO INTELIGENTE ====================

# Directorio de caché para imágenes procesadas
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache_imagenes')
os.makedirs(CACHE_DIR, exist_ok=True)


def trim_whitespace(img):
    """
    Elimina el espacio blanco alrededor de la imagen

    Args:
        img (PIL.Image): Imagen a procesar

    Returns:
        PIL.Image: Imagen con espacio blanco eliminado
    """
    # Convertir a RGB si es necesario
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Obtener el fondo (asumimos que es blanco o el color del primer pixel)
    bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))

    # Calcular la diferencia
    diff = ImageChops.difference(img, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)

    # Obtener el bounding box del contenido
    bbox = diff.getbbox()

    if bbox:
        return img.crop(bbox)
    return img


def imagen_cuadrada_producto(url, size=1000, producto_objetivo=0.90, forzar_regenerar=False):
    """
    Procesa una imagen de producto para crear una versión cuadrada optimizada

    El procesamiento incluye:
    1. Descargar imagen desde URL
    2. Eliminar espacio blanco excesivo (trim)
    3. Escalar proporcionalmente para que el producto ocupe ~90% del espacio
    4. Centrar en lienzo blanco cuadrado
    5. Guardar en caché

    Args:
        url (str): URL de la imagen original
        size (int): Tamaño del lienzo cuadrado (default: 1000)
        producto_objetivo (float): Fracción del espacio que debe ocupar el producto (default: 0.90)
        forzar_regenerar (bool): Si True, regenera aunque exista en caché

    Returns:
        str: Ruta local del archivo procesado

    Ejemplo:
        >>> ruta = imagen_cuadrada_producto(
        ...     "https://m.media-amazon.com/images/I/415G84gcWGL._SL1500_.jpg",
        ...     size=1000,
        ...     producto_objetivo=0.90
        ... )
        >>> print(ruta)  # './cache_imagenes/abc123def.jpg'
    """
    if not url:
        return None

    # Generar hash para caché (basado en URL + parámetros)
    cache_key = hashlib.md5(f"{url}_{size}_{producto_objetivo}".encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.jpg")

    # Si existe en caché y no se fuerza regenerar, retornar
    if os.path.exists(cache_path) and not forzar_regenerar:
        return cache_path

    try:
        # 1. Descargar imagen
        print(f"  📥 Descargando imagen: {url[:60]}...", flush=True)
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # 2. Abrir con PIL
        img_original = Image.open(BytesIO(response.content))

        # Convertir a RGB si es necesario (algunos PNG tienen alpha)
        if img_original.mode in ('RGBA', 'LA', 'P'):
            # Crear fondo blanco
            bg = Image.new('RGB', img_original.size, (255, 255, 255))
            if img_original.mode == 'P':
                img_original = img_original.convert('RGBA')
            bg.paste(img_original, mask=img_original.split()[-1] if img_original.mode == 'RGBA' else None)
            img_original = bg
        elif img_original.mode != 'RGB':
            img_original = img_original.convert('RGB')

        # 3. Trim del espacio blanco
        print(f"  ✂️  Eliminando espacio blanco...", flush=True)
        img_trimmed = trim_whitespace(img_original)

        # 4. Calcular escala para que el producto ocupe producto_objetivo del lienzo
        # El producto trimmed debe ocupar producto_objetivo (ej: 90%) del tamaño final
        target_size = int(size * producto_objetivo)

        # Calcular el ratio de escalado manteniendo aspect ratio
        ratio = min(target_size / img_trimmed.width, target_size / img_trimmed.height)
        new_width = int(img_trimmed.width * ratio)
        new_height = int(img_trimmed.height * ratio)

        print(f"  🔍 Escalando: {img_trimmed.size} → {new_width}×{new_height}", flush=True)
        img_scaled = img_trimmed.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 5. Crear lienzo blanco cuadrado
        canvas = Image.new('RGB', (size, size), (255, 255, 255))

        # 6. Centrar el producto en el lienzo
        offset_x = (size - new_width) // 2
        offset_y = (size - new_height) // 2
        canvas.paste(img_scaled, (offset_x, offset_y))

        # 7. Guardar en caché
        canvas.save(cache_path, 'JPEG', quality=95, optimize=True)
        print(f"  ✅ Imagen procesada: {cache_path}", flush=True)

        return cache_path

    except Exception as e:
        print(f"  ❌ Error procesando imagen: {e}", flush=True)
        return None


# ==================== TESTING ====================

if __name__ == "__main__":
    # Tests básicos
    print("Testing módulo imagenes.py\n")

    # Test Amazon
    url_amazon = "https://m.media-amazon.com/images/I/41abc._SL500_.jpg"
    url_transformada = transformar_imagen_amazon(url_amazon)
    print(f"Amazon:")
    print(f"  Input:  {url_amazon}")
    print(f"  Output: {url_transformada}")
    print(f"  ✅ Formato aplicado: {FORMATO_AMAZON}\n")

    # Test Mercado Libre
    url_ml = "https://http2.mlstatic.com/D_NQ_NP_123456-O.jpg"
    url_transformada_ml = transformar_imagen_ml(url_ml)
    print(f"Mercado Libre:")
    print(f"  Input:  {url_ml}")
    print(f"  Output: {url_transformada_ml}")
    print(f"  ✅ Formato aplicado: {FORMATO_ML}\n")

    # Test cambio de formato
    print(f"Cambio de formato:")
    anterior = cambiar_formato_amazon('._SS1000_')
    print(f"  Formato actual: {FORMATO_AMAZON}")
