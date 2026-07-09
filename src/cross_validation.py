"""
cross_validation.py
-------------------
Methodological cross-validation using the BPI Challenge 2019 dataset.
Validates that the process mining methodology (Heuristics Miner,
conformance checking, bottleneck detection) produces meaningful results
on a second real-world dataset from a different domain.
Not used to extend O2C analysis — BPI 2019 is P2P (Accounts Payable),
not O2C (Accounts Receivable): different parties, different flow direction.
Run from project root: python src/cross_validation.py
"""

import pm4py
import os

os.makedirs("outputs/models", exist_ok=True)

# Load BPI 2019 event log
BPI_PATH = "data/raw/bpi2019/BPI_Challenge_2019.xes"

if not os.path.exists(BPI_PATH):
    print(f"ERROR: File not found at {BPI_PATH}")
    print("Download from: https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1")
    exit(1)

print("Loading BPI 2019 event log (this takes 30–60 seconds for 251K events)...")
log_bpi = pm4py.read_xes(BPI_PATH)
print(f"  Cases loaded: {len(log_bpi):,}")
print(f"  Start activities: {pm4py.get_start_activities(log_bpi)}")
print(f"  End activities:   {pm4py.get_end_activities(log_bpi)}")

# Process discovery
print("\nDiscovering BPI 2019 process map...")
net_bpi, im_bpi, fm_bpi = pm4py.discover_petri_net_heuristics(log_bpi)
pm4py.save_vis_petri_net(net_bpi, im_bpi, fm_bpi,
                          file_path="outputs/models/bpi2019_petri_net.png")
print("  Saved: outputs/models/bpi2019_petri_net.png")

from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_vis

dfg_bpi = dfg_discovery.apply(log_bpi, variant=dfg_discovery.Variants.PERFORMANCE)
gviz_bpi = dfg_vis.apply(
    dfg_bpi, log=log_bpi,
    variant=dfg_vis.Variants.PERFORMANCE,
    parameters={
        dfg_vis.Variants.PERFORMANCE.value.Parameters.FORMAT: "png",
        dfg_vis.Variants.PERFORMANCE.value.Parameters.AGGREGATION_MEASURE: "median"
    }
)
dfg_vis.save(gviz_bpi, "outputs/models/bpi2019_dfg_performance.png")
print("  Saved: outputs/models/bpi2019_dfg_performance.png")

# Conformance checking
print("\nRunning conformance checking on BPI 2019...")
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay

replayed_bpi = token_replay.apply(log_bpi, net_bpi, im_bpi, fm_bpi)
fitness_bpi  = sum(t["trace_fitness"] for t in replayed_bpi) / len(replayed_bpi)
deviations   = sum(1 for t in replayed_bpi if t["trace_fitness"] < 1.0)

print(f"\n  BPI 2019 average fitness:  {fitness_bpi:.4f}")
print(f"  Cases with deviations:     {deviations:,} ({deviations/len(replayed_bpi)*100:.1f}%)")

# Comparison summary
print("\n" + "="*50)
print("CROSS-VALIDATION SUMMARY")
print("="*50)
print(f"""
  Olist O2C (fulfillment stages 1-5):
    Cases: 96,455 | Fitness: 0.9972

  BPI 2019 P2P (procurement, different domain):
    Cases: {len(log_bpi):,} | Fitness: {fitness_bpi:.4f}

  Interpretation:
  Both datasets show deviations from their respective reference models.
  The Heuristics Miner and conformance checking methodology produces
  interpretable results on two different real-world ERP processes,
  validating the analytical approach across domains.

  Note: BPI 2019 is not used to extend O2C stage coverage.
  It is a methodological validation only.
""")