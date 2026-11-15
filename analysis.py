import os
import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

DATA_FOLDER = "."
CSV_FOLDER = "dashboards_CSV"
OUT_FOLDER = "analysis_output"
YEAR_START = 20250101
YEAR_END = 20251231
BOOTSTRAP_RUNS = 2000
SEED = 42

# numpy 2 renamed trapz to trapezoid, older versions only have trapz
trapezoid = np.trapezoid

os.makedirs(OUT_FOLDER, exist_ok=True)
rng = np.random.default_rng(SEED)
con = duckdb.connect()

con.execute(f"CREATE VIEW transactions AS SELECT * FROM read_parquet('{DATA_FOLDER}/fact_transaction.parquet')")
con.execute(f"CREATE VIEW clickstream AS SELECT * FROM read_parquet('{DATA_FOLDER}/fact_clickstream.parquet')")
con.execute(f"CREATE VIEW customers AS SELECT * FROM read_parquet('{DATA_FOLDER}/dim_customer.parquet')")

results = []


def record(name, value):
    results.append({"metric": name, "value": value})


def p_text(value):
    return "p < 1e-300" if value == 0 else f"p = {value:.3g}"


def proportion_test(success_a, n_a, success_b, n_b):
    p_a, p_b = success_a / n_a, success_b / n_b
    pooled = (success_a + success_b) / (n_a + n_b)
    se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z = (p_a - p_b) / se_pooled
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    # the interval uses the unpooled error, the test uses the pooled one
    se_diff = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    diff = p_a - p_b
    return p_a, p_b, diff, diff - 1.96 * se_diff, diff + 1.96 * se_diff, z, p_value


def kaplan_meier(duration, event):
    # standard estimator: censored customers stay in the risk set on their own day
    frame = pd.DataFrame({"day": duration, "event": event}).sort_values("day")
    at_risk = len(frame)
    survival = 1.0
    rows = [{"day": 0, "survival": 1.0, "at_risk": at_risk}]
    for day, group in frame.groupby("day"):
        events = int(group.event.sum())
        if events:
            survival *= 1 - events / at_risk
            rows.append({"day": day, "survival": survival, "at_risk": at_risk})
        at_risk -= len(group)
    return pd.DataFrame(rows)


# Customer level table for 2025. Used by the repeat test and the concentration curve.
per_customer = con.sql(f"""
    SELECT t.customer_id, c.signup_channel,
           COUNT(*) AS orders,
           SUM(t.transaction_total) AS revenue
    FROM transactions t
    JOIN customers c ON c.customer_id = t.customer_id
    WHERE t.customer_id IS NOT NULL
      AND t.transaction_date_id BETWEEN {YEAR_START} AND {YEAR_END}
    GROUP BY 1, 2
""").df()
per_customer["revenue"] = per_customer.revenue.astype(float)

print("=" * 60)
print("1. SEGMENT MIX VS SIGNUP CHANNEL")
print("=" * 60)

acq = pd.read_csv(f"{CSV_FOLDER}/summary_acquisition.csv")
table = acq.pivot(index="signup_channel", columns="Segment", values="total_customers").fillna(0)
chi2, p_value, dof, _ = stats.chi2_contingency(table.values)
n = table.values.sum()
cramers_v = np.sqrt(chi2 / (n * (min(table.shape) - 1)))

vip_share = table["VIP"] / table.sum(axis=1) * 100
print(table.to_string())
print(f"\nVIP share by channel (%):\n{vip_share.round(2).to_string()}")
print(f"\nchi2 = {chi2:.1f}, dof = {dof}, {p_text(p_value)}, Cramers V = {cramers_v:.4f}")
print("Sample size is large, so significance is easy to reach. V shows the association is weak.")
record("chi2_segment_channel", round(chi2, 2))
record("cramers_v_segment_channel", round(cramers_v, 4))
record("vip_share_mobile_pct", round(vip_share["Mobile"], 2))
record("vip_share_online_pct", round(vip_share["Online"], 2))

print("\n" + "=" * 60)
print("2. RATE DIFFERENCES WITH CONFIDENCE INTERVALS")
print("=" * 60)

