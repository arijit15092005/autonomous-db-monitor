import os
import sqlite3
from datetime import datetime

try:
    import streamlit as st
except Exception:
    st = None

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None

DB_PATH = "app_data.db"


def get_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url and st is not None:
        try:
            if "DATABASE_URL" in st.secrets:
                raw_url = str(st.secrets["DATABASE_URL"]).strip()
        except Exception:
            pass
    if raw_url:
        raw_url = raw_url.replace("psql ", "").strip("'\"")
        raw_url = raw_url.replace("&channel_binding=require", "").replace("?channel_binding=require", "")
    return raw_url


def is_postgres() -> bool:
    return get_database_url().startswith("postgres")


class UnifiedCursor:
    def __init__(self, cursor, pg_mode: bool):
        self._cursor = cursor
        self._pg_mode = pg_mode

    def _adapt(self, sql: str) -> str:
        return sql.replace("?", "%s") if self._pg_mode else sql

    def execute(self, sql: str, params=()):
        return self._cursor.execute(self._adapt(sql), params)

    def executemany(self, sql: str, seq_of_params):
        return self._cursor.executemany(self._adapt(sql), seq_of_params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount


class UnifiedConnection:
    def __init__(self, conn, pg_mode: bool):
        self._conn = conn
        self.pg_mode = pg_mode

    def cursor(self):
        if self.pg_mode:
            return UnifiedCursor(self._conn.cursor(cursor_factory=RealDictCursor), True)
        return UnifiedCursor(self._conn.cursor(), False)

    def execute(self, sql: str, params=()):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_of_params):
        cur = self.cursor()
        cur.executemany(sql, seq_of_params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    @property
    def raw_conn(self):
        return self._conn


def get_connection() -> UnifiedConnection:
    db_url = get_database_url()
    if db_url.startswith("postgres"):
        if psycopg2 is None:
            raise ImportError("psycopg2-binary is required for PostgreSQL connections.")
        conn = psycopg2.connect(db_url)
        return UnifiedConnection(conn, pg_mode=True)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return UnifiedConnection(conn, pg_mode=False)


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    if conn.pg_mode:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_transactions (
                id SERIAL PRIMARY KEY,
                endpoint TEXT NOT NULL,
                response_time_ms DOUBLE PRECISION NOT NULL,
                status_code INTEGER NOT NULL,
                timestamp TEXT,
                source_type TEXT DEFAULT 'REAL_DB',
                z_score DOUBLE PRECISION DEFAULT 0.0,
                is_anomaly INTEGER DEFAULT 0,
                alert_sent INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_logs (
                id SERIAL PRIMARY KEY,
                transaction_id INTEGER UNIQUE,
                endpoint TEXT NOT NULL,
                response_time_ms DOUBLE PRECISION NOT NULL,
                status_code INTEGER NOT NULL,
                z_score DOUBLE PRECISION NOT NULL,
                severity TEXT NOT NULL,
                reason TEXT NOT NULL,
                detected_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_status (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL,
                last_processed_id INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sample_orders (
                order_id SERIAL PRIMARY KEY,
                customer_name TEXT NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                region TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                response_time_ms REAL NOT NULL,
                status_code INTEGER NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("PRAGMA table_info(api_transactions)")
        existing_columns = {row["name"] for row in cursor.fetchall()}

        if "timestamp" not in existing_columns:
            cursor.execute("ALTER TABLE api_transactions ADD COLUMN timestamp TEXT")
            cursor.execute(
                "UPDATE api_transactions SET timestamp = ? WHERE timestamp IS NULL",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
            )
        if "source_type" not in existing_columns:
            cursor.execute("ALTER TABLE api_transactions ADD COLUMN source_type TEXT DEFAULT 'SIMULATED'")
        if "z_score" not in existing_columns:
            cursor.execute("ALTER TABLE api_transactions ADD COLUMN z_score REAL DEFAULT 0.0")
        if "is_anomaly" not in existing_columns:
            cursor.execute("ALTER TABLE api_transactions ADD COLUMN is_anomaly INTEGER DEFAULT 0")
        if "alert_sent" not in existing_columns:
            cursor.execute("ALTER TABLE api_transactions ADD COLUMN alert_sent INTEGER DEFAULT 0")

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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                status TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL,
                last_processed_id INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sample_orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                amount REAL NOT NULL,
                region TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

    cursor.execute("SELECT COUNT(*) AS cnt FROM sample_orders")
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
    backend_label = "Cloud PostgreSQL" if is_postgres() else "Local SQLite (app_data.db)"
    print(f"[DB] Schema verified on {backend_label}.")


if __name__ == "__main__":
    init_database()