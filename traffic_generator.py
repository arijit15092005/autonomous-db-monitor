import time
import random
from datetime import datetime
from init_db import get_connection, init_database

REAL_WORKLOAD_QUERIES = [
    ("SQL_SELECT_RECENT_ORDERS", "SELECT * FROM sample_orders ORDER BY order_id DESC LIMIT 25"),
    ("SQL_AGGREGATE_BY_REGION", "SELECT region, COUNT(*), AVG(amount) FROM sample_orders GROUP BY region"),
    ("SQL_FILTER_HIGH_VALUE", "SELECT customer_name, amount FROM sample_orders WHERE amount > 500"),
    ("SQL_TRANSACTION_COUNT", "SELECT COUNT(*) FROM api_transactions"),
]


def execute_real_db_query(simulate_heavy_load: bool = False):
    conn = get_connection()
    cursor = conn.cursor()

    if simulate_heavy_load:
        operation_name = "SQL_HEAVY_CROSS_JOIN_SCAN"
        sql = """
            SELECT a.region, COUNT(*)
            FROM sample_orders a
            CROSS JOIN sample_orders b
            WHERE a.amount > b.amount
            GROUP BY a.region
        """
    else:
        operation_name, sql = random.choice(REAL_WORKLOAD_QUERIES)

    status_code = 200
    start_time = time.perf_counter()
    try:
        cursor.execute(sql)
        _ = cursor.fetchall()
    except Exception as e:
        status_code = 500
        print(f"[DB Query Error] {operation_name}: {e}")
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT INTO api_transactions
        (endpoint, response_time_ms, status_code, timestamp, source_type)
        VALUES (?, ?, ?, ?, ?)
        """,
        (operation_name, elapsed_ms, status_code, now_str, "REAL_DB"),
    )
    conn.commit()
    conn.close()

    return {
        "endpoint": operation_name,
        "response_time_ms": elapsed_ms,
        "status_code": status_code,
        "timestamp": now_str,
        "source_type": "REAL_DB",
    }


def inject_simulated_spike():
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    spike_ms = round(random.uniform(450.0, 750.0), 2)
    cursor.execute(
        """
        INSERT INTO api_transactions
        (endpoint, response_time_ms, status_code, timestamp, source_type)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("DEMO_SIMULATED_SPIKE", spike_ms, 504, now_str, "SIMULATED"),
    )
    conn.commit()
    conn.close()
    return spike_ms


if __name__ == "__main__":
    init_database()
    for _ in range(5):
        result = execute_real_db_query(simulate_heavy_load=False)
        print(f"Executed {result['endpoint']} -> {result['response_time_ms']} ms (Status {result['status_code']})")
        time.sleep(0.5)