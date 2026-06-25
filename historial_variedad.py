#!/usr/bin/env python3
"""historial_variedad.py — Historial de publicaciones y score de novedad"""

import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_FILE = os.path.join(BASE_DIR, "historial.json")

# ── MODELO / SKU ─────────────────────────────────────────────────────
# Detecta códigos tipo WH-1000XM5, OLED65C3, KD-55X80L, RTX4070, B550M
_MODEL_RE = re.compile(
    r'\b(?:'
    r'[A-Z0-9]{2,6}-\d{3,}[A-Z0-9\-/]{0,10}'   # WH-1000XM5, KD-55X80L
    r'|[A-Z]{2,6}\d{3,}[A-Z0-9\-]{0,8}'          # OLED65C3, RTX4070, B550M
    r'|\d{2,4}[A-Z]{2,}[0-9A-Z\-]{0,8}'           # 65C3, 27QHD, 55CU8000
    r')\b',
    re.IGNORECASE,
)

def _extraer_modelo(titulo):
    """Extrae el modelo/SKU más largo de un título. Devuelve string en mayúsculas o ''."""
    if not titulo:
        return ""
    matches = _MODEL_RE.findall(titulo)
    candidates = [m.upper() for m in matches
                  if re.search(r'[A-Za-z]', m) and re.search(r'\d', m) and len(m) >= 4]
    return max(candidates, key=len) if candidates else ""

# ── I/O ─────────────────────────────────────────────────────────────
def _cargar():
    if not os.path.exists(HISTORIAL_FILE):
        return {}
    with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _guardar(data):
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── SCORE ────────────────────────────────────────────────────────────
def score_novedad(item_id, historial=None):
    """
    1.0  — nunca visto
    0.8  — publicado hace >14 días
    0.5  — publicado hace 7-14 días
    0.2  — publicado hace 3-7 días
    0.0  — publicado hace <3 días
    Penalización extra: -0.15 por publicación adicional (máx -0.3)
    """
    if historial is None:
        historial = _cargar()
    entry = historial.get(str(item_id))
    if not entry:
        return 1.0
    ultimo = datetime.fromisoformat(entry["last_published"])
    if ultimo.tzinfo is None:
        ultimo = ultimo.replace(tzinfo=timezone.utc)
    dias  = (datetime.now(timezone.utc) - ultimo).days
    veces = entry.get("times_published", 1)
    if   dias >= 14: base = 0.8
    elif dias >= 7:  base = 0.5
    elif dias >= 3:  base = 0.2
    else:            base = 0.0
    penalizacion = min(0.3, max(0, veces - 1) * 0.15)
    return round(max(0.0, base - penalizacion), 2)

# ── MARCAR ───────────────────────────────────────────────────────────
def marcar_publicado(item_id, source="", title="", ean="", modelo=""):
    historial = _cargar()
    key       = str(item_id)
    ahora     = datetime.now(timezone.utc).isoformat()
    modelo    = modelo or _extraer_modelo(title)
    if key in historial:
        historial[key]["last_published"]   = ahora
        historial[key]["times_published"] += 1
        if title:  historial[key]["title"]  = title
        if ean:    historial[key]["ean"]    = ean
        if modelo: historial[key]["modelo"] = modelo
    else:
        historial[key] = {
            "id": key, "source": source, "title": title,
            "first_seen": ahora, "last_published": ahora, "times_published": 1,
            "ean": ean, "modelo": modelo,
        }
    _guardar(historial)
    return historial[key]

def marcar_varios(items):
    """Marca una lista de objetos oferta como publicados en un solo write."""
    historial = _cargar()
    ahora     = datetime.now(timezone.utc).isoformat()
    for p in items:
        key = str(p.get("id") or p.get("asin") or "")
        if not key:
            continue
        ean    = p.get("ean", "")
        modelo = p.get("modelo") or _extraer_modelo(p.get("title", ""))
        if key in historial:
            historial[key]["last_published"]   = ahora
            historial[key]["times_published"] += 1
            if p.get("title"): historial[key]["title"]  = p["title"]
            if ean:            historial[key]["ean"]    = ean
            if modelo:         historial[key]["modelo"] = modelo
        else:
            historial[key] = {
                "id": key, "source": p.get("source", ""), "title": p.get("title", ""),
                "first_seen": ahora, "last_published": ahora, "times_published": 1,
                "ean": ean, "modelo": modelo,
            }
    _guardar(historial)
    return len(items)

