import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="ElecMart Analytics", layout="wide")

DATA_DIR = "dashboards_CSV"


@st.cache_data
def load(name):
    return pd.read_csv(f"{DATA_DIR}/{name}.csv")


def money(value):
    if pd.isna(value):
        return "$0"
    if abs(value) >= 1e6:
        return f"${value / 1e6:.1f}M"
    if abs(value) >= 1e3:
        return f"${value / 1e3:.1f}K"
    return f"${value:,.2f}"


def count(value):
    if pd.isna(value):
        return "0"
    if value >= 1e6:
        return f"{value / 1e6:.2f}M"
    if value >= 1e3:
        return f"{value / 1e3:.1f}K"
    return f"{value:,.0f}"


def style_frame(df, money_cols=(), count_cols=()):
    out = df.copy()
    for col in money_cols:
        if col in out.columns:
            out[col] = out[col].map(money)
    for col in count_cols:
        if col in out.columns:
            out[col] = out[col].map(count)
    return out


def month_label(value):
    return pd.Timestamp(value).strftime("%b %Y")


CHART_BG = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
SEGMENT_COLORS = {
    "VIP": "#2CA02C",
    "Loyal Customers": "#98DF8A",
    "Regular": "#C7C7C7",
    "At Risk": "#FF7F0E",
    "Lost": "#D62728",
}
WEBROOMING_LABELS = {
    ("any_time", 0): "Never browsed",
    ("any_time", 1): "Browsed, any time",
    ("14_days", 0): "No browse in 14 days",
    ("14_days", 1): "Browsed within 14 days",
}
WEBROOMING_ORDER = ["Never browsed", "Browsed, any time",
                    "No browse in 14 days", "Browsed within 14 days"]

st.title("ElecMart Analytics")
st.caption("Analysis window: 2025-01-01 to 2025-12-31. The trend chart covers 2023-2025. "
           "Source: ElecMart Retail Analytics Dataset (synthetic).")

overview, acquisition, customers, retention, products, notes = st.tabs(
    ["Overview", "Acquisition", "Customers", "Retention", "Products", "Definitions"])

