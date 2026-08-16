import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import os

st.set_page_config(page_title="Real-Time Fall Detection", layout="wide")

# Automatically refresh page every 1000 ms (1 second)
count = st_autorefresh(interval=1000, key="datarefresh")

st.title("⚡ Live Real-Time Fall Detection Dashboard")

# Thresholds
acc_threshold = st.sidebar.slider("Acc Threshold (g)", 1.5, 5.0, 3.0, 0.1)
gyro_threshold = st.sidebar.slider("Gyro Threshold (°/s)", 100, 800, 400, 25)

# Load live file without caching
live_file = "live_data.csv"

if os.path.exists(live_file):
    df = pd.read_csv(live_file)
    
    # Calculate vector magnitudes
    df['SVM_Acc'] = np.sqrt(df['AccX']**2 + df['AccY']**2 + df['AccZ']**2)
    df['SVM_Gyro'] = np.sqrt(df['GyroX']**2 + df['GyroY']**2 + df['GyroZ']**2)
    
    # Check for falls
    falls = df[(df['SVM_Acc'] >= acc_threshold) & (df['SVM_Gyro'] >= gyro_threshold)]
    
    # Show last 100 readings in real-time chart
    recent_df = df.tail(100)
    
    st.metric("Latest Acceleration", f"{recent_df['SVM_Acc'].iloc[-1]:.2f} g")
    st.metric("Total Falls Detected", len(falls))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=recent_df['SVM_Acc'], name="Live SVM Acc"))
    fig.add_hline(y=acc_threshold, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Waiting for live incoming telemetry stream...")