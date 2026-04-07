import os
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

def seed_intelligence():
    load_dotenv()
    
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "user": os.getenv("DB_USER", "passione_admin"),
        "password": os.getenv("DB_PASSWORD", "passione_password"),
        "dbname": os.getenv("DB_NAME", "passione_db")
    }
    
    items = [
        {
            "title": "Milan Market Penetration",
            "content": "Analysis of competitive nightlife entities in the Navigli district. Identified three high-value acquisition targets with low digital security footprints.",
            "summary": "High-value acquisition targets in Milan.",
            "status": "Active",
            "item_type": "dossier",
            "reference_id": "DOS-77-MIL",
            "metadata": {"department": "Rossini Research Dept."}
        },
        {
            "title": "The Roman Contingency",
            "content": "Historical audit of the 2022 expansion into Trastevere. Core findings highlight logistic bottlenecks and local jurisdictional friction.",
            "summary": "Historical audit of Trastevere expansion.",
            "status": "Archived",
            "item_type": "dossier",
            "reference_id": "DOS-22-ROM",
            "metadata": {"department": "Rossini Research Dept."}
        },
        {
            "title": "Vespa Surveillance Mesh (v2.1)",
            "content": "Technical specifications for the the distributed surveillance network using Vespa drones.",
            "summary": "Vespa surveillance mesh specs.",
            "status": "Approved",
            "item_type": "blueprint",
            "reference_id": "PRD-VESPA-V2",
            "metadata": {"icon": "architecture", "last_sync": "2h ago"}
        },
        {
            "title": "Automated Supply Chain Re-Routing",
            "content": "Logic for real-time re-routing of logistics in response to law enforcement activity.",
            "summary": "Dynamic logistics re-routing.",
            "status": "Drafted",
            "item_type": "blueprint",
            "reference_id": "PRD-SUPPLY-DYN",
            "metadata": {"icon": "design_services", "last_sync": "5h ago"}
        },
        {
            "title": "Identity Scrambler App Specs",
            "content": "Design and security protocols for the internal communication scrambling application.",
            "summary": "Internal secure comms app specs.",
            "status": "Approved",
            "item_type": "blueprint",
            "reference_id": "PRD-ID-SCRAMBLE",
            "metadata": {"icon": "description", "last_sync": "12m ago"}
        }
    ]
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        print("Seeding intelligence_items...")
        for item in items:
            cursor.execute(
                """
                INSERT INTO intelligence_items (title, content, summary, status, item_type, reference_id, metadata, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    item["title"],
                    item["content"],
                    item["summary"],
                    item["status"],
                    item["item_type"],
                    item["reference_id"],
                    psycopg2.extras.Json(item["metadata"]) if hasattr(psycopg2.extras, 'Json') else str(item["metadata"]).replace("'", '"'),
                    datetime.now(timezone.utc)
                )
            )
        
        conn.commit()
        print("Intelligence items seeded successfully.")
        
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error seeding intelligence items: {e}")

if __name__ == "__main__":
    seed_intelligence()
