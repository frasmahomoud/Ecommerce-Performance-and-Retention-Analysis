import os
import duckdb
import pandas as pd

DATA_FOLDER = "."
OUT_FOLDER = "dashboards_CSV"
YEAR_START = 20250101
YEAR_END = 20251231
SNAPSHOT = "2026-01-01"  # day after the last transaction, fixed so results are reproducible

os.makedirs(OUT_FOLDER, exist_ok=True)
con = duckdb.connect()

# Views keep the queries short and readable.
for name, file in [
    ("clickstream", "fact_clickstream"),
    ("transactions", "fact_transaction"),
    ("sales", "fact_sale"),
    ("customers", "dim_customer"),
    ("products", "dim_product"),
    ("catROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS customer_pctegories", "dim_category"),
]:
    con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{DATA_FOLDER}/{file}.parquet')")


def save(name, sql):
    df = con.sql(sql).df()
    df.to_csv(f"{OUT_FOLDER}/{name}.csv", index=False)
    print(f"saved {name}.csv  ({len(df)} rows)")
    return df


# 1. KPIs. Gross keeps the old column names, net excludes returned orders.
save("summary_kpis", f"""
WITH sessions AS (
    SELECT COUNT(*) AS total_visitors,
           COUNT(DISTINCT CASE WHEN purchased_flag THEN customer_id END) AS total_buyers,
           SUM(CASE WHEN number_of_pages_viewed = 1 THEN 1 ELSE 0 END) AS single_page_sessions
    FROM clickstream
    WHERE session_start_date_id BETWEEN {YEAR_START} AND {YEAR_END}
),
orders AS (
    SELECT COUNT(*) AS total_orders,
           SUM(transaction_total) AS total_revenue,
           SUM(transaction_cost) AS total_cost,
           SUM(transaction_total - transaction_cost) AS total_profit,
           SUM(CASE WHEN transaction_status = 'Completed' THEN 1 ELSE 0 END) AS net_orders,
           SUM(CASE WHEN transaction_status = 'Completed' THEN transaction_total ELSE 0 END) AS net_revenue,
           SUM(CASE WHEN transaction_status = 'Completed' THEN transaction_total - transaction_cost ELSE 0 END) AS net_profit,
           SUM(CASE WHEN customer_id IS NULL THEN transaction_total ELSE 0 END) AS guest_revenue
    FROM transactions
    WHERE transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
)
SELECT sessions.*, orders.*,
       ROUND(total_revenue / total_orders, 2) AS avg_order_value,
       ROUND(net_revenue / net_orders, 2) AS net_aov,
       ROUND((total_orders - net_orders) * 100.0 / total_orders, 2) AS return_rate_pct,
       ROUND(guest_revenue * 100.0 / total_revenue, 2) AS guest_revenue_pct,
       ROUND(single_page_sessions * 100.0 / total_visitors, 2) AS single_page_pct
FROM sessions, orders
""")

# 2. Funnel counts. Column names unchanged so the existing chart keeps working.
save("summary_funnel", f"""
SELECT COUNT(*) AS "Total Sessions",
       SUM(CAST(product_page_visited_flag AS INT)) AS "Viewed Product",
       SUM(CAST(added_to_cart_flag AS INT)) AS "Added to Cart",
       SUM(CAST(purchased_flag AS INT)) AS "Purchased"
FROM clickstream
WHERE session_start_date_id BETWEEN {YEAR_START} AND {YEAR_END}
""")

save("funnel_rates", f"""
WITH stages AS (
    SELECT COUNT(*) AS sessions,
           SUM(CAST(product_page_visited_flag AS INT)) AS viewed,
           SUM(CAST(added_to_cart_flag AS INT)) AS cart,
           SUM(CAST(purchased_flag AS INT)) AS purchased,
           SUM(CASE WHEN number_of_pages_viewed = 1 THEN 1 ELSE 0 END) AS single_page
    FROM clickstream
    WHERE session_start_date_id BETWEEN {YEAR_START} AND {YEAR_END}
)
SELECT ROUND(viewed * 100.0 / sessions, 2) AS visit_to_view_pct,
       ROUND(cart * 100.0 / viewed, 2) AS view_to_cart_pct,
       ROUND(purchased * 100.0 / cart, 2) AS cart_to_purchase_pct,
       ROUND(purchased * 100.0 / sessions, 2) AS overall_conversion_pct,
       ROUND((cart - purchased) * 100.0 / cart, 2) AS cart_abandonment_pct,
       ROUND(single_page * 100.0 / sessions, 2) AS single_page_bounce_pct
FROM stages
""")

