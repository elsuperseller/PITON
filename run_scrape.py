#!/usr/bin/env python3
"""
run_scrape.py — Pipeline diario: ML scraping → historial → output JSON
Usado por GitHub Actions. También corre manualmente:
  python run_scrape.py
  python run_scrape.py --queries "laptop auriculares" --min-discount 20
"""

import argparse
import json
import os
import sys
from datetime import datetime

import scraper_ml
import historial_variedad as hv

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Queries y categorías por defecto
DEFAULT_QUERIES = [
    "laptop", "auriculares inalámbricos", "smart tv", "tablet",
    "smartwatch", "cafetera", "licuadora", "aspiradora",
    "silla gamer", "cámara fotográfica",
]
DEFAULT_CATS = [
    "MLM1055",  # Electrónica
    "MLM1276",  # Hogar y Muebles
    "MLM1459",  # Deportes y Fitness
    "MLM1367",  # Juguetes y Bebés
    "MLM1499",  # Salud y Belleza
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries",      default="", help="Queries separadas por '|'")
    parser.add_argument("--categorias",   default="", help="IDs de categoría separadas por ','")
    parser.add_argument("--min-discount", type=int,   default=20)
    parser.add_argument("--max-results",  type=int,   default=50)
    parser.add_argument("--min-score",    type=float, default=0.1)
    parser.add_argument("--marcar",       action="store_true", help="Marcar resultados como publicados")
    args = parser.parse_args()

    queries    = [q.strip() for q in args.queries.split("|") if q.strip()] or DEFAULT_QUERIES
    categorias = [c.strip() for c in args.categorias.split(",") if c.strip()] or DEFAULT_CATS

    print(f"🚀 Pipeline ML — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", flush=True)
    print(f"   Queries: {len(queries)} | Categorías: {len(categorias)} | Desc≥{args.min_discount}%", flush=True)

    # 1. Scraping
    items = scraper_ml.scrape(
        queries=queries,
        categorias=categorias,
        min_discount=args.min_discount,
        max_per_query=args.max_results,
    )
    print(f"📦 Scraping: {len(items)} ofertas brutas", flush=True)

    # 2. Historial + score de novedad
    items = hv.aplicar_scores(items)
    antes = len(items)
    items = [p for p in items if p.get("novedad_score", 1.0) >= args.min_score]
    print(f"🧠 Historial: {antes} → {len(items)} (min_score={args.min_score})", flush=True)

    # 3. Guardar output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts       = datetime.utcnow().strftime("%Y-%m-%d_%H%M")
    outfile  = os.path.join(OUTPUT_DIR, f"{ts}.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "total": len(items), "items": items}, f,
                  ensure_ascii=False, indent=2)
    print(f"💾 Guardado: output/{ts}.json ({len(items)} ofertas)", flush=True)

    # 4. Marcar como publicados (opcional)
    if args.marcar:
        n = hv.marcar_varios(items)
        print(f"✅ {n} items marcados en historial", flush=True)

    # Stats finales
    s = hv.stats()
    print(f"📊 Historial total: {s['total']} IDs | 7d: {s['publicados_7d']} | 24h: {s['publicados_24h']}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
