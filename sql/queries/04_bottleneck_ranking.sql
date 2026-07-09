-- Ranks each stage by how much longer it takes for late orders vs on-time orders.
-- Delta = the stage's contribution to delay.

WITH stage_durations AS (
    SELECT
        e.order_id,
        e.activity,
        EXTRACT(EPOCH FROM (
            e.event_timestamp -
            LAG(e.event_timestamp) OVER (
                PARTITION BY e.order_id ORDER BY e.event_timestamp
            )
        )) / 86400.0 AS days_elapsed
    FROM events e
),
with_otd AS (
    SELECT sd.activity,
           sd.days_elapsed,
           om.is_late
    FROM stage_durations sd
    JOIN order_metrics om ON sd.order_id = om.order_id
    WHERE sd.days_elapsed IS NOT NULL
      AND sd.days_elapsed > 0
)
SELECT
    activity,
    COUNT(*) FILTER (WHERE is_late = FALSE)                                        AS n_on_time,
    COUNT(*) FILTER (WHERE is_late = TRUE)                                         AS n_late,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_elapsed)
          FILTER (WHERE is_late = FALSE)::NUMERIC, 3)                              AS median_on_time_days,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_elapsed)
          FILTER (WHERE is_late = TRUE)::NUMERIC, 3)                               AS median_late_days,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_elapsed)
           FILTER (WHERE is_late = TRUE) -
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_elapsed)
           FILTER (WHERE is_late = FALSE))::NUMERIC, 3)                            AS delta_days
FROM with_otd
GROUP BY activity
ORDER BY delta_days DESC;