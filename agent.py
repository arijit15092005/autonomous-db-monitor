import sys
import time
import pandas as pd
from datetime import datetime
from init_db import get_connection, init_database
from detector import AnomalyDetector
from alerter import AlertDispatcher
from traffic_generator import execute_real_db_query

POLL_INTERVAL_SECONDS = 10
WINDOW_SIZE = 25
Z_THRESHOLD = 2.8


def get_last_processed_id() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_processed_id FROM agent_status WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return int(row["last_processed_id"]) if row else 0


def update_heartbeat(status: str, last_processed_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT INTO agent_status (id, status, last_heartbeat, last_processed_id)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            last_heartbeat = excluded.last_heartbeat,
            last_processed_id = excluded.last_processed_id
        """,
        (status, now_str, last_processed_id),
    )
    conn.commit()
    conn.close()


def run_single_cycle(detector: AnomalyDetector, alerter: AlertDispatcher, last_processed_id: int, auto_probe_db: bool = True) -> int:
    if auto_probe_db:
        execute_real_db_query(simulate_heavy_load=False)

    conn = get_connection()
    recent_df = pd.read_sql_query(
        f"""
        SELECT * FROM api_transactions
        ORDER BY id DESC LIMIT {WINDOW_SIZE + 50}
        """,
        conn.raw_conn,
    )

    if not recent_df.empty:
        recent_df = recent_df.sort_values("id").reset_index(drop=True)
        evaluated_df = detector.evaluate_transactions(recent_df, "response_time_ms")
        new_rows = evaluated_df[evaluated_df["id"] > last_processed_id]

        if not new_rows.empty:
            cursor = conn.cursor()
            for _, row in new_rows.iterrows():
                cursor.execute(
                    """
                    UPDATE api_transactions
                    SET z_score = ?, is_anomaly = ?
                    WHERE id = ?
                    """,
                    (float(row["z_score"]), int(row["is_anomaly"]), int(row["id"])),
                )
            conn.commit()

            anomalies = new_rows[new_rows["is_anomaly"] == 1]
            if not anomalies.empty:
                alerter.dispatch_anomalies(anomalies.to_dict(orient="records"))

            last_processed_id = int(new_rows["id"].max())
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Processed {len(new_rows)} tx(s) | "
                f"Latest ID: {last_processed_id} | Anomalies: {len(anomalies)}"
            )

    conn.close()
    update_heartbeat("ONLINE", last_processed_id)
    return last_processed_id


def run_agent(auto_probe_db: bool = True, once: bool = False):
    init_database()
    detector = AnomalyDetector(z_threshold=Z_THRESHOLD, window_size=WINDOW_SIZE)
    alerter = AlertDispatcher()

    last_processed_id = get_last_processed_id()
    print(f"[Agent] Started Autonomous Monitoring Agent (resuming from ID > {last_processed_id})")

    if once:
        for _ in range(3):
            last_processed_id = run_single_cycle(detector, alerter, last_processed_id, auto_probe_db=auto_probe_db)
            time.sleep(2)
        print("[Agent] Cloud scheduled monitoring burst completed.")
        return

    try:
        while True:
            try:
                last_processed_id = run_single_cycle(detector, alerter, last_processed_id, auto_probe_db=auto_probe_db)
            except Exception as loop_err:
                print(f"[Warning] Temporary DB/loop issue, retrying safely: {loop_err}")

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        update_heartbeat("OFFLINE", last_processed_id)
        print("\n[Agent] Stopped cleanly by user.")


if __name__ == "__main__":
    run_once = "--once" in sys.argv
    run_agent(auto_probe_db=True, once=run_once)