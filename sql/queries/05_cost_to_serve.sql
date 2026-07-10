SELECT
    om.seller_state,
    om.customer_state,
    COUNT(*)                                                     AS total_orders,
    SUM(CASE WHEN om.is_late THEN 1 ELSE 0 END)                 AS late_orders,
    ROUND(COUNT(*) * 14.80, 2)                                   AS base_handling_cost,
    ROUND(SUM(CASE WHEN om.is_late THEN 1 ELSE 0 END) * 22.0, 2) AS late_recovery_cost,
    ROUND(COUNT(*) * 14.80
          + SUM(CASE WHEN om.is_late THEN 1 ELSE 0 END) * 22.0, 2) AS total_cost_to_serve
FROM order_metrics om
GROUP BY om.seller_state, om.customer_state
HAVING COUNT(*) >= 50
ORDER BY total_cost_to_serve DESC;