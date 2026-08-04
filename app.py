import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- 1. Page Configuration ---
st.set_page_config(page_title="ElecMart Performance Hub", layout="wide", initial_sidebar_state="collapsed")
st.title("ElecMart Executive Performance Hub 📊")
st.markdown("---")

# --- Color Palette ---
PRIMARY_COLOR = '#00BFA5' # Teal
SECONDARY_COLORS = ['#00BFA5', '#1f77b4', '#FF7F0E', '#E57373', '#9575CD']
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

st.markdown("---")

# --- 4. Row 1: Funnel & Cohort ---
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    df_funnel = load_funnel()
    df_funnel['custom_text'] = df_funnel['Count'].apply(lambda x: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.1f}k")
    fig_funnel = px.funnel(df_funnel, x='Count', y='Stage', text='custom_text', title='Conversion Funnel (Macro Level)', color_discrete_sequence=[PRIMARY_COLOR])
    fig_funnel.update_traces(texttemplate='<b>%{text}</b><br>%{percentInitial:.0%}', textfont=dict(size=14, color='white'))
    fig_funnel.update_layout(template='plotly_dark', height=350, yaxis_title=None, xaxis_title=None, plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_funnel, use_container_width=True)

with row1_col2:
    retention_pct = load_cohort()
    # Using 'Teal' color scale to match the Primary Color
    fig_cohort = px.imshow(retention_pct, text_auto='.1f', aspect="auto", color_continuous_scale='Teal', title='Customer Retention Cohort (%)')
    fig_cohort.update_layout(template='plotly_dark', height=350, coloraxis_showscale=False, xaxis=dict(side='bottom', title='Months Since First Purchase', showgrid=False), yaxis=dict(title='', showgrid=False), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_cohort, use_container_width=True)

st.markdown("---")

# --- 5. Row 2: Traffic & Devices (Modern Progress Bars) ---
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    df_traffic = load_traffic()
    fig_traffic = px.bar(df_traffic, x='overall_conversion_rate', y='traffic_source', orientation='h', text='overall_conversion_rate', color_discrete_sequence=[PRIMARY_COLOR], title='Conversion Rate by Traffic Source')
    fig_traffic.update_traces(texttemplate='<b>%{text:.2f}%</b>', textposition='outside', textfont=dict(color='white'))
    fig_traffic.update_layout(template='plotly_dark', height=250, xaxis=dict(showgrid=False, visible=False, rangemode='tozero'), yaxis=dict(title=''), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_traffic, use_container_width=True)

with row2_col2:
    st.markdown("<h5 style='text-align: left; color: white;'>Traffic Share by Device Type</h5>", unsafe_allow_html=True)
    df_device = load_devices()
    df_device['Percentage'] = (df_device['total_sessions'] / df_device['total_sessions'].sum()) * 100
    df_device['Dummy'] = 'Devices' # Needed for horizontal stacked bar
    
    # Modern Horizontal Stacked Bar instead of Donut
    fig_dev = px.bar(df_device, y='Dummy', x='Percentage', color='device_type', orientation='h', text='Percentage', color_discrete_sequence=['#1f77b4', '#00BFA5', '#FF7F0E'])
    fig_dev.update_traces(texttemplate='<b>%{x:.1f}%</b><br>%{data.name}', textposition='inside', insidetextanchor='middle')
    fig_dev.update_layout(template='plotly_dark', height=150, barmode='stack', showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=10, b=0, l=0, r=0))
    st.plotly_chart(fig_dev, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True) # Spacer
    
    st.markdown("<h5 style='text-align: left; color: white;'>Customer Retention Profile</h5>", unsafe_allow_html=True)
    df_retention = load_retention_profile()
    df_retention['Percentage'] = (df_retention['customer_count'] / df_retention['customer_count'].sum()) * 100
    df_retention['Dummy'] = 'Retention'
    
    # Modern Horizontal Stacked Bar instead of Donut
    fig_ret = px.bar(df_retention, y='Dummy', x='Percentage', color='customer_type', orientation='h', text='Percentage', color_discrete_sequence=['#00BFA5', '#546E7A'])
    fig_ret.update_traces(texttemplate='<b>%{x:.1f}%</b><br>%{data.name}', textposition='inside', insidetextanchor='middle')
    fig_ret.update_layout(template='plotly_dark', height=150, barmode='stack', showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=10, b=0, l=0, r=0))
    st.plotly_chart(fig_ret, use_container_width=True)

st.markdown("---")

# --- 6. Row 3: RFM Treemap & Segment Traffic Heatmap ---
row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    segment_counts = load_rfm_segments()
    # Updated Color Map for Dark Theme compatibility
    color_map = {'VIP': '#00BFA5', 'Loyal Customers': '#4DB6AC', 'Regular': '#78909C', 'At Risk': '#FFB74D', 'Lost': '#E57373'}
    fig_treemap = px.treemap(segment_counts, path=[px.Constant("All Customers"), 'Segment'], values='Customer_Count', title='RFM Customer Segments', color='Segment', color_discrete_map=color_map)
    fig_treemap.update_traces(textinfo='label+value+percent root', hovertemplate='<b>%{label}</b><br>Customers: %{value}<br>%{percentRoot:.1%} of total')
    fig_treemap.update_layout(template='plotly_dark', height=400, margin=dict(t=40, b=0, l=0, r=0), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT)
    st.plotly_chart(fig_treemap, use_container_width=True)

with row3_col2:
    segment_channels = load_segment_channels()
    segment_channels['percentage'] = segment_channels.groupby('Segment')['total_customers'].transform(lambda x: (x / x.sum()) * 100)
    
    # Pivoting data for Heatmap instead of Stacked Bar
    heatmap_data = segment_channels.pivot(index='Segment', columns='traffic_source', values='percentage')
    
    # Reordering rows to make logical sense (Best to Worst)
    ordered_segments = ['VIP', 'Loyal Customers', 'Regular', 'At Risk', 'Lost']
    existing_segments = [s for s in ordered_segments if s in heatmap_data.index]
    heatmap_data = heatmap_data.reindex(existing_segments)
    
    fig_seg_heatmap = px.imshow(heatmap_data, text_auto='.1f', aspect="auto", color_continuous_scale='Blues', title='Traffic Distribution by Segment (%)')
    fig_seg_heatmap.update_layout(template='plotly_dark', height=400, coloraxis_showscale=False, xaxis=dict(side='bottom', title='', showgrid=False), yaxis=dict(title='', showgrid=False), plot_bgcolor=BG_TRANSPARENT, paper_bgcolor=BG_TRANSPARENT, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_seg_heatmap, use_container_width=True)

# Note: SQL Expander buttons were removed in this clean UI version to reduce clutter, 
# but they can be easily re-added using st.expander() below each chart if needed for the portfolio.
