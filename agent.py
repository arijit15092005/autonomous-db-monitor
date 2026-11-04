import sqlite3
import time
import pandas as pd
from detector import AnomalyDetector
from alerter import AlertDispatcher

DB_PATH = "app_data.db"
POLL_INTERVAL_SECONDS = 5

def run_agent():
    detector = AnomalyDetector(z_threshold=2.8)
    alerter = AlertDispatcher()
    last_processed_id = 0

    print(f"[*] Autonomous Database Agent running. Polling every {POLL_INTERVAL_SECONDS}s...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM api_transactions")
    res = cursor.fetchone()[0]
    last_processed_id = res if res else 0
    conn.close()

    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            window_df = pd.read_sql_query(
                "SELECT * FROM api_transactions ORDER BY id DESC LIMIT 200", 
                conn
            )
            new_records_df = pd.read_sql_query(
                f"SELECT * FROM api_transactions WHERE id > {last_processed_id}",
                conn
            )
            conn.close()

            if not new_records_df.empty:
                max_id = new_records_df["id"].max()
                anomalies = detector.find_anomalies(window_df, "response_time_ms")
                new_anomalies = anomalies[anomalies["id"].isin(new_records_df["id"])]

                if not new_anomalies.empty:
                    records = new_anomalies.to_dict(orient="records")
                    alerter.log_incident(records)
                    alerter.notify_desktop(
                        "Database Spike Detected",
                        f"{len(records)} latency anomalies found."
                    )

                last_processed_id = max_id

        except Exception as e:
            print(f"[Error] Execution loop failure: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_agent()