# ---------------------------------------------------------------- Overview
with overview:
    kpis = load("summary_kpis").iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net Revenue", money(kpis.net_revenue), help="Completed orders only")
    c2.metric("Net Profit", money(kpis.net_profit))
    c3.metric("Net Orders", count(kpis.net_orders))
    c4.metric("Net AOV", money(kpis.net_aov))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Gross Revenue", money(kpis.total_revenue), help="Includes returned orders")
    c6.metric("Return Rate", f"{kpis.return_rate_pct:.2f}%")
    c7.metric("Sessions", count(kpis.total_visitors))
    c8.metric("Guest Revenue Share", f"{kpis.guest_revenue_pct:.2f}%",
              help="Orders with no customer_id, excluded from customer-level analysis")

    with st.expander("SQL for these KPIs"):
        st.code("""
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
       ROUND(net_revenue / net_orders, 2) AS net_aov,
       ROUND((total_orders - net_orders) * 100.0 / total_orders, 2) AS return_rate_pct,
       ROUND(guest_revenue * 100.0 / total_revenue, 2) AS guest_revenue_pct
FROM sessions, orders;
""", language="sql")

    st.divider()
    left, right = st.columns(2)

    with left:
        funnel = load("summary_funnel")
        stages = pd.DataFrame({"Stage": funnel.columns, "Count": funnel.iloc[0].values})
        stages["label"] = stages["Count"].apply(count)
        fig = px.funnel(stages, x="Count", y="Stage", text="label",
                        title="Session Funnel", color_discrete_sequence=["#2CA02C"])
        fig.update_traces(texttemplate="%{text}<br>%{percentInitial:.0%}",
                          textposition="auto", textfont=dict(size=14, color="white"))
        fig.update_layout(height=380, xaxis_title=None, yaxis_title=None,
                          margin=dict(t=50, b=0, l=0, r=0), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Percentages are share of all sessions, not step-to-step rates.")

        rates = load("funnel_rates").iloc[0]
        st.table(pd.DataFrame({
            "Step": ["Visit to view", "View to cart", "Cart to purchase",
                     "Overall conversion", "Cart abandonment", "Single-page sessions"],
            "Rate": [f"{rates.visit_to_view_pct:.2f}%", f"{rates.view_to_cart_pct:.2f}%",
                     f"{rates.cart_to_purchase_pct:.2f}%", f"{rates.overall_conversion_pct:.2f}%",
                     f"{rates.cart_abandonment_pct:.2f}%", f"{rates.single_page_bounce_pct:.2f}%"],
        }))
        st.caption("Cart abandonment of 66.43% is below the ~70% industry average "
                   "(Baymard Institute), so checkout is not unusually weak. "
                   "Single-page sessions are the only true bounces; the other 31.6% of "
                   "no-product sessions viewed 2-3 pages.")

    with right:
        trend = load("yearly_trend")
        trend["year"] = trend["year"].astype(str)
        fig = go.Figure()
        fig.add_bar(x=trend.year, y=trend.revenue / 1e6, name="Revenue ($M)",
                    marker_color="#2CA02C")
        fig.add_scatter(x=trend.year, y=trend.store_revenue_pct, name="Store share of revenue (%)",
                        yaxis="y2", mode="lines+markers", line=dict(color="#FF7F0E", width=3))
        fig.update_layout(
            title="Growth and Channel Shift, 2023-2025", height=380,
            xaxis=dict(type="category"),
            yaxis=dict(title="Revenue ($M)"),
            yaxis2=dict(title="Store share (%)", overlaying="y", side="right", range=[0, 60]),
            legend=dict(orientation="h", y=-0.15), margin=dict(t=50, b=0, l=50, r=50), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Store share fell from 54.22% to 28.93% while conversion rose from 2.37% to 4.93%.")
        st.dataframe(style_frame(trend, money_cols=["revenue", "profit"],
                                 count_cols=["sessions", "purchase_sessions", "orders"]),
                     hide_index=True, use_container_width=True)

    with st.expander("SQL for the funnel and the trend"):
        st.code("""
-- Funnel
SELECT COUNT(*) AS "Total Sessions",
       SUM(CAST(product_page_visited_flag AS INT)) AS "Viewed Product",
       SUM(CAST(added_to_cart_flag AS INT)) AS "Added to Cart",
       SUM(CAST(purchased_flag AS INT)) AS "Purchased"
FROM clickstream
WHERE session_start_date_id BETWEEN 20250101 AND 20251231;

-- Yearly trend (the only output that uses all three years)
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
           SUM(CASE WHEN sales_channel = 'Store' THEN transaction_total ELSE 0 END) AS store_revenue
    FROM transactions GROUP BY 1
)
SELECT s.year, s.sessions, s.purchase_sessions, o.orders, ROUND(o.revenue, 2) AS revenue,
       ROUND(s.purchase_sessions * 100.0 / s.sessions, 2) AS conversion_pct,
       ROUND(o.store_revenue * 100.0 / o.revenue, 2) AS store_revenue_pct
FROM sessions s JOIN orders o ON s.year = o.year ORDER BY s.year;
""", language="sql")

# ------------------------------------------------------------ Acquisition
with acquisition:
    traffic = load("summary_traffic")
    sources = sorted(traffic.traffic_source.unique())
    chosen_sources = st.multiselect("Traffic sources", sources, default=sources)
    view_traffic = traffic[traffic.traffic_source.isin(chosen_sources)]

    if view_traffic.empty:
        st.info("Select at least one traffic source.")
    else:
        share_metric = st.radio("Share metric", ["revenue", "profit", "orders"],
                                horizontal=True, key="source_metric")
        left, right = st.columns(2)

        with left:
            fig = px.bar(view_traffic, x="overall_conversion_rate", y="traffic_source",
                         orientation="h", text="overall_conversion_rate",
                         title="Session Conversion by Source",
                         color_discrete_sequence=["#2CA02C"])
            fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            fig.update_layout(height=360, xaxis=dict(visible=False), yaxis_title=None,
                              margin=dict(t=50, b=0, l=0, r=40), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)

        with right:
            share = view_traffic.copy()
            share["share_pct"] = share[share_metric] / share[share_metric].sum() * 100
            fig = px.bar(share, x="share_pct", y="traffic_source", orientation="h",
                         text="share_pct", title=f"Share of Online {share_metric.title()} by Source",
                         color_discrete_sequence=["#1F77B4"])
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(height=360, xaxis=dict(visible=False), yaxis_title=None,
                              margin=dict(t=50, b=0, l=0, r=40), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)

        st.caption("Revenue is joined on session_id, so every online order is counted once. "
                   "Store orders carry no session_id and cannot be attributed to a source.")
        st.dataframe(style_frame(
            view_traffic,
            money_cols=["revenue", "profit", "aov"],
            count_cols=["total_sessions", "orders"]),
            hide_index=True, use_container_width=True)

    st.divider()
    devices = load("summary_devices")
    device_list = sorted(devices.device_type.unique())
    chosen_devices = st.multiselect("Devices", device_list, default=device_list)
    view_devices = devices[devices.device_type.isin(chosen_devices)]

    if view_devices.empty:
        st.info("Select at least one device.")
    else:
        left, right = st.columns(2)
        with left:
            fig = px.bar(view_devices, x="device_type", y="conversion_rate",
                         text="conversion_rate", title="Conversion by Device",
                         color_discrete_sequence=["#2CA02C"])
            fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            fig.update_layout(height=340, yaxis_title="Conversion (%)", xaxis_title=None,
                              margin=dict(t=50, b=0, l=50, r=0), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)
        with right:
            fig = px.bar(view_devices, x="device_type", y="aov", text="aov",
                         title="Average Order Value by Device",
                         color_discrete_sequence=["#1F77B4"])
            fig.update_traces(texttemplate="$%{text:.0f}", textposition="outside")
            fig.update_layout(height=340, yaxis_title="AOV ($)", xaxis_title=None,
                              yaxis=dict(range=[0, 1100]),
                              margin=dict(t=50, b=0, l=50, r=0), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)

        st.caption("Conversion rises with screen size, but order value does not. "
                   "The axis starts at zero because the three AOVs differ by less than 1%.")
        st.dataframe(style_frame(
            view_devices,
            money_cols=["revenue", "aov"],
            count_cols=["total_sessions", "orders"]),
            hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Acquisition Channel and Customer Value")
    acq_value = load("acquisition_value")
    acq = load("summary_acquisition")
    acq["share"] = acq.groupby("signup_channel")["total_customers"].transform(
        lambda s: s / s.sum() * 100)

    left, right = st.columns([3, 2])
    with left:
        fig = px.bar(acq, x="signup_channel", y="share", color="Segment",
                     text="share", title="Segment Mix by Signup Channel",
                     color_discrete_map=SEGMENT_COLORS)
        fig.update_traces(texttemplate="%{text:.0f}%", textposition="inside")
        fig.update_layout(height=380, barmode="stack", yaxis_title="Share of channel (%)",
                          xaxis_title=None, legend=dict(orientation="h", y=-0.15),
                          margin=dict(t=50, b=0, l=50, r=0), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.dataframe(style_frame(acq_value, money_cols=["revenue", "profit", "arpu"],
                                 count_cols=["customers"]),
                     hide_index=True, use_container_width=True)
        st.caption("signup_channel is one value per customer, so there is no double counting. "
                   "Mobile has the lowest session conversion but the highest revenue per customer.")

    with st.expander("SQL for source revenue, devices and signup channel"):
        st.code("""
-- Source revenue: the session_id join gives one row per order
WITH sessions AS (
    SELECT traffic_source, COUNT(*) AS total_sessions,
           SUM(CAST(purchased_flag AS INT)) AS purchases
    FROM clickstream WHERE session_start_date_id BETWEEN 20250101 AND 20251231
    GROUP BY traffic_source
),
orders AS (
    SELECT c.traffic_source, COUNT(*) AS orders,
           SUM(t.transaction_total) AS revenue,
           SUM(t.transaction_total - t.transaction_cost) AS profit
    FROM transactions t JOIN clickstream c ON c.session_id = t.session_id
    WHERE t.transaction_date_id BETWEEN 20250101 AND 20251231
    GROUP BY c.traffic_source
)
SELECT s.traffic_source, s.total_sessions,
       ROUND(s.purchases * 100.0 / s.total_sessions, 2) AS overall_conversion_rate,
       o.orders, ROUND(o.revenue, 2) AS revenue, ROUND(o.profit, 2) AS profit,
       ROUND(o.revenue / o.orders, 2) AS aov,
       ROUND(o.revenue * 100.0 / SUM(o.revenue) OVER (), 2) AS revenue_share_pct
FROM sessions s JOIN orders o ON s.traffic_source = o.traffic_source;

-- Signup channel value
WITH per_customer AS (
    SELECT customer_id, COUNT(*) AS orders, SUM(transaction_total) AS revenue,
           SUM(transaction_total - transaction_cost) AS profit
    FROM transactions
    WHERE customer_id IS NOT NULL AND transaction_date_id BETWEEN 20250101 AND 20251231
    GROUP BY customer_id
)
SELECT c.signup_channel, COUNT(*) AS customers,
       ROUND(SUM(CASE WHEN p.orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS repeat_pct,
       ROUND(SUM(p.revenue), 2) AS revenue, ROUND(SUM(p.revenue) / COUNT(*), 2) AS arpu
FROM per_customer p JOIN customers c ON c.customer_id = p.customer_id
GROUP BY 1 ORDER BY revenue DESC;
""", language="sql")

# -------------------------------------------------------------- Customers
with customers:
    segments = load("summary_rfm_segments")
    value = load("segment_value")
    segment_list = list(SEGMENT_COLORS.keys())
    chosen_segments = st.multiselect("Segments", segment_list, default=segment_list)
    cust_metric = st.radio("Value metric", ["revenue", "profit", "customers"],
                           horizontal=True, key="segment_metric")

    view_segments = segments[segments.Segment.isin(chosen_segments)]
    view_value = value[value.segment.isin(chosen_segments)]

    if view_value.empty:
        st.info("Select at least one segment.")
    else:
        left, right = st.columns(2)
        with left:
            fig = px.treemap(view_segments, path=[px.Constant("Selected customers"), "Segment"],
                             values="Customer_Count", color="Segment",
                             color_discrete_map=SEGMENT_COLORS, title="Customers by Segment")
            fig.update_traces(textinfo="label+value+percent root")
            fig.update_layout(height=380, margin=dict(t=50, b=0, l=0, r=0), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)

        with right:
            bar = view_value.copy()
            bar["pct"] = bar[cust_metric] / bar[cust_metric].sum() * 100
            bar = bar.sort_values("pct", ascending=False)
            fig = px.bar(bar, x="pct", y="segment", orientation="h", text="pct",
                         color="segment", color_discrete_map=SEGMENT_COLORS,
                         title=f"Share of Identified {cust_metric.title()}")
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(height=380, showlegend=False, xaxis=dict(visible=False),
                              yaxis_title=None, margin=dict(t=50, b=0, l=0, r=40), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)

        st.caption("At Risk holds the largest revenue pool. VIP and Loyal together are "
                   "17.9% of customers and 33.6% of revenue, so the 80/20 rule does not hold here.")
        st.dataframe(style_frame(
            view_value,
            money_cols=["revenue", "profit", "arpu"],
            count_cols=["customers", "orders"]),
            hide_index=True, use_container_width=True)

    st.divider()
    left, right = st.columns(2)
    with left:
        profile = load("summary_retention_profile")
        fig = px.pie(profile, values="customer_count", names="customer_type", hole=0.6,
                     title="One-Time vs Repeat Buyers",
                     color_discrete_sequence=["#B0BEC5", "#2CA02C"])
        fig.update_traces(textinfo="percent+label", textposition="outside")
        fig.update_layout(height=340, showlegend=False, margin=dict(t=50, b=0, l=60, r=60), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Repeat means more than one transaction inside 2025.")

    with right:
        web = load("webrooming")
        web["group"] = [WEBROOMING_LABELS[(w, b)]
                        for w, b in zip(web.window_label, web.browsed)]
        fig = px.bar(web, x="group", y="arpu", text="arpu",
                     title="Store Revenue per Customer by Browsing Window",
                     color_discrete_sequence=["#1F77B4"],
                     category_orders={"group": WEBROOMING_ORDER})
        fig.update_traces(texttemplate="$%{text:.0f}", textposition="outside")
        fig.update_layout(height=340, yaxis_title="Revenue per customer ($)", xaxis_title=None,
                          margin=dict(t=50, b=0, l=50, r=0), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Order value is about $961 in every group. The 14-day gap comes from "
                   "more store visits, not larger baskets, so the direction is not identified.")

    with st.expander("SQL for RFM, segment value and webrooming"):
        st.code("""
-- RFM: scores are assigned by value, so equal inputs always get equal scores
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
    SELECT quantile_cont(recency, 0.25) AS r25, quantile_cont(recency, 0.50) AS r50,
           quantile_cont(recency, 0.75) AS r75, quantile_cont(monetary, 0.25) AS m25,
           quantile_cont(monetary, 0.50) AS m50, quantile_cont(monetary, 0.75) AS m75
    FROM base
),
scored AS (
    SELECT b.customer_id,
           CASE WHEN b.recency <= e.r25 THEN 4 WHEN b.recency <= e.r50 THEN 3
                WHEN b.recency <= e.r75 THEN 2 ELSE 1 END AS r_score,
           CASE WHEN b.frequency = 1 THEN 1 WHEN b.frequency = 2 THEN 2
                WHEN b.frequency <= 4 THEN 3 ELSE 4 END AS f_score,
           CASE WHEN b.monetary <= e.m25 THEN 1 WHEN b.monetary <= e.m50 THEN 2
                WHEN b.monetary <= e.m75 THEN 3 ELSE 4 END AS m_score
    FROM base b CROSS JOIN edges e
),
segmented AS (
    SELECT *, CASE
        WHEN r_score = 4 AND f_score = 4 AND m_score = 4 THEN 'VIP'
        WHEN r_score = 4 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score IN (2, 3) AND f_score >= 3 THEN 'At Risk'
        WHEN r_score = 1 THEN 'Lost'
        ELSE 'Regular' END AS segment
    FROM scored
)
SELECT segment, COUNT(*) AS customers FROM segmented GROUP BY 1;

-- Webrooming: EXISTS avoids the row fan-out a join would create
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
    SELECT s.customer_id, s.transaction_total,
           CASE WHEN EXISTS (SELECT 1 FROM browse b
               WHERE b.customer_id = s.customer_id
                 AND b.browse_date BETWEEN s.tx_date - INTERVAL 14 DAY AND s.tx_date
           ) THEN 1 ELSE 0 END AS browsed_14d
    FROM store_orders s
),
per_customer AS (
    SELECT customer_id, MAX(browsed_14d) AS browsed_14d, SUM(transaction_total) AS revenue
    FROM flagged GROUP BY customer_id
)
SELECT browsed_14d, COUNT(*) AS customers, ROUND(SUM(revenue) / COUNT(*), 2) AS arpu
FROM per_customer GROUP BY 1;
""", language="sql")

# -------------------------------------------------------------- Retention
with retention:
    cohort = load("summary_cohort")
    months = sorted(cohort.cohort_month.unique())
    labels = [month_label(m) for m in months]
    chosen_labels = st.multiselect("Cohort months", labels, default=labels)
    chosen_months = [m for m, lab in zip(months, labels) if lab in chosen_labels]
    view_cohort = cohort[cohort.cohort_month.isin(chosen_months)]

    if view_cohort.empty:
        st.info("Select at least one cohort month.")
    else:
        matrix = view_cohort.pivot(index="cohort_month", columns="month_index",
                                   values="active_customers")
        pct = matrix.divide(matrix[0], axis=0) * 100
        pct.index = [month_label(i) for i in pct.index]

        fig = px.imshow(pct, text_auto=".1f", aspect="auto", color_continuous_scale="YlGnBu",
                        range_color=[10, 30],
                        title="Monthly Retention by First-Purchase Cohort (%)")
        fig.update_layout(height=420, coloraxis_showscale=False,
                          xaxis=dict(title="Months since first purchase in window", side="bottom"),
                          yaxis=dict(title="Cohort month"), margin=dict(t=50, b=0, l=60, r=0), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Color scale is fixed to 10-30% so month-to-month differences stay visible; "
                   "the month-0 column is always 100 by definition.")

        comp = load("cohort_composition")
        comp = comp[comp.cohort_month.isin(chosen_months)]
        st.caption(f"These are first purchases inside the data window, not new signups. "
                   f"Of {int(comp.customers.sum()):,} customers, only {int(comp.new_signups.sum()):,} "
                   f"({comp.new_signups.sum() / comp.customers.sum() * 100:.1f}%) signed up in 2025.")

    st.divider()
    left, right = st.columns(2)
    calendar = load("retention_by_calendar_month")
    age = load("retention_by_cohort_age")

    with left:
        fig = px.line(calendar, x="calendar_month", y="avg_retention_pct", markers=True,
                      title="Retention Grouped by Calendar Month",
                      color_discrete_sequence=["#D62728"])
        fig.update_layout(height=340, yaxis_title="Average retention (%)", xaxis_title=None,
                          margin=dict(t=50, b=0, l=50, r=0), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = px.line(age, x="cohort_age", y="avg_retention_pct", markers=True,
                      title="Retention Grouped by Cohort Age",
                      color_discrete_sequence=["#1F77B4"])
        fig.update_layout(height=340, yaxis_title="Average retention (%)",
                          xaxis_title="Months since first purchase",
                          margin=dict(t=50, b=0, l=50, r=0), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)

    st.caption("In December every cohort sits near 25% regardless of age, and in mid-year "
               "every cohort sits near 16%. The rise by age is a composition effect: older ages "
               "only exist for early cohorts, whose later months land in Q4.")

    st.divider()
    left, right = st.columns([2, 1])
    with left:
        curve = load("second_purchase_curve")
        fig = px.line(curve, x="days_since_first_purchase", y="cumulative_repeat_pct",
                      markers=True, title="Time to Second Purchase, Jan-Jun 2025 Cohorts",
                      color_discrete_sequence=["#2CA02C"])
        fig.update_layout(height=340, yaxis_title="Cumulative repeat (%)",
                          xaxis_title="Days since first purchase",
                          margin=dict(t=50, b=0, l=50, r=0), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        second = load("second_purchase_summary").iloc[0]
        st.metric("Customers", count(second.cohort_customers))
        st.metric("Bought again", f"{second.repeat_pct:.2f}%")
        st.metric("Median days to second order", f"{second.median_days_to_second:.0f}")
        cycle = load("purchase_cycle").iloc[0]
        st.metric("Median gap, all years", f"{cycle.median_days:.0f} days")

    st.caption("Only Jan-Jun cohorts are used so every customer has at least 180 days of "
               "follow-up. A customer who has not bought again at day 30 has not churned.")

    with st.expander("SQL for cohorts and time to second purchase"):
        st.code("""
-- Cohorts
WITH first_purchase AS (
    SELECT customer_id, MIN(transaction_timestamp) AS first_purchase_date
    FROM transactions WHERE customer_id IS NOT NULL GROUP BY customer_id
),
activity AS (
    SELECT t.customer_id,
           date_trunc('month', f.first_purchase_date) AS cohort_month,
           date_diff('month', f.first_purchase_date, t.transaction_timestamp) AS month_index
    FROM transactions t JOIN first_purchase f ON f.customer_id = t.customer_id
    WHERE t.transaction_date_id BETWEEN 20250101 AND 20251231
      AND f.first_purchase_date >= DATE '2025-01-01'
)
SELECT CAST(cohort_month AS DATE) AS cohort_month, month_index,
       COUNT(DISTINCT customer_id) AS active_customers
FROM activity GROUP BY 1, 2 ORDER BY 1, 2;

-- Time to second purchase
WITH numbered AS (
    SELECT customer_id, transaction_timestamp,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY transaction_timestamp) AS n
    FROM transactions WHERE customer_id IS NOT NULL
),
first_two AS (
    SELECT customer_id,
           MIN(CASE WHEN n = 1 THEN transaction_timestamp END) AS first_purchase,
           MIN(CASE WHEN n = 2 THEN transaction_timestamp END) AS second_purchase
    FROM numbered GROUP BY customer_id
)
SELECT date_diff('day', first_purchase, second_purchase) AS days_to_second
FROM first_two
WHERE first_purchase >= DATE '2025-01-01' AND first_purchase < DATE '2025-07-01';
""", language="sql")

# --------------------------------------------------------------- Products
with products:
    cats = load("category_performance")
    cat_list = sorted(cats.category_name.unique())
    chosen_cats = st.multiselect("Categories", cat_list, default=cat_list)
    view_cats = cats[cats.category_name.isin(chosen_cats)]

    if view_cats.empty:
        st.info("Select at least one category.")
    else:
        view_cats = view_cats.copy()
        view_cats["revenue_label"] = view_cats["revenue"].map(money)
        left, right = st.columns(2)
        with left:
            ordered = view_cats.sort_values("revenue", ascending=False)
            fig = px.bar(ordered, x="revenue", y="category_name", orientation="h",
                         text="revenue_label", title="Revenue by Category",
                         color_discrete_sequence=["#2CA02C"])
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, xaxis=dict(visible=False), yaxis_title=None,
                              yaxis=dict(autorange="reversed"),
                              margin=dict(t=50, b=0, l=0, r=80), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)
        with right:
            ordered = view_cats.sort_values("margin_pct")
            fig = px.bar(ordered, x="margin_pct", y="category_name", orientation="h",
                         text="margin_pct", title="Gross Margin by Category",
                         color_discrete_sequence=["#1F77B4"])
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(height=380, xaxis=dict(visible=False), yaxis_title=None,
                              margin=dict(t=50, b=0, l=0, r=40), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)

        st.caption("Margin ranges from 11.06% in Gaming to 30.32% in Kitchen Appliances. "
                   "Margin is flat across price tiers and across customer segments.")
        st.dataframe(style_frame(view_cats, money_cols=["revenue", "profit"],
                                 count_cols=["lines_sold", "units"]),
                     hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Basket Affinity Test")
    basket = load("basket_summary").iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Completed orders", count(basket.orders))
    c2.metric("Average items", f"{basket.avg_items:.1f}")
    c3.metric("Distinct product pairs", count(basket.distinct_pairs))
    c4.metric("Pairs with 50+ orders", int(basket.pairs_ge_50))

    rules = load("basket_category_rules")
    rules = rules[rules.category_a.isin(chosen_cats) & rules.category_b.isin(chosen_cats)]
    if len(chosen_cats) < 2 or rules.empty:
        st.info("Select at least two categories to see the lift matrix.")
    else:
        mirror = rules.rename(columns={"category_a": "category_b", "category_b": "category_a"})
        lift_matrix = pd.concat([rules, mirror]).pivot(
            index="category_a", columns="category_b", values="lift")
        fig = px.imshow(lift_matrix, text_auto=".2f", aspect="auto",
                        color_continuous_scale="RdBu", color_continuous_midpoint=1.0,
                        title="Category Pair Lift (1.0 = independent)")
        fig.update_layout(height=460, margin=dict(t=50, b=0, l=80, r=0), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("The diagonal is empty because same-category pairs are not measured here.")

        st.info("No cross-sell signal. All 36 category pairs have lift below 1 "
                f"({rules.lift.min():.3f} to {rules.lift.max():.3f}), and the strongest product pair "
                "appears in only 36 of 431,377 orders. Bundling across categories is not supported "
                "by this data.")

    with st.expander("SQL for category margin and basket lift"):
        st.code("""
-- Category margin
SELECT cat.category_name, SUM(s.line_total) AS revenue,
       SUM(s.line_total - s.line_cost) AS profit,
       ROUND(SUM(s.line_total - s.line_cost) * 100.0 / SUM(s.line_total), 2) AS margin_pct
FROM sales s
JOIN products p ON p.product_id = s.product_id
JOIN categories cat ON cat.category_id = p.category_id
WHERE s.transaction_date_id BETWEEN 20250101 AND 20251231
GROUP BY 1 ORDER BY revenue DESC;

-- Basket lift at category level
WITH basket AS (
    SELECT DISTINCT s.transaction_id, p.category_id
    FROM sales s
    JOIN transactions t ON t.transaction_id = s.transaction_id
    JOIN products p ON p.product_id = s.product_id
    WHERE s.transaction_date_id BETWEEN 20250101 AND 20251231
      AND t.transaction_status = 'Completed'
),
totals AS (SELECT COUNT(DISTINCT transaction_id) AS n_orders FROM basket),
cat_orders AS (SELECT category_id, COUNT(*) AS n FROM basket GROUP BY 1),
pairs AS (
    SELECT a.category_id AS ca, b.category_id AS cb, COUNT(*) AS pair_orders
    FROM basket a JOIN basket b
      ON a.transaction_id = b.transaction_id AND a.category_id < b.category_id
    GROUP BY 1, 2
)
SELECT p.pair_orders,
       ROUND(p.pair_orders * t.n_orders * 1.0 / (oa.n * ob.n), 3) AS lift
FROM pairs p CROSS JOIN totals t
JOIN cat_orders oa ON oa.category_id = p.ca
JOIN cat_orders ob ON ob.category_id = p.cb;
""", language="sql")

# ------------------------------------------------------------ Definitions
with notes:
    st.subheader("Metric Definitions")
    st.table(pd.DataFrame({
        "Metric": ["Net revenue", "Return rate", "Guest revenue share", "Single-page sessions",
                   "Repeat buyer", "Recency score", "Frequency score", "Monetary score",
                   "VIP", "Loyal Customers", "At Risk", "Lost", "Regular", "Lift"],
        "Definition": [
            "transaction_total where status = Completed",
            "Returned orders / all orders",
            "Revenue from orders with no customer_id",
            "Sessions with exactly one page view",
            "More than one transaction in 2025",
            "4 if recency <= 24 days, 3 if <= 66, 2 if <= 153, else 1",
            "1 if 1 order, 2 if 2 orders, 3 if 3-4, 4 if 5+",
            "Quartile of 2025 spend, edges 579.54 / 1565.73 / 4135.73",
            "R=4, F=4, M=4",
            "R=4 and F>=3, excluding VIP",
            "R in (2,3) and F>=3",
            "R=1",
            "Everything else",
            "Observed co-occurrence / expected under independence",
        ],
    }))

    st.subheader("Limitations")
    st.markdown("""
- The dataset is synthetic. Session duration is capped at 12 minutes and the median is 2.0
  for every device, so duration carries no behavioural signal.
- Basket size is always 1 to 3 items, and gross margin is flat near 18.7% across segments,
  channels and price tiers. Only category margin varies.
- 19.02% of 2025 revenue has no customer_id, so customer-level analysis covers 81% of revenue.
- Store orders have no session_id, so store revenue cannot be attributed to a traffic source.
- Clickstream has no product_id, so browsing cannot be linked to the product later purchased.
- There is no advertising spend anywhere in the schema, so CAC and ROI cannot be computed.
- Only completed transactions are recorded, so checkout friction cannot be measured.
- Transactions start in 2023 while signup dates go back to 2001. Cohorts therefore measure
  first purchase inside the window, not acquisition.
- Discounts are negligible: 97.86% of orders have zero discount.
- All comparisons are observational. No A/B test or holdout exists in this data.
""")

    st.subheader("Reproducibility")
    st.markdown("""
`generate_summary.py` reads the raw parquet files and writes every CSV in `dashboards_CSV/`.
The dashboard only reads those CSVs, so the numbers on screen and the numbers in the queries
come from the same place. Run the generator once after downloading the dataset from Kaggle.
""")
