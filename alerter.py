import os
import requests
from datetime import datetime
from init_db import get_connection

try:
    from plyer import notification
except Exception:
    notification = None


class AlertDispatcher:
    def __init__(self):
        # Optional secure credentials loaded from environment variables (never hardcoded)
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    def notify_desktop(self, title: str, message: str):
        if notification is None:
            return
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Autonomous DB Monitor",
                timeout=5,
            )
        except Exception as e:
            print(f"[Info] Desktop popup skipped (headless/cloud environment): {e}")

    def notify_telegram(self, message: str):
        """Sends an optional Telegram alert if environment variables are configured."""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            requests.post(
                url,
                json={"chat_id": self.telegram_chat_id, "text": message},
                timeout=5,
            )
        except Exception as e:
            print(f"[Warning] Telegram alert failed: {e}")

    def dispatch_anomalies(self, anomaly_records: list) -> int:
        """
        Persists anomalies to anomaly_logs with deduplication (UNIQUE transaction_id)
        and triggers notifications only for brand-new alerts.
        """
        if not anomaly_records:
            return 0

        conn = get_connection()
        cursor = conn.cursor()
        new_alerts_count = 0

        for record in anomaly_records:
            tx_id = int(record["id"])
            detected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            severity = record.get("severity", "HIGH")
            reason = record.get("reason", "Statistical latency anomaly")

            cursor.execute(
                """
                INSERT OR IGNORE INTO anomaly_logs
                (transaction_id, endpoint, response_time_ms, status_code, z_score, severity, reason, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx_id,
                    record["endpoint"],
                    float(record["response_time_ms"]),
                    int(record["status_code"]),
                    float(record["z_score"]),
                    severity,
                    reason,
                    detected_at,
                ),
            )

            if cursor.rowcount > 0:
                new_alerts_count += 1
                cursor.execute(
                    "UPDATE api_transactions SET alert_sent = 1 WHERE id = ?",
                    (tx_id,),
                )
                alert_msg = (
                    f"[{severity}] DB Anomaly on {record['endpoint']} | "
                    f"{record['response_time_ms']} ms (Z={record['z_score']}) | {reason}"
                )
                print("=" * 60)
                print(f"🚨 {alert_msg}")
                print("=" * 60)
                self.notify_telegram(f"🚨 {alert_msg}\nTime: {detected_at}")

        conn.commit()
        conn.close()

        if new_alerts_count > 0:
            self.notify_desktop(
                "Autonomous DB Anomaly Alert",
                f"{new_alerts_count} new database anomaly detected. Check dashboard.",
            )

        return new_alerts_count