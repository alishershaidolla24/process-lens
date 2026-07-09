"""
process_mining.py
-----------------
Discovers the O2C process map from the event log (DFG, performance overlay,
Heuristics Miner) and checks conformance against the discovered reference
model via token-based replay.
Run from project root: python src/process_mining.py
"""

import pm4py
import pandas as pd
from sqlalchemy import create_engine
import os

DB_URL = "postgresql://_shaidolla@localhost/process_lens"
engine = create_engine(DB_URL)

os.makedirs("outputs/models", exist_ok=True)
os.makedirs("outputs/charts", exist_ok=True)

# Load event log from PostgreSQL
print("Loading event log...")
df = pd.read_sql("""
    SELECT
        order_id        AS "case:concept:name",
        activity        AS "concept:name",
        event_timestamp AS "time:timestamp"
    FROM events
    ORDER BY order_id, event_timestamp
""", engine)

print(f"  Rows loaded: {len(df):,}")
print(f"  Unique orders: {df['case:concept:name'].nunique():,}")

df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], utc=True)

df = pm4py.format_dataframe(
    df,
    case_id="case:concept:name",
    activity_key="concept:name",
    timestamp_key="time:timestamp"
)

log = pm4py.convert_to_event_log(df)
print(f"  Event log created: {len(log)} cases\n")

# Directly-follows graph (DFG) discovery
print("Discovering DFG...")
dfg, start_activities, end_activities = pm4py.discover_dfg(log)

pm4py.save_vis_dfg(
    dfg, start_activities, end_activities,
    file_path="outputs/models/dfg_frequency.png"
)
print("  Saved: outputs/models/dfg_frequency.png")

# Performance-weighted DFG — median duration between activities
print("\nDiscovering performance DFG...")
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_vis

dfg_perf = dfg_discovery.apply(
    log,
    variant=dfg_discovery.Variants.PERFORMANCE
)

gviz_perf = dfg_vis.apply(
    dfg_perf,
    log=log,
    variant=dfg_vis.Variants.PERFORMANCE,
    parameters={
        dfg_vis.Variants.PERFORMANCE.value.Parameters.FORMAT: "png",
        dfg_vis.Variants.PERFORMANCE.value.Parameters.AGGREGATION_MEASURE: "median"
    }
)
dfg_vis.save(gviz_perf, "outputs/models/dfg_performance.png")
print("  Saved: outputs/models/dfg_performance.png")

# Heuristics Miner — Petri net (used for conformance checking below)
print("\nRunning Heuristics Miner...")
net, im, fm = pm4py.discover_petri_net_heuristics(log)

pm4py.save_vis_petri_net(
    net, im, fm,
    file_path="outputs/models/petri_net.png"
)
print("  Saved: outputs/models/petri_net.png")

# Process variant analysis
print("\nAnalysing process variants...")
variants = pm4py.get_variants(log)
variants_sorted = sorted(variants.items(), key=lambda x: len(x[1]), reverse=True)

print(f"  Total unique variants: {len(variants_sorted)}")
print(f"\n  Top 5 variants by frequency:")
for i, (variant, cases) in enumerate(variants_sorted[:5]):
    path = " → ".join(variant) if isinstance(variant, tuple) else str(variant)
    pct = len(cases) / len(log) * 100
    print(f"  [{i+1}] {len(cases):,} cases ({pct:.1f}%): {path}")

print("\nProcess maps saved to outputs/models/.")

# Conformance checking — token-based replay against the discovered Petri net
print("\n" + "="*50)
print("CONFORMANCE CHECKING")
print("="*50)

from pm4py.algo.conformance.tokenreplay import algorithm as token_replay

print("\nRunning token-based replay (this may take 1-2 minutes)...")
replayed = token_replay.apply(log, net, im, fm)

fitness_scores = [t["trace_fitness"] for t in replayed]
avg_fitness    = sum(fitness_scores) / len(fitness_scores)
perfect_fit    = sum(1 for f in fitness_scores if f == 1.0)
deviation_rate = 1 - (perfect_fit / len(fitness_scores))

print(f"\n  Cases analysed:          {len(replayed):,}")
print(f"  Average fitness score:   {avg_fitness:.4f}")
print(f"  Cases with perfect fit:  {perfect_fit:,} ({perfect_fit/len(replayed)*100:.1f}%)")
print(f"  Cases with deviations:   {len(replayed)-perfect_fit:,} ({deviation_rate*100:.1f}%)")

import pandas as pd
fitness_df = pd.DataFrame({
    "order_id": [t.get("case_id", i) for i, t in enumerate(replayed)],
    "fitness":  fitness_scores
})
fitness_df.to_csv("outputs/conformance_fitness.csv", index=False)
print(f"\n  Case-level fitness saved: outputs/conformance_fitness.csv")

print(f"\n  Fitness interpretation:")
if avg_fitness >= 0.95:
    print("  → Strong fit. Process follows reference model closely.")
elif avg_fitness >= 0.80:
    print("  → Moderate fit. Notable deviations present — investigate.")
else:
    print("  → Weak fit. Significant process deviations — primary finding.")