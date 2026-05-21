#!/usr/bin/env python3
"""
importar_historial.py — Poblar historial.json desde publicaciones anteriores.

DOS MODOS:
  1. CSV local  (exporta desde Sheets: Archivo → Descargar → CSV)
     python importar_historial.py --csv COMPILACION_OFERTAS.csv

  2. Apps Script directo (sin exportar nada — lee la hoja en vivo)
     python importar_historial.py --sheets

Estructura esperada de la hoja (columnas en orden):
  A  —  (vacío / número)
  B  —  Fecha  (dd/MM/yyyy  ó  d/M/yyyy)
  C  —  (vacío)
  D  —  Imagen URL
  E  —  Link del producto
  F  —  Título
  G  —  Precio original
  H  —  Precio con descuento
  I  —  Descuento %
  J  —  Link (repetido)
  K  —  (vacío)
  L  —  Fuente  (Mercado Libre / Amazon)
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_FILE = os.path.join(BASE_DIR, "historial.json")

# URL del Apps Script para lectura (debe incluir doGet que devuelva los datos)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbydiVcrVOXuZWDGfUvtl38QxmHv0nPpPKtR1lUCHr0wvQB9ky0EU756uRtf2JeAcYZoww/exec?action=leer"


# ── Extraer ID del producto desde el link ────────────────────────────
def extraer_id(link: str) -> tuple[str, str]:
    """Retorna (id, source) desde un link de Amazon MX o Mercado Libre."""
    if not link:
        return "", ""
    # Amazon: /dp/ASIN o /gp/product/ASIN
    m = re.search(r'/dp/([A-Z0-9]{10})', link)
    if not m:
        m = re.search(r'/gp/product/([A-Z0-9]{10})', link)
    if m:
        return m.group(1), "amazon"
    # Mercado Libre: MLM seguido de dígitos
    m = re.search(r'(MLM[\-_]?\d+)', link, re.IGNORECASE)
    if m:
        return re.sub(r'[\-_]', '', m.group(1).upper()), "ml"
    return "", ""


# ── Parsear fecha desde string ────────────────────────────────────────
def parsear_fecha(fecha_str: str) -> str:
    """Devuelve ISO 8601 UTC. Acepta varios formatos."""
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%-d/%-m/%Y", "%Y-%m-%d",
                "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            dt = datetime.strptime(fecha_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    # Si no parsea, usar hoy
    return datetime.now(timezone.utc).isoformat()


# ── Cargar / guardar historial ────────────────────────────────────────
def cargar_historial() -> dict:
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_historial(data: dict):
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Registrar un item en el historial ────────────────────────────────
def registrar(historial: dict, item_id: str, source: str, titulo: str, fecha_iso: str):
    key = str(item_id)
    if key in historial:
        # Ya existe — actualizar si esta publicación es más reciente
        if fecha_iso > historial[key]["last_published"]:
            historial[key]["last_published"] = fecha_iso
        historial[key]["times_published"] += 1
        if titulo:
            historial[key]["title"] = titulo
    else:
        historial[key] = {
            "id": key,
            "source": source,
            "title": titulo,
            "first_seen": fecha_iso,
            "last_published": fecha_iso,
            "times_published": 1,
        }


# ── Modo 1: CSV local ─────────────────────────────────────────────────
def importar_csv(ruta_csv: str) -> int:
    historial = cargar_historial()
    previos   = len(historial)
    nuevos    = 0
    actualizados = 0

    with open(ruta_csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0:
                # Si la primera fila tiene encabezados, saltar
                if any(h.lower() in ("fecha", "link", "título", "fuente", "date") for h in row):
                    print(f"  → Encabezado detectado, saltando fila 1", flush=True)
                    continue
            if len(row) < 6:
                continue
            fecha_str = row[1].strip() if len(row) > 1 else ""
            link      = row[4].strip() if len(row) > 4 else ""
            titulo    = row[5].strip() if len(row) > 5 else ""

            if not link:
                continue

            item_id, source = extraer_id(link)
            if not item_id:
                continue

            fecha_iso = parsear_fecha(fecha_str) if fecha_str else datetime.now(timezone.utc).isoformat()
            ya_estaba = item_id in historial
            registrar(historial, item_id, source, titulo, fecha_iso)
            if ya_estaba:
                actualizados += 1
            else:
                nuevos += 1

    guardar_historial(historial)
    print(f"✅ CSV procesado: {nuevos} nuevos + {actualizados} actualizados (total historial: {len(historial)})", flush=True)
    return nuevos


# ── Modo 2: Apps Script (doGet?action=leer) ───────────────────────────
def importar_sheets() -> int:
    try:
        import requests
    except ImportError:
        print("❌ requests no instalado: pip install requests", flush=True)
        return 0

    print(f"📡 Leyendo hoja desde Apps Script…", flush=True)
    try:
        r = requests.get(APPS_SCRIPT_URL, timeout=60)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"❌ No se pudo leer desde Apps Script: {e}", flush=True)
        print("   Asegúrate de agregar el doGet de lectura al Apps Script.", flush=True)
        return 0

    rows  = data.get("rows", [])
    historial    = cargar_historial()
    nuevos       = 0
    actualizados = 0

    for row in rows:
        link      = str(row.get("link", "")).strip()
        titulo    = str(row.get("titulo", "")).strip()
        fecha_str = str(row.get("fecha", "")).strip()

        if not link:
            continue
        item_id, source = extraer_id(link)
        if not item_id:
            continue

        fecha_iso = parsear_fecha(fecha_str) if fecha_str else datetime.now(timezone.utc).isoformat()
        ya_estaba = item_id in historial
        registrar(historial, item_id, source, titulo, fecha_iso)
        if ya_estaba:
            actualizados += 1
        else:
            nuevos += 1

    guardar_historial(historial)
    print(f"✅ Sheets procesado: {nuevos} nuevos + {actualizados} actualizados (total historial: {len(historial)})", flush=True)
    return nuevos


# ── main ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Importar historial de publicaciones")
    parser.add_argument("--csv",    metavar="ARCHIVO.csv",
                        help="Ruta al CSV exportado desde Google Sheets")
    parser.add_argument("--sheets", action="store_true",
                        help="Leer directo desde Apps Script (requiere doGet de lectura)")
    args = parser.parse_args()

    if args.csv:
        if not os.path.exists(args.csv):
            print(f"❌ No se encontró el archivo: {args.csv}", flush=True)
            sys.exit(1)
        importar_csv(args.csv)
    elif args.sheets:
        importar_sheets()
    else:
        parser.print_help()
        print("\nEjemplo:\n  python importar_historial.py --csv COMPILACION_OFERTAS.csv")
        sys.exit(1)


if __name__ == "__main__":
    main()
