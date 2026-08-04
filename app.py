import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. Page Configuration ---
st.set_page_config(page_title="ElecMart Performance Hub", layout="wide")
st.title("ElecMart Executive Performance Hub 📊")
st.markdown("---")

# --- Design System (Premium Dark Theme) ---
PRIMARY_BLUE = '#3B82F6'    # Modern SaaS Blue
SUCCESS_GREEN = '#10B981'   # Emerald Green for good metrics
WARNING_YELLOW = '#F59E0B'  # Amber for At-Risk
DANGER_RED = '#EF4444'      # Red for Churn/Lost
NEUTRAL_GRAY = '#64748B'    # Slate Gray for regular users
BG_TRANSPARENT = 'rgba(0,0,0,0)'

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
    fig_funnel = px.funnel(df_funnel, x='Count', y='Stage', text='custom_text', title='Conversion Funnel (Macro Level)', color_discrete_sequence=[PRIMARY_BLUE])
    fig_funnel.update_traces(texttemplate='<b>%{text}</b><br>%{percentInitial:.0%}', textfont=dict(size=14, color='white'))
    fig_funnel.update_layout(template='plotly_dark', height=400, yaxis_title=None, xaxis_title=None, plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_funnel, use_container_width=True)
    
    with st.expander("View SQL Query"):
        st.code("""
        SELECT COUNT(session_id) AS "Total Sessions", SUM(CAST(product_page_visited_flag AS INT)) AS "Viewed Product",
               SUM(CAST(added_to_cart_flag AS INT)) AS "Added to Cart", SUM(CAST(purchased_flag AS INT)) AS "Purchased"
        FROM fact_clickstream;
        """, language="sql")

with row1_col2:
    retention_pct = load_cohort()
    # Changed to 'Blues' for a professional look
    fig_cohort = px.imshow(retention_pct, text_auto='.1f', aspect="auto", color_continuous_scale='Blues', title='Customer Retention Cohort (%)')
    fig_cohort.update_layout(template='plotly_dark', height=400, coloraxis_showscale=False, xaxis=dict(side='bottom', title='Months Since First Purchase', showgrid=False), yaxis=dict(title='', showgrid=False), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=40, b=0, l=0, r=0))
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
    max_val = df_traffic['overall_conversion_rate'].max()
    
    fig_traffic = px.bar(df_traffic, x='overall_conversion_rate', y='traffic_source', orientation='h', text='overall_conversion_rate', color_discrete_sequence=[PRIMARY_BLUE], title='Conversion Rate by Traffic Source')
    fig_traffic.update_traces(texttemplate='<b>%{text:.2f}%</b>', textposition='outside', textfont=dict(color='white'))
    
    # FIX for clipped numbers: Add 15% extra padding to the right of the maximum value
    fig_traffic.update_xaxes(range=[0, max_val * 1.15], showgrid=False, visible=False)
    
    fig_traffic.update_layout(template='plotly_dark', height=400, yaxis=dict(title=''), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(l=0, r=0, t=40, b=0))
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
    # Sleek, thinner donuts (hole=0.7) with better colors
    df_device = load_devices()
    fig_donut_dev = px.pie(df_device, values='total_sessions', names='device_type', hole=0.7, title='Traffic Share by Device Type', color_discrete_sequence=[PRIMARY_BLUE, SUCCESS_GREEN, WARNING_YELLOW])
    fig_donut_dev.update_traces(textinfo='percent+label', textposition='outside', pull=[0.02, 0, 0], textfont=dict(color='white'))
    fig_donut_dev.update_layout(template='plotly_dark', height=200, showlegend=False, plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=40, b=10, l=40, r=40))
    st.plotly_chart(fig_donut_dev, use_container_width=True)
    
    df_retention = load_retention_profile()
    fig_retention = px.pie(df_retention, values='customer_count', names='customer_type', hole=0.7, title='Customer Retention Profile', color_discrete_sequence=[SUCCESS_GREEN, NEUTRAL_GRAY])
    fig_retention.update_traces(textinfo='percent+label', textposition='outside', pull=[0.02, 0], textfont=dict(color='white'))
    fig_retention.update_layout(template='plotly_dark', height=200, showlegend=False, plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=40, b=10, l=40, r=40))
    st.plotly_chart(fig_retention, use_container_width=True)
    
    with st.expander("View Retention SQL Query"):
        st.code("""
        WITH Customer_Orders AS (
            SELECT customer_id, LAG(transaction_timestamp) OVER(PARTITION BY customer_id ORDER BY transaction_timestamp) AS prev_transaction_timestamp, transaction_timestamp
            FROM fact_transaction WHERE customer_id IS NOT NULL
        )
        SELECT CASE WHEN AVG(date_diff('day', prev_transaction_timestamp, transaction_timestamp)) IS NULL THEN 'One-Time Buyer' ELSE 'Repeat Customer' END AS customer_type,
               COUNT(customer_id) AS customer_count
        FROM Customer_Orders GROUP BY customer_type;
        """, language="sql")

