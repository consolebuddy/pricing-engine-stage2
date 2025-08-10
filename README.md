# Donizo Material Scraper (Stage 2)

Clean, modular scraper that pulls renovation material prices from major French suppliers (e.g., Leroy Merlin, Castorama, ManoMano) and outputs developer-friendly JSON/CSV for the pricing engine.

## Features
- **Modular**: All site/category behavior lives in `config/scraper_config.yaml`.
- **Pagination / Infinite Scroll**: Static pages via `next_selector`; dynamic pages via Playwright scrolling.
- **Variations / Grouped Listings**: Optional `variation_badges` selector duplicates base item with variation suffix.
- **Anti-bot hygiene**: Rotating UA (configurable), polite jittered delays, optional Playwright.
- **Output**: `/data/materials.json` and `/data/materials.csv` plus versioned snapshots in `/data/history/`.
- **Fields per product**: name, category, price, currency, URL, brand, pack size, `updated_at` (ISO 8601), `source`, `image_url`, `availability`, `supplier`.
- **Bonus**: Simulated API (FastAPI) + price-comparison ready structure + vector-friendly fields.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install
```

## Run

```bash
cd donizo-material-scraper
python scraper.py --config config/scraper_config.yaml --out data
# Only specific site:
python scraper.py --site leroy_merlin
# Force dynamic mode (if configured):
python scraper.py --site manomano --dynamic
```

## Output
- `data/materials.json` (latest)
- `data/materials.csv`
- `data/history/materials_YYYYMMDDTHHMMSSZ.json` (versioned snapshot)

### JSON record (example)
```json
{
  "id": "Leroy Merlin::tiles::Carrelage sol grès cérame 60x60",
  "product_name": "Carrelage sol grès cérame 60x60",
  "category": "tiles",
  "price": 18.9,
  "currency": "EUR",
  "product_url": "https://www.leroymerlin.fr/produit/...",
  "brand": "Sensea",
  "pack_size": "1.2 m² / boîte",
  "updated_at": "2025-08-10T00:00:00+00:00",
  "source": "https://www.leroymerlin.fr/cat/produits/carrelage-et-parquet/...",
  "image_url": "https://.../image.jpg",
  "availability": "in_stock",
  "supplier": "Leroy Merlin",
  "supplier_site": "https://www.leroymerlin.fr"
}
```

## Logic, Assumptions & Anti-bot
- **Normalization**: `price` parsed as float; `currency` default `EUR` if none detected.
- **Availability**: simple heuristic on stock text; extend per-site for reliability.
- **Variations**: any `variation_badges` create derivative items per variant.
- **Anti-bot**: polite jitter, session reuse, desktop UA; for production add proxy rotation, exponential backoff, and request budgets per site.
- **Pagination**: static via `pagination.next_selector`; dynamic via `pagination.scrolls` + `pagination.wait`.

## Product Variations & Grouped Listings
Some cards represent a family (sizes/colors). We emit distinct variant rows to preserve pricing per option. Further enrichment can follow the product page to extract canonical variant JSON.

## Tests
`tests/test_scraper.py` validates helpers like price normalization and whitespace cleaning.

```bash
pytest -q
```

## Bonus: Simulated API
```bash
pip install fastapi uvicorn
python -m uvicorn api.server:app --reload --port 8080
# GET /materials
# GET /materials/tiles?supplier=Leroy%20Merlin
```

## Price Comparison
With `supplier`, `category`, and normalized `product_name`, building a min/median/max comparator across suppliers is straightforward (groupby product key).

## Vector-DB Ready
Add a field like `embedding_text = f"{brand} {product_name} {category} {pack_size}"` before indexing into pgvector/Chroma. The JSON layout is flat for easy mapping.

## Auto-sync Proposal
- **Monthly**: cron/Actions job runs scraper, stores versioned JSON in object storage, triggers diff report.
- **Near real-time**: smaller per-category deltas during business hours with alerting on price spikes and OOS transitions.

### Ethics & Compliance
Respect robots.txt, TOS, and site rate limits. Obtain permission for sustained crawling and consider official APIs when available.