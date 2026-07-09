-- Cycle time per stage: median and 90th percentile
-- Uses LAG() window function to calculate time between consecutive events

WITH stage_durations AS (
    SELECT
        order_id,
        activity,
        event_timestamp,
        LAG(event_timestamp) OVER (
            PARTITION BY order_id
            ORDER BY event_timestamp
        ) AS prev_timestamp,
        EXTRACT(EPOCH FROM (
            event_timestamp -
            LAG(event_timestamp) OVER (
                PARTITION BY order_id
                ORDER BY event_timestamp
            )
        )) / 86400.0 AS days_elapsed
    FROM events
)
SELECT
    activity,
    COUNT(*)                                                             AS n_transitions,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
          (ORDER BY days_elapsed)::NUMERIC, 2)                          AS median_days,
    ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP
          (ORDER BY days_elapsed)::NUMERIC, 2)                          AS p90_days,
    ROUND(AVG(days_elapsed)::NUMERIC, 2)                                AS mean_days
FROM stage_durations
WHERE days_elapsed IS NOT NULL
  AND days_elapsed > 0
GROUP BY activity
ORDER BY median_days DESC;