st.markdown("---")

# --- 6. Row 3: RFM Treemap & Segment Traffic Stacked Bar ---
row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    segment_counts = load_rfm_segments()
    # Meaningful semantic colors for Treemap
    color_map = {'VIP': SUCCESS_GREEN, 'Loyal Customers': '#34D399', 'Regular': NEUTRAL_GRAY, 'At Risk': WARNING_YELLOW, 'Lost': DANGER_RED}
    fig_treemap = px.treemap(segment_counts, path=[px.Constant("All Customers"), 'Segment'], values='Customer_Count', title='RFM Customer Segments', color='Segment', color_discrete_map=color_map)
    fig_treemap.update_traces(textinfo='label+value+percent root', hovertemplate='<b>%{label}</b><br>Customers: %{value}<br>%{percentRoot:.1%} of total')
    fig_treemap.update_layout(template='plotly_dark', height=400, margin=dict(t=40, b=0, l=0, r=0), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT)
    st.plotly_chart(fig_treemap, use_container_width=True)
    
    with st.expander("View SQL & Python Logic"):
        st.markdown("**1. Base RFM Extraction (SQL)**")
        st.code("""
        SELECT customer_id, transaction_id, transaction_timestamp, transaction_total
        FROM fact_transaction WHERE customer_id IS NOT NULL;
        """, language="sql")
        st.markdown("**2. RFM Scoring (Pandas)**")
        st.code("""
        rfm['R'] = pd.qcut(rfm['Recency'], q=4, labels=[4, 3, 2, 1])
        rfm['F'] = pd.qcut(rfm['Frequency'].rank(method='first'), q=4, labels=[1, 2, 3, 4])
        rfm['M'] = pd.qcut(rfm['Monetary'], q=4, labels=[1, 2, 3, 4])
        """, language="python")

with row3_col2:
    st.markdown("<h5 style='text-align: left; color: white;'>Traffic Source Distribution by Segment</h5>", unsafe_allow_html=True)
    segment_channels = load_segment_channels()
    segment_channels['percentage'] = segment_channels.groupby('Segment')['total_customers'].transform(lambda x: (x / x.sum()) * 100)
    
    # Restored the 100% Stacked Bar chart for visual variety, but with a clean discrete color palette
    fig_seg_traffic = px.bar(segment_channels, y='Segment', x='percentage', color='traffic_source', orientation='h', text='percentage', color_discrete_sequence=px.colors.qualitative.Pastel)
    
    # Ensuring text fits perfectly inside the bars
    fig_seg_traffic.update_traces(texttemplate='<b>%{text:.1f}%</b>', textposition='inside', insidetextanchor='middle', textfont=dict(color='#1E1E1E'))
    
    fig_seg_traffic.update_layout(template='plotly_dark', height=360, barmode='stack', legend_title_text='Traffic Source', xaxis=dict(title='Percentage (%)', showgrid=False), yaxis=dict(title='', showgrid=False), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=10, b=0, l=0, r=0))
    st.plotly_chart(fig_seg_traffic, use_container_width=True)
    
    with st.expander("View SQL Query"):
        st.code("""
        SELECT r.Segment, c.traffic_source, COUNT(DISTINCT r.customer_id) AS total_customers
        FROM rfm_reset r JOIN fact_clickstream c ON r.customer_id = c.customer_id
        WHERE c.purchased_flag = True GROUP BY r.Segment, c.traffic_source;
        """, language="sql")
        
