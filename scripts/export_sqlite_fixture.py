"""Export the SQLite catalogue into a Django fixture for loading into Postgres.

Reads db.sqlite3 with the stdlib sqlite3 driver rather than through Django, so
it keeps working after settings.py has already been switched to Postgres (and
regardless of the search_vector column, which only exists on the Postgres side).

    python scripts/export_sqlite_fixture.py
    python manage.py loaddata catalog/fixtures/catalog.json   # after migrate
"""

import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB = BASE_DIR / "db.sqlite3"
OUT = BASE_DIR / "catalog" / "fixtures" / "catalog.json"

# table -> (django model label, columns to export)
TABLES = [
    ("categories", "catalog.category",
     ["name", "slug", "image_url", "is_active", "created_at"]),
    ("subcategories", "catalog.subcategory",
     ["category_id", "name", "slug", "is_active"]),
    ("products", "catalog.product",
     ["subcategory_id", "name", "slug", "description", "price",
      "compare_at_price", "warranty_years", "rating", "review_count",
      "is_featured", "is_active", "created_at", "updated_at"]),
    ("product_images", "catalog.productimage",
     ["product_id", "image_url", "alt_text", "sort_order", "is_primary"]),
    ("product_variants", "catalog.productvariant",
     ["product_id", "name", "price", "is_active"]),
    ("product_reviews", "catalog.productreview",
     ["product_id", "rating", "review_text", "created_at"]),
    ("collections", "catalog.collection",
     ["name", "slug", "description", "image_url", "is_featured", "is_active",
      "created_at"]),
    ("collection_products", "catalog.collectionproduct",
     ["collection_id", "product_id", "sort_order"]),
]

# sqlite column name -> django field name, where they differ
FIELD_ALIASES = {
    "category_id": "category",
    "subcategory_id": "subcategory",
    "product_id": "product",
    "collection_id": "collection",
}


def main():
    if not DB.exists():
        raise SystemExit(f"No SQLite database at {DB}")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    records = []

    for table, model, columns in TABLES:
        rows = conn.execute(f"SELECT id, {', '.join(columns)} FROM {table}").fetchall()
        for row in rows:
            fields = {}
            for column in columns:
                value = row[column]
                if column.endswith("is_active") or column.startswith("is_"):
                    value = bool(value)
                fields[FIELD_ALIASES.get(column, column)] = value
            records.append({"model": model, "pk": row["id"], "fields": fields})
        print(f"{table:22} {len(rows):>4} rows")

    conn.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, indent=1, default=str), encoding="utf-8")
    print(f"\nWrote {len(records)} records to {OUT.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
