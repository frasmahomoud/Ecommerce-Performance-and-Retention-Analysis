import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. Page Configuration ---
st.set_page_config(page_title="ElecMart Performance Hub", layout="wide")
st.title("ElecMart Executive Performance Hub")
st.markdown("---")

# --- 2. Data Loading ---
@st.cache_data
def load_kpis(): 
    return pd.read_csv('dashboards_CSV/summary_kpis.csv').iloc[0]

@st.cache_data
def load_funnel(): 
    df = pd.read_csv('dashboards_CSV/summary_funnel.csv')
    return pd.DataFrame({'Stage': df.columns, 'Count': df.iloc[0].values})

@st.cache_data
def load_cohort(): 
    df = pd.read_csv('dashboards_CSV/summary_cohort.csv')
    retention = df.pivot(index='cohort_month', columns='month_index', values='active_customers')
    cohort_sizes = retention.iloc[:, 0]
    retention_pct = retention.divide(cohort_sizes, axis=0) * 100
    retention_pct.index = pd.to_datetime(retention_pct.index).strftime('%b')
    return retention_pct

@st.cache_data
def load_traffic(): 
    return pd.read_csv('dashboards_CSV/summary_traffic.csv')

@st.cache_data
def load_devices(): 
    return pd.read_csv('dashboards_CSV/summary_devices.csv')

@st.cache_data
def load_retention_profile(): 
    return pd.read_csv('dashboards_CSV/summary_retention_profile.csv')

@st.cache_data
def load_rfm_segments(): 
    return pd.read_csv('dashboards_CSV/summary_rfm_segments.csv')

@st.cache_data
def load_segment_channels(): 
    return pd.read_csv('dashboards_CSV/summary_segment_channels.csv')

# --- 3. Top KPI Cards ---
kpis = load_kpis()

def format_money(num):
    if pd.isna(num): return "$0"
    if num >= 1e6: return f"${num / 1e6:.1f}M"
    elif num >= 1e3: return f"${num / 1e3:.1f}K"
    return f"${num:.2f}"

def format_num(num):
    if pd.isna(num): return "0"
    if num >= 1e6: return f"{num / 1e6:.1f}M"
    elif num >= 1e3: return f"{num / 1e3:.1f}K"
    return f"{num:,.0f}"

col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Total Revenue", format_money(kpis['total_revenue']))
with col2: st.metric("Total Profit", format_money(kpis['total_profit']))
with col3: st.metric("Total Orders", format_num(kpis['total_orders']))
with col4: st.metric("Avg Order Value", format_money(kpis['avg_order_value']))

with st.expander("View SQL Query for KPIs"):
    st.code("""
    WITH visitor_stats AS (
        SELECT COUNT(session_id) AS total_visitors, COUNT(DISTINCT CASE WHEN purchased_flag = TRUE THEN customer_id END) AS total_buyers
        FROM fact_clickstream
    ),
    transaction_stats AS (
        SELECT COUNT(DISTINCT transaction_id) AS total_orders, SUM(transaction_total) AS total_revenue,
               SUM(transaction_cost) AS total_cost, SUM(transaction_total) - SUM(transaction_cost) AS total_profit
        FROM fact_transaction
    )
    SELECT v.total_visitors, v.total_buyers, t.total_orders, t.total_revenue, t.total_cost, t.total_profit
    FROM visitor_stats v, transaction_stats t;
    """, language="sql")

st.markdown("---")

# --- 4. Row 1: Funnel & Cohort ---
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    df_funnel = load_funnel()
    df_funnel['custom_text'] = df_funnel['Count'].apply(lambda x: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.1f}k")
    fig_funnel = px.funnel(df_funnel, x='Count', y='Stage', text='custom_text', title='Conversion Funnel (Macro Level)', color_discrete_sequence=['#2CA02C'])
    fig_funnel.update_traces(texttemplate='%{text}<br>%{percentInitial:.0%}', textposition='auto', textfont=dict(size=14, color='white'))
    fig_funnel.update_layout(height=400, yaxis_title=None, xaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_funnel, use_container_width=True)
    
    with st.expander("View SQL Query"):
        st.code("""
        SELECT COUNT(session_id) AS "Total Sessions", SUM(CAST(product_page_visited_flag AS INT)) AS "Viewed Product",
               SUM(CAST(added_to_cart_flag AS INT)) AS "Added to Cart", SUM(CAST(purchased_flag AS INT)) AS "Purchased"
        FROM fact_clickstream;
        """, language="sql")

