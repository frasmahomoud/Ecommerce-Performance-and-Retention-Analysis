-- ElecMart analytics queries
-- Same queries executed by generate_summary.py, generate_basket.py and analysis.py.
-- Window: 2025-01-01 to 2025-12-31. Only the yearly trend uses all three years.
-- Run in DuckDB from the folder holding the Kaggle parquet files.

CREATE VIEW clickstream  AS SELECT * FROM read_parquet('fact_clickstream.parquet');
CREATE VIEW transactions AS SELECT * FROM read_parquet('fact_transaction.parquet');
CREATE VIEW sales        AS SELECT * FROM read_parquet('fact_sale.parquet');
CREATE VIEW customers    AS SELECT * FROM read_parquet('dim_customer.parquet');
CREATE VIEW products     AS SELECT * FROM read_parquet('dim_product.parquet');
CREATE VIEW categories   AS SELECT * FROM read_parquet('dim_category.parquet');


-- 1. Headline KPIs. Gross includes returned orders, net excludes them. -> summary_kpis.csv
WITH sessions AS (
    SELECT COUNT(*) AS total_visitors,
           COUNT(DISTINCT CASE WHEN purchased_flag THEN customer_id END) AS total_buyers,
           SUM(CASE WHEN number_of_pages_viewed = 1 THEN 1 ELSE 0 END) AS single_page_sessions
    FROM clickstream
    WHERE session_start_date_id BETWEEN 20250101 AND 20251231
),
orders AS (
    SELECT COUNT(*) AS total_orders,
           SUM(transaction_total) AS total_revenue,
           SUM(transaction_cost) AS total_cost,
           SUM(transaction_total - transaction_cost) AS total_profit,
           SUM(CASE WHEN transaction_status = 'Completed' THEN 1 ELSE 0 END) AS net_orders,
           SUM(CASE WHEN transaction_status = 'Completed' THEN transaction_total ELSE 0 END) AS net_revenue,
           SUM(CASE WHEN transaction_status = 'Completed'
                    THEN transaction_total - transaction_cost ELSE 0 END) AS net_profit,
           SUM(CASE WHEN customer_id IS NULL THEN transaction_total ELSE 0 END) AS guest_revenue
    FROM transactions
    WHERE transaction_date_id BETWEEN 20250101 AND 20251231
)
SELECT sessions.*, orders.*,
       ROUND(total_revenue / total_orders, 2) AS avg_order_value,
       ROUND(net_revenue / net_orders, 2) AS net_aov,
       ROUND((total_orders - net_orders) * 100.0 / total_orders, 2) AS return_rate_pct,
       ROUND(guest_revenue * 100.0 / total_revenue, 2) AS guest_revenue_pct,
       ROUND(single_page_sessions * 100.0 / total_visitors, 2) AS single_page_pct
FROM sessions, orders;


-- 2a. Funnel counts. Flags nest, so each stage is a subset of the one above. -> summary_funnel.csv
SELECT COUNT(*) AS "Total Sessions",
       SUM(CAST(product_page_visited_flag AS INT)) AS "Viewed Product",
       SUM(CAST(added_to_cart_flag AS INT)) AS "Added to Cart",
       SUM(CAST(purchased_flag AS INT)) AS "Purchased"
FROM clickstream
WHERE session_start_date_id BETWEEN 20250101 AND 20251231;

-- 2b. Step-to-step rates, kept separate from the share-of-total figures. -> funnel_rates.csv
WITH stages AS (
    SELECT COUNT(*) AS sessions,
           SUM(CAST(product_page_visited_flag AS INT)) AS viewed,
           SUM(CAST(added_to_cart_flag AS INT)) AS cart,
           SUM(CAST(purchased_flag AS INT)) AS purchased,
           SUM(CASE WHEN number_of_pages_viewed = 1 THEN 1 ELSE 0 END) AS single_page
    FROM clickstream
    WHERE session_start_date_id BETWEEN 20250101 AND 20251231
)
SELECT ROUND(viewed * 100.0 / sessions, 2) AS visit_to_view_pct,
       ROUND(cart * 100.0 / viewed, 2) AS view_to_cart_pct,
       ROUND(purchased * 100.0 / cart, 2) AS cart_to_purchase_pct,
       ROUND(purchased * 100.0 / sessions, 2) AS overall_conversion_pct,
       ROUND((cart - purchased) * 100.0 / cart, 2) AS cart_abandonment_pct,
       ROUND(single_page * 100.0 / sessions, 2) AS single_page_bounce_pct
