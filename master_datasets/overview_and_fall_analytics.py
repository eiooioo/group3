import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os

# Determine path relative to app.py location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_name = os.path.join(BASE_DIR, "all_workers.xlsx")

if not os.path.exists(file_name):
    # Fallback to root directory if placed in root
    file_name = "all_workers.xlsx"

# Page Configuration
st.set_page_config(
    page_title="Worker Safety Overview & Fall Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

file_name = "all_workers.xlsx"
if not os.path.exists(file_name):
    st.error(f"❌ File '{file_name}' not found in current directory: {os.getcwd()}")
    st.info("Please ensure 'all_workers.xlsx' is placed in the same folder as app.py.")
    st.stop()

# 1. Data Loader
@st.cache_data
def load_and_process_data(path):
    xls = pd.ExcelFile(path)
    all_dfs = []
    
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet)
        df['Worker_Name'] = sheet
        
        # Calculate Signal Vector Magnitudes
        df['SVM_Acc'] = np.sqrt(df['AccX']**2 + df['AccY']**2 + df['AccZ']**2)
        df['SVM_Gyro'] = np.sqrt(df['GyroX']**2 + df['GyroY']**2 + df['GyroZ']**2)
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        all_dfs.append(df)
        
    combined = pd.concat(all_dfs, ignore_index=True)
    return combined, xls.sheet_names

df_raw, worker_sheets = load_and_process_data(file_name)

# 2. Sidebar Controls
st.sidebar.title("Dashboard Controls")

# Options include All Workers + individual sheets
view_options = ["All Workers (Combined Overview)"] + worker_sheets
selected_option = st.sidebar.selectbox("Select View Profile", view_options)

st.sidebar.markdown("---")
st.sidebar.subheader("Fall Detection Thresholds")
acc_threshold = st.sidebar.slider("Acceleration Threshold (g)", 1.5, 5.0, 3.0, 0.1)
gyro_threshold = st.sidebar.slider("Gyroscope Threshold (°/s)", 100, 800, 400, 25)

# Calculate fall flags across raw dataset
df_raw['Is_Fall'] = (df_raw['SVM_Acc'] >= acc_threshold) & (df_raw['SVM_Gyro'] >= gyro_threshold)

# Filter dataset depending on sidebar selection
if selected_option == "All Workers (Combined Overview)":
    active_df = df_raw.copy()
else:
    active_df = df_raw[df_raw['Worker_Name'] == selected_option].copy()

falls_detected = active_df[active_df['Is_Fall']]

# 3. Dynamic KPIs
st.title("👷 Real-Time Worker Safety & Fall Analytics")
st.caption(f"Viewing Telemetry for: **{selected_option}**")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Telemetry Samples", f"{len(active_df):,}")
col2.metric("Peak Acceleration", f"{active_df['SVM_Acc'].max():.2f} g")
col3.metric("Peak Gyroscope", f"{active_df['SVM_Gyro'].max():.1f} °/s")
col4.metric(
    "Total Fall Flags", 
    f"{len(falls_detected)}", 
    delta="CRITICAL ALERT" if len(falls_detected) > 0 else "NORMAL",
    delta_color="inverse" if len(falls_detected) > 0 else "normal"
)

st.markdown("---")

# 4. Mode-Specific Visualizations
if selected_option == "All Workers (Combined Overview)":
    st.subheader("📊 Comparative Fall Analysis Across All Workers")
    
    # Combined Fall Event Breakdown Bar Chart
    fall_counts = df_raw[df_raw['Is_Fall']]['Worker_Name'].value_counts().reset_index()
    fall_counts.columns = ['Worker_Name', 'Fall_Count']
    
    fig_bar = px.bar(
        fall_counts, 
        x='Worker_Name', 
        y='Fall_Count', 
        color='Worker_Name',
        title=f"Total Fall Flags Triggered per Worker (Thresholds: {acc_threshold}g & {gyro_threshold}°/s)",
        labels={'Worker_Name': 'Worker Profile', 'Fall_Count': 'Fall Incidents'},
        text_auto=True
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Combined Multi-Line Telemetry Overlay Chart
    st.subheader("📈 Multi-Worker Telemetry Overlay")
    fig_combined = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=False, 
        vertical_spacing=0.1,
        subplot_titles=("Acceleration Vector Magnitude (SVM Acc)", "Gyroscope Vector Magnitude (SVM Gyro)")
    )
    
    for worker in worker_sheets:
        worker_data = df_raw[df_raw['Worker_Name'] == worker]
        fig_combined.add_trace(
            go.Scatter(x=worker_data['Timestamp'], y=worker_data['SVM_Acc'], mode='lines', name=f"{worker} (Acc)"),
            row=1, col=1
        )
        fig_combined.add_trace(
            go.Scatter(x=worker_data['Timestamp'], y=worker_data['SVM_Gyro'], mode='lines', name=f"{worker} (Gyro)"),
            row=2, col=1
        )
        
    fig_combined.add_hline(y=acc_threshold, line_dash="dash", line_color="red", row=1, col=1)
    fig_combined.add_hline(y=gyro_threshold, line_dash="dash", line_color="red", row=2, col=1)
    fig_combined.update_layout(height=600, hovermode="x unified")
    st.plotly_chart(fig_combined, use_container_width=True)

else:
    # Individual Worker Detailed Plot
    st.subheader(f"📈 Sensor Telemetry for {selected_option}")
    fig_indiv = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08,
        subplot_titles=("SVM Acc (g)", "SVM Gyro (°/s)")
    )
    
    fig_indiv.add_trace(go.Scatter(x=active_df['Timestamp'], y=active_df['SVM_Acc'], name="SVM Acc"), row=1, col=1)
    fig_indiv.add_hline(y=acc_threshold, line_dash="dash", line_color="red", row=1, col=1)
    
    fig_indiv.add_trace(go.Scatter(x=active_df['Timestamp'], y=active_df['SVM_Gyro'], name="SVM Gyro"), row=2, col=1)
    fig_indiv.add_hline(y=gyro_threshold, line_dash="dash", line_color="red", row=2, col=1)
    
    if not falls_detected.empty:
        fig_indiv.add_trace(
            go.Scatter(x=falls_detected['Timestamp'], y=falls_detected['SVM_Acc'], mode='markers', name='FALL', marker=dict(color='red', size=10, symbol='x')),
            row=1, col=1
        )
        fig_indiv.add_trace(
            go.Scatter(x=falls_detected['Timestamp'], y=falls_detected['SVM_Gyro'], mode='markers', name='FALL', marker=dict(color='red', size=10, symbol='x'), showlegend=False),
            row=2, col=1
        )
        
    fig_indiv.update_layout(height=600, hovermode="x unified")
    st.plotly_chart(fig_indiv, use_container_width=True)

# 5. Incident Audit Log Table
st.subheader("📋 Incident Audit Log")
if not falls_detected.empty:
    st.warning(f"⚠️ {len(falls_detected)} potential fall event(s) detected.")
    st.dataframe(
        falls_detected[['Worker_Name', 'Timestamp', 'AccX', 'AccY', 'AccZ', 'SVM_Acc', 'GyroX', 'GyroY', 'GyroZ', 'SVM_Gyro']],
        use_container_width=True
    )
else:
    st.success("✅ No fall incidents detected under current threshold parameters.")