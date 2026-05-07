import streamlit as st
import pandas as pd
import plotly.express as px
import json

# Must be the first Streamlit command
st.set_page_config(
    page_title="Butuan Incident Management Dashboard",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# THEME COLORS & CUSTOM CSS
# =========================
# Palette: Blue, Green, Orange
THEME_COLORS = ['#2E86C1', '#27AE60', '#F39C12', '#1ABC9C', '#D35400']

st.markdown("""
<style>
    /* Metric Card Styling */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E6E9EF;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #2E86C1; /* Default Blue */
    }
    
    /* Assign specific colors to different metric cards based on order */
    div[data-testid="stMetric"]:nth-of-type(1) { border-left-color: #2E86C1; } /* Blue */
    div[data-testid="stMetric"]:nth-of-type(2) { border-left-color: #F39C12; } /* Orange */
    div[data-testid="stMetric"]:nth-of-type(3) { border-left-color: #27AE60; } /* Green */
    div[data-testid="stMetric"]:nth-of-type(4) { border-left-color: #2E86C1; } /* Blue */

    section[data-testid="stSidebar"] img {
        display: block;
        margin: 0 auto 20px auto;
        width: 100px;
        border-radius: 16px;
        border: 1px solid #E6E9EF;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.08);
        transition: transform 0.25s ease, box-shadow 0.25s ease, filter 0.25s ease;
        cursor: pointer;
    }

    section[data-testid="stSidebar"] img:hover {
        transform: translateY(-2px) scale(1.03);
        box-shadow: 0 18px 35px rgba(0, 0, 0, 0.14);
        filter: brightness(1.02);
    }

    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("data.csv")
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("⚠️ Data file 'data.csv' not found. Please ensure it is in the same directory.")
    st.stop()

# =========================
# DATA CLEANING
# =========================
time_cols = [
    "COMPUTED RESPONSE TIME",
    "COMPUTED DISPATCH TIME",
    "COMPUTED RUN TIME",
    "COMPUTED SCENE TIME",
    "COMPUTED TRANSPORT TIME",
    "AVERAGED TURN AROUND TIME"
]

for col in time_cols:
    if col in df.columns:
        df[col] = pd.to_timedelta(df[col], errors='coerce').dt.total_seconds()

df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'], errors='coerce')

# Feature engineering
df['hour'] = df['TIMESTAMP'].dt.hour
df['day'] = df['TIMESTAMP'].dt.day_name()
df['month'] = df['TIMESTAMP'].dt.to_period('M').astype(str)

# SLA flag (8 mins = 480 sec)
df['within_sla'] = df['COMPUTED RESPONSE TIME'] <= 480

# =========================
# SIDEBAR FILTERS
# ======================
with st.sidebar:
    st.image("logo.jpg", width=100)
    st.header("Dashboard Filters")
    st.markdown("Use the filters below to slice the data.")

    barangays = st.multiselect("Select Barangay", sorted(df['BARANGAY'].dropna().unique()))
    priority = st.multiselect("Select Priority", sorted(df['PRIORITY DISPATCH'].dropna().unique()))
    month = st.multiselect("Select Month", sorted(df['month'].dropna().unique()))

filtered_df = df.copy()

if barangays:
    filtered_df = filtered_df[filtered_df['BARANGAY'].isin(barangays)]
if priority:
    filtered_df = filtered_df[filtered_df['PRIORITY DISPATCH'].isin(priority)]
if month:
    filtered_df = filtered_df[filtered_df['month'].isin(month)]

# =========================
# MAIN HEADER & KPIs
# =========================
st.title("Incident Management Dashboard")
st.markdown("Real-time monitoring and analytics for emergency response.")
st.divider()

col1, col2, col3 = st.columns(3)

col1.metric("Total Incidents", f"{len(filtered_df):,}")

avg_run = filtered_df['COMPUTED RUN TIME'].mean() / 60
col2.metric("Avg Run Time", f"{avg_run:.1f} min")

top_user = filtered_df['USER'].value_counts().index[0] if len(filtered_df) > 0 else "N/A"
top_user_count = filtered_df['USER'].value_counts().values[0] if len(filtered_df) > 0 else 0
col3.metric("Top User", top_user)
col3.markdown(f"**Incidents Handled:** {top_user_count}")

st.markdown("<br>", unsafe_allow_html=True) # Spacer

# =========================
# INCIDENT TRENDS
# =========================
st.subheader("Incident Trends Over Time (Last 4 Months)")

# Filter data for last 4 months
last_4_months = filtered_df[filtered_df['TIMESTAMP'] >= filtered_df['TIMESTAMP'].max() - pd.Timedelta(days=120)]
# Group by day (extract date from timestamp)
last_4_months_copy = last_4_months.copy()
last_4_months_copy['DATE'] = last_4_months_copy['TIMESTAMP'].dt.date
trend = last_4_months_copy.groupby('DATE').size().reset_index(name='count')

fig_trend = px.line(
    trend, x='DATE', y='count', 
    color_discrete_sequence=["#2E86C1"] # Blue
)
fig_trend.update_layout(plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Date", yaxis_title="Incidents")
fig_trend.update_xaxes(showgrid=True, gridcolor='#E6E9EF')
fig_trend.update_yaxes(showgrid=True, gridcolor='#E6E9EF')
st.plotly_chart(fig_trend, use_container_width=True)

# =========================
# DISTRIBUTIONS (BAR & PIE)
# =========================
col_a, col_b = st.columns([6, 4]) # 60/40 split

with col_a:
    st.subheader("Top 10 Barangays")
    st.write("Barangays with the highest number of incidents.")
    brgy_counts = filtered_df['BARANGAY'].value_counts().head(10).reset_index()
    brgy_counts.columns = ['BARANGAY', 'Count']
    
    fig_bar = px.bar(
        brgy_counts, x='BARANGAY', y='Count',
        color_discrete_sequence=["#2E86C1"] # Green
    )
    fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", xaxis_title="", yaxis_title="Incidents")
    st.plotly_chart(fig_bar, use_container_width=True)

with col_b:
    st.subheader("Resource Team Allocation")
    fig_pie = px.pie(
        filtered_df, names='RESOURCE TEAM', 
        color_discrete_sequence=THEME_COLORS, # Mixed theme colors
        hole=0.4 # Donut chart looks cleaner
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# =========================
# RESPONSE TIME & HEATMAP
# =========================
st.divider()
st.subheader("Incident Heatmap (Day vs Hour)")
filtered_df['hour_label'] = filtered_df['hour'].fillna(0).astype(int).replace({0: 24})
heatmap_data = filtered_df.pivot_table(index='day', columns='hour_label', aggfunc='size', fill_value=0)
# Order days logically
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
heatmap_data = heatmap_data.reindex(days_order).dropna()

fig_heat = px.imshow(
    heatmap_data, 
    color_continuous_scale='Blues', # Using blue scale
    aspect="auto"
)
st.plotly_chart(fig_heat, use_container_width=True)

# =========================
# LOAD GEOJSON
# =========================
try:
    with open("Butuan Data.geojson", encoding="utf-8") as f:
        geojson = json.load(f)
except FileNotFoundError:
    st.error("⚠️ GeoJSON file 'Butuan Data.geojson' not found.")
    geojson = None
except Exception as e:
    st.error(f"⚠️ Error loading GeoJSON: {e}")
    geojson = None

# =========================
# AGGREGATE & CATEGORIZE
# =========================
barangay_heatmap = (
    filtered_df.groupby("BARANGAY")
    .size()
    .reset_index(name="INCIDENT_COUNT")
)

# Define thresholds and labels
# You can adjust these numbers based on what "High" means for Butuan
bins = [0, 5, 15, 50, float('inf')]
labels = ['Low (1-5)', 'Moderate (6-15)', 'High (16-50)', 'Critical (50+)']

barangay_heatmap['Risk Level'] = pd.cut(
    barangay_heatmap['INCIDENT_COUNT'], 
    bins=bins, 
    labels=labels, 
    include_lowest=True
)

# Map categories to specific colors
color_discrete_map = {
    'Low (1-5)': '#27AE60',      # Green
    'Moderate (6-15)': '#F39C12', # Orange
    'High (16-50)': '#E67E22',    # Dark Orange
    'Critical (50+)': '#C0392B'   # Red
}

# =========================
# CREATE CATEGORICAL CHOROPLETH
# =========================
if geojson is not None:
    fig_map = px.choropleth_mapbox(
        barangay_heatmap,
        geojson=geojson,
        locations="BARANGAY",
        featureidkey="properties.BARANGAY",
        color="Risk Level",  # Switch to categorical column
        
        color_discrete_map=color_discrete_map, # Use our custom colors
        category_orders={"Risk Level": labels}, # Keeps the legend in order
        
        mapbox_style="carto-positron",
        center={"lat": 8.9475, "lon": 125.5406},
        zoom=10,
        opacity=0.7,
        hover_name="BARANGAY",
        hover_data={
            "INCIDENT_COUNT": True,
            "Risk Level": True
        }
    )

    # Remove range_color as it's no longer continuous
    # Remove coloraxis_colorbar from layout as discrete maps use a legend
else:
    st.warning("⚠️ Could not build the choropleth map because the GeoJSON file failed to load.")