with row1_col2:
    retention_pct = load_cohort()
    fig_cohort = px.imshow(retention_pct, text_auto='.1f', aspect="auto", color_continuous_scale='YlGnBu', title='Customer Retention Cohort Analysis (%)')
    fig_cohort.update_layout(height=400, coloraxis_showscale=False, xaxis=dict(side='bottom', title='Months Since First Purchase', showgrid=False), yaxis=dict(title='Cohort Month', showgrid=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_cohort, use_container_width=True)
    
    with st.expander("View SQL & Python Logic"):
        st.markdown("**1. Data Extraction (SQL)**")
        st.code("""
        WITH First_Purchase AS (
            SELECT customer_id, MIN(transaction_timestamp) AS first_purchase_date FROM fact_transaction GROUP BY customer_id
        ),
        Cohort_Data AS (
            SELECT ft.customer_id, date_trunc('month', fp.first_purchase_date) AS cohort_month,
                   date_diff('month', fp.first_purchase_date, ft.transaction_timestamp) AS month_index
            FROM fact_transaction ft JOIN First_Purchase fp ON ft.customer_id = fp.customer_id
        )
        SELECT CAST(cohort_month AS DATE) AS cohort_month, month_index, COUNT(DISTINCT customer_id) AS active_customers
        FROM Cohort_Data GROUP BY cohort_month, month_index ORDER BY cohort_month, month_index;
        """, language="sql")
        st.markdown("**2. Pivot Transformation (Pandas)**")
        st.code("""
        retention = df.pivot(index='cohort_month', columns='month_index', values='active_customers')
        cohort_sizes = retention.iloc[:, 0]
        retention_pct = retention.divide(cohort_sizes, axis=0) * 100
        """, language="python")

st.markdown("---")

# --- 5. Row 2: Traffic & Devices ---
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    df_traffic = load_traffic()
    fig_traffic = px.bar(df_traffic, x='overall_conversion_rate', y='traffic_source', orientation='h', text='overall_conversion_rate', color_discrete_sequence=['#2CA02C'], title='Conversion Rate by Traffic Source')
    fig_traffic.update_traces(texttemplate='%{text:.2f}%', textposition='inside', textfont=dict(color='white'))
    fig_traffic.update_layout(height=400, xaxis=dict(showgrid=False, visible=False, rangemode='tozero'), yaxis=dict(title=''), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_traffic, use_container_width=True)
    
    with st.expander("View SQL Query"):
        st.code("""
        WITH source_funnel AS (
            SELECT traffic_source, COUNT(session_id) AS total_sessions, SUM(CAST(purchased_flag AS INT)) AS purchases
            FROM fact_clickstream GROUP BY traffic_source
        )
        SELECT traffic_source, ROUND(purchases * 100.0 / NULLIF(total_sessions, 0), 2) AS overall_conversion_rate
        FROM source_funnel ORDER BY overall_conversion_rate ASC;
        """, language="sql")

with row2_col2:
    df_device = load_devices()
    fig_donut_dev = px.pie(df_device, values='total_sessions', names='device_type', hole=0.6, title='Traffic Share by Device Type', color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c'])
    fig_donut_dev.update_traces(textinfo='percent+label', textposition='outside', pull=[0.05, 0, 0], textfont=dict(color='white'))
    fig_donut_dev.update_layout(height=400, showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=20, l=80, r=80))
    st.plotly_chart(fig_donut_dev, use_container_width=True)
    
    with st.expander("View SQL Query"):
        st.code("""
        SELECT device_type, COUNT(session_id) AS total_sessions,
               ROUND(SUM(CAST(purchased_flag AS INT)) * 100.0 / COUNT(session_id), 2) AS conversion_rate
        FROM fact_clickstream GROUP BY device_type ORDER BY total_sessions DESC;
        """, language="sql")

st.markdown("---")

# --- 6. Row 3: Retention & RFM ---
row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    df_retention = load_retention_profile()
    fig_retention = px.pie(df_retention, values='customer_count', names='customer_type', hole=0.6, title='Customer Retention Profile', color_discrete_sequence=['#2CA02C', '#B0BEC5'])
    fig_retention.update_traces(textinfo='percent+label', textposition='outside', pull=[0.05, 0])
    
    retention_labels = fig_retention.data[0].labels
    retention_color_map = {'Repeat Customer': 'white', 'One-Time Buyer': 'white'}
    fig_retention.data[0].textfont.color = [retention_color_map.get(label, 'white') for label in retention_labels]
    
    fig_retention.update_layout(height=400, showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=0, l=80, r=80))
    st.plotly_chart(fig_retention, use_container_width=True)
    
    with st.expander("View SQL Query"):
        st.code("""
        WITH Customer_Orders AS (
            SELECT customer_id, LAG(transaction_timestamp) OVER(PARTITION BY customer_id ORDER BY transaction_timestamp) AS prev_transaction_timestamp, transaction_timestamp
            FROM fact_transaction WHERE customer_id IS NOT NULL
        )
        SELECT CASE WHEN AVG(date_diff('day', prev_transaction_timestamp, transaction_timestamp)) IS NULL THEN 'One-Time Buyer' ELSE 'Repeat Customer' END AS customer_type,
               COUNT(customer_id) AS customer_count
        FROM Customer_Orders GROUP BY customer_type;
        """, language="sql")

