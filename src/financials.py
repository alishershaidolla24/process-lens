import pandas as pd
import numpy as np
from sqlalchemy import create_engine

DB_URL = "postgresql://_shaidolla@localhost/process_lens"
engine = create_engine(DB_URL)

COST_PER_CASE = 14.80
RECOVERY_COST_PER_LATE = 22
WACC = 0.09
IMPLEMENTATION_COST = 45000
YEAR1_REALIZATION = 0.70
HORIZON_YEARS = 3

print("Loading order metrics...")
orders = pd.read_sql("SELECT is_late FROM order_metrics", engine)

total_orders = len(orders)
late_orders = int(orders["is_late"].sum())
late_rate = late_orders / total_orders

print(f"  Total orders: {total_orders:,}")
print(f"  Late orders: {late_orders:,} ({late_rate*100:.1f}%)")

annual_recovery_cost = late_orders * RECOVERY_COST_PER_LATE
print(f"  Current annual cost of late deliveries: ${annual_recovery_cost:,.2f}")


def project_npv(late_rate_improvement_pp, label):
    new_late_rate = max(late_rate - late_rate_improvement_pp, 0)
    orders_avoided = round((late_rate - new_late_rate) * total_orders)
    annual_savings = orders_avoided * RECOVERY_COST_PER_LATE

    cash_flows = [-IMPLEMENTATION_COST]
    for year in range(1, HORIZON_YEARS + 1):
        realization = YEAR1_REALIZATION if year == 1 else 1.0
        cash_flows.append(annual_savings * realization)

    npv = sum(cf / (1 + WACC) ** i for i, cf in enumerate(cash_flows))
    payback_years = IMPLEMENTATION_COST / annual_savings if annual_savings > 0 else float("inf")

    print(f"\n  {label}:")
    print(f"    Late rate: {late_rate*100:.1f}% -> {new_late_rate*100:.1f}%")
    print(f"    Orders avoided/year: {orders_avoided:,}")
    print(f"    Annual savings: ${annual_savings:,.2f}")
    print(f"    3-year NPV @ {WACC*100:.0f}% WACC: ${npv:,.2f}")
    print(f"    Payback: {payback_years:.1f} years")

    return {
        "scenario": label,
        "new_late_rate": round(new_late_rate * 100, 1),
        "orders_avoided": orders_avoided,
        "annual_savings": round(annual_savings, 2),
        "npv": round(npv, 2),
        "payback_years": round(payback_years, 2),
    }

print("\nSensitivity analysis — late-rate improvement scenarios")
scenarios = [
    project_npv(0.01, "Pessimistic (1pp late-rate reduction)"),
    project_npv(0.03, "Base case (3pp late-rate reduction)"),
    project_npv(0.05, "Optimistic (5pp late-rate reduction)"),
]

scenarios_df = pd.DataFrame(scenarios)
scenarios_df.to_csv("outputs/reports/financial_sensitivity.csv", index=False)
print(f"\n  Sensitivity table saved: outputs/reports/financial_sensitivity.csv")