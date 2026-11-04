import sqlite3
import random

def init_database():
    conn = sqlite3.connect("app_data.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT NOT NULL,
        response_time_ms REAL NOT NULL,
        status_code INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Populate 100 baseline records (normal latency ~120ms to 180ms)
    print("Generating baseline traffic...")
    for _ in range(100):
        latency = round(random.gauss(150, 15), 2)
        cursor.execute(
            "INSERT INTO api_transactions (endpoint, response_time_ms, status_code) VALUES (?, ?, ?)",
            ("/checkout", latency, 200)
        )

    conn.commit()
    conn.close()
    print("Database seeded: 'app_data.db' ready.")

if __name__ == "__main__":
    init_database()