with row3_col2:
    segment_counts = load_rfm_segments()
    color_map = {'VIP': '#2CA02C', 'Loyal Customers': '#98DF8A', 'Regular': '#C7C7C7', 'At Risk': '#FF7F0E', 'Lost': '#D62728'}
    fig_treemap = px.treemap(segment_counts, path=[px.Constant("All Customers"), 'Segment'], values='Customer_Count', title='RFM Customer Segments', color='Segment', color_discrete_map=color_map)
    fig_treemap.update_traces(textinfo='label+value+percent root', hovertemplate='<b>%{label}</b><br>Customers: %{value}<br>%{percentRoot:.1%} of total')
    
    segment_text_color = {'VIP': 'white', 'Loyal Customers': 'black', 'Regular': 'black', 'At Risk': 'white', 'Lost': 'white'}
    fig_treemap.data[0].textfont.color = [segment_text_color.get(label, 'black') for label in fig_treemap.data[0].labels]
    
    fig_treemap.update_layout(height=400, margin=dict(t=40, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_treemap, use_container_width=True)
    
    with st.expander("View SQL & Python Logic"):
        st.markdown("**1. Base RFM Extraction (SQL)**")
        st.code("""
        SELECT customer_id, transaction_id, transaction_timestamp, transaction_total
        FROM fact_transaction WHERE customer_id IS NOT NULL;
        """, language="sql")
        st.markdown("**2. RFM Scoring & Segmentation (Pandas)**")
        st.code("""
        rfm = df.groupby('customer_id').agg({
            'transaction_timestamp': lambda x: (snapshot_date - x.max()).days,
            'transaction_id': 'count',
            'transaction_total': 'sum'
        })
        
        rfm['R'] = pd.qcut(rfm['Recency'], q=4, labels=[4, 3, 2, 1])
        rfm['F'] = pd.qcut(rfm['Frequency'].rank(method='first'), q=4, labels=[1, 2, 3, 4])
        rfm['M'] = pd.qcut(rfm['Monetary'], q=4, labels=[1, 2, 3, 4])
        
        conditions = [
            (rfm['R'] == 4) & (rfm['F'] >= 3),
            rfm['R'] == 1
        ]
        """, language="python")

st.markdown("---")

# --- 7. Row 4: Segment Traffic ---
st.subheader("Traffic Source Distribution by Customer Segment")
segment_channels = load_segment_channels()
segment_channels['percentage'] = segment_channels.groupby('Segment')['total_customers'].transform(lambda x: (x / x.sum()) * 100)

fig_seg_traffic = px.bar(segment_channels, y='Segment', x='percentage', color='traffic_source', orientation='h', text='percentage', color_discrete_sequence=px.colors.qualitative.Safe)
fig_seg_traffic.update_traces(texttemplate='%{text:.1f}%', textposition='inside', insidetextanchor='middle')

text_color_map = {
    'Campaign': '#000000',
    'Referral': '#000000',
    'Organic': '#FFFFFF',
    'Direct': '#FFFFFF',
}

for trace in fig_seg_traffic.data:
    if trace.name in text_color_map:
        trace.textfont.color = text_color_map[trace.name]
    else:
        trace.textfont.color = '#333333'

fig_seg_traffic.update_layout(height=350, barmode='stack', xaxis=dict(title='Percentage (%)', showgrid=False), yaxis=dict(title='', showgrid=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10, b=0, l=0, r=0))
st.plotly_chart(fig_seg_traffic, use_container_width=True)

with st.expander("View SQL Query"):
    st.code("""
    SELECT r.Segment, c.traffic_source, COUNT(DISTINCT r.customer_id) AS total_customers
    FROM rfm_reset r JOIN fact_clickstream c ON r.customer_id = c.customer_id
    WHERE c.purchased_flag = True GROUP BY r.Segment, c.traffic_source;
    """, language="sql")
