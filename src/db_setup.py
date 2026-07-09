"""
db_setup.py
-----------
Creates the PostgreSQL schema and loads all Olist CSV files.
Run once. Safe to re-run (schema uses DROP IF EXISTS).
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Connection ---
DB_URL = "postgresql://_shaidolla@localhost/process_lens"
engine = create_engine(DB_URL)

# --- Create schema ---
print("Creating schema...")
with engine.begin() as conn:
    with open("sql/schema.sql", "r") as f:
        conn.execute(text(f.read()))
print("Schema created.")

# --- Load CSVs ---
OLIST_DIR = "data/raw/olist"

timestamp_cols = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ],
    "reviews": ["review_creation_date"]
}

files = {
    "orders":       "olist_orders_dataset.csv",
    "order_items":  "olist_order_items_dataset.csv",
    "payments":     "olist_order_payments_dataset.csv",
    "reviews":      "olist_order_reviews_dataset.csv",
    "customers":    "olist_customers_dataset.csv",
    "sellers":      "olist_sellers_dataset.csv",
}

for table, filename in files.items():
    path = os.path.join(OLIST_DIR, filename)
    print(f"Loading {table} from {filename}...")
    
    df = pd.read_csv(
        path,
        parse_dates=timestamp_cols.get(table, [])
    )
    
    df.to_sql(table, engine, if_exists="append", index=False)
    print(f"  → {len(df):,} rows loaded into '{table}'")

print("\nAll tables loaded successfully.")