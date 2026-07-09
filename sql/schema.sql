-- ============================================================
-- Process Lens: PostgreSQL Schema
-- Mirrors Olist CSV structure exactly
-- Column names match source files — no translation layer
-- ============================================================

-- Drop tables if re-running (safe restart)
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS order_metrics CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS sellers CASCADE;

-- Core orders table
CREATE TABLE orders (
    order_id                        TEXT PRIMARY KEY,
    customer_id                     TEXT,
    order_status                    TEXT,
    order_purchase_timestamp        TIMESTAMP,
    order_approved_at               TIMESTAMP,
    order_delivered_carrier_date    TIMESTAMP,
    order_delivered_customer_date   TIMESTAMP,
    order_estimated_delivery_date   TIMESTAMP
);

-- Order items
CREATE TABLE order_items (
    order_id             TEXT REFERENCES orders(order_id),
    order_item_id        INTEGER,
    product_id           TEXT,
    seller_id            TEXT,
    shipping_limit_date  TIMESTAMP,
    price                NUMERIC(10,2),
    freight_value        NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

-- Payments
CREATE TABLE payments (
    order_id                TEXT REFERENCES orders(order_id),
    payment_sequential      INTEGER,
    payment_type            TEXT,
    payment_installments    INTEGER,
    payment_value           NUMERIC(10,2)
);

-- Customer reviews
CREATE TABLE reviews (
    review_id                TEXT,
    order_id                 TEXT REFERENCES orders(order_id),
    review_score             INTEGER CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title     TEXT,
    review_comment_message   TEXT,
    review_creation_date     TIMESTAMP,
    review_answer_timestamp  TIMESTAMP
);

-- Customers
CREATE TABLE customers (
    customer_id              TEXT PRIMARY KEY,
    customer_unique_id       TEXT,
    customer_zip_code_prefix TEXT,
    customer_city            TEXT,
    customer_state           TEXT
);

-- Sellers
CREATE TABLE sellers (
    seller_id               TEXT PRIMARY KEY,
    seller_zip_code_prefix  TEXT,
    seller_city             TEXT,
    seller_state             TEXT
);

-- Event log (built by event_log_builder.py — populated later)
CREATE TABLE events (
    event_id        BIGSERIAL PRIMARY KEY,
    order_id        TEXT REFERENCES orders(order_id),
    activity        TEXT,
    event_timestamp TIMESTAMP,
    resource        TEXT
);