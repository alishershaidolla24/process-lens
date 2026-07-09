# Process Lens

> Order-to-Cash process mining: bottleneck detection, simulation-validated redesign, and predictive delay classification on 99,441 real e-commerce orders.

![Python](https://img.shields.io/badge/Python-3.14.6-blue?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18.4-blue?logo=postgresql)
![pm4py](https://img.shields.io/badge/pm4py-Process_Mining-orange)
![XGBoost](https://img.shields.io/badge/XGBoost-Classifier-green)
![SimPy](https://img.shields.io/badge/SimPy-Simulation-purple)
![Status](https://img.shields.io/badge/Status-In_Progress-yellow)

---

## What This Project Does

Process Lens applies operations consulting methodology to the Order-to-Cash (O2C) fulfillment process — the sequence from order creation to delivery — using real e-commerce event data.

It answers: **"Where is the process breaking down, how much is it costing, and how do we prove the fix will work?"**

**The analytical chain:**
1. Constructs an event log from 99,441 real orders (Olist Brazilian E-Commerce dataset)
2. Discovers the actual process flow using process mining (pm4py Heuristics Miner)
3. Measures conformance against the ideal process — identifies deviation rate and bottleneck stages
4. Validates bottlenecks statistically (Mann-Whitney U, effect size)
5. Builds a financial model: cost-to-serve, 3-year NPV at 9% WACC, sensitivity analysis
6. Validates the proposed redesign through discrete-event simulation (SimPy) with 95% CI
7. Trains an XGBoost classifier to predict at-risk orders at the moment of creation
8. Packages findings into a consulting-grade business case (SCQA framework)

---

## Tech Stack

| Layer | Tools |
|---|---|
| Data storage | PostgreSQL 18.4 |
| Data analysis | Python 3.14.6, pandas, SQL (window functions, CTEs) |
| Process mining | pm4py (Heuristics Miner, conformance checking) |
| Statistical testing | scipy.stats (Mann-Whitney U, Chi-squared, effect size) |
| Simulation | SimPy (discrete-event, calibrated to real distributions) |
| Machine learning | XGBoost + SHAP (binary classifier, temporal CV) |
| Financial modelling | Python + openpyxl (NPV, WACC, cost-to-serve) |
| Visualisation | matplotlib, seaborn, networkx, Graphviz |

---

## Key Findings

> *Analysis in progress — findings will be populated as each phase completes.*

---

## Project Structure

    process-lens/
    ├── data/
    │   ├── raw/              ← Not in repo — see Data Sources below
    │   ├── processed/
    │   └── data_quality_log.md
    ├── sql/
    │   ├── schema.sql
    │   └── queries/          ← 6 analytical SQL queries
    ├── notebooks/            ← Jupyter notebooks per phase
    ├── src/                  ← Python modules
    └── outputs/              ← Charts, models, reports
---

## Data Sources

**Primary:** [Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 99,441 real orders, CC BY-NC-SA 4.0

**Cross-validation:** [BPI Challenge 2019](https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1) — 251,734 events, real SAP P2P export, 4TU Research Data Centre

To run this project locally, download both datasets and place CSVs in `data/raw/olist/` and `data/raw/bpi2019/`.

---

## How to Run Locally

```bash
# 1. Clone and enter
git clone https://github.com/alishershaidolla24/process-lens.git
cd process-lens

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install packages
pip install -r requirements.txt

# 4. Set up PostgreSQL database
psql -U postgres -c "CREATE DATABASE process_lens;"
python src/db_setup.py

# 5. Run notebooks in order
jupyter notebook notebooks/
```

---

## Methodology

Full DMAIC (Define → Measure → Analyze → Improve → Control) cycle applied to O2C fulfillment. Process mining with pm4py Heuristics Miner for discovery; token-based replay for conformance checking. Statistical bottleneck validation with Mann-Whitney U (non-parametric, correct for right-skewed cycle-time distributions). SimPy discrete-event simulation calibrated to observed Olist distributions validates the to-be process before claiming projected improvements. XGBoost classifier (temporal train/test split, SHAP explainability) enables proactive intervention on at-risk orders.

---

## Financial Model Assumptions

| Variable | Value | Source |
|---|---|---|
| Cost per O2C case | $14.80 (median) | APQC 2023 |
| Recovery cost per late delivery | $22 | Metapack 2022 |
| WACC | 9.0% | Damodaran (online retail), Jan 2024 |
| Implementation cost | $35K–$55K | APQC 2023 |
| Year 1 benefit realization | 70% | McKinsey Operations Practice 2022 |
| Avg order value, late rate, complaint rate | Data-derived | Olist dataset |

---

