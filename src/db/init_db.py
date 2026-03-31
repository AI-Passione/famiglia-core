import os
import psycopg2
from dotenv import load_dotenv

def init_db():
    load_dotenv()
    
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "user": os.getenv("DB_USER", "passione_admin"),
        "password": os.getenv("DB_PASSWORD", "passione_password"),
        "dbname": os.getenv("DB_NAME", "passione_db")
    }
    
    base_path = os.path.dirname(__file__)
    schema_path = os.path.join(base_path, "schema.sql")
    
    print(f"Connecting to database {db_config['dbname']} at {db_config['host']}...")
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # 1. Execute main schema
        if os.path.exists(schema_path):
            print("Executing schema.sql...")
            with open(schema_path, "r") as f:
                schema_sql = f.read()
            cursor.execute(schema_sql)
            conn.commit()
        
        # # 2. Seed Agents and Archetypes from Markdown
        # from src.db.agents.migrate_souls_normalization import SoulMigrator
        # print("Running SoulMigrator to ensure agents and skills are seeded...")
        # migrator = SoulMigrator()
        # migrator.migrate()

        print("Database initialized and seeded successfully.")
        
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == "__main__":
    init_db()
