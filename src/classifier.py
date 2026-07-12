import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from sqlalchemy import create_engine

DB_URL = "postgresql://_shaidolla@localhost/process_lens"
engine = create_engine(DB_URL)

print("Loading order-level features...")
df = pd.read_sql("""
    SELECT
        o.order_id,
        o.order_purchase_timestamp,
        EXTRACT(EPOCH FROM (
            o.order_estimated_delivery_date - o.order_purchase_timestamp
        )) / 86400.0 AS promise_days,
        EXTRACT(DOW FROM o.order_purchase_timestamp) AS purchase_dow,
        EXTRACT(MONTH FROM o.order_purchase_timestamp) AS purchase_month,
        items.n_items,
        items.total_price,
        items.total_freight,
        pay.total_payment,
        pay.max_installments,
        s.seller_state,
        c.customer_state,
        (s.seller_state = c.customer_state) AS same_state,
        om.is_late
    FROM orders o
    JOIN order_metrics om ON o.order_id = om.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN (
        SELECT order_id, COUNT(*) AS n_items, SUM(price) AS total_price,
               SUM(freight_value) AS total_freight,
               (ARRAY_AGG(seller_id))[1] AS seller_id
        FROM order_items GROUP BY order_id
    ) items ON o.order_id = items.order_id
    JOIN sellers s ON items.seller_id = s.seller_id
    JOIN (
        SELECT order_id, SUM(payment_value) AS total_payment,
               MAX(payment_installments) AS max_installments
        FROM payments GROUP BY order_id
    ) pay ON o.order_id = pay.order_id
    WHERE o.order_status = 'delivered'
""", engine)
print(f"  Orders loaded: {len(df):,}")
print(f"  Late rate: {df['is_late'].mean()*100:.1f}%")

df = df.sort_values("order_purchase_timestamp").reset_index(drop=True)

split_idx = int(len(df) * 0.8)
train = df.iloc[:split_idx]
test = df.iloc[split_idx:]
print(f"  Train: {len(train):,} orders, up to {train['order_purchase_timestamp'].max()}")
print(f"  Test:  {len(test):,} orders, from {test['order_purchase_timestamp'].min()}")

feature_cols = [
    "promise_days", "purchase_dow", "purchase_month",
    "n_items", "total_price", "total_freight",
    "total_payment", "max_installments", "same_state",
]
categorical_cols = ["seller_state", "customer_state"]

train_x = pd.get_dummies(train[feature_cols + categorical_cols], columns=categorical_cols)
test_x = pd.get_dummies(test[feature_cols + categorical_cols], columns=categorical_cols)
test_x = test_x.reindex(columns=train_x.columns, fill_value=0)

train_y = train["is_late"].astype(int)
test_y = test["is_late"].astype(int)

model = xgb.XGBClassifier(
    n_estimators=400,
    max_depth=6,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="auc",
    random_state=42,
)
model.fit(train_x, train_y)

pred_proba = model.predict_proba(test_x)[:, 1]
auc = roc_auc_score(test_y, pred_proba)

print(f"\nAUC-ROC on held-out temporal test set: {auc:.3f}")
print(f"Meets >0.70 target: {'Yes' if auc > 0.70 else 'No'}")

print("\nPrecision/recall at different risk percentiles:")
for pct in [0.05, 0.10, 0.15, 0.20]:
    cutoff = np.quantile(pred_proba, 1 - pct)
    pred_label = (pred_proba >= cutoff).astype(int)
    precision = precision_score(test_y, pred_label, zero_division=0)
    recall = recall_score(test_y, pred_label, zero_division=0)
    flagged = pred_label.sum()
    print(f"  Top {pct*100:.0f}% flagged (probability >= {cutoff:.3f}): "
          f"precision={precision:.3f}, recall={recall:.3f}, orders flagged={flagged:,}")
    
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(test_x)

mean_abs_shap = np.abs(shap_values).mean(axis=0)
importance = pd.Series(mean_abs_shap, index=test_x.columns).sort_values(ascending=False)

print("\nTop 10 features by mean absolute SHAP value:")
print(importance.head(10))

importance.head(10).to_csv("outputs/reports/classifier_feature_importance.csv")
print("\nFeature importance saved: outputs/reports/classifier_feature_importance.csv")