import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

DB_URL = "postgresql://_shaidolla@localhost/process_lens"
engine = create_engine(DB_URL)

print("Loading weekly order volume and late rate...")
df = pd.read_sql("""
    SELECT
        DATE_TRUNC('week', o.order_purchase_timestamp) AS week,
        COUNT(*) AS n_orders,
        SUM(CASE WHEN om.is_late THEN 1 ELSE 0 END) AS n_late
    FROM order_metrics om
    JOIN orders o ON om.order_id = o.order_id
    GROUP BY week
    ORDER BY week
""", engine)

df["late_rate"] = df["n_late"] / df["n_orders"]
df = df[df["n_orders"] >= 30].reset_index(drop=True)
print(f"  Weeks with enough volume for stable control limits: {len(df)}")

BASELINE_WEEKS = 12
baseline = df.tail(BASELINE_WEEKS)
p_bar = baseline["n_late"].sum() / baseline["n_orders"].sum()
print(f"  Baseline window: last {BASELINE_WEEKS} weeks "
      f"({baseline['week'].min().date()} to {baseline['week'].max().date()})")
print(f"  Baseline late rate (center line): {p_bar*100:.2f}%")

first_12 = df.head(12)
first_12_rate = first_12["n_late"].sum() / first_12["n_orders"].sum()
print(f"  Late rate, first 12 weeks: {first_12_rate*100:.2f}%")
print(f"  Late rate, last 12 weeks:  {p_bar*100:.2f}%")

df["ucl"] = p_bar + 3 * np.sqrt(p_bar * (1 - p_bar) / df["n_orders"])
df["lcl"] = (p_bar - 3 * np.sqrt(p_bar * (1 - p_bar) / df["n_orders"])).clip(lower=0)

out_of_control = df[(df["late_rate"] > df["ucl"]) | (df["late_rate"] < df["lcl"])]
print("\n  Flagged weeks (out of control):")
for _, row in out_of_control.iterrows():
    print(f"    {row['week'].date()}: {row['late_rate']*100:.1f}% "
          f"(limits {row['lcl']*100:.1f}%-{row['ucl']*100:.1f}%)")
print(f"  Weeks outside control limits: {len(out_of_control)} out of {len(df)}")

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(df["week"], df["late_rate"] * 100, marker="o", markersize=3, label="Weekly late rate")
ax.plot(df["week"], df["ucl"] * 100, linestyle="--", color="red", label="Upper control limit")
ax.plot(df["week"], df["lcl"] * 100, linestyle="--", color="red", label="Lower control limit")
ax.axhline(p_bar * 100, color="gray", label="Center line (baseline)")
ax.axvspan(baseline["week"].min(), baseline["week"].max(), color="gray", alpha=0.15,
           label="Baseline window")
ax.set_ylabel("Late rate (%)")
ax.set_title("O2C Late Delivery Rate -- Control Chart (p-Chart)")
ax.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("outputs/charts/control_chart.png", dpi=150)
plt.close()

print("\nControl chart saved: outputs/charts/control_chart.png")