"""
event_log_builder.py
---------------------
Transforms Olist's order-level timestamps into a long-format event log.
One row per event per order (4 events per delivered order).
Output: populates the 'events' table in PostgreSQL.
"""

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql://_shaidolla@localhost/process_lens"
engine = create_engine(DB_URL)

# Load orders — delivered only, with all required timestamps
print("Loading orders from PostgreSQL...")
orders = pd.read_sql("""
    SELECT order_id,
           order_purchase_timestamp,
           order_approved_at,
           order_delivered_carrier_date,
           order_delivered_customer_date
    FROM orders
    WHERE order_status = 'delivered'
      AND order_approved_at IS NOT NULL
      AND order_delivered_carrier_date IS NOT NULL
      AND order_delivered_customer_date IS NOT NULL
""", engine, parse_dates=[
    'order_purchase_timestamp',
    'order_approved_at',
    'order_delivered_carrier_date',
    'order_delivered_customer_date'
])
print(f"  Orders loaded: {len(orders):,}")

# Define stage mapping
stages = [
    ("Order Created",             "order_purchase_timestamp",     "system"),
    ("Order Approved",            "order_approved_at",            "system"),
    ("Picked Packed and Shipped", "order_delivered_carrier_date", "seller"),
    ("Delivered",                 "order_delivered_customer_date","carrier"),
]

# Build event log
print("Building event log...")
events = []
for _, row in orders.iterrows():
    for activity, col, resource in stages:
        ts = row[col]
        if pd.notna(ts):
            events.append({
                "order_id":        row["order_id"],
                "activity":        activity,
                "event_timestamp": ts,
                "resource":        resource
            })

events_df = pd.DataFrame(events)
events_df = events_df.sort_values(["order_id", "event_timestamp"])

# Validate: every order should have exactly 4 events
events_per_order = events_df.groupby("order_id").size()
assert events_per_order.min() == 4, "Some orders have fewer than 4 events!"
assert events_per_order.max() == 4, "Some orders have more than 4 events!"

print(f"  Total events: {len(events_df):,}")
print(f"  Unique orders: {events_df['order_id'].nunique():,}")
print(f"  Events per order: {events_per_order.mean():.1f} (should be 4.0)")

# Load into PostgreSQL
print("Loading into PostgreSQL events table...")
with engine.begin() as conn:
    conn.execute(text("TRUNCATE events;"))
events_df.to_sql("events", engine, if_exists="append", index=False)
print("  Done.")

print("\nEvent log built successfully.")
print(f"  Activities: {sorted(events_df['activity'].unique())}")