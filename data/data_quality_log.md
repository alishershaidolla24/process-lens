# Data Quality Log & Project Scope

## Section 1: Scope Statement

**Date written:** 07.07.26
**Written before any data analysis:** Yes

### Business Question
Where in the Olist O2C fulfillment process (stages 1–5) are delays 
concentrated, what is their financial cost, and what intervention 
reduces them most efficiently?

### Process Scope
- IN SCOPE: Order Created → Order Approved → Picked/Packed/Shipped → Delivered
- OUT OF SCOPE: Invoice sent, payment received (stages 6–7)
  - Reason: No public O2C dataset provides these with clean timestamps
  - In a real engagement: AR/billing module data would fill these stages

### KPIs
**Primary:**
- OTD rate (%) — on-time delivery rate across all orders
- End-to-end cycle time (days, median and 90th percentile)

**Secondary:**
- Cycle time per stage (median + 90th percentile)
- Conformance fitness score (from pm4py)
- % cases deviating from reference model

**Financial:**
- Cost per order (by seller_state → customer_state route)
- Annual cost of delays
- 3-year NPV of improvement scenario

**Predictive:**
- AUC-ROC of bottleneck classifier
- Precision and recall at selected threshold

### Pre-Committed Success Criteria
These are defined NOW, before analysis, to prevent post-hoc rationalisation:

1. At least one stage where Mann-Whitney U p < 0.05 with medium or large effect
2. Conformance fitness < 1.0 (expected — documents deviation magnitude)
3. SimPy as-is OTD within ±2 pp of observed OTD (calibration check)
4. SimPy to-be OTD improvement ≥ 8 pp at base case
5. Classifier AUC-ROC > 0.70 on held-out test set
6. NPV positive under base and optimistic scenarios

---

## Section 2: Data Quality Log — Initial Load

**Date:** 2026-07-07
**Script run:** `python src/data_validation.py`

| Issue | Count | Decision | Reason |
|-------|-------|----------|--------|
| Non-delivered orders | 2,963 | Exclude | Only completed O2C cycles are in scope (delivered only) |
| Null `order_approved_at` | 14 | Exclude | Cannot construct Approval event — case unusable for stage analysis |
| Null `order_delivered_carrier_date` | 2 | Exclude | Cannot construct Shipped event |
| Null `order_delivered_customer_date` | 8 | Exclude | Cannot compute OTD or Delivered event |
| Chronological violations | 1,373 | Exclude | Timestamps out of sequence — likely system clock errors or data entry issues; 1.4% of delivered orders |
| Extreme outliers (>3× p95 of 29 days) | 79 | Keep with flag | Real edge cases; included in dataset but excluded from median/percentile calculations |

**Baseline OTD rate (pre-analysis):** 91.9% (7,826 late orders out of 96,470 clean delivered)
**Late order rate:** 8.1%
**Usable delivered orders after cleaning:** ~95,081
*(96,478 delivered − 14 null approved − 2 null carrier − 8 null customer − 1,373 chronological violations)*

**Order status breakdown (full dataset):**
| Status | Count |
|--------|-------|
| delivered | 96,478 |
| shipped | 1,107 |
| canceled | 625 |
| unavailable | 609 |
| invoiced | 314 |
| processing | 301 |
| created | 5 |
| approved | 2 |

*Note: Chronological violations (1,373 orders) were logged as excluded but not yet filtered in `event_log_builder.py` — event log currently contains 96,455 orders. Filter will be added in next builder revision.*

---

## Section 3: Baseline KPIs (Pre-Analysis)

**Date:** 2026-07-07
**Sources:** `sql/queries/02_cycle_time_by_stage.sql`, `sql/queries/03_otd_by_seller_region.sql`

| KPI | Value |
|-----|-------|
| Total orders in event log | 96,455 |
| Overall OTD rate | 91.9% |
| Late order rate | 8.1% (7,826 late orders) |
| Median end-to-end cycle time | ~9.0 days (sum of stage medians: 0.01 + 1.84 + 7.09) |
| 90th percentile cycle time | ~26.3 days (sum of stage p90s: 1.40 + 5.99 + 18.90) |
| Slowest stage — median | **Delivered (carrier delivery): 7.09 days** |
| Slowest stage — p90 | Delivered: 18.90 days |
| Fastest stage — median | Order Approved: 0.01 days (near-instant) |
| Route with highest late rate | MA → SP: 26.9% late (130 orders) |
| Second highest late rate | SP → AL: 25.3% late (273 orders) |

