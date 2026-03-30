import os
import json
import duckdb
from typing import Dict, Any, List, Optional

class DuckDBTool:
    """
    Centralized tool for interacting with the Famiglia Local Data Warehouse (DuckDB).
    Ensures persistent clinical data management across all agents.
    """

    def __init__(self):
        self.dwh_path = os.getenv("DUCKDB_DWH_PATH", "/app/data/duckdb_dwh.db")
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.dwh_path), exist_ok=True)
        self._initialize_schema()

    def _initialize_schema(self):
        """Initialize core clinical schemas and tables."""
        try:
            with duckdb.connect(self.dwh_path) as con:
                # Create clinical layers
                print(f"[DuckDBTool 📊] Initializing clinical schemas...")
                con.execute("CREATE SCHEMA IF NOT EXISTS ods")
                con.execute("CREATE SCHEMA IF NOT EXISTS staging")
                con.execute("CREATE SCHEMA IF NOT EXISTS intermediate")
                con.execute("CREATE SCHEMA IF NOT EXISTS mart")
                print(f"[DuckDBTool 📊] ODS, Staging, Intermediate, Mart schemas guaranteed.")
                
                con.execute("""
                    CREATE TABLE IF NOT EXISTS mart.observations (
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        agent_id TEXT,
                        observation TEXT,
                        metadata JSON
                    )
                """)
                print(f"[DuckDBTool 📊] Multi-layered DWH initialized at {self.dwh_path}. Layers: ODS, Staging, Intermediate, Mart.")
        except Exception as e:
            print(f"[DuckDBTool 📊] WARNING: Schema initialization failed: {e}")

    def query(self, sql: str, agent_name: str = "Unknown") -> List[Any]:
        """Execute a SQL query and return results. Defaults to mart schema search path."""
        try:
            with duckdb.connect(self.dwh_path) as con:
                print(f"[{agent_name} 📊] Executing SQL: {sql[:100]}...")
                con.execute("SET search_path='mart,staging,intermediate,ods'")
                result = con.execute(sql).fetchall()
                con.execute("CHECKPOINT")
                con.close()
                print(f"[{agent_name} 📊] Query complete. Retrieved {len(result)} records.", flush=True)
                return result
        except Exception as e:
            print(f"[{agent_name} 📊] WARNING: Query failed: {e}")
            return []

    def ingest(self, file_path: str, table_name: str, agent_name: str = "Unknown") -> bool:
        """Ingest a file into the ODS layer with metadata injection."""
        try:
            if not os.path.exists(file_path):
                return False

            if file_path.endswith('.parquet'):
                read_func = f"read_parquet('{file_path}')"
            elif file_path.endswith('.json'):
                read_func = f"read_json_auto('{file_path}')"
            else:
                read_func = f"read_csv_auto('{file_path}', sample_size=-1)"

            # Land in ODS with UTC ingestion timestamp
            full_table_name = f"ods.{table_name}"
            print(f"[{agent_name} 📊] Attempting ingestion: {file_path} -> {full_table_name}")
            
            with duckdb.connect(self.dwh_path) as con:
                table_exists = con.execute(f"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'ods' AND table_name = '{table_name}'").fetchone()[0] > 0
                
                if table_exists:
                    print(f"[{agent_name} 📊] Table {full_table_name} exists. Attempting append with clinical schema check.", flush=True)
                    try:
                        con.execute(f"INSERT INTO {full_table_name} SELECT *, current_timestamp AS ingested_at FROM {read_func}")
                    except Exception as e:
                        if "Binder Error" in str(e) or "Column count mismatch" in str(e):
                            print(f"[{agent_name} 📊] WARNING: Schema mismatch detected. Performing clinical reset on {full_table_name}...", flush=True)
                            con.execute(f"DROP TABLE {full_table_name}")
                            con.execute(f"CREATE TABLE {full_table_name} AS SELECT *, current_timestamp AS ingested_at FROM {read_func}")
                        else:
                            raise e
                else:
                    print(f"[{agent_name} 📊] Creating new table {full_table_name}.", flush=True)
                    con.execute(f"CREATE TABLE {full_table_name} AS SELECT *, current_timestamp AS ingested_at FROM {read_func}")
                
                # Verify row count after ingestion
                rc = con.execute(f"SELECT count(*) FROM {full_table_name}").fetchone()[0]
                con.execute("CHECKPOINT")
                con.close()
                print(f"[{agent_name} 📊] Ingestion successful. {full_table_name} now has {rc} rows.", flush=True)
                return True
        except Exception as e:
            print(f"[{agent_name} 📊] WARNING: Ingestion failed: {e}")
            return False

    def inspect(self, table_name: str, agent_name: str = "Unknown") -> Dict[str, Any]:
        """Inspect table, searching across DWH layers."""
        try:
            with duckdb.connect(self.dwh_path) as con:
                print(f"[{agent_name} 📊] Inspecting table: {table_name}")
                con.execute("SET search_path='mart,staging,intermediate,ods,main'")
                schema = con.execute(f"DESCRIBE {table_name}").fetchall()
                sample = con.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
                row_count = con.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
                con.execute("CHECKPOINT")
                con.close()
                print(f"[{agent_name} 📊] Inspection complete: {row_count} total rows found.", flush=True)
                return {
                    "schema": schema,
                    "sample": sample,
                    "row_count": row_count
                }
        except Exception as e:
            print(f"[{agent_name} 📊] WARNING: Inspection failed for {table_name}: {e}")
            return {}

    def record_observation(self, agent_id: str, observation: str, metadata: Optional[Dict[str, Any]] = None):
        """Persist a clinical observation into the mart layer."""
        try:
            with duckdb.connect(self.dwh_path) as con:
                con.execute(
                    "INSERT INTO mart.observations (agent_id, observation, metadata) VALUES (?, ?, ?)",
                    (agent_id, observation, json.dumps(metadata) if metadata else None)
                )
                print(f"[{agent_id} 📊] Clinical observation persisted in mart.")
        except Exception as e:
            print(f"[{agent_id} 📊] WARNING: Failed to persist observation: {e}")

# Singleton
duckdb_tool = DuckDBTool()
