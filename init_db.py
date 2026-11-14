import sqlite3
from datetime import datetime

DB_PATH = "app_data.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Safely initializes or upgrades app_data.db without deleting existing records."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Preserve existing api_transactions table if it already exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL,
            response_time_ms REAL NOT NULL,
            status_code INTEGER NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Safely inspect existing columns and add new ones without data loss
    cursor.execute("PRAGMA table_info(api_transactions)")
    existing_columns = {row["name"] for row in cursor.fetchall()}

    if "timestamp" not in existing_columns:
        cursor.execute("ALTER TABLE api_transactions ADD COLUMN timestamp TEXT")
        cursor.execute(
            "UPDATE api_transactions SET timestamp = ? WHERE timestamp IS NULL",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
        )

    if "source_type" not in existing_columns:
        cursor.execute(
            "ALTER TABLE api_transactions ADD COLUMN source_type TEXT DEFAULT 'SIMULATED'"
        )

    if "z_score" not in existing_columns:
        cursor.execute(
            "ALTER TABLE api_transactions ADD COLUMN z_score REAL DEFAULT 0.0"
        )

    if "is_anomaly" not in existing_columns:
        cursor.execute(
            "ALTER TABLE api_transactions ADD COLUMN is_anomaly INTEGER DEFAULT 0"
        )

    if "alert_sent" not in existing_columns:
        cursor.execute(
            "ALTER TABLE api_transactions ADD COLUMN alert_sent INTEGER DEFAULT 0"
        )

    # 3. Persistent Anomaly History Table (survives restarts & browser refreshes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER UNIQUE,
            endpoint TEXT NOT NULL,
            response_time_ms REAL NOT NULL,
            status_code INTEGER NOT NULL,
            z_score REAL NOT NULL,
            severity TEXT NOT NULL,
            reason TEXT NOT NULL,
            detected_at TEXT NOT NULL
        )
    """)

    # 4. Agent Heartbeat Table (tracks if agent.py is alive)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            status TEXT NOT NULL,
            last_heartbeat TEXT NOT NULL,
            last_processed_id INTEGER DEFAULT 0
        )
    """)

    # 5. Reference table for genuine SQL workload queries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sample_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            amount REAL NOT NULL,
            region TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed sample_orders only if empty (gives real SQL queries something genuine to scan)
    cursor.execute("SELECT COUNT(*) as cnt FROM sample_orders")
    if cursor.fetchone()["cnt"] == 0:
        sample_rows = [
            (f"Customer_{i}", round(100 + (i % 50) * 12.5, 2), ["North", "South", "East", "West"][i % 4])
            for i in range(1, 501)
        ]
        cursor.executemany(
            "INSERT INTO sample_orders (customer_name, amount, region) VALUES (?, ?, ?)",
            sample_rows,
        )

    conn.commit()
    conn.close()
    print("[DB] Safe schema check & upgrade complete on 'app_data.db'. Existing records preserved.")


if __name__ == "__main__":
    init_database()