FROM stages;


-- 3. Traffic. Revenue joins on session_id, so every online order is counted once. -> summary_traffic.csv
WITH sessions AS (
    SELECT traffic_source,
           COUNT(*) AS total_sessions,
           SUM(CAST(product_page_visited_flag AS INT)) AS viewed,
           SUM(CAST(added_to_cart_flag AS INT)) AS cart,
           SUM(CAST(purchased_flag AS INT)) AS purchases
    FROM clickstream
    WHERE session_start_date_id BETWEEN 20250101 AND 20251231
    GROUP BY traffic_source
),
orders AS (
    SELECT c.traffic_source,
           COUNT(*) AS orders,
           SUM(t.transaction_total) AS revenue,
           SUM(t.transaction_total - t.transaction_cost) AS profit
    FROM transactions t
    JOIN clickstream c ON c.session_id = t.session_id
    WHERE t.transaction_date_id BETWEEN 20250101 AND 20251231
    GROUP BY c.traffic_source
)
SELECT s.traffic_source, s.total_sessions, s.viewed, s.cart, s.purchases,
       ROUND(s.purchases * 100.0 / s.total_sessions, 2) AS overall_conversion_rate,
       ROUND(s.cart * 100.0 / s.viewed, 2) AS view_to_cart_pct,
       o.orders, ROUND(o.revenue, 2) AS revenue, ROUND(o.profit, 2) AS profit,
       ROUND(o.revenue / o.orders, 2) AS aov,
       ROUND(o.profit * 100.0 / o.revenue, 2) AS margin_pct,
       ROUND(o.revenue * 100.0 / SUM(o.revenue) OVER (), 2) AS revenue_share_pct
FROM sessions s JOIN orders o ON s.traffic_source = o.traffic_source
ORDER BY overall_conversion_rate DESC;


-- 4. Devices. Duration is capped at 12 minutes in the source data. -> summary_devices.csv
WITH sessions AS (
    SELECT device_type,
           COUNT(*) AS total_sessions,
           SUM(CAST(purchased_flag AS INT)) AS purchases,
           AVG(number_of_pages_viewed) AS avg_pages,
           AVG(date_diff('second', session_start_time, session_end_time) / 60.0) AS avg_minutes,
           MEDIAN(date_diff('second', session_start_time, session_end_time) / 60.0) AS median_minutes
    FROM clickstream
    WHERE session_start_date_id BETWEEN 20250101 AND 20251231
    GROUP BY device_type
),
orders AS (
    SELECT c.device_type, COUNT(*) AS orders, SUM(t.transaction_total) AS revenue
    FROM transactions t
    JOIN clickstream c ON c.session_id = t.session_id
    WHERE t.transaction_date_id BETWEEN 20250101 AND 20251231
    GROUP BY c.device_type
)
SELECT s.device_type, s.total_sessions,
       ROUND(s.purchases * 100.0 / s.total_sessions, 2) AS conversion_rate,
       ROUND(s.avg_pages, 2) AS avg_pages_viewed,
       ROUND(s.avg_minutes, 2) AS avg_duration_minutes,
       ROUND(s.median_minutes, 2) AS median_duration_minutes,
       o.orders, ROUND(o.revenue, 2) AS revenue,
       ROUND(o.revenue / o.orders, 2) AS aov
FROM sessions s JOIN orders o ON s.device_type = o.device_type
ORDER BY s.total_sessions DESC;


-- 5. Repeat buyers. Repeat means more than one transaction inside the year. -> summary_retention_profile.csv
WITH per_customer AS (
    SELECT customer_id, COUNT(*) AS orders
    FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN 20250101 AND 20251231
    GROUP BY customer_id
)
SELECT CASE WHEN orders > 1 THEN 'Repeat Customer' ELSE 'One-Time Buyer' END AS customer_type,
       COUNT(*) AS customer_count
