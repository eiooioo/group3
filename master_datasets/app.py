import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import sqlite3
import os

st.set_page_config(page_title="Real-Time Fall Monitor", layout="wide")

# Refresh every 1000ms (1 second)
st_autorefresh(interval=1000, key="datarefresh")

st.title("⚡ Real-Time SQLite Fall Monitoring Dashboard")

# Threshold Sliders
acc_threshold = st.sidebar.slider("Acc Threshold (g)", 1.5, 5.0, 3.0, 0.1)
gyro_threshold = st.sidebar.slider("Gyro Threshold (°/s)", 100, 800, 400, 25)

# Locate SQLite DB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "fall_data.db")

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    
    # Query recent 200 telemetry entries
    query = "SELECT * FROM fall_events ORDER BY id DESC LIMIT 200"
    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        # Reverse to show chronological order on charts
        df = df.iloc[::-1].reset_index(drop=True)
        
        # Calculate dynamic threshold alerts based on current sidebar values
        df['dynamic_fall'] = (df['acc_magnitude'] >= acc_threshold) & (df['gyro_magnitude'] >= gyro_threshold)
        total_falls = df['dynamic_fall'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("Latest Acc (g)", f"{df['acc_magnitude'].iloc[-1]:.2f} g")
        col2.metric("Total Falls Logged (Recent)", int(total_falls))

        # Real-time Plotly Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['acc_magnitude'], mode='lines+markers', name="Acc Magnitude (g)"))
        fig.add_hline(y=acc_threshold, line_dash="dash", line_color="red", annotation_text="Threshold")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Historical Data Table
        with st.expander("View Raw Database Log"):
            st.dataframe(df.sort_values(by="id", ascending=False))
    else:
        st.info("Database initialized. Waiting for telemetry entries...")
else:
    st.warning("Database file `fall_data.db` not found. Please run `valentine.py` to start logging.")