# Autonomous Database Anomaly Monitor

An autonomous full-stack database monitoring agent built with Python, Streamlit, Neon Cloud PostgreSQL, and GitHub Actions, featuring rolling Z-score statistical anomaly detection and automated alerting.

---

## 👥 Team Members (Section B, ECE - IEM)
| Name | Roll No. | Enrollment No. |
| :--- | :---: | :---: |
| **Arijit Mallik** (Team Lead) | 154 | 12024052003154 |
| **Sayan Maity** | 156 | 12024052003156 |
| **Sudipta Maiti** | 159 | 12024052003159 |
| **Sayan Bag** | 160 | 12024052003160 |

---

## 🚀 Project Overview & Architecture
This project is an autonomous full-stack database anomaly monitoring system designed to fulfill academic and industry requirements:
- **Frontend / Dashboard:** Live Streamlit web application providing real-time telemetry, transaction counts, latency charts, and anomaly logs.
- **Backend Monitoring Agent (gent.py):** Collects performance metrics, executes rolling Z-score statistical anomaly detection, and updates database state autonomously.
- **Cloud Database:** Persistent Neon Serverless PostgreSQL storing transactions, anomalies, and agent heartbeats 24/7.
- **Cloud Automation:** GitHub Actions executing background monitoring heartbeats automatically.

---

## 🌱 UN Sustainable Development Goals (SDG) Alignment

| SDG Goal | Target Area | How This Project Contributes |
| :--- | :--- | :--- |
| **SDG 9** | Industry, Innovation & Infrastructure | Builds resilient, self-healing cloud database infrastructure with automated fault detection and real-time observability. |
| **SDG 12** | Responsible Consumption & Production | Detects runaway queries and latency spikes early, reducing wasted cloud compute power and server energy consumption. |
| **SDG 8** | Decent Work & Economic Growth | Automates 24/7 database monitoring, reducing manual DevOps fatigue and preventing costly business service downtime. |

---

## 🔗 Live Links
- **Live Streamlit App:** [Autonomous DB Monitor Dashboard](https://autonomous-db-monitor-n9pmtm9idw6tjc4zfx4ypv.streamlit.app/)
- **GitHub Repository:** [arijit15092005/autonomous-db-monitor](https://github.com/arijit15092005/autonomous-db-monitor)