# ── ÍNDICE CROSS-PLATFORM ────────────────────────────────────────────
def _build_cross_index(historial):
    """
    Construye índices por EAN y modelo para detectar duplicados cross-platform.
    Solo incluye items publicados en los últimos 14 días.
    Retorna (ean_idx, modelo_idx): dict EAN→entry y dict MODELO→entry.
    """
    ean_idx    = {}
    modelo_idx = {}
    ahora      = datetime.now(timezone.utc)
    for key, entry in historial.items():
        dt = datetime.fromisoformat(entry["last_published"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if (ahora - dt).days > 14:
            continue
        ean = entry.get("ean", "")
        if ean:
            ean_idx[ean] = {"key": key, "source": entry.get("source", ""), "title": entry.get("title", "")}
        modelo = entry.get("modelo") or _extraer_modelo(entry.get("title", ""))
        if modelo and len(modelo) >= 5:
            modelo_idx[modelo] = {"key": key, "source": entry.get("source", ""), "title": entry.get("title", "")}
    return ean_idx, modelo_idx

# ── SCORES ───────────────────────────────────────────────────────────
def aplicar_scores(items):
    """
    Agrega `novedad_score` a cada item y ordena de mayor a menor.
    También detecta duplicados cross-platform (mismo EAN o mismo modelo
    publicado recientemente en la otra plataforma) y añade `cross_platform_dup`.
    """
    historial          = _cargar()
    ean_idx, modelo_idx = _build_cross_index(historial)
    cross_total        = 0

    for p in items:
        key    = str(p.get("id") or p.get("asin") or "")
        source = p.get("source", "")
        p["novedad_score"] = score_novedad(key, historial)

        # Solo buscar cross-platform si no está ya penalizado a 0 por mismo canal
        if p["novedad_score"] > 0.0:
            ean    = p.get("ean", "")
            modelo = p.get("modelo") or _extraer_modelo(p.get("title", ""))

            match = None
            if ean and ean in ean_idx and ean_idx[ean]["source"] != source:
                match = ean_idx[ean]
            elif modelo and len(modelo) >= 5 and modelo in modelo_idx and modelo_idx[modelo]["source"] != source:
                match = modelo_idx[modelo]

            if match:
                p["cross_platform_dup"] = match["source"]   # "amazon" o "ml"
                p["novedad_score"]      = 0.0
                cross_total += 1

    if cross_total:
        print(f"  🔀 Cross-platform: {cross_total} productos ya publicados en otra plataforma", flush=True)

    return sorted(items, key=lambda p: p["novedad_score"], reverse=True)

def filtrar(items, min_score=0.1):
    """Descarta items con novedad_score < min_score."""
    return [p for p in aplicar_scores(items) if p.get("novedad_score", 1.0) >= min_score]

# ── ESTADÍSTICAS ─────────────────────────────────────────────────────
def stats():
    historial = _cargar()
    ahora     = datetime.now(timezone.utc)
    def dias_diff(e):
        dt = datetime.fromisoformat(e["last_published"])
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return (ahora - dt).days
    recientes = sorted(historial.values(), key=lambda e: e["last_published"], reverse=True)[:10]
    return {
        "total":          len(historial),
        "publicados_24h": sum(1 for e in historial.values() if dias_diff(e) < 1),
        "publicados_7d":  sum(1 for e in historial.values() if dias_diff(e) < 7),
        "recientes":      recientes,
    }

# ── LIMPIEZA ─────────────────────────────────────────────────────────
def limpiar(dias=60):
    """Elimina entradas sin publicación en los últimos `dias` días."""
    historial = _cargar()
    corte     = datetime.now(timezone.utc) - timedelta(days=dias)
    antes     = len(historial)
    def _dt(s):
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    historial = {k: v for k, v in historial.items()
                 if _dt(v["last_published"]) >= corte}
    _guardar(historial)
    return {"eliminados": antes - len(historial), "restantes": len(historial)}