**Stage cycle times (from query 02):**

| Stage | Transitions | Median (days) | p90 (days) | Mean (days) |
|-------|-------------|---------------|------------|-------------|
| Delivered (carrier → customer) | 96,446 | 7.09 | 18.90 | 9.32 |
| Picked Packed and Shipped | 96,290 | 1.84 | 5.99 | 2.84 |
| Order Approved | 95,211 | 0.01 | 1.40 | 0.41 |

**Top late routes (from query 03, min. 50 orders):**

| Route (seller → customer) | Orders | Late | Late % | OTD % |
|---------------------------|--------|------|--------|-------|
| MA → SP | 130 | 35 | 26.9% | 73.1% |
| SP → AL | 273 | 69 | 25.3% | 74.7% |
| RJ → CE | 56 | 14 | 25.0% | 75.0% |
| SP → MA | 549 | 122 | 22.2% | 77.8% |

**Key observations:**
- Carrier delivery (7.09 days median) is 3.9× longer than pick-pack (1.84 days) — primary bottleneck is last-mile logistics, not warehouse operations
- OTD of 91.9% vs. B2C e-commerce benchmark of ~93–95% — underperforming by ~2–4 pp
- The p90 of 26.3 days vs. median of 9.0 days shows high right-skew — a minority of orders experience severe delays

*These numbers are the baseline. All improvement projections are measured against them.*

---

## Section 4: Statistical Test Results (Phase 4)

**Date:** 2026-07-09
**Scripts run:** `python src/statistical_tests.py`
**SQL run:** `04_bottleneck_ranking.sql`, `06_pareto_delay_drivers.sql`

### Mann-Whitney U Results

Why Mann-Whitney U and not a t-test: cycle times are right-skewed (hard lower bound at 0, no upper bound) — the t-test's normality assumption doesn't hold, Mann-Whitney U doesn't require it.

| Stage | Median OT (days) | Median Late (days) | Delta | p-value | Significant | Effect (rank-biserial r) | Category |
|-------|------------------|--------------------|-------|---------|-------------|--------|----------|
| Delivered (carrier → customer) | 6.917 | 23.919 | 17.002 | <0.000001 | ✓ | 0.737 | large |
| Picked Packed and Shipped | 1.775 | 3.014 | 1.240 | <0.000001 | ✓ | 0.284 | small |
| Order Approved | 0.014 | 0.018 | 0.003 | <0.000001 | ✓ | 0.077 | small |
| Order Created | — | — | — | SKIPPED | n/a | n/a | insufficient sample (n_late = 3) |

**Primary bottleneck confirmed:** Delivered (carrier delivery leg) — p<0.000001, effect r=0.737 (large). This is the only stage with a large effect size, and satisfies pre-committed success criterion #1 from Section 1. Late orders take ~17 more days at this single stage than on-time orders — this is where the O2C cycle actually breaks, not at approval or pick/pack.

### Chi-squared Result (seller region vs. late rate)

