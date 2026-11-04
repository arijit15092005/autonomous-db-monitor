import sqlite3
import random
import time

DB_PATH = "app_data.db"

def simulate_traffic():
    print("[*] Simulating live incoming database traffic. Press Ctrl+C to stop...")
    while True:
        # 90% chance: normal latency (120ms - 180ms, HTTP 200)
        # 10% chance: anomalous spike (600ms - 1200ms, HTTP 500/504)
        is_spike = random.random() < 0.10

        if is_spike:
            latency = round(random.uniform(650.0, 1200.0), 2)
            status = random.choice([500, 502, 504])
            endpoint = "/checkout"
            print(f"[!] Generating anomalous spike: {latency}ms (Status: {status})")
        else:
            latency = round(random.gauss(150, 15), 2)
            status = 200
            endpoint = random.choice(["/home", "/search", "/items", "/checkout"])

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO api_transactions (endpoint, response_time_ms, status_code) VALUES (?, ?, ?)",
                (endpoint, latency, status)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Error] Failed to insert traffic record: {e}")

        # Push a new transaction every 1 to 2 seconds
        time.sleep(random.uniform(1.0, 2.0))

if __name__ == "__main__":
    simulate_traffic()