
# ElecMart — Funnel, Retention & Customer Value Analysis
![Python](https://img.shields.io/badge/Python-3.11-blue)
![DuckDB](https://img.shields.io/badge/DuckDB-SQL-yellow)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)


**[Live Dashboard](https://ecommerce-performance-and-retention-analysis.streamlit.app/)**

Funnel, retention and customer-value analysis of 14.5M sessions and 900K transactions
from a synthetic omnichannel electronics retailer. Main window: 2025, with a three-year
trend for context.

<img width="1838" height="933" alt="1" src="https://github.com/user-attachments/assets/25d12090-0e19-4558-bb73-06b9f1cfcea8" />

## What this project does

Reads the raw Kaggle parquet files, builds every metric in SQL, adds a statistical layer
in Python, and serves the results through an interactive Streamlit dashboard. The
dashboard reads pre-aggregated CSVs only, so the numbers on screen and the numbers in the
queries come from the same place.

## What I found

**The business is moving online.** Store share of revenue fell from 54.2% to 28.9% across
2023–2025, while session conversion rose from 2.37% to 4.93%. Online now drives 71% of
revenue directly.

**"At Risk" is the revenue core, not a leak.** That segment is 26.7% of customers but
42.1% of revenue ($153.8M) — more than VIP and Loyal combined (33.6%).

**The 80/20 rule does not hold.** 35.4% of customers account for 80% of revenue. Top 10%
hold 41.4%, top 20% hold 61.7%.

**Retention is seasonal, not lifecycle-driven.** Every cohort sits near 25% in December
and near 16% mid-year, regardless of age. The apparent rise by cohort age is a composition
effect, not improving loyalty.

**Silence in month 1 is not churn.** Median time to second purchase is 124 days. Only
17.7% buy again within 30 days, but 61.8% do within 180.
> Two medians appear in this project and they measure different things.
> **86 days** is the median among the 6,871 Jan–Jun 2025 customers who did buy again —
> conditional on repurchase, with 180+ days of follow-up for everyone.
> **124 days** is the Kaplan-Meier median across all 16,387 customers whose first purchase
> fell in 2025, treating the 6,575 who had not bought again by year end as censored.
> The dashboard shows 86. The reminder timing uses 124, because it answers when half of a
> cohort will have bought again, not how long the fastest half took.

**Mobile converts worst and is worth the most.** Lowest session conversion (4.19% vs
Desktop 6.16%, gap 1.97 pp, 95% CI −2.01 to −1.92) yet the highest AOV ($1,004) and the
highest revenue per customer by signup channel ($3,815 vs Online $2,779).

**Returns were being counted as revenue.** 5.5% of orders are returned. Gross revenue
$451.7M vs net $426.6M.

<img width="1790" height="838" alt="2" src="https://github.com/user-attachments/assets/1283e5af-326c-4109-97a9-cef0180b9644" />

<img width="1787" height="667" alt="3 1" src="https://github.com/user-attachments/assets/67a7e826-ac5b-48f8-a5a8-2bb6e10899f6" />

## What I would do about it

- **Time retention messages to the real cycle.** Send the repeat-purchase reminder around
  day 90–120, not day 30. A day-30 campaign targets a window where only 17.7% are ready.
- **Protect the At Risk pool first.** $153.8M sits in a segment that is cooling off. It
  deserves the retention budget ahead of VIP perks.
- **Stop treating mobile conversion as a failure.** It is the best acquisition channel by
  customer value. Judge it on signup value, not session conversion.
- **Push margin, not just volume.** Kitchen Appliances runs at 30.3% margin, Gaming at
  11.1%. Category mix is a lever the current reporting ignores.
- **Do not build cross-category bundles.** All 36 category pairs have lift below 1
  (0.475 to 0.882), and the strongest product pair appears in only 36 of 431,377 orders.
  Same-category pairs are excluded by design, because the question is cross-sell rather
  than multi-buy. Baskets are capped at 1–3 items, so any within-category clustering
  pushes cross-category lift down mechanically. The reading is "no cross-category
  bundling signal", not "categories repel each other".
- **Report net revenue and track return rate** as a standing KPI.

<img width="1762" height="852" alt="4 1" src="https://github.com/user-attachments/assets/26431f9c-399f-4066-8a38-b59caa5751d7" />

## What changed after verification

The first version of this project made claims that did not survive checking against the
raw data. Three examples:

- An "AOV of $1,628" was revenue per customer. True AOV is $989.
- An "86% month-1 churn rate" treated non-purchase as churn in a non-contractual business.
  Replaced with a censoring-aware time-to-second-purchase curve.
- RFM scores were assigned by row order for customers with identical purchase counts,
  affecting about 11,657 customers. Replaced with fixed value bands.

Statistical tests, confidence intervals and the full metric definitions live in
`analysis.py`, `analysis_output/`, and the Definitions tab of the dashboard.

## Tech stack

Python · DuckDB (SQL) · pandas · SciPy · Plotly · Streamlit

## Run it yourself


The dashboard performs no aggregation of its own. Shares are recomputed from the counts
already present in each CSV, so a stale percentage column can never change what you see.
The SQL shown in each tab is the same SQL the generators run.

```bash
kaggle datasets download -d ajibsss/elecmart-retail-analytics-dataset
unzip -q elecmart-retail-analytics-dataset.zip
pip install -r requirements.txt
python generate_summary.py
python generate_basket.py
python analysis.py
streamlit run app.py
```
app.py                dashboard, reads CSVs only
generate_summary.py   all SQL, produces dashboards_CSV/
generate_basket.py    basket affinity + second purchase, 6 CSVs
analysis.py           statistical layer, produces analysis_output/
dashboards_CSV/       26 aggregated files
analysis_output/      statistical_results.csv, curve data, 2 figures
```

## Data and limitations

Source: [ElecMart Retail Analytics Dataset](https://www.kaggle.com/datasets/ajibsss/elecmart-retail-analytics-dataset)
(CC BY-SA 4.0). The data is synthetic.

- 19% of 2025 revenue has no customer_id, so customer-level analysis covers 81% of revenue.
- Store orders carry no session_id, so store revenue cannot be attributed to a channel.
- Clickstream has no product_id, so browsing cannot be linked to the product purchased.
- No advertising spend exists in the schema, so CAC and ROI cannot be computed.
- Session duration is capped at 12 minutes with the same median on every device, so it
  carries no behavioural signal.

All comparisons are observational. No A/B test or holdout exists in this data.
