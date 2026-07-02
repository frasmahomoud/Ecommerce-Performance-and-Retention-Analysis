-- 1. Overall Funnel Performance: Tracking user drop-off across key journey stages
SELECT
    -- Raw volume metrics per funnel stage
    COUNT(session_id) AS total_sessions,
    SUM(CAST(product_page_visited_flag AS INT)) AS viewed_product_sessions,
    SUM(CAST(added_to_cart_flag AS INT)) AS added_cart_sessions,
    SUM(CAST(purchased_flag AS INT)) AS purchased_sessions,

    -- Step-by-step conversion rates to identify specific friction points
    ROUND(SUM(CAST(product_page_visited_flag AS INT)) * 100.0 / COUNT(session_id), 2) AS visit_to_view_percent,
    ROUND(SUM(CAST(added_to_cart_flag AS INT)) * 100.0 / NULLIF(SUM(CAST(product_page_visited_flag AS INT)), 0), 2) AS view_to_cart_percent,
    ROUND(SUM(CAST(purchased_flag AS INT)) * 100.0 / NULLIF(SUM(CAST(added_to_cart_flag AS INT)), 0), 2) AS cart_to_purchase_percent,

    -- Overall platform conversion rate
    ROUND(SUM(CAST(purchased_flag AS INT)) * 100.0 / COUNT(session_id), 2) AS overall_conversion_percent
FROM 'fact_clickstream.parquet'
WHERE session_start_date_id BETWEEN 20250101 AND 20251231;


-- 2. Marketing ROI: Funnel conversion and drop-off rates broken down by traffic source
WITH source_funnel AS (
    SELECT
        traffic_source,
        -- Tracking initial volume to assess channel scale alongside conversion quality
        COUNT(session_id) AS total_sessions, 
        SUM(CAST(product_page_visited_flag AS INT)) AS views,
        SUM(CAST(added_to_cart_flag AS INT)) AS cart,
        SUM(CAST(purchased_flag AS INT)) AS purchases
    FROM 'fact_clickstream.parquet'
    WHERE session_start_date_id BETWEEN 20250101 AND 20251231
    GROUP BY traffic_source
)

SELECT
    traffic_source,
    total_sessions,
    views,
    cart,
    purchases,

    -- Micro-conversions per stage
    ROUND(views * 100.0 / NULLIF(total_sessions, 0), 2) AS session_to_view_rate,
    ROUND(cart * 100.0 / NULLIF(views, 0), 2) AS view_to_cart_rate,
    ROUND(purchases * 100.0 / NULLIF(cart, 0), 2) AS cart_to_purchase_rate,

    -- Ultimate channel conversion rate
    ROUND(purchases * 100.0 / NULLIF(total_sessions, 0), 2) AS overall_conversion_rate
FROM source_funnel
ORDER BY overall_conversion_rate DESC;


-- 3. Omnichannel Device Performance: Analyzing traffic volume vs. conversion efficiency
-- This query highlights the mobile UX bottleneck by comparing session volume, engagement depth (pages viewed), and final conversion rates across different devices.
SELECT
    device_type,
    COUNT(session_id) AS total_sessions,
    ROUND(AVG(date_diff('second', session_start_time, session_end_time) / 60.0), 2) AS avg_duration_minutes,
    ROUND(AVG(number_of_pages_viewed), 2) AS avg_pages_viewed,
    SUM(CAST(added_to_cart_flag AS INT)) AS cart_sessions,
    SUM(CAST(purchased_flag AS INT)) AS purchase_sessions,
    ROUND(SUM(CAST(purchased_flag AS INT)) * 100.0 / COUNT(session_id), 2) AS conversion_rate
FROM 'fact_clickstream.parquet'
WHERE session_start_date_id BETWEEN 20250101 AND 20251231
GROUP BY device_type
ORDER BY total_sessions DESC;


-- 4. The Webrooming Phenomenon: Quantifying online research driving offline sales
-- Using an EXISTS subquery to identify customers who browsed the website without purchasing, but subsequently completed a transaction in a physical store.
SELECT
    COUNT(DISTINCT ft.customer_id) AS webrooming_customers,
    ROUND(SUM(CAST(ft.transaction_total AS FLOAT)), 2) AS total_offline_revenue
FROM 'fact_transaction.parquet' ft
WHERE ft.sales_channel = 'Store'
  AND ft.customer_id IS NOT NULL
  AND ft.transaction_date_id BETWEEN 20250101 AND 20251231
  AND EXISTS (
      SELECT 1
      FROM 'fact_clickstream.parquet' cs
      WHERE cs.customer_id = ft.customer_id
        AND cs.purchased_flag = FALSE
        AND cs.session_start_date_id BETWEEN 20250101 AND 20251231
        AND cs.session_start_date_id <= ft.transaction_date_id
  );



-- 5. The Retention Engine: Calculating overall repeat purchase rate to validate customer loyalty
-- This query classifies users based on distinct purchase days to quantify the base of returning customers vs. one-time buyers.
WITH Customer_Stats AS (
    SELECT
        customer_id,
        COUNT(DISTINCT transaction_date_id) AS distinct_purchase_days
    FROM 'fact_transaction.parquet'
    WHERE customer_id IS NOT NULL
      AND transaction_date_id BETWEEN 20250101 AND 20251231
    GROUP BY customer_id
),

Classification AS (
    SELECT
        customer_id,
        CASE
            WHEN distinct_purchase_days > 1 THEN 'Repeat Customer'
            ELSE 'One-Time Buyer'
        END AS customer_type
    FROM Customer_Stats
)

SELECT
    customer_type,
    COUNT(customer_id) AS total_customers,
    ROUND(COUNT(customer_id) * 100.0 / SUM(COUNT(customer_id)) OVER (), 1) AS percentage
FROM Classification
GROUP BY customer_type;


-- 6. Cohort Retention Matrix: Tracking monthly customer churn and re-engagement cycles
-- This query generates the foundation for the retention heatmap, exposing the "Month-1 Cliff" and the "Q4 Resurrection" trends.
WITH First_Purchase AS (
    SELECT
        customer_id,
        MIN(transaction_timestamp) AS first_purchase_date
    FROM 'fact_transaction.parquet'
    GROUP BY customer_id
),

Cohort_Data AS (
    SELECT
        ft.customer_id,
        date_trunc('month', fp.first_purchase_date) AS cohort_month,
        date_diff('month', fp.first_purchase_date, ft.transaction_timestamp) AS month_index
    FROM 'fact_transaction.parquet' ft
    JOIN First_Purchase fp ON ft.customer_id = fp.customer_id
    WHERE ft.transaction_date_id BETWEEN 20250101 AND 20251231
      AND fp.first_purchase_date >= '2025-01-01' 
)

SELECT
    CAST(cohort_month AS DATE) AS cohort_month,
    month_index,
    COUNT(DISTINCT customer_id) AS active_customers
FROM Cohort_Data
GROUP BY cohort_month, month_index
ORDER BY cohort_month, month_index;




