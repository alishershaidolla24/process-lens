"""
statistical_tests.py
--------------------
Statistical bottleneck validation.

Tests:
  1. Mann-Whitney U — is each stage's duration significantly different
     between late and on-time orders? (non-parametric, correct for
     right-skewed cycle time distributions — do NOT use t-test here)
  2. Chi-squared — is seller region significantly associated with late rate?

Reports p-value AND effect size for each test.
A p-value alone doesn't tell you if the difference matters in practice.
Effect size (rank-biserial correlation) tells you the magnitude.

Run from project root: python src/statistical_tests.py
"""

import pandas as pd
import numpy as np
from scipy import stats
from sqlalchemy import create_engine

DB_URL = "postgresql://_shaidolla@localhost/process_lens"
engine  = create_engine(DB_URL)

print("Loading stage durations with OTD flag...")

df = pd.read_sql("""
    WITH stage_durations AS (
        SELECT
            e.order_id,
            e.activity,
            EXTRACT(EPOCH FROM (
                e.event_timestamp -
                LAG(e.event_timestamp) OVER (
                    PARTITION BY e.order_id ORDER BY e.event_timestamp
                )
            )) / 86400.0 AS days_elapsed
        FROM events e
    )
    SELECT
        sd.order_id,
        sd.activity,
        sd.days_elapsed,
        om.is_late,
        om.seller_state,
        om.customer_state
    FROM stage_durations sd
    JOIN order_metrics om ON sd.order_id = om.order_id
    WHERE sd.days_elapsed IS NOT NULL
      AND sd.days_elapsed > 0
""", engine)

print(f"  Rows loaded: {len(df):,}")
print(f"  Activities: {sorted(df['activity'].unique())}\n")

# Test 1: Mann-Whitney U per stage (non-parametric — cycle times are
# right-skewed, so the t-test's normality assumption doesn't hold)
print("=" * 55)
print("TEST 1: Mann-Whitney U — Stage Duration by OTD Status")
print("=" * 55)

results = []

for activity in df["activity"].unique():
    grp      = df[df["activity"] == activity].dropna(subset=["days_elapsed"])
    on_time  = grp[grp["is_late"] == False]["days_elapsed"].values
    late     = grp[grp["is_late"] == True]["days_elapsed"].values

    if min(len(on_time), len(late)) < 30:
        print(f"  {activity}: SKIPPED — insufficient sample (n_late={len(late)})")
        continue

    stat, p = stats.mannwhitneyu(on_time, late, alternative="less")

    n1, n2      = len(on_time), len(late)
    effect_size = 1 - (2 * stat) / (n1 * n2)

    results.append({
        "activity":           activity,
        "n_on_time":          n1,
        "n_late":             n2,
        "median_on_time_d":   round(float(np.median(on_time)), 3),
        "median_late_d":      round(float(np.median(late)), 3),
        "delta_d":            round(float(np.median(late) - np.median(on_time)), 3),
        "p_value":            round(p, 6),
        "significant":        p < 0.05,
        "effect_size":        round(effect_size, 3),
        "effect_category":    ("large"  if abs(effect_size) > 0.5 else
                               "medium" if abs(effect_size) > 0.3 else "small"),
    })

results_df = pd.DataFrame(results).sort_values("delta_d", ascending=False)

print(f"\n{'Activity':<30} {'Median OT':>10} {'Median L':>9} {'Delta':>7} "
      f"{'p-value':>10} {'Sig':>5} {'Effect':>8} {'Category':>8}")
print("-" * 90)
for _, row in results_df.iterrows():
    sig = "✓" if row["significant"] else "✗"
    print(f"  {row['activity']:<28} {row['median_on_time_d']:>10.3f} "
          f"{row['median_late_d']:>9.3f} {row['delta_d']:>7.3f} "
          f"{row['p_value']:>10.6f} {sig:>5} {row['effect_size']:>8.3f} "
          f"{row['effect_category']:>8}")

results_df.to_csv("outputs/mann_whitney_results.csv", index=False)
print(f"\n  Full results saved: outputs/mann_whitney_results.csv")

# Test 2: Chi-squared - seller region vs late rate
print("\n" + "=" * 55)
print("TEST 2: Chi-squared — Seller Region vs Late Rate")
print("=" * 55)

orders_df = pd.read_sql("""
    SELECT seller_state, is_late
    FROM order_metrics
    WHERE seller_state IS NOT NULL
""", engine)

contingency = pd.crosstab(orders_df["seller_state"], orders_df["is_late"])
chi2, p_chi, dof, expected = stats.chi2_contingency(contingency)

n        = contingency.values.sum()
cramers_v = np.sqrt(chi2 / (n * (min(contingency.shape) - 1)))

print(f"\n  Chi-squared statistic: {chi2:.2f}")
print(f"  Degrees of freedom:    {dof}")
print(f"  p-value:               {p_chi:.2e}")
print(f"  Significant (p<0.05):  {'Yes ✓' if p_chi < 0.05 else 'No ✗'}")
print(f"  Cramér's V:            {cramers_v:.4f}")
print(f"  Effect category:       {'large' if cramers_v > 0.35 else 'medium' if cramers_v > 0.15 else 'small'}")

state_otd = orders_df.groupby("seller_state")["is_late"].agg(
    total="count", late="sum"
).reset_index()
state_otd["late_pct"] = (state_otd["late"] / state_otd["total"] * 100).round(1)
state_otd = state_otd[state_otd["total"] >= 50].sort_values("late_pct", ascending=False)

print(f"\n  Top 5 seller states by late rate (min 50 orders):")
for _, row in state_otd.head(5).iterrows():
    print(f"    {row['seller_state']}: {row['late_pct']}% late "
          f"({int(row['late'])} / {int(row['total'])} orders)")