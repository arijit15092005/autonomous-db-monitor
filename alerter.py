from plyer import notification

class AlertDispatcher:
    def notify_desktop(self, title: str, message: str):
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="DB Monitor Agent",
                timeout=5
            )
        except Exception as e:
            print(f"[Warning] Desktop notification failed: {e}")

    def log_incident(self, anomaly_data: list):
        print("\n" + "=" * 55)
        print("🚨 [ALERT] DATABASE ANOMALY DETECTED")
        print("=" * 55)
        for record in anomaly_data:
            print(f"Record ID: {record.get('id')} | "
                  f"Latency: {record.get('response_time_ms')}ms | "
                  f"Z-Score: {round(record.get('z_score', 0), 2)}")
        print("=" * 55 + "\n")