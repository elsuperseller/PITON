"""
Autenticación con la API de MercadoLibre, reutilizando el mismo registro
de aplicación y la misma base de datos de tokens que el proyecto
"Mercado Ads Manager" (~/Desktop/mercadoads).

IMPORTANTE: NO duplicar estas credenciales/tokens en un store separado.
El refresh_token de ML es de un solo uso — si SUPERSELLER y Ads Manager
refrescaran por separado, cada refresh invalidaría el refresh_token que
el otro proyecto tiene guardado. Por eso ambos leen/escriben la MISMA
tabla `auth_tokens` en el MISMO archivo database.sqlite: solo hay una
fuente de verdad, sin importar cuál de las dos apps refresque el token.
"""

import os
import sqlite3
import requests
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _cargar_env(ruta=os.path.join(BASE_DIR, ".env")):
    """Carga variables KEY=VALUE de un .env simple, sin depender de python-dotenv."""
    if not os.path.exists(ruta):
        return
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip())


_cargar_env()

ML_CLIENT_ID = os.environ.get("ML_CLIENT_ID")
ML_CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")
ML_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"

if not ML_CLIENT_ID or not ML_CLIENT_SECRET:
    raise RuntimeError(
        "Faltan ML_CLIENT_ID / ML_CLIENT_SECRET. Define un archivo .env "
        f"en {BASE_DIR} (ver .env.example) con las credenciales de la app "
        "de MercadoLibre compartida con Mercado Ads Manager."
    )

# Misma base de datos que usa Mercado Ads Manager (fuente única de verdad)
ADS_MANAGER_DB = os.path.expanduser("~/Desktop/mercadoads/backend/database.sqlite")


def _leer_ultimo_token():
    conn = sqlite3.connect(ADS_MANAGER_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT access_token, refresh_token, expires_at FROM auth_tokens ORDER BY id DESC LIMIT 1"
        )
        return cur.fetchone()
    finally:
        conn.close()


def _guardar_token(access_token, refresh_token, expires_in):
    expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + "Z"
    conn = sqlite3.connect(ADS_MANAGER_DB)
    try:
        conn.execute(
            "INSERT INTO auth_tokens (access_token, refresh_token, expires_at) VALUES (?, ?, ?)",
            (access_token, refresh_token, expires_at),
        )
        conn.commit()
    finally:
        conn.close()


def _refrescar_token(refresh_token):
    r = requests.post(ML_TOKEN_URL, json={
        "grant_type": "refresh_token",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }, timeout=15)
    r.raise_for_status()
    data = r.json()
    _guardar_token(data["access_token"], data["refresh_token"], data["expires_in"])
    print("  🔄 Token de MercadoLibre refrescado (guardado en database.sqlite de Ads Manager)", flush=True)
    return data["access_token"]


def get_valid_token():
    """
    Retorna un access_token vigente de MercadoLibre.
    Si el guardado está vencido, lo refresca y guarda el nuevo par
    access_token/refresh_token en la MISMA base de datos de Ads Manager.
    """
    row = _leer_ultimo_token()
    if not row:
        raise RuntimeError(
            "No hay token de MercadoLibre en la base de datos de Ads Manager "
            f"({ADS_MANAGER_DB}). Hay que autenticar ese proyecto primero."
        )

    access_token, refresh_token, expires_at_str = row

    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", ""))
        vigente = expires_at > datetime.utcnow() + timedelta(seconds=30)
    except Exception:
        vigente = False

    if vigente:
        return access_token

    if not refresh_token:
        raise RuntimeError("Token de MercadoLibre vencido y sin refresh_token disponible")

    return _refrescar_token(refresh_token)
