# Autonomous Database Anomaly Monitoring Agent

A Python-based monitoring worker that continuously monitors transactional database tables, calculates rolling statistical baselines, detects latency anomalies using dynamic Z-score calculations, and dispatches native desktop alerts.

## Features
- **Database:** SQLite store tracking response latency and status codes.
- **Statistical Engine:** Evaluates rolling windows using Z-Score ($Z > 2.8$) deviation logic.
- **Autonomous Poller:** Continuously monitors newly appended records.
- **Alert Dispatcher:** Dispatches native OS banner notifications via `plyer`.
- **Traffic Simulator:** Generates continuous stochastic transactions with periodic anomalous latency spikes.

## Setup & Running

1. **Create and activate environment:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt