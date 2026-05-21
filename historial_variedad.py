#!/usr/bin/env python3
"""historial_variedad.py — Historial de publicaciones y score de novedad"""

import json
import os
from datetime import datetime, timedelta, timezone

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_FILE = os.path.join(BASE_DIR, "historial.json")

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
def marcar_publicado(item_id, source="", title=""):
    historial = _cargar()
    key       = str(item_id)
    ahora     = datetime.now(timezone.utc).isoformat()
    if key in historial:
        historial[key]["last_published"]   = ahora
        historial[key]["times_published"] += 1
        if title: historial[key]["title"] = title
    else:
        historial[key] = {
            "id": key, "source": source, "title": title,
            "first_seen": ahora, "last_published": ahora, "times_published": 1,
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
        if key in historial:
            historial[key]["last_published"]   = ahora
            historial[key]["times_published"] += 1
            if p.get("title"): historial[key]["title"] = p["title"]
        else:
            historial[key] = {
                "id": key, "source": p.get("source", ""), "title": p.get("title", ""),
                "first_seen": ahora, "last_published": ahora, "times_published": 1,
            }
    _guardar(historial)
    return len(items)

# ── SCORES ───────────────────────────────────────────────────────────
def aplicar_scores(items):
    """Agrega `novedad_score` a cada item y ordena de mayor a menor."""
    historial = _cargar()
    for p in items:
        key = str(p.get("id") or p.get("asin") or "")
        p["novedad_score"] = score_novedad(key, historial)
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