FROM per_customer
GROUP BY 1;


-- 6. RFM. Scores are assigned by value, so equal inputs always get equal scores.
--    Frequency uses fixed bands because the quartile edges fall inside large tie blocks.
--    The generators inline this CTE in each query; here it is a view to keep the file readable.
CREATE TEMP VIEW rfm_segmented AS
WITH base AS (
    SELECT customer_id,
           date_diff('day', MAX(transaction_timestamp), DATE '2026-01-01') AS recency,
           COUNT(*) AS frequency,
           SUM(transaction_total) AS monetary
    FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN 20250101 AND 20251231
    GROUP BY customer_id
),
edges AS (
    SELECT quantile_cont(recency, 0.25) AS r25,
           quantile_cont(recency, 0.50) AS r50,
           quantile_cont(recency, 0.75) AS r75,
           quantile_cont(monetary, 0.25) AS m25,
           quantile_cont(monetary, 0.50) AS m50,
           quantile_cont(monetary, 0.75) AS m75
    FROM base
),
scored AS (
    SELECT b.customer_id, b.recency, b.frequency, b.monetary,
           CASE WHEN b.recency <= e.r25 THEN 4
                WHEN b.recency <= e.r50 THEN 3
                WHEN b.recency <= e.r75 THEN 2
                ELSE 1 END AS r_score,
           CASE WHEN b.frequency = 1 THEN 1
                WHEN b.frequency = 2 THEN 2
                WHEN b.frequency <= 4 THEN 3
                ELSE 4 END AS f_score,
           CASE WHEN b.monetary <= e.m25 THEN 1
                WHEN b.monetary <= e.m50 THEN 2
                WHEN b.monetary <= e.m75 THEN 3
                ELSE 4 END AS m_score
    FROM base b CROSS JOIN edges e
)
SELECT *,
       CASE WHEN r_score = 4 AND f_score = 4 AND m_score = 4 THEN 'VIP'
            WHEN r_score = 4 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score IN (2, 3) AND f_score >= 3 THEN 'At Risk'
            WHEN r_score = 1 THEN 'Lost'
            ELSE 'Regular' END AS segment
FROM scored;

-- 6a. Customers per segment. -> summary_rfm_segments.csv
SELECT segment AS "Segment", COUNT(*) AS "Customer_Count"
FROM rfm_segmented GROUP BY 1 ORDER BY "Customer_Count" DESC;

-- 6b. Value per segment. customer_pct counts customers, order_pct counts orders. -> segment_value.csv
SELECT s.segment,
       COUNT(DISTINCT s.customer_id) AS customers,
       COUNT(t.transaction_id) AS orders,
       ROUND(SUM(t.transaction_total), 2) AS revenue,
       ROUND(SUM(t.transaction_total - t.transaction_cost), 2) AS profit,
       ROUND(SUM(t.transaction_total) / COUNT(DISTINCT s.customer_id), 2) AS arpu,
       ROUND(SUM(t.transaction_total) * 100.0 / SUM(SUM(t.transaction_total)) OVER (), 2) AS revenue_pct,
       ROUND(COUNT(DISTINCT s.customer_id) * 100.0
             / SUM(COUNT(DISTINCT s.customer_id)) OVER (), 2) AS customer_pct,
       ROUND(COUNT(t.transaction_id) * 100.0
             / SUM(COUNT(t.transaction_id)) OVER (), 2) AS order_pct
FROM rfm_segmented s
JOIN transactions t ON t.customer_id = s.customer_id
WHERE t.transaction_date_id BETWEEN 20250101 AND 20251231
GROUP BY s.segment
ORDER BY revenue DESC;

-- 6c. Every score combination, so the segment counts can be rebuilt by hand. -> rfm_score_distribution.csv
SELECT r_score, f_score, m_score, COUNT(*) AS customers
FROM rfm_segmented GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;


-- 7a. Segment by acquisition channel. signup_channel is one value per customer. -> summary_acquisition.csv
SELECT s.segment AS "Segment", c.signup_channel, COUNT(*) AS total_customers,
       ROUND(SUM(t.revenue), 2) AS revenue