- Chi-squared statistic: 351.14 | df: 21 | p-value: 1.10e-61
- Significant (p<0.05): Yes ✓
- Cramér's V: 0.0603 (small effect)
- Conclusion: seller region **is** statistically significantly associated with late delivery rate, but the association is weak in practical/magnitude terms (small Cramér's V) — region matters, but it's not the dominant driver on its own. This nuance matters for the business case: don't oversell "move sellers out of region X" as the fix.

**Top 5 seller states by late rate (min. 50 orders):**

| Seller state | Late rate | Late / Total orders |
|---|---|---|
| MA | 23.2% | 90 / 388 |
| RN | 9.8% | 5 / 51 |
| CE | 9.4% | 8 / 85 |
| SP | 8.8% | 6,001 / 68,415 |
| RJ | 8.5% | 354 / 4,185 |

### Pareto Finding (from query 06 — seller→customer route level)

- Top ~18 seller→customer routes account for ~80% of all late deliveries (cumulative_pct crosses 80% at the SP→MA / PR→SP boundary, 79.6% → 81.0%).
- Dominant late-delivery routes are concentrated where **SP (São Paulo) is the seller state**, paired with distant customer states (RJ, MA, BA, CE, AL) — consistent with last-mile/interstate logistics being the bottleneck, not a single rogue seller or carrier.
- Highest late-rate outlier routes (>20% late, smaller volume): SP→AL (26.3%), SP→MA (21.2%), MA→SP (25.2%) — small volume but severe, worth flagging separately from the high-volume Pareto drivers (SP→SP, SP→RJ).

### Interpretation for the business case

1. The bottleneck is not warehouse/pick-pack (small effect) or order approval (near-instant, negligible) — it's the **carrier delivery leg**, statistically confirmed with a large effect size. Any intervention should target carrier performance and last-mile logistics, not internal fulfillment operations.
2. Seller region has a statistically real but practically weak relationship with lateness — useful as a secondary segmentation variable (e.g., for cost-to-serve breakdown) but not the headline fix.
3. Late deliveries are geographically concentrated (Pareto), which supports a **targeted intervention** (e.g., carrier renegotiation or regional DC placement on the top ~18 routes) rather than a blanket process redesign — a more credible, lower-cost recommendation for the business case.

## Section 5: Financial Model Results (Phase 5)

**Date:** 2026-07-10
**Script run:** `python src/financials.py`
**SQL run:** `05_cost_to_serve.sql`

### Cost-to-Serve (top routes by total cost)

| Route | Orders | Late | Base Cost | Recovery Cost | Total Cost |
|-------|--------|------|-----------|----------------|------------|
| SP → SP | 30,735 | 1,912 | $454,878.00 | $42,064.00 | $496,942.00 |
| SP → RJ | 8,158 | 1,264 | $120,738.40 | $27,808.00 | $148,546.40 |
| SP → MG | 7,440 | 472 | $110,112.00 | $10,384.00 | $120,496.00 |

### NPV Sensitivity

| Scenario | Late Rate After | Orders Avoided/Year | Annual Savings | 3-Year NPV | Payback |
|----------|-----------------|----------------------|-----------------|------------|---------|
| Pessimistic | 7.1% | 965 | $21,230.00 | $2,896.27 | 2.1 years |
| Base | 5.1% | 2,894 | $63,668.00 | $98,639.17 | 0.7 years |
| Optimistic | 3.1% | 4,824 | $106,128.00 | $194,431.70 | 0.4 years |

**Conclusion:** Even the pessimistic scenario (1pp late-rate improvement) produces a positive 3-year NPV, meaning the business case for intervention holds under conservative assumptions, not just the optimistic case. Combined with the cost-to-serve breakdown, the SP→SP and SP→RJ routes represent the largest total cost exposure and should be the first targets for any carrier or process intervention.

## Section 6: Simulation Results (Phase 6)

**Date:** 2026-07-12
**Script run:** `python src/simulation.py`

### Calibration Check

- Simulated as-is OTD: 91.6% vs observed 91.9% — delta: 0.3pp
- Within ±2pp target: Yes

### To-Be Improvement

- Simulated to-be OTD: 96.3% (SHRINK_FACTOR = 0.70, a 30% reduction in carrier delivery time, targeting the ~18 highest-cost Pareto routes)
- Improvement vs as-is: 4.7pp
- Meets ≥8pp target: No

**Note on the ≥8pp target:** Not met under a realistic assumption, and this is a real finding rather than a modeling shortfall. As-is OTD is already 91.6%, leaving a theoretical ceiling of only 8.4pp even if carrier delivery became perfectly reliable. Testing progressively more aggressive shrink factors confirmed this: a 70% reduction in delivery time (SHRINK_FACTOR = 0.3) — an implausible assumption for any real carrier intervention — still only reached 7.5pp. The pre-committed ≥8pp target likely underestimated how little headroom remains once a process already performs reasonably well. A defensible, realistic assumption (30% delivery-time reduction) produces a genuine 4.7pp improvement, confirmed by non-overlapping 95% confidence intervals (as-is 91.8% ± 0.2pp vs. to-be 96.2% ± 0.2pp) — the effect is real, just smaller than the original target assumed.

### Confidence Intervals (20 replications, 2,000 orders each)

- As-is: 91.8% ± 0.2pp (95% CI)
- To-be: 96.2% ± 0.2pp (95% CI)
- Intervals overlap: No