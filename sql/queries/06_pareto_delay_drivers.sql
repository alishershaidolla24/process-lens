-- Pareto analysis: which seller → customer state routes cause most delays?
-- Cumulative % shows how many routes you need to fix to capture 80% of delays.

WITH segment_delays AS (
    SELECT
        om.seller_state,
        om.customer_state,
        COUNT(*)                                       AS total_orders,
        SUM(CASE WHEN om.is_late THEN 1 ELSE 0 END)   AS late_orders
    FROM order_metrics om
    GROUP BY om.seller_state, om.customer_state
    HAVING COUNT(*) >= 50
)
SELECT
    seller_state,
    customer_state,
    total_orders,
    late_orders,
    ROUND((100.0 * late_orders / total_orders)::NUMERIC, 1)               AS late_pct,
    SUM(late_orders) OVER (ORDER BY late_orders DESC
                           ROWS UNBOUNDED PRECEDING)                      AS cumulative_late,
    ROUND((100.0 * SUM(late_orders) OVER (ORDER BY late_orders DESC
                        ROWS UNBOUNDED PRECEDING)
           / SUM(late_orders) OVER ())::NUMERIC, 1)                       AS cumulative_pct
FROM segment_delays
ORDER BY late_orders DESC;