# 3. Traffic. Revenue comes from the session_id link, so each order is counted once.
save("summary_traffic", f"""
WITH sessions AS (
    SELECT traffic_source,
           COUNT(*) AS total_sessions,
           SUM(CAST(product_page_visited_flag AS INT)) AS viewed,
           SUM(CAST(added_to_cart_flag AS INT)) AS cart,
           SUM(CAST(purchased_flag AS INT)) AS purchases
    FROM clickstream
    WHERE session_start_date_id BETWEEN {YEAR_START} AND {YEAR_END}
    GROUP BY traffic_source
),
orders AS (
    SELECT c.traffic_source,
           COUNT(*) AS orders,
           SUM(t.transaction_total) AS revenue,
           SUM(t.transaction_total - t.transaction_cost) AS profit
    FROM transactions t
    JOIN clickstream c ON c.session_id = t.session_id
    WHERE t.transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
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
ORDER BY overall_conversion_rate DESC
""")

# 4. Devices. Duration is capped at 12 minutes in the source data.
save("summary_devices", f"""
WITH sessions AS (
    SELECT device_type,
           COUNT(*) AS total_sessions,
           SUM(CAST(purchased_flag AS INT)) AS purchases,
           AVG(number_of_pages_viewed) AS avg_pages,
           AVG(date_diff('second', session_start_time, session_end_time) / 60.0) AS avg_minutes,
           MEDIAN(date_diff('second', session_start_time, session_end_time) / 60.0) AS median_minutes
    FROM clickstream
    WHERE session_start_date_id BETWEEN {YEAR_START} AND {YEAR_END}
    GROUP BY device_type
),
orders AS (
    SELECT c.device_type, COUNT(*) AS orders, SUM(t.transaction_total) AS revenue
    FROM transactions t
    JOIN clickstream c ON c.session_id = t.session_id
    WHERE t.transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
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
ORDER BY s.total_sessions DESC
""")

# 5. Repeat buyers. Repeat means more than one transaction inside the year.
save("summary_retention_profile", f"""
WITH per_customer AS (
    SELECT customer_id, COUNT(*) AS orders
    FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
    GROUP BY customer_id
)
SELECT CASE WHEN orders > 1 THEN 'Repeat Customer' ELSE 'One-Time Buyer' END AS customer_type,
       COUNT(*) AS customer_count
FROM per_customer
GROUP BY 1
""")

# 6. RFM. Scores are assigned by value, so equal inputs always get equal scores.
#    Frequency uses fixed bands because quartile edges fall inside large tie blocks.
rfm_sql = f"""
WITH base AS (
    SELECT customer_id,
           date_diff('day', MAX(transaction_timestamp), DATE '{SNAPSHOT}') AS recency,
           COUNT(*) AS frequency,
           SUM(transaction_total) AS monetary
    FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
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
),
segmented AS (
    SELECT *,
           CASE WHEN r_score = 4 AND f_score = 4 AND m_score = 4 THEN 'VIP'
                WHEN r_score = 4 AND f_score >= 3 THEN 'Loyal Customers'
                WHEN r_score IN (2, 3) AND f_score >= 3 THEN 'At Risk'
                WHEN r_score = 1 THEN 'Lost'
                ELSE 'Regular' END AS segment
    FROM scored
)
"""

save("summary_rfm_segments", rfm_sql + """
SELECT segment AS "Segment", COUNT(*) AS "Customer_Count"
FROM segmented GROUP BY 1 ORDER BY "Customer_Count" DESC
""")

save("segment_value", rfm_sql + f"""
SELECT s.segment,
       COUNT(DISTINCT s.customer_id) AS customers,
       COUNT(t.transaction_id) AS orders,
       ROUND(SUM(t.transaction_total), 2) AS revenue,
       ROUND(SUM(t.transaction_total - t.transaction_cost), 2) AS profit,
       ROUND(SUM(t.transaction_total) / COUNT(DISTINCT s.customer_id), 2) AS arpu,
       ROUND(SUM(t.transaction_total) * 100.0 / SUM(SUM(t.transaction_total)) OVER (), 2) AS revenue_pct,
       ROUND(COUNT(DISTINCT s.customer_id) * 100.0 / SUM(COUNT(DISTINCT s.customer_id)) OVER (), 2) AS customer_pct,
ROUND(COUNT(t.transaction_id) * 100.0 / SUM(COUNT(t.transaction_id)) OVER (), 2) AS order_pct
FROM segmented s
JOIN transactions t ON t.customer_id = s.customer_id
WHERE t.transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
GROUP BY s.segment
ORDER BY revenue DESC
""")

save("rfm_score_distribution", rfm_sql + """
SELECT r_score, f_score, m_score, COUNT(*) AS customers
FROM segmented GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
""")

# 7. Acquisition. signup_channel is one value per customer, so there is no double counting.
save("summary_acquisition", rfm_sql + f"""
SELECT s.segment AS "Segment", c.signup_channel, COUNT(*) AS total_customers,
       ROUND(SUM(t.revenue), 2) AS revenue
FROM segmented s
JOIN customers c ON c.customer_id = s.customer_id
JOIN (
    SELECT customer_id, SUM(transaction_total) AS revenue
    FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
    GROUP BY customer_id
) t ON t.customer_id = s.customer_id
GROUP BY 1, 2 ORDER BY 1, revenue DESC
""")

save("acquisition_value", f"""
WITH per_customer AS (
    SELECT customer_id, COUNT(*) AS orders, SUM(transaction_total) AS revenue,
           SUM(transaction_total - transaction_cost) AS profit
    FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
    GROUP BY customer_id
)
SELECT c.signup_channel, COUNT(*) AS customers,
       ROUND(SUM(CASE WHEN p.orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS repeat_pct,
       ROUND(SUM(p.revenue), 2) AS revenue,
       ROUND(SUM(p.profit), 2) AS profit,
       ROUND(SUM(p.revenue) / COUNT(*), 2) AS arpu
FROM per_customer p JOIN customers c ON c.customer_id = p.customer_id
GROUP BY 1 ORDER BY revenue DESC
""")

# 8. Cohorts. These are first purchases inside the data window, not new signups.
save("summary_cohort", f"""
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
    WHERE t.transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
      AND f.first_purchase_date >= DATE '2025-01-01'
)
SELECT CAST(cohort_month AS DATE) AS cohort_month, month_index,
       COUNT(DISTINCT customer_id) AS active_customers
FROM activity GROUP BY 1, 2 ORDER BY 1, 2
""")

save("cohort_composition", """
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
GROUP BY 1 ORDER BY 1
""")

# 9. Split calendar time from cohort age. Same numbers, two different groupings.
cohort = pd.read_csv(f"{OUT_FOLDER}/summary_cohort.csv")
matrix = cohort.pivot(index="cohort_month", columns="month_index", values="active_customers")
retention = matrix.divide(matrix[0], axis=0) * 100

rows = []
for cohort_month, values in retention.iterrows():
    start = pd.Timestamp(cohort_month)
    for age, value in values.items():
        if age == 0 or pd.isna(value):
            continue
        rows.append({
            "calendar_month": (start + pd.DateOffset(months=int(age))).strftime("%Y-%m"),
            "cohort_age": int(age),
            "retention_pct": value,
        })

long = pd.DataFrame(rows)
by_calendar = long.groupby("calendar_month").agg(
    avg_retention_pct=("retention_pct", "mean"), cohorts=("retention_pct", "size")).reset_index()
by_age = long.groupby("cohort_age").agg(
    avg_retention_pct=("retention_pct", "mean"), cohorts=("retention_pct", "size")).reset_index()

by_calendar.to_csv(f"{OUT_FOLDER}/retention_by_calendar_month.csv", index=False)
by_age.to_csv(f"{OUT_FOLDER}/retention_by_cohort_age.csv", index=False)
print("saved retention_by_calendar_month.csv and retention_by_cohort_age.csv")

# 10. Webrooming. EXISTS avoids the row fan-out that a join would cause.
save("webrooming", f"""
WITH store_orders AS (
    SELECT customer_id, transaction_id, transaction_total,
           CAST(strptime(CAST(transaction_date_id AS VARCHAR), '%Y%m%d') AS DATE) AS tx_date
    FROM transactions
    WHERE sales_channel = 'Store' AND customer_id IS NOT NULL
      AND transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
),
browse AS (
    SELECT DISTINCT customer_id,
           CAST(strptime(CAST(session_start_date_id AS VARCHAR), '%Y%m%d') AS DATE) AS browse_date
    FROM clickstream
    WHERE customer_id IS NOT NULL AND purchased_flag = FALSE
      AND session_start_date_id BETWEEN {YEAR_START} AND {YEAR_END}
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
ORDER BY 1, 2
""")

# 11. Buying cycle across all three years, so long gaps are not cut off by the window.
save("purchase_cycle", """
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
FROM gaps
""")

# 12. Three year trend. This is the only output that is not limited to 2025.
save("yearly_trend", """
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
ORDER BY s.year
""")

# 13. Category margin. Margin varies by category, not by price tier.
save("category_performance", f"""
SELECT cat.category_name,
       COUNT(*) AS lines_sold,
       SUM(s.quantity) AS units,
       ROUND(SUM(s.line_total), 2) AS revenue,
       ROUND(SUM(s.line_total - s.line_cost), 2) AS profit,
       ROUND(SUM(s.line_total - s.line_cost) * 100.0 / SUM(s.line_total), 2) AS margin_pct
FROM sales s
JOIN products p ON p.product_id = s.product_id
JOIN categories cat ON cat.category_id = p.category_id
WHERE s.transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
GROUP BY 1 ORDER BY revenue DESC
""")

# Reconciliation: segment revenue must equal revenue that has a customer attached.
segment_total = con.sql(rfm_sql + f"""
    SELECT ROUND(SUM(t.transaction_total), 2)
    FROM segmented s JOIN transactions t ON t.customer_id = s.customer_id
    WHERE t.transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
""").fetchone()[0]
identified = con.sql(f"""
    SELECT ROUND(SUM(transaction_total), 2) FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
""").fetchone()[0]
print(f"\nsegment revenue {segment_total} vs identified revenue {identified} -> "
      f"{'OK' if abs(segment_total - identified) < 1 else 'MISMATCH'}")