-- OTD rate by seller state → customer state route
SELECT
    s.seller_state,
    c.customer_state,
    COUNT(*)                                                               AS total_orders,
    SUM(CASE WHEN o.order_delivered_customer_date
                  > o.order_estimated_delivery_date THEN 1 ELSE 0 END)    AS late_orders,
    ROUND((100.0 * SUM(CASE WHEN o.order_delivered_customer_date
                                > o.order_estimated_delivery_date
                            THEN 1 ELSE 0 END) / COUNT(*))::NUMERIC, 1)   AS late_pct,
    ROUND((100.0 * (1.0 - SUM(CASE WHEN o.order_delivered_customer_date
                                       > o.order_estimated_delivery_date
                                  THEN 1 ELSE 0 END)::FLOAT
                       / COUNT(*)))::NUMERIC, 1)                           AS otd_pct
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN sellers s      ON oi.seller_id = s.seller_id
JOIN customers c    ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY s.seller_state, c.customer_state
HAVING COUNT(*) >= 50
ORDER BY late_pct DESC;