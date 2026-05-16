#!/usr/bin/env python3
"""
run_scrape.py — Pipeline diario: scraping → historial → output JSON
Usado por GitHub Actions (.github/workflows/scrape.yml). También corre manualmente.

═══════════════════════════════════════════════════════════
FUENTES DE DATOS
═══════════════════════════════════════════════════════════
  ML (Mercado Libre) — siempre activo
    Queries por keyword + categorías MLM
    Filtros: descuento mínimo, score de novedad (historial)

  Amazon — opcional vía --amazon-ranking
    bestsellers       : los más vendidos por categoría (actualizado c/hora)
    new-releases      : lanzamientos recientes con mayor demanda
    movers-and-shakers: mayor mejora de BSR en las últimas 24 h
    Requiere Playwright: pip install playwright && playwright install chrome

═══════════════════════════════════════════════════════════
PIPELINE DE FILTROS (en orden)
═══════════════════════════════════════════════════════════
  1. Scraping bruto (ML + Amazon rankings si --amazon-ranking está activo)
  2. Historial de novedad  — score 0.0-1.0 según días desde
     última publicación; descarta si score < --min-score
     (los ASINs de Amazon se tratan igual que IDs de ML)
  3. Guardado en output/YYYY-MM-DD_HHMM.json
  4. (Opcional) Marcado en historial — --marcar

Nota: los filtros de descuento, "Termina en" y dedup por ASIN
se aplican en servidor.py cuando se usa la app interactiva.
En el pipeline (este archivo) el filtro de descuento es --min-discount
y la dedup la hace scrape_ranking() internamente.

═══════════════════════════════════════════════════════════
EJEMPLOS DE USO
═══════════════════════════════════════════════════════════
  # Solo ML (default — compatible con GitHub Actions actual)
  python run_scrape.py

  # ML + Best Sellers Amazon en categorías default
  python run_scrape.py --amazon-ranking bestsellers

  # ML + New Releases en categorías específicas
  python run_scrape.py --amazon-ranking new-releases \\
      --amazon-cats electronics,sports,toys

  # ML + Movers & Shakers, 1 página por categoría
  python run_scrape.py --amazon-ranking movers-and-shakers \\
      --amazon-pages 1

  # Solo ML con parámetros personalizados
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

# ── Queries y categorías ML por defecto ─────────────────────────────
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


def _items_amazon_ranking(tipo, cats_arg, pages):
    """
    Scrapea rankings de Amazon y convierte los ASINs al formato de item
    compatible con historial_variedad (requiere campo 'id').

    Parámetros
    ----------
    tipo      : "bestsellers" | "new-releases" | "movers-and-shakers"
    cats_arg  : str con slugs separados por coma, o "" para usar default
    pages     : int, páginas por categoría (max recomendado: 2)

    Retorna lista de dicts con al menos {id, source, title}.
    El enriquecimiento de precio/imagen se hace en servidor.py;
    aquí sólo necesitamos el ID para el historial de novedad.
    """
    try:
        import scraper_amazon as _az
    except ImportError:
        print("  ⚠️  scraper_amazon no disponible — omitiendo Amazon rankings", flush=True)
        return []

    cats = [c.strip() for c in cats_arg.split(",") if c.strip()] or None
    asins = _az.scrape_ranking(tipo=tipo, categorias=cats, pages=pages)
    return [{"id": a, "asin": a, "source": f"amazon_{tipo}", "title": "",
             "descuento_pct": 0, "price_discounted": 0} for a in asins]


def main():
    parser = argparse.ArgumentParser(description="Pipeline de scraping SuperSeller")

    # ── Flags ML ────────────────────────────────────────────────────
    parser.add_argument("--queries",      default="",
                        help="Queries ML separadas por '|'")
    parser.add_argument("--categorias",   default="",
                        help="IDs de categoría ML separadas por ','")
    parser.add_argument("--min-discount", type=int,   default=20,
                        help="Descuento mínimo %% para ML (default: 20)")
    parser.add_argument("--max-results",  type=int,   default=50,
                        help="Máx. resultados por query ML (default: 50)")
    parser.add_argument("--min-score",    type=float, default=0.1,
                        help="Score mínimo de novedad 0.0-1.0 (default: 0.1)")
    parser.add_argument("--marcar",       action="store_true",
                        help="Marcar resultados como publicados en historial")

    # ── Flags Amazon Rankings ────────────────────────────────────────
    parser.add_argument("--amazon-ranking", default="", metavar="TIPO",
                        help=("Activa scraping de rankings Amazon. "
                              "TIPO: bestsellers | new-releases | movers-and-shakers"))
    parser.add_argument("--amazon-cats",    default="",
                        help=("Slugs de categoría Amazon separados por coma. "
                              "Omitir = usar RANKING_CATEGORIAS_DEFAULT. "
                              "Ej: electronics,sports,toys"))
    parser.add_argument("--amazon-pages",   type=int, default=2,
                        help=("Páginas por categoría Amazon (default: 2 = 100 productos). "
                              "Cada página tiene 50 productos."))

    args = parser.parse_args()

    ts_inicio = datetime.utcnow()
    print(f"🚀 Pipeline SuperSeller — {ts_inicio.strftime('%Y-%m-%d %H:%M UTC')}", flush=True)

    # ── 1a. Scraping ML ─────────────────────────────────────────────
    queries    = [q.strip() for q in args.queries.split("|") if q.strip()] or DEFAULT_QUERIES
    categorias = [c.strip() for c in args.categorias.split(",") if c.strip()] or DEFAULT_CATS

    print(f"   ML → {len(queries)} queries | {len(categorias)} cats | desc≥{args.min_discount}%", flush=True)
    items = scraper_ml.scrape(
        queries=queries,
        categorias=categorias,
        min_discount=args.min_discount,
        max_per_query=args.max_results,
    )
    print(f"📦 ML: {len(items)} ofertas brutas", flush=True)

    # ── 1b. Scraping Amazon Rankings (opcional) ──────────────────────
    if args.amazon_ranking:
        tipo = args.amazon_ranking.strip().lower()
        print(f"📊 Amazon {tipo} → cats={args.amazon_cats or 'default'} | {args.amazon_pages} págs c/u", flush=True)
        az_items = _items_amazon_ranking(tipo, args.amazon_cats, args.amazon_pages)
        print(f"📦 Amazon {tipo}: {len(az_items)} ASINs", flush=True)
        items.extend(az_items)

    print(f"📦 Total bruto: {len(items)} items", flush=True)

    # ── 2. Historial + score de novedad ─────────────────────────────
    # Aplica a ML y Amazon por igual — dedup por ID antes de guardar
    items = hv.aplicar_scores(items)
    antes = len(items)
    items = [p for p in items if p.get("novedad_score", 1.0) >= args.min_score]
    print(f"🧠 Historial: {antes} → {len(items)} (min_score={args.min_score})", flush=True)

    # ── 3. Guardar output ────────────────────────────────────────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts      = ts_inicio.strftime("%Y-%m-%d_%H%M")
    outfile = os.path.join(OUTPUT_DIR, f"{ts}.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "total": len(items), "items": items}, f,
                  ensure_ascii=False, indent=2)
    print(f"💾 Guardado: output/{ts}.json ({len(items)} items)", flush=True)

    # ── 4. Marcar como publicados (opcional) ─────────────────────────
    if args.marcar:
        n = hv.marcar_varios(items)
        print(f"✅ {n} items marcados en historial", flush=True)

    # ── Stats finales ────────────────────────────────────────────────
    s = hv.stats()
    print(f"📊 Historial total: {s['total']} IDs | 7d: {s['publicados_7d']} | 24h: {s['publicados_24h']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
