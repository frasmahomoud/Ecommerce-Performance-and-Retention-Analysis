import duckdb
import pandas as pd
import numpy as np

# ==========================================
# 1. Extract & Aggregate RFM Base Data (Using DuckDB for speed)
# ==========================================
query_rfm = """
SELECT
    customer_id,
    MAX(transaction_timestamp) AS last_purchase_date,
    COUNT(DISTINCT transaction_date_id) AS Frequency,
    SUM(transaction_total) AS Monetary
FROM 'fact_transaction.parquet'
WHERE customer_id IS NOT NULL
  AND transaction_date_id BETWEEN 20250101 AND 20251231
GROUP BY customer_id
"""
rfm_raw = duckdb.query(query_rfm).to_df()
# Cast Monetary to float to avoid Decimal computation errors in Pandas qcut
rfm_raw['Monetary'] = rfm_raw['Monetary'].astype(float)

# Calculate Recency in days (Adding 1 day to snapshot to avoid 0 recency)
reference_date = rfm_raw['last_purchase_date'].max() + pd.Timedelta(days=1)
rfm_raw['Recency'] = (reference_date - rfm_raw['last_purchase_date']).dt.days


# ==========================================
# 2. RFM Scoring & Segmentation (Using Pandas)
# ==========================================
rfm = rfm_raw.set_index('customer_id')

# Assign quartiles (1-4)
rfm['R'] = pd.qcut(rfm['Recency'], q=4, labels=[4, 3, 2, 1])
rfm['F'] = pd.qcut(rfm['Frequency'].rank(method='first'), q=4, labels=[1, 2, 3, 4])
rfm['M'] = pd.qcut(rfm['Monetary'], q=4, labels=[1, 2, 3, 4])

# Combine into a single score
rfm['RFM_Score'] = rfm['R'].astype(str) + rfm['F'].astype(str) + rfm['M'].astype(str)

# Apply business logic for segments
conditions = [
    rfm['RFM_Score'] == '444',
    (rfm['R'] == 4) & (rfm['F'] >= 3),
    (rfm['R'] <= 2) & (rfm['F'] >= 3),
    rfm['R'] == 1
]

choices = ['VIP', 'Loyal Customers', 'At Risk', 'Lost']
rfm['Segment'] = np.select(conditions, choices, default='Regular')


# ==========================================
# 3. The Acquisition Trap: Linking Segments to Traffic Sources
# ==========================================
# Reset index to use customer_id in the SQL join
rfm_reset = rfm.reset_index()

# Use DuckDB to join the segmented Pandas dataframe with the clickstream parquet file
query_traffic = """
SELECT
    r.Segment,
    c.traffic_source AS Traffic_Source,
    COUNT(DISTINCT r.customer_id) AS Total_Customers
FROM rfm_reset r
JOIN 'fact_clickstream.parquet' c ON r.customer_id = c.customer_id
WHERE c.purchased_flag = True
GROUP BY r.Segment, c.traffic_source
ORDER BY r.Segment, Total_Customers DESC
"""
traffic_segments = duckdb.query(query_traffic).to_df()

# Calculate percentage distribution within each segment to expose channel quality
traffic_segments['Percentage_in_Segment'] = traffic_segments.groupby('Segment')['Total_Customers'].transform(lambda x: round((x / x.sum()) * 100, 2))

# Display the final cross-tabulated dataset
print(traffic_segments.to_string(index=False))
