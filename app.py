import streamlit as st
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="Autonomous DB Monitor", layout="wide", page_icon="📡")

st.title("📡 Autonomous Database Anomaly Monitor")
st.markdown("Live monitoring agent calculating dynamic rolling Z-scores to flag database transaction anomalies.")

# Sidebar Controls
st.sidebar.header("Agent Configuration")
threshold = st.sidebar.slider("Z-Score Anomaly Threshold", min_value=1.5, max_value=4.0, value=2.8, step=0.1)
window_size = st.sidebar.slider("Rolling Baseline Window", min_value=10, max_value=50, value=20, step=5)

# Session State for Live Transactions
if "transactions" not in st.session_state:
    np.random.seed(42)
    initial_latencies = np.random.normal(loc=150, scale=15, size=30).tolist()
    st.session_state.transactions = [
        {"id": i + 1, "endpoint": "/home", "response_time_ms": round(lat, 2), "status": 200}
        for i, lat in enumerate(initial_latencies)
    ]

# Actions
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("Generate Traffic"):
        new_id = len(st.session_state.transactions) + 1
        lat = round(np.random.normal(150, 15), 2)
        st.session_state.transactions.append({"id": new_id, "endpoint": "/api/data", "response_time_ms": lat, "status": 200})
with col2:
    if st.button("🚨 Inject Spike"):
        new_id = len(st.session_state.transactions) + 1
        spike_lat = round(np.random.uniform(700, 1100), 2)
        st.session_state.transactions.append({"id": new_id, "endpoint": "/checkout", "response_time_ms": spike_lat, "status": 504})

# Data Processing & Anomaly Math
df = pd.DataFrame(st.session_state.transactions)
df["rolling_mean"] = df["response_time_ms"].rolling(window=window_size, min_periods=5).mean()
df["rolling_std"] = df["response_time_ms"].rolling(window=window_size, min_periods=5).std().replace(0, 1e-6)
df["z_score"] = (df["response_time_ms"] - df["rolling_mean"]) / df["rolling_std"]
df["is_anomaly"] = df["z_score"] > threshold

# Metrics Row
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Transactions Monitored", len(df))
m2.metric("Latest Latency", f"{df['response_time_ms'].iloc[-1]} ms")
m3.metric("Baseline Mean", f"{round(df['rolling_mean'].iloc[-1], 2)} ms")
anomalies_count = int(df["is_anomaly"].sum())
m4.metric("Anomalies Flagged", anomalies_count, delta="Spikes Detected" if anomalies_count > 0 else None, delta_color="inverse")

# Main Latency Chart
st.subheader("Real-Time Latency & Dynamic Baseline")
st.line_chart(df.set_index("id")[["response_time_ms", "rolling_mean"]])

# Recent Table
st.subheader("Transaction Log & Anomaly Status")
def highlight_anomalies(val):
    return 'background-color: #ff4b4b; color: white;' if val is True else ''

display_df = df[["id", "endpoint", "response_time_ms", "status", "z_score", "is_anomaly"]].tail(15)
st.dataframe(display_df.style.applymap(highlight_anomalies, subset=["is_anomaly"]), use_container_width=True)