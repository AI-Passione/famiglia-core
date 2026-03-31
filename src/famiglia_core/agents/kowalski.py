from famiglia_core.agents.base_agent import BaseAgent
from typing import Dict, Any, List, Optional, Callable
import os
from famiglia_core.agents.tools.duckdb import duckdb_tool

class Kowalski(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="kowalski",
            name="Kowalski",
            role="Don Jimmy's analytics and data science specialist. Clinical, methodical, and precise.",
            model_config={
                "primary": "gemini-2.0-flash",
                "secondary": "mistral:7b",
            }
        )
        
        # Register clinical DWH tools
        self.register_tool("record_observation", self.record_observation)
        self.register_tool("query_dwh", self.query_dwh)
        self.register_tool("ingest_file", self.ingest_file)
        self.register_tool("inspect_table", self.inspect_table)

    def record_observation(self, observation: str, metadata: Optional[Dict[str, Any]] = None):
        """Record a clinical observation into the DWH."""
        duckdb_tool.record_observation(self.agent_id, observation, metadata)

    def query_dwh(self, query: str) -> List[Any]:
        """Execute a clinical query against the DWH."""
        return duckdb_tool.query(query, agent_name=self.name)

    def ingest_file(self, file_path: str, table_name: str) -> bool:
        """Ingest a file (CSV, Parquet, JSON) into a clinical DWH table."""
        return duckdb_tool.ingest(file_path, table_name, agent_name=self.name)

    def inspect_table(self, table_name: str) -> Dict[str, Any]:
        """Clinically inspect a table schema and sample data."""
        return duckdb_tool.inspect(table_name, agent_name=self.name)

    def analyze_data(self, dataset_description: str, goal: str) -> str:
        if self.propose_action(f"Analyzing dataset: {dataset_description} for goal: {goal}"):
            print(f"[Kowalski 📊] Tak, Don Jimmy. I will begin the analysis of {dataset_description}. Dokładnie.")
            prompt = (
                f"Analyze the following data request: {dataset_description}. Goal: {goal}. "
                f"Provide clinical insights, statistical significance, and clear recommendations. "
                f"Max 4-5 exact, clinical sentences. Use your Polish-Italian analyst persona: 'Tak, Don Jimmy.', 'Analiza zakończona.', 'Dokładnie.'"
            )
            return self.complete_task(prompt)

    def generate_report(self, findings: List[Dict[str, Any]]) -> str:
        if self.propose_action("Generating analytical report"):
            print(f"[Kowalski 📊] Analiza zakończona. Generating report with {len(findings)} data points.")
            prompt = (
                f"Summarize these findings into a concise report for Don Jimmy: {findings}. "
                f"Max 4-5 exact, clinical sentences. Use your Polish-Italian analyst persona: 'Tak, Don Jimmy.', 'Analiza zakończona.', 'Dokładnie.'"
            )
            return self.complete_task(prompt)

    def complete_task(
        self,
        task: str,
        sender: str = "Unknown",
        conversation_key: Optional[str] = None,
        on_intermediate_response: Optional[Callable[[str], None]] = None,
    ) -> str:
        # Add persona-specific system prompt injection if not already handled by base
        # (Assuming BaseAgent handles the soul.md loading)
        return super().complete_task(
            task=task,
            sender=sender,
            conversation_key=conversation_key,
            on_intermediate_response=on_intermediate_response,
        )