devices = pd.read_csv(f"{CSV_FOLDER}/summary_devices.csv").set_index("device_type")
mobile, desktop = devices.loc["Mobile"], devices.loc["Desktop"]
pa, pb, diff, lo, hi, z, pv = proportion_test(
    mobile.orders, mobile.total_sessions, desktop.orders, desktop.total_sessions)
print(f"\nConversion, Mobile vs Desktop: {pa:.2%} vs {pb:.2%}")
print(f"difference {diff:+.2%}, 95% CI [{lo:+.2%}, {hi:+.2%}], z = {z:.1f}, {p_text(pv)}")
record("conversion_gap_mobile_desktop_pp", round(diff * 100, 2))
record("conversion_gap_ci_low_pp", round(lo * 100, 2))
record("conversion_gap_ci_high_pp", round(hi * 100, 2))

repeat = per_customer.assign(repeated=per_customer.orders > 1).groupby("signup_channel").agg(
    customers=("customer_id", "size"), repeated=("repeated", "sum"))
pa, pb, diff, lo, hi, z, pv = proportion_test(
    repeat.loc["Mobile", "repeated"], repeat.loc["Mobile", "customers"],
    repeat.loc["Online", "repeated"], repeat.loc["Online", "customers"])
print(f"\nRepeat rate, Mobile vs Online signup: {pa:.2%} vs {pb:.2%}")
print(f"difference {diff:+.2%}, 95% CI [{lo:+.2%}, {hi:+.2%}], z = {z:.1f}, {p_text(pv)}")
record("repeat_gap_mobile_online_pp", round(diff * 100, 2))
record("repeat_gap_ci_low_pp", round(lo * 100, 2))
record("repeat_gap_ci_high_pp", round(hi * 100, 2))

print("\n" + "=" * 60)
print("3. REVENUE CONCENTRATION")
print("=" * 60)

revenue = np.sort(per_customer.revenue.values)
cum_revenue = np.cumsum(revenue) / revenue.sum()
x = np.concatenate([[0], np.arange(1, len(revenue) + 1) / len(revenue)])
y = np.concatenate([[0], cum_revenue])
gini = 1 - 2 * trapezoid(y, x)

top_10_share = revenue[-int(len(revenue) * 0.1):].sum() / revenue.sum()
top_20_share = revenue[-int(len(revenue) * 0.2):].sum() / revenue.sum()
bottom_for_20 = np.searchsorted(cum_revenue, 0.20) + 1
share_holding_80 = (len(revenue) - bottom_for_20 + 1) / len(revenue)

print(f"\ncustomers = {len(revenue):,}, Gini = {gini:.3f}")
print(f"top 10% hold {top_10_share:.1%} of revenue")
print(f"top 20% hold {top_20_share:.1%} of revenue")
print(f"{share_holding_80:.1%} of customers are needed to reach 80% of revenue")
record("gini_revenue", round(gini, 3))
record("top10_revenue_share_pct", round(top_10_share * 100, 2))
record("top20_revenue_share_pct", round(top_20_share * 100, 2))
record("customer_share_holding_80pct_revenue", round(share_holding_80 * 100, 2))

plt.figure(figsize=(5, 5))
plt.plot(x, y, label="Observed")
plt.plot([0, 1], [0, 1], linestyle="--", color="grey", label="Equal share")
plt.xlabel("Cumulative share of customers")
plt.ylabel("Cumulative share of revenue")
plt.title(f"Lorenz curve, 2025 (Gini = {gini:.3f})")
plt.legend()
plt.tight_layout()
plt.savefig(f"{OUT_FOLDER}/lorenz_curve.png", dpi=150)
plt.close()

print("\n" + "=" * 60)
print("4. TIME TO SECOND PURCHASE, CENSORING AWARE")
print("=" * 60)

first_two = con.sql("""
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
    SELECT * FROM paired WHERE first_purchase >= DATE '2025-01-01'
""").df()

window_end = pd.Timestamp("2025-12-31")
first_two["event"] = first_two.second_purchase.notna().astype(int)
first_two["duration"] = np.where(
    first_two.event == 1,
    (first_two.second_purchase - first_two.first_purchase).dt.days,
    (window_end - first_two.first_purchase).dt.days)

km = kaplan_meier(first_two.duration.values, first_two.event.values)
km["repeat_pct"] = (1 - km.survival) * 100

