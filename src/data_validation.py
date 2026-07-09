"""
data_validation.py
------------------
Checks the loaded Olist data for quality issues.
Run after db_setup.py. Documents findings in data_quality_log.md.
"""

import pandas as pd
from sqlalchemy import create_engine

DB_URL = "postgresql://_shaidolla@localhost/process_lens"
engine = create_engine(DB_URL)

print("=" * 50)
print("DATA VALIDATION REPORT")
print("=" * 50)

df = pd.read_sql("""
    SELECT order_id,
           order_status,
           order_purchase_timestamp,
           order_approved_at,
           order_delivered_carrier_date,
           order_delivered_customer_date,
           order_estimated_delivery_date
    FROM orders
""", engine)

total = len(df)
print(f"\nTotal orders in dataset: {total:,}")

# 1. Order status breakdown
print("\n--- Order status breakdown ---")
print(df['order_status'].value_counts())

# 2. Null timestamps (delivered orders only)
delivered = df[df['order_status'] == 'delivered']
print(f"\n--- Null timestamps (delivered orders only, n={len(delivered):,}) ---")
for col in ['order_approved_at', 'order_delivered_carrier_date',
            'order_delivered_customer_date', 'order_estimated_delivery_date']:
    nulls = delivered[col].isna().sum()
    print(f"  {col}: {nulls:,} nulls ({nulls/len(delivered)*100:.2f}%)")

# 3. Chronological violations
print("\n--- Chronological violations ---")
violations = (
    (delivered['order_approved_at'] < delivered['order_purchase_timestamp']) |
    (delivered['order_delivered_carrier_date'] < delivered['order_approved_at']) |
    (delivered['order_delivered_customer_date'] < delivered['order_delivered_carrier_date'])
).sum()
print(f"  Orders with timestamps out of sequence: {violations:,}")

# 4. OTD rate
print("\n--- OTD Rate ---")
delivered_clean = delivered.dropna(subset=[
    'order_delivered_customer_date', 'order_estimated_delivery_date'
])
late = (delivered_clean['order_delivered_customer_date'] >
        delivered_clean['order_estimated_delivery_date']).sum()
otd = 1 - late / len(delivered_clean)
print(f"  Total delivered (clean): {len(delivered_clean):,}")
print(f"  Late orders: {late:,} ({late/len(delivered_clean)*100:.1f}%)")
print(f"  OTD rate: {otd*100:.1f}%")

# 5. Extreme cycle time outliers
delivered_clean = delivered_clean.copy()
delivered_clean['total_days'] = (
    delivered_clean['order_delivered_customer_date'] -
    delivered_clean['order_purchase_timestamp']
).dt.days
p95 = delivered_clean['total_days'].quantile(0.95)
extreme = (delivered_clean['total_days'] > 3 * p95).sum()
print(f"\n--- Extreme outliers (>3× p95 cycle time of {p95:.0f} days) ---")
print(f"  Extreme outliers: {extreme:,}")