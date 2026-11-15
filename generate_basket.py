import os
import duckdb
import pandas as pd

DATA_FOLDER = "."
OUT_FOLDER = "dashboards_CSV"
YEAR_START = 20250101
YEAR_END = 20251231
MIN_PAIR_COUNT = 100  # pairs below this are too rare for a stable lift

os.makedirs(OUT_FOLDER, exist_ok=True)
con = duckdb.connect()

for name, file in [
    ("sales", "fact_sale"),
    ("transactions", "fact_transaction"),
    ("products", "dim_product"),
    ("categories", "dim_category"),
]:
    con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{DATA_FOLDER}/{file}.parquet')")


def save(name, sql):
    df = con.sql(sql).df()
    df.to_csv(f"{OUT_FOLDER}/{name}.csv", index=False)
    print(f"saved {name}.csv  ({len(df)} rows)")
    return df


# Basket analysis uses completed orders only, to match the net revenue definition.
basket_sql = f"""
WITH basket AS (
    SELECT DISTINCT s.transaction_id, s.product_id, p.category_id
    FROM sales s
    JOIN transactions t ON t.transaction_id = s.transaction_id
    JOIN products p ON p.product_id = s.product_id
    WHERE s.transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
      AND t.transaction_status = 'Completed'
),
totals AS (
    SELECT COUNT(DISTINCT transaction_id) AS n_orders FROM basket
)
"""

# 1. Context for the rules: basket size and how many pairs clear each threshold.
save("basket_summary", basket_sql + """
, sizes AS (
    SELECT transaction_id, COUNT(*) AS items FROM basket GROUP BY 1
),
pairs AS (
    SELECT a.product_id AS pa, b.product_id AS pb, COUNT(*) AS pair_orders
    FROM basket a JOIN basket b
      ON a.transaction_id = b.transaction_id AND a.product_id < b.product_id
    GROUP BY 1, 2
)
SELECT (SELECT n_orders FROM totals) AS orders,
       (SELECT ROUND(AVG(items), 2) FROM sizes) AS avg_items,
       (SELECT SUM(CASE WHEN items = 1 THEN 1 ELSE 0 END) FROM sizes) AS single_item_orders,
       (SELECT COUNT(*) FROM pairs) AS distinct_pairs,
       (SELECT COUNT(*) FROM pairs WHERE pair_orders >= 50) AS pairs_ge_50,
       (SELECT COUNT(*) FROM pairs WHERE pair_orders >= 100) AS pairs_ge_100,
       (SELECT COUNT(*) FROM pairs WHERE pair_orders >= 200) AS pairs_ge_200
""")

# 2. Product pairs. Lift above 1 means the two products appear together more than chance.
save("basket_product_rules", basket_sql + f"""
, product_orders AS (
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
WHERE p.pair_orders >= {MIN_PAIR_COUNT}
ORDER BY lift DESC
""")

# 3. Category pairs. Fewer combinations, so the signal is stronger than at product level.
save("basket_category_rules", basket_sql + """
, cat_basket AS (
    SELECT DISTINCT transaction_id, category_id FROM basket
),
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
ORDER BY lift DESC
""")

# 4. Time to second purchase. Only Jan-Jun cohorts, so every customer has 6+ months of follow-up.
per_customer = con.sql("""
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
    FROM numbered
    GROUP BY customer_id
)
SELECT customer_id,
       CAST(first_purchase AS DATE) AS first_purchase,
       date_diff('day', first_purchase, second_purchase) AS days_to_second
FROM first_two
WHERE first_purchase >= DATE '2025-01-01' AND first_purchase < DATE '2025-07-01'
""").df()

total = len(per_customer)
repeated = per_customer["days_to_second"].notna()
gaps = per_customer.loc[repeated, "days_to_second"]

summary = pd.DataFrame([{
    "cohort_customers": total,
    "repeated_customers": int(repeated.sum()),
    "repeat_pct": round(repeated.sum() * 100.0 / total, 2),
    "median_days_to_second": float(gaps.median()),
    "p25_days": float(gaps.quantile(0.25)),
    "p75_days": float(gaps.quantile(0.75)),
    "pct_within_30d": round((gaps <= 30).sum() * 100.0 / total, 2),
    "pct_within_90d": round((gaps <= 90).sum() * 100.0 / total, 2),
    "pct_within_180d": round((gaps <= 180).sum() * 100.0 / total, 2),
}])
summary.to_csv(f"{OUT_FOLDER}/second_purchase_summary.csv", index=False)
print(f"saved second_purchase_summary.csv  ({len(summary)} rows)")

curve = pd.DataFrame({
    "days_since_first_purchase": [30, 60, 90, 120, 180],
})
curve["cumulative_repeated"] = curve["days_since_first_purchase"].apply(
    lambda d: int((gaps <= d).sum()))
curve["cumulative_repeat_pct"] = (curve["cumulative_repeated"] * 100.0 / total).round(2)
curve.to_csv(f"{OUT_FOLDER}/second_purchase_curve.csv", index=False)
print(f"saved second_purchase_curve.csv  ({len(curve)} rows)")

# 5. Same measure without the cohort restriction, for comparison.
save("second_purchase_all_years", """
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
    FROM numbered
    GROUP BY customer_id
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
FROM gaps
""")

print("\n--- basket_summary ---")
print(pd.read_csv(f"{OUT_FOLDER}/basket_summary.csv").to_string(index=False))
print("\n--- second_purchase_summary ---")
print(summary.to_string(index=False))
