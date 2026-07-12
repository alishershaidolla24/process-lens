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
    SELECT order_id,
           COUNT(*) AS n_items,
           SUM(price) AS total_price,
           SUM(freight_value) AS total_freight,
           (ARRAY_AGG(seller_id))[1] AS seller_id
    FROM order_items
    GROUP BY order_id
) items ON o.order_id = items.order_id
JOIN sellers s ON items.seller_id = s.seller_id
JOIN (
    SELECT order_id,
           SUM(payment_value) AS total_payment,
           MAX(payment_installments) AS max_installments
    FROM payments
    GROUP BY order_id
) pay ON o.order_id = pay.order_id
WHERE o.order_status = 'delivered';