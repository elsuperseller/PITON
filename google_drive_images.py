"""
Módulo para subir imágenes procesadas a Google Drive
Gestiona el upload automático y limpieza de archivos antiguos

CONFIGURACIÓN INICIAL:
1. Habilitar Google Drive API en Google Cloud Console
2. Crear Service Account
3. Descargar JSON de credenciales
4. Guardar como 'google-drive-credentials.json' en este directorio
5. Compartir carpetas de Drive con el email del Service Account

Documentación: https://developers.google.com/drive/api/guides/about-sdk
"""

import os
import hashlib
from datetime import datetime, timedelta
import imagenes

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_DRIVE_DISPONIBLE = True
except ImportError:
    GOOGLE_DRIVE_DISPONIBLE = False
    print("⚠️  Librerías de Google Drive no instaladas. Ejecuta:")
    print("    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

# ==================== CONFIGURACIÓN ====================

# Ruta al archivo de credenciales
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'google-drive-credentials.json')

# Scopes necesarios
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Mapeo de audiencia_id → Google Drive folder_id (Shared Drive)
CARPETAS_DRIVE = {
    "superseller": "13GlMZFroyfoX2-Lns41Mxs1nBFURt0_c",
    "coleccionistas": "1puYtN2zN1vI9oozyXD8CuEtIcYToRWmh",
    "Superseller": "13GlMZFroyfoX2-Lns41Mxs1nBFURt0_c",  # Alias
    "Collector Secret Society": "1puYtN2zN1vI9oozyXD8CuEtIcYToRWmh"  # Alias
}

# Días de retención de imágenes en Drive
DIAS_RETENCION = 7

# ==================== CLIENTE GOOGLE DRIVE ====================

def get_drive_service():
    """
    Obtiene cliente autenticado de Google Drive API

    Returns:
        Resource: Cliente de Google Drive API

    Raises:
        FileNotFoundError: Si no existe google-drive-credentials.json
        Exception: Si hay error en autenticación
    """
    if not GOOGLE_DRIVE_DISPONIBLE:
        raise Exception("Librerías de Google Drive no instaladas")

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"No se encontró {CREDENTIALS_FILE}\n"
            "Configura las credenciales siguiendo las instrucciones en el módulo"
        )

    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=SCOPES
    )

    service = build('drive', 'v3', credentials=credentials)
    return service

# ==================== FUNCIONES ====================

def subir_imagen_procesada(url_original, audiencia_id):
    """
    Procesa una imagen y la sube a Google Drive

    Args:
        url_original (str): URL de la imagen original de Amazon
        audiencia_id (str): ID de la audiencia (superseller, coleccionistas, etc)

    Returns:
        str: URL pública de la imagen en Google Drive, o None si falla

    Flujo:
        1. Procesar imagen → cuadrada 1000×1000 (imagenes.py)
        2. Subir a Google Drive en carpeta de audiencia
        3. Compartir públicamente (anyone with link)
        4. Retornar URL compartida
    """
    try:
        # 1. Procesar imagen localmente
        print(f"  🖼️  Procesando imagen para {audiencia_id}...", flush=True)
        ruta_local = imagenes.imagen_cuadrada_producto(
            url_original,
            size=1000,
            producto_objetivo=0.90
        )

        if not ruta_local or not os.path.exists(ruta_local):
            print(f"  ❌ Error: No se pudo procesar imagen", flush=True)
            return None

        # 2. Obtener folder_id de la audiencia
        folder_id = CARPETAS_DRIVE.get(audiencia_id)
        if not folder_id:
            print(f"  ❌ Error: Audiencia '{audiencia_id}' no tiene carpeta en Drive", flush=True)
            return None

        # 3. Generar nombre único
        hash_url = hashlib.md5(url_original.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"img_{hash_url}_{timestamp}.jpg"

        print(f"  ☁️  Subiendo a Google Drive...", flush=True)

        # 4. Obtener servicio de Drive
        service = get_drive_service()

        # 5. Metadata del archivo
        file_metadata = {
            'name': nombre_archivo,
            'parents': [folder_id]
        }

        # 6. Subir archivo
        media = MediaFileUpload(
            ruta_local,
            mimetype='image/jpeg',
            resumable=True
        )

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink,webContentLink',
            supportsAllDrives=True
        ).execute()

        file_id = file.get('id')

        print(f"  🔓 Compartiendo públicamente...", flush=True)

        # 7. Compartir públicamente (anyone with link can view)
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }

        service.permissions().create(
            fileId=file_id,
            body=permission,
            supportsAllDrives=True
        ).execute()

        # 8. URL pública directa (para embed en Google Sheets)
        # Formato: https://drive.google.com/uc?export=view&id={file_id}
        url_publica = f"https://drive.google.com/uc?export=view&id={file_id}"

        print(f"  ✅ Imagen subida: {url_publica}", flush=True)

        return url_publica

    except FileNotFoundError as e:
        print(f"  ❌ {e}", flush=True)
        return None
    except Exception as e:
        print(f"  ❌ Error subiendo imagen a Drive: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


def limpiar_imagenes_antiguas(audiencia_id, dias=DIAS_RETENCION):
    """
    Elimina imágenes más antiguas de N días en la carpeta de una audiencia

    Args:
        audiencia_id (str): ID de la audiencia
        dias (int): Días de retención (default: 7)

    Returns:
        int: Número de archivos eliminados
    """
    try:
        folder_id = CARPETAS_DRIVE.get(audiencia_id)
        if not folder_id:
            print(f"  ❌ Audiencia '{audiencia_id}' no tiene carpeta en Drive", flush=True)
            return 0

        # Fecha límite (archivos más viejos que esto se eliminan)
        fecha_limite = datetime.now() - timedelta(days=dias)

        print(f"  🗑️  Limpiando archivos > {dias} días en {audiencia_id}...", flush=True)

        # Obtener servicio de Drive
        service = get_drive_service()

        # Buscar archivos JPEG en la carpeta
        query = f"'{folder_id}' in parents and mimeType='image/jpeg' and trashed=false"

        results = service.files().list(
            q=query,
            fields='files(id, name, createdTime)',
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        archivos = results.get('files', [])
        eliminados = 0

        for archivo in archivos:
            # Fecha de creación
            created_time_str = archivo.get('createdTime', '')

            if not created_time_str:
                continue

            # Parsear fecha (formato ISO 8601: 2024-10-26T23:55:02.786Z)
            created_time = datetime.fromisoformat(created_time_str.replace('Z', '+00:00'))

            # Comparar fechas (aware datetime)
            if created_time.replace(tzinfo=None) < fecha_limite:
                file_id = archivo.get('id')
                nombre = archivo.get('name', 'sin_nombre')

                print(f"    🗑️  Eliminando: {nombre} ({created_time_str})", flush=True)

                # Mover a papelera
                service.files().update(
                    fileId=file_id,
                    body={'trashed': True},
                    supportsAllDrives=True
                ).execute()

                eliminados += 1

        print(f"  ✅ Archivos eliminados: {eliminados}", flush=True)
        return eliminados

    except FileNotFoundError as e:
        print(f"  ❌ {e}", flush=True)
        return 0
    except Exception as e:
        print(f"  ❌ Error limpiando archivos antiguos: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 0


# ==================== TESTING ====================

if __name__ == "__main__":
    print("Testing módulo google_drive_images.py")
    print()
    print("Carpetas configuradas:")
    for audiencia, folder_id in CARPETAS_DRIVE.items():
        print(f"  - {audiencia}: {folder_id}")
    print()
    print("⚠️  Para probar upload, ejecutar desde servidor.py con MCP disponible")
