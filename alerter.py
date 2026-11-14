import os
import requests
from datetime import datetime
from init_db import get_connection


class AlertDispatcher:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = (webhook_url or os.getenv("ALERT_WEBHOOK_URL", "")).strip()

    def _get_anomaly_columns(self, cursor):
        """Inspect existing anomaly_logs columns in PostgreSQL or SQLite so inserts never break."""
        try:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'anomaly_logs'
                """
            )
            cols = [row[0] for row in cursor.fetchall()]
            if cols:
                return set(cols)
        except Exception:
            pass

        cursor.execute("PRAGMA table_info(anomaly_logs)")
        return {row[1] for row in cursor.fetchall()}

    def dispatch_anomalies(self, anomalies: list) -> int:
        if not anomalies:
            return 0

        conn = get_connection()
        cursor = conn.cursor()
        existing_cols = self._get_anomaly_columns(cursor)
        saved_count = 0

        for item in anomalies:
            tx_id = item.get("id")
            endpoint = str(item.get("endpoint", "UNKNOWN"))
            latency = float(item.get("response_time_ms", 0.0))
            z_score = float(item.get("z_score", 0.0))
            severity = "CRITICAL" if abs(z_score) >= 4.0 else "HIGH"
            detected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = (
                f"[{severity}] Latency spike on {endpoint}: "
                f"{latency:.2f} ms (Z-Score: {z_score:.2f})"
            )

            # Skip duplicate transaction_id safely in both PostgreSQL and SQLite
            if tx_id is not None and "transaction_id" in existing_cols:
                cursor.execute(
                    "SELECT 1 FROM anomaly_logs WHERE transaction_id = ?",
                    (int(tx_id),),
                )
                if cursor.fetchone():
                    continue

            candidate_data = {
                "transaction_id": int(tx_id) if tx_id is not None else None,
                "endpoint": endpoint,
                "response_time_ms": latency,
                "z_score": z_score,
                "severity": severity,
                "message": message,
                "detected_at": detected_at,
                "timestamp": detected_at,
                "created_at": detected_at,
            }

            cols_to_insert = [
                col for col, val in candidate_data.items()
                if col in existing_cols and val is not None
            ]

            if cols_to_insert:
                placeholders = ", ".join(["?"] * len(cols_to_insert))
                col_names = ", ".join(cols_to_insert)
                values = tuple(candidate_data[col] for col in cols_to_insert)

                cursor.execute(
                    f"INSERT INTO anomaly_logs ({col_names}) VALUES ({placeholders})",
                    values,
                )
                saved_count += 1

            print(f"[ALERT DISPATCHED] {detected_at} | {message}")

            if self.webhook_url:
                try:
                    requests.post(
                        self.webhook_url,
                        json={
                            "text": message,
                            "endpoint": endpoint,
                            "response_time_ms": latency,
                            "z_score": round(z_score, 2),
                            "severity": severity,
                            "detected_at": detected_at,
                        },
                        timeout=5,
                    )
                except Exception as webhook_err:
                    print(f"[Warning] Webhook notification skipped: {webhook_err}")

        conn.commit()
        conn.close()
        return saved_count


def trigger_alerts(anomalies: list, webhook_url: str = None) -> int:
    """Backward-compatible helper function if called directly."""
    dispatcher = AlertDispatcher(webhook_url=webhook_url)
    return dispatcher.dispatch_anomalies(anomalies)