print(f"\ncustomers = {len(first_two):,}, observed second purchases = {first_two.event.sum():,}")
print(f"censored = {(first_two.event == 0).sum():,}")
for day in [30, 60, 90, 180]:
    reached = km[km.day <= day]
    value = reached.repeat_pct.iloc[-1]
    print(f"repeated by day {day}: {value:.2f}%")
    record(f"km_repeat_by_day_{day}", round(value, 2))

half = km[km.repeat_pct >= 50]
median_km = int(half.day.iloc[0]) if len(half) else None
print(f"median days to second purchase (KM): {median_km}")
record("km_median_days_to_second", median_km)

km.to_csv(f"{OUT_FOLDER}/kaplan_meier_curve.csv", index=False)

plt.figure(figsize=(7, 4))
plt.plot(km.day, km.repeat_pct)
plt.xlabel("Days since first purchase")
plt.ylabel("Share who bought again (%)")
plt.title("Time to second purchase, Kaplan-Meier")
plt.tight_layout()
plt.savefig(f"{OUT_FOLDER}/repeat_curve.png", dpi=150)
plt.close()

print("\n" + "=" * 60)
print("5. BOOTSTRAP INTERVALS")
print("=" * 60)

# sorted input keeps the bootstrap identical on every run
gaps = np.sort(con.sql("""
    WITH ordered AS (
        SELECT customer_id, transaction_timestamp,
               LAG(transaction_timestamp) OVER (
                   PARTITION BY customer_id ORDER BY transaction_timestamp) AS previous
        FROM transactions WHERE customer_id IS NOT NULL
    )
    SELECT date_diff('day', previous, transaction_timestamp) AS gap_days
    FROM ordered WHERE previous IS NOT NULL
""").df().gap_days.values)

# a subsample keeps the bootstrap fast and widens the interval slightly
gap_sample = rng.choice(gaps, size=30000, replace=False)
medians = [np.median(rng.choice(gap_sample, size=len(gap_sample), replace=True))
           for _ in range(BOOTSTRAP_RUNS)]
lo, hi = np.percentile(medians, [2.5, 97.5])
print(f"\nmedian gap between orders = {np.median(gaps):.0f} days, 95% CI [{lo:.1f}, {hi:.1f}]")
record("median_gap_days", float(np.median(gaps)))
record("median_gap_ci_low", round(float(lo), 1))
record("median_gap_ci_high", round(float(hi), 1))

store = con.sql(f"""
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
        SELECT s.customer_id, s.transaction_total,
               CASE WHEN EXISTS (
                   SELECT 1 FROM browse b
                   WHERE b.customer_id = s.customer_id
                     AND b.browse_date BETWEEN s.tx_date - INTERVAL 14 DAY AND s.tx_date
               ) THEN 1 ELSE 0 END AS browsed
        FROM store_orders s
    )
    SELECT customer_id, MAX(browsed) AS browsed, SUM(transaction_total) AS revenue
    FROM flagged GROUP BY 1
""").df().sort_values("customer_id").reset_index(drop=True)
store["revenue"] = store.revenue.astype(float)

browsed = store.loc[store.browsed == 1, "revenue"].values
not_browsed = store.loc[store.browsed == 0, "revenue"].values
diffs = [rng.choice(browsed, len(browsed), True).mean()
         - rng.choice(not_browsed, len(not_browsed), True).mean()
         for _ in range(BOOTSTRAP_RUNS)]
lo, hi = np.percentile(diffs, [2.5, 97.5])
point = browsed.mean() - not_browsed.mean()
print(f"\nstore ARPU gap, browsed within 14 days minus not = ${point:,.2f}")
print(f"95% CI [${lo:,.2f}, ${hi:,.2f}]")
print(f"group means: ${browsed.mean():,.2f} vs ${not_browsed.mean():,.2f}")
record("webrooming_arpu_gap", round(float(point), 2))
record("webrooming_arpu_gap_ci_low", round(float(lo), 2))
record("webrooming_arpu_gap_ci_high", round(float(hi), 2))

pd.DataFrame(results).to_csv(f"{OUT_FOLDER}/statistical_results.csv", index=False)
print(f"\nSaved results and 2 figures to {OUT_FOLDER}/")