FROM rfm_segmented s
JOIN customers c ON c.customer_id = s.customer_id
JOIN (
    SELECT customer_id, SUM(transaction_total) AS revenue
    FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN 20250101 AND 20251231
    GROUP BY customer_id
) t ON t.customer_id = s.customer_id
GROUP BY 1, 2 ORDER BY 1, revenue DESC;

-- 7b. Value per acquisition channel, with no double counting. -> acquisition_value.csv
WITH per_customer AS (
    SELECT customer_id, COUNT(*) AS orders, SUM(transaction_total) AS revenue,
           SUM(transaction_total - transaction_cost) AS profit
    FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN 20250101 AND 20251231
    GROUP BY customer_id
)
SELECT c.signup_channel, COUNT(*) AS customers,
       ROUND(SUM(CASE WHEN p.orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS repeat_pct,
       ROUND(SUM(p.revenue), 2) AS revenue,
       ROUND(SUM(p.profit), 2) AS profit,
       ROUND(SUM(p.revenue) / COUNT(*), 2) AS arpu
FROM per_customer p JOIN customers c ON c.customer_id = p.customer_id
GROUP BY 1 ORDER BY revenue DESC;


-- 8a. Monthly cohorts. These are first purchases inside the window, not new signups. -> summary_cohort.csv
WITH first_purchase AS (
    SELECT customer_id, MIN(transaction_timestamp) AS first_purchase_date
    FROM transactions
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
),
activity AS (
    SELECT t.customer_id,
           date_trunc('month', f.first_purchase_date) AS cohort_month,
           date_diff('month', f.first_purchase_date, t.transaction_timestamp) AS month_index
    FROM transactions t
    JOIN first_purchase f ON f.customer_id = t.customer_id
    WHERE t.transaction_date_id BETWEEN 20250101 AND 20251231
      AND f.first_purchase_date >= DATE '2025-01-01'
)
SELECT CAST(cohort_month AS DATE) AS cohort_month, month_index,
       COUNT(DISTINCT customer_id) AS active_customers
FROM activity GROUP BY 1, 2 ORDER BY 1, 2;

-- 8b. How many of each cohort actually signed up in 2025. -> cohort_composition.csv
WITH first_purchase AS (
    SELECT customer_id, MIN(transaction_timestamp) AS first_purchase_date
    FROM transactions
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
)
SELECT CAST(date_trunc('month', f.first_purchase_date) AS DATE) AS cohort_month,
       COUNT(*) AS customers,
       SUM(CASE WHEN YEAR(c.signup_date) = 2025 THEN 1 ELSE 0 END) AS new_signups,
       SUM(CASE WHEN YEAR(c.signup_date) < 2025 THEN 1 ELSE 0 END) AS existing_customers
FROM first_purchase f JOIN customers c ON c.customer_id = f.customer_id
WHERE f.first_purchase_date >= DATE '2025-01-01'
GROUP BY 1 ORDER BY 1;


-- 9. Webrooming. EXISTS avoids the row fan-out a join would create. -> webrooming.csv
WITH store_orders AS (
    SELECT customer_id, transaction_id, transaction_total,
           CAST(strptime(CAST(transaction_date_id AS VARCHAR), '%Y%m%d') AS DATE) AS tx_date
    FROM transactions
    WHERE sales_channel = 'Store' AND customer_id IS NOT NULL
      AND transaction_date_id BETWEEN 20250101 AND 20251231
),
browse AS (
    SELECT DISTINCT customer_id,
           CAST(strptime(CAST(session_start_date_id AS VARCHAR), '%Y%m%d') AS DATE) AS browse_date
    FROM clickstream
    WHERE customer_id IS NOT NULL AND purchased_flag = FALSE
      AND session_start_date_id BETWEEN 20250101 AND 20251231
),
flagged AS (
    SELECT s.customer_id, s.transaction_id, s.transaction_total,
           CASE WHEN EXISTS (
               SELECT 1 FROM browse b
               WHERE b.customer_id = s.customer_id AND b.browse_date <= s.tx_date
           ) THEN 1 ELSE 0 END AS browsed_any,
           CASE WHEN EXISTS (
               SELECT 1 FROM browse b
               WHERE b.customer_id = s.customer_id
                 AND b.browse_date BETWEEN s.tx_date - INTERVAL 14 DAY AND s.tx_date
           ) THEN 1 ELSE 0 END AS browsed_14d
    FROM store_orders s
),
per_customer AS (
    SELECT customer_id, MAX(browsed_any) AS browsed_any, MAX(browsed_14d) AS browsed_14d,
           COUNT(*) AS orders, SUM(transaction_total) AS revenue
    FROM flagged GROUP BY customer_id
)
SELECT 'any_time' AS window_label, browsed_any AS browsed, COUNT(*) AS customers,
       SUM(orders) AS orders, ROUND(SUM(revenue), 2) AS revenue,
       ROUND(SUM(revenue) / COUNT(*), 2) AS arpu
FROM per_customer GROUP BY 2
UNION ALL
SELECT '14_days', browsed_14d, COUNT(*), SUM(orders), ROUND(SUM(revenue), 2),
       ROUND(SUM(revenue) / COUNT(*), 2)
FROM per_customer GROUP BY 2
ORDER BY 1, 2;


-- 10. Buying cycle across all three years, so long gaps are not cut off by the window. -> purchase_cycle.csv
WITH ordered AS (
    SELECT customer_id, transaction_timestamp,
           LAG(transaction_timestamp) OVER (
               PARTITION BY customer_id ORDER BY transaction_timestamp) AS previous_purchase
    FROM transactions
    WHERE customer_id IS NOT NULL
),
gaps AS (
    SELECT date_diff('day', previous_purchase, transaction_timestamp) AS gap_days
    FROM ordered WHERE previous_purchase IS NOT NULL
)
SELECT COUNT(*) AS gaps,
       ROUND(AVG(gap_days), 1) AS mean_days,
       MEDIAN(gap_days) AS median_days,
       quantile_cont(gap_days, 0.25) AS p25_days,
       quantile_cont(gap_days, 0.75) AS p75_days,
       ROUND(SUM(CASE WHEN gap_days <= 30 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_within_30d,
       ROUND(SUM(CASE WHEN gap_days <= 90 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_within_90d
FROM gaps;


-- 11. Three year trend. The only output not limited to 2025. -> yearly_trend.csv
WITH sessions AS (
    SELECT LEFT(CAST(session_start_date_id AS VARCHAR), 4) AS year,
           COUNT(*) AS sessions,
           SUM(CAST(purchased_flag AS INT)) AS purchase_sessions
    FROM clickstream GROUP BY 1
),
orders AS (
    SELECT LEFT(CAST(transaction_date_id AS VARCHAR), 4) AS year,
           COUNT(*) AS orders,
           SUM(transaction_total) AS revenue,
           SUM(transaction_total - transaction_cost) AS profit,
           SUM(CASE WHEN sales_channel = 'Store' THEN transaction_total ELSE 0 END) AS store_revenue
    FROM transactions GROUP BY 1
)
SELECT s.year, s.sessions, s.purchase_sessions, o.orders,
       ROUND(o.revenue, 2) AS revenue, ROUND(o.profit, 2) AS profit,
       ROUND(s.purchase_sessions * 100.0 / s.sessions, 2) AS conversion_pct,
       ROUND(o.store_revenue * 100.0 / o.revenue, 2) AS store_revenue_pct
FROM sessions s JOIN orders o ON s.year = o.year
ORDER BY s.year;


-- 12. Category margin. Margin varies by category, not by price tier. -> category_performance.csv
SELECT cat.category_name,
       COUNT(*) AS lines_sold,
       SUM(s.quantity) AS units,
       ROUND(SUM(s.line_total), 2) AS revenue,
       ROUND(SUM(s.line_total - s.line_cost), 2) AS profit,
       ROUND(SUM(s.line_total - s.line_cost) * 100.0 / SUM(s.line_total), 2) AS margin_pct
FROM sales s
JOIN products p ON p.product_id = s.product_id
JOIN categories cat ON cat.category_id = p.category_id
WHERE s.transaction_date_id BETWEEN 20250101 AND 20251231
GROUP BY 1 ORDER BY revenue DESC;


-- Basket queries use completed orders only, to match the net revenue definition.
CREATE TEMP VIEW basket AS
SELECT DISTINCT s.transaction_id, s.product_id, p.category_id
FROM sales s
JOIN transactions t ON t.transaction_id = s.transaction_id
JOIN products p ON p.product_id = s.product_id
WHERE s.transaction_date_id BETWEEN 20250101 AND 20251231
  AND t.transaction_status = 'Completed';

-- 13. Basket size and how many product pairs clear each support threshold. -> basket_summary.csv
WITH sizes AS (
    SELECT transaction_id, COUNT(*) AS items FROM basket GROUP BY 1
),
pairs AS (
    SELECT a.product_id AS pa, b.product_id AS pb, COUNT(*) AS pair_orders
    FROM basket a JOIN basket b
      ON a.transaction_id = b.transaction_id AND a.product_id < b.product_id
    GROUP BY 1, 2
)
SELECT (SELECT COUNT(DISTINCT transaction_id) FROM basket) AS orders,
       (SELECT ROUND(AVG(items), 2) FROM sizes) AS avg_items,
       (SELECT SUM(CASE WHEN items = 1 THEN 1 ELSE 0 END) FROM sizes) AS single_item_orders,
       (SELECT COUNT(*) FROM pairs) AS distinct_pairs,
       (SELECT COUNT(*) FROM pairs WHERE pair_orders >= 50) AS pairs_ge_50,
       (SELECT COUNT(*) FROM pairs WHERE pair_orders >= 100) AS pairs_ge_100,
       (SELECT COUNT(*) FROM pairs WHERE pair_orders >= 200) AS pairs_ge_200;

-- 14. Product pairs above 100 shared orders. Returns no rows: no pair reaches 50. -> basket_product_rules.csv
WITH totals AS (SELECT COUNT(DISTINCT transaction_id) AS n_orders FROM basket),
product_orders AS (
    SELECT product_id, COUNT(*) AS orders_with_product FROM basket GROUP BY 1
),
pairs AS (
    SELECT a.product_id AS product_a, b.product_id AS product_b, COUNT(*) AS pair_orders
    FROM basket a JOIN basket b
      ON a.transaction_id = b.transaction_id AND a.product_id < b.product_id
    GROUP BY 1, 2
)
SELECT pa.product_name AS product_a_name,
       pb.product_name AS product_b_name,
       ca.category_name AS category_a,
       cb.category_name AS category_b,
       p.pair_orders,
       ROUND(p.pair_orders * 100.0 / t.n_orders, 3) AS support_pct,
       ROUND(p.pair_orders * 100.0 / oa.orders_with_product, 2) AS confidence_a_to_b_pct,
       ROUND(p.pair_orders * 100.0 / ob.orders_with_product, 2) AS confidence_b_to_a_pct,
       ROUND(p.pair_orders * t.n_orders * 1.0
             / (oa.orders_with_product * ob.orders_with_product), 3) AS lift
FROM pairs p
CROSS JOIN totals t
JOIN product_orders oa ON oa.product_id = p.product_a
JOIN product_orders ob ON ob.product_id = p.product_b
JOIN products pa ON pa.product_id = p.product_a
JOIN products pb ON pb.product_id = p.product_b
JOIN categories ca ON ca.category_id = pa.category_id
JOIN categories cb ON cb.category_id = pb.category_id
WHERE p.pair_orders >= 100
ORDER BY lift DESC;

-- 15. Category pairs. Same-category pairs are excluded because the question is cross-sell. -> basket_category_rules.csv
WITH cat_basket AS (
    SELECT DISTINCT transaction_id, category_id FROM basket
),
totals AS (SELECT COUNT(DISTINCT transaction_id) AS n_orders FROM basket),
cat_orders AS (
    SELECT category_id, COUNT(*) AS orders_with_category FROM cat_basket GROUP BY 1
),
pairs AS (
    SELECT a.category_id AS category_a, b.category_id AS category_b, COUNT(*) AS pair_orders
    FROM cat_basket a JOIN cat_basket b
      ON a.transaction_id = b.transaction_id AND a.category_id < b.category_id
    GROUP BY 1, 2
)
SELECT ca.category_name AS category_a,
       cb.category_name AS category_b,
       p.pair_orders,
       ROUND(p.pair_orders * 100.0 / t.n_orders, 3) AS support_pct,
       ROUND(p.pair_orders * 100.0 / oa.orders_with_category, 2) AS confidence_a_to_b_pct,
       ROUND(p.pair_orders * 100.0 / ob.orders_with_category, 2) AS confidence_b_to_a_pct,
       ROUND(p.pair_orders * t.n_orders * 1.0
             / (oa.orders_with_category * ob.orders_with_category), 3) AS lift
FROM pairs p
CROSS JOIN totals t
JOIN cat_orders oa ON oa.category_id = p.category_a
JOIN cat_orders ob ON ob.category_id = p.category_b
JOIN categories ca ON ca.category_id = p.category_a
JOIN categories cb ON cb.category_id = p.category_b
ORDER BY lift DESC;


-- 16. Days to second purchase. Jan-Jun cohorts only, so everyone has 180+ days of follow-up.
--     The Python layer turns this into second_purchase_summary.csv and second_purchase_curve.csv.
WITH numbered AS (
    SELECT customer_id, transaction_timestamp,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id ORDER BY transaction_timestamp) AS purchase_number
    FROM transactions
    WHERE customer_id IS NOT NULL
),
first_two AS (
    SELECT customer_id,
           MIN(CASE WHEN purchase_number = 1 THEN transaction_timestamp END) AS first_purchase,
           MIN(CASE WHEN purchase_number = 2 THEN transaction_timestamp END) AS second_purchase
    FROM numbered GROUP BY customer_id
)
SELECT customer_id,
       CAST(first_purchase AS DATE) AS first_purchase,
       date_diff('day', first_purchase, second_purchase) AS days_to_second
FROM first_two
WHERE first_purchase >= DATE '2025-01-01' AND first_purchase < DATE '2025-07-01';

-- 17. Same measure with no cohort restriction, for comparison. -> second_purchase_all_years.csv
WITH numbered AS (
    SELECT customer_id, transaction_timestamp,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id ORDER BY transaction_timestamp) AS purchase_number
    FROM transactions
    WHERE customer_id IS NOT NULL
),
first_two AS (
    SELECT customer_id,
           MIN(CASE WHEN purchase_number = 1 THEN transaction_timestamp END) AS first_purchase,
           MIN(CASE WHEN purchase_number = 2 THEN transaction_timestamp END) AS second_purchase
    FROM numbered GROUP BY customer_id
),
gaps AS (
    SELECT date_diff('day', first_purchase, second_purchase) AS days_to_second
    FROM first_two
)
SELECT COUNT(*) AS customers,
       COUNT(days_to_second) AS repeated,
       ROUND(COUNT(days_to_second) * 100.0 / COUNT(*), 2) AS repeat_pct,
       MEDIAN(days_to_second) AS median_days_to_second,
       ROUND(AVG(days_to_second), 1) AS mean_days_to_second
FROM gaps;


-- 18. Customer level revenue and channel. Input to the chi-square and Lorenz curve. (analysis.py)
SELECT t.customer_id, c.signup_channel,
       COUNT(*) AS orders,
       SUM(t.transaction_total) AS revenue
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
WHERE t.customer_id IS NOT NULL
  AND t.transaction_date_id BETWEEN 20250101 AND 20251231
GROUP BY 1, 2;

-- 19. First and second purchase for every 2025 first-time buyer. Input to Kaplan-Meier. (analysis.py)
WITH numbered AS (
    SELECT customer_id, transaction_timestamp,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id ORDER BY transaction_timestamp) AS n
    FROM transactions
    WHERE customer_id IS NOT NULL
),
paired AS (
    SELECT customer_id,
           MIN(CASE WHEN n = 1 THEN transaction_timestamp END) AS first_purchase,
           MIN(CASE WHEN n = 2 THEN transaction_timestamp END) AS second_purchase
    FROM numbered GROUP BY 1
)
SELECT * FROM paired WHERE first_purchase >= DATE '2025-01-01';