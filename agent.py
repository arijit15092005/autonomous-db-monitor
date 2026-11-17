import os
import time
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from init_db import get_connection, init_database, is_postgres
from detector import AnomalyDetector
from alerter import AlertDispatcher
from traffic_generator import execute_real_db_query

# Load local .env variables to force connection to Neon Cloud PostgreSQL
load_dotenv()

def run_autonomous_agent(once: bool = False):
    print("[Agent] Initializing database and starting Autonomous Monitoring Agent...")
    init_database()
    
    while True:
        try:
            conn = get_connection()
            postgres_mode = is_postgres()
            print(f"[Agent] Connected. Using Cloud PostgreSQL: {postgres_mode}")
            
            # Execute real telemetry check and log transaction
            res = execute_real_db_query(simulate_heavy_load=False)
            print(f"[Agent] Telemetry logged -> Endpoint: {res['endpoint']}, Latency: {res['response_time_ms']} ms")
            
            # Update agent heartbeat in database with precise UTC timestamp
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            
            # Use correct placeholder (%s for PostgreSQL, ? for SQLite)
            ph = "%s" if postgres_mode else "?"
            
            # Check if agent_status row exists, update or insert
            status_check = conn.execute("SELECT COUNT(*) FROM agent_status WHERE id = 1").fetchone()
            # Handle tuple or scalar return from different DB wrappers
            count_val = status_check[0] if status_check else 0
            
            if count_val > 0:
                query = f"UPDATE agent_status SET status = {ph}, last_heartbeat = {ph} WHERE id = 1"
                conn.execute(query, ("ONLINE", now_str))
            else:
                query = f"INSERT INTO agent_status (id, status, last_heartbeat) VALUES (1, {ph}, {ph})"
                conn.execute(query, ("ONLINE", now_str))
                
            conn.commit()
            conn.close()
            print(f"[Agent] Heartbeat successfully updated at {now_str} (UTC) -> Status: ONLINE")
            
            if once:
                break
                
            print("[Agent] Sleeping for 60 seconds before next check...")
            time.sleep(60)
            
        except Exception as e:
            print(f"[Agent Error]: {e}")
            if once:
                break
            time.sleep(15)

if __name__ == "__main__":
    once_flag = "--once" in sys.argv
    run_autonomous_agent(once=once_flag)