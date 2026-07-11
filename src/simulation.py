import simpy
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

DB_URL = "postgresql://_shaidolla@localhost/process_lens"
engine = create_engine(DB_URL)

N_ORDERS = 10000
np.random.seed(42)

print("Loading per-order stage durations and promise windows...")
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
        EXTRACT(EPOCH FROM (
            o.order_estimated_delivery_date - o.order_purchase_timestamp
        )) / 86400.0 AS promise_days
    FROM stage_durations sd
    JOIN orders o ON sd.order_id = o.order_id
    WHERE sd.days_elapsed IS NOT NULL
""", engine)

violation_orders = df.loc[df["days_elapsed"] < 0, "order_id"].unique()
df = df[~df["order_id"].isin(violation_orders)]
print(f"  Excluded {len(violation_orders):,} orders with chronological violations")

wide = df.pivot_table(
    index=["order_id", "promise_days"], columns="activity", values="days_elapsed"
).reset_index()
wide = wide.dropna(subset=["Order Approved", "Picked Packed and Shipped", "Delivered"])
print(f"  Orders with complete stage data: {len(wide):,}")

direct_late_rate = 1 - (
    (wide["Order Approved"] + wide["Picked Packed and Shipped"] + wide["Delivered"])
    > wide["promise_days"]
).mean()
print(f"  Direct OTD, full population, no bootstrap: {direct_late_rate*100:.1f}%")


def simulate_order(env, durations, idx, results):
    total = 0.0
    for duration in durations:
        yield env.timeout(duration)
        total += duration
    results[idx] = total


def run_simulation(sample):
    env = simpy.Environment()
    results = np.zeros(len(sample))
    for idx, (_, row) in enumerate(sample.iterrows()):
        durations = [row["Order Approved"], row["Picked Packed and Shipped"], row["Delivered"]]
        env.process(simulate_order(env, durations, idx, results))
    env.run()
    return results


def run_as_is(n_orders):
    sample = wide.sample(n=n_orders, replace=True)
    total = run_simulation(sample)
    otd = 1 - (total > sample["promise_days"].values).mean()
    return otd, sample, total


print("\nRunning as-is simulation...")
as_is_otd, as_is_sample, as_is_total = run_as_is(N_ORDERS)

print(f"  Simulated median cycle time: {np.median(as_is_total):.2f} days")
print(f"  Simulated OTD rate: {as_is_otd*100:.1f}%")
print(f"  Observed OTD rate: 91.9%")
print(f"  Calibration delta: {abs(as_is_otd*100 - 91.9):.1f}pp")

SHRINK_FACTOR = 0.70  # assumption 

print("\nRunning to-be simulation (improved carrier delivery)...")
to_be_sample = as_is_sample.copy()
to_be_sample["Delivered"] = to_be_sample["Delivered"] * SHRINK_FACTOR
to_be_total = run_simulation(to_be_sample)
to_be_otd = 1 - (to_be_total > to_be_sample["promise_days"].values).mean()

improvement_pp = (to_be_otd - as_is_otd) * 100

print(f"  Simulated median cycle time: {np.median(to_be_total):.2f} days")
print(f"  Simulated OTD rate: {to_be_otd*100:.1f}%")
print(f"  OTD improvement vs as-is: {improvement_pp:.1f}pp")

results_df = pd.DataFrame({
    "scenario": ["as_is", "to_be"],
    "median_cycle_days": [np.median(as_is_total), np.median(to_be_total)],
    "otd_rate": [as_is_otd, to_be_otd],
})
results_df.to_csv("outputs/reports/simulation_results.csv", index=False)
print(f"\n  Results saved: outputs/reports/simulation_results.csv")

def run_replications(n_orders, n_reps=20, shrink_factor=None):
    otd_rates = []
    for _ in range(n_reps):
        sample = wide.sample(n=n_orders, replace=True)
        if shrink_factor:
            sample = sample.copy()
            sample["Delivered"] = sample["Delivered"] * shrink_factor
        total = run_simulation(sample)
        otd = 1 - (total > sample["promise_days"].values).mean()
        otd_rates.append(otd)
    return np.array(otd_rates)


print("\nRunning replications for confidence intervals...")
as_is_reps = run_replications(2000, n_reps=20)
to_be_reps = run_replications(2000, n_reps=20, shrink_factor=SHRINK_FACTOR)

as_is_mean, as_is_ci = as_is_reps.mean(), 1.96 * as_is_reps.std() / np.sqrt(len(as_is_reps))
to_be_mean, to_be_ci = to_be_reps.mean(), 1.96 * to_be_reps.std() / np.sqrt(len(to_be_reps))

print(f"  As-is OTD:  {as_is_mean*100:.1f}% ± {as_is_ci*100:.1f}pp (95% CI)")
print(f"  To-be OTD:  {to_be_mean*100:.1f}% ± {to_be_ci*100:.1f}pp (95% CI)")