#!/usr/bin/env python3
"""
amazon_browse_nodes.py - Catálogo oficial de browseNodeIds para Amazon México
Obtenido mediante GetBrowseNodes API el 2026-10-08
"""

# Nodos raíz por categoría principal
RAICES = {
    "Juguetes y Juegos": "11260442011",
    "Electrónicos": "9482558011",
    "Hogar y Cocina": "9482593011",
    "Deportes y Aire Libre": "9482660011",
    "Herramientas y Mejoras del Hogar": "9482593011",
    "Ropa, Zapatos y Accesorios": "9482610011",
    "Libros": "9298576011",
}

# Nodo "Categorías" (nivel debajo de raíz, contiene las subcategorías reales)
CATEGORIAS_NODES = {
    "Juguetes y Juegos": "11260443011",
    "Electrónicos": "9482559011",
    "Hogar y Cocina": "9482594011",
    "Deportes y Aire Libre": "9482661011",
}

# Mapeo de subcategorías (formato "Categoría Principal__Subcategoría")
# Estos son los IDs que se usan en el buscador
SUBCATEGORIAS = {
    # === JUGUETES Y JUEGOS ===
    "Juguetes y Juegos__Figuras de Acción": "11337634011",
    "Juguetes y Juegos__Muñecas y Accesorios": "11337428011",
    "Juguetes y Juegos__Coleccionables": "20940159011",  # "Juguetes Coleccionables"
    "Juguetes y Juegos__Aire Libre y Deportes": "11337412011",
    "Juguetes y Juegos__Artes y Manualidades": "11337413011",
    "Juguetes y Juegos__Artículos para Fiesta": "11337414011",
    "Juguetes y Juegos__Instrumentos Musicales de Juguete": "11337418011",
    "Juguetes y Juegos__Juegos de Construcción": "11337421011",
    "Juguetes y Juegos__Juegos de Imitación": "11337422011",
    "Juguetes y Juegos__Juegos y Accesorios para Juegos": "11337420011",
    "Juguetes y Juegos__Juguetes Educativos": "11337424011",
    "Juguetes y Juegos__Juguetes Electrónicos": "11337425011",
    "Juguetes y Juegos__Juguetes Novedosos y de Broma": "11337426011",
    "Juguetes y Juegos__Juguetes para Bebés y Niños Pequeños": "11337427011",
    "Juguetes y Juegos__Muñecos, Figuras y Sets de Juego": "11337429011",
    "Juguetes y Juegos__Peluches": "11337430011",
    "Juguetes y Juegos__Radiocontrol": "11337504011",
    "Juguetes y Juegos__Rompecabezas": "11337431011",
    "Juguetes y Juegos__Títeres y Escenarios para Títeres": "11337432011",
    "Juguetes y Juegos__Vehículos de Juguete": "11337433011",

    # === ELECTRÓNICOS ===
    "Electrónicos__Audio y Video Portátil": "9687392011",
    "Electrónicos__Celulares y Accesorios": "9687422011",
    "Electrónicos__Computadoras, Componentes y Accesorios": "9687880011",
    "Electrónicos__Cámaras y Fotografía": "9687605011",
    "Electrónicos__Electrónica para Autos": "9687471011",
    "Electrónicos__Electrónicos de Oficina": "9705965011",
    "Electrónicos__Equipos de Audio y Hi-Fi": "9687565011",
    "Electrónicos__Lectores de Libros Electrónicos y Accesorios": "9687881011",
    "Electrónicos__Navegación Satelital, GPS y Accesorios": "9687860011",
    "Electrónicos__Radiocomunicación": "9687892011",
    "Electrónicos__Tecnología para Vestir": "15144312011",
    "Electrónicos__Televisión y Vídeo": "9687925011",
    "Electrónicos__Teléfonos, VoIP y Accesorios": "9687911011",
    "Electrónicos__Accesorios de Alimentación": "9687281011",
    "Electrónicos__Audífonos, auriculares y accesorios": "24035342011",
    "Electrónicos__Pilas y Cargadores": "9687374011",
    "Electrónicos__Tabletas": "10189676011",

    # === HOGAR Y COCINA ===
    "Hogar y Cocina__Almacenamiento y Organización": "9756857011",
    "Hogar y Cocina__Arte y Manualidades": "10201738011",
    "Hogar y Cocina__Aspiración, Limpieza y Planchado": "9725297011",
    "Hogar y Cocina__Aspiradoras y herramientas de limpieza para el hogar": "24426809011",
    "Hogar y Cocina__Baño": "9756950011",
    "Hogar y Cocina__Blancos para el Hogar": "9757431011",
    "Hogar y Cocina__Climatización y Calefacción": "9725442011",
    "Hogar y Cocina__Cocina": "9721682011",
    "Hogar y Cocina__Cuidado del Hogar y Limpieza": "11525771011",
    "Hogar y Cocina__Decoración del Hogar": "9757037011",
    "Hogar y Cocina__Iluminación": "9939347011",
    "Hogar y Cocina__Muebles": "9757251011",
    "Hogar y Cocina__Obras de Arte y Material Decorativo": "9757416011",

    # === DEPORTES Y AIRE LIBRE ===
    "Deportes y Aire Libre__Accesorios Deportivos y de Recreación al Aire Libre": "20687658011",
    "Deportes y Aire Libre__Airsoft": "9783917011",
    "Deportes y Aire Libre__Animación": "9784513011",
    "Deportes y Aire Libre__Artes Marciales": "9783947011",
    "Deportes y Aire Libre__Atletismo": "9784025011",
    "Deportes y Aire Libre__Bádminton": "9784072011",
    "Deportes y Aire Libre__Balonmano": "9784163011",
    "Deportes y Aire Libre__Basquetbol": "9784119011",
    "Deportes y Aire Libre__Béisbol": "9784206011",
    "Deportes y Aire Libre__Billar": "9784285011",
    "Deportes y Aire Libre__Box": "9784332011",
    "Deportes y Aire Libre__Campismo y Senderismo": "9783688011",
    "Deportes y Aire Libre__Caza": "9784387011",
    "Deportes y Aire Libre__Ciclismo": "9784530011",
    "Deportes y Aire Libre__Correr": "9790484011",
    "Deportes y Aire Libre__Danza": "9785852011",
    "Deportes y Aire Libre__Deportes Acuáticos": "9785900011",
    "Deportes y Aire Libre__Deportes de Invierno": "9786306011",
    "Deportes y Aire Libre__Fútbol": "9786709011",
    "Deportes y Aire Libre__Golf": "9789827011",
    "Deportes y Aire Libre__Gimnasia": "9789894011",
    "Deportes y Aire Libre__Pesca": "9786633011",
    "Deportes y Aire Libre__Tenis": "9789598011",
}

def get_browse_node_id(categoria_completa):
    """
    Devuelve el browseNodeId para una categoría.

    Args:
        categoria_completa: String en formato "Principal__Subcategoría" o solo "Principal"

    Returns:
        str: El browseNodeId correspondiente o None si no se encuentra
    """
    # Si viene con formato "Principal__Subcategoría"
    if "__" in categoria_completa:
        return SUBCATEGORIAS.get(categoria_completa)

    # Si es solo la categoría principal, devolver el nodo "Categorías"
    return CATEGORIAS_NODES.get(categoria_completa)

def listar_subcategorias(categoria_principal):
    """
    Lista todas las subcategorías disponibles para una categoría principal.

    Args:
        categoria_principal: Nombre de la categoría principal (ej: "Juguetes y Juegos")

    Returns:
        dict: Diccionario {nombre_subcategoria: nodeId}
    """
    prefix = f"{categoria_principal}__"
    return {
        k.replace(prefix, ""): v
        for k, v in SUBCATEGORIAS.items()
        if k.startswith(prefix)
    }
