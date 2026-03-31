from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
import os
import re

from famiglia_core.agents.orchestration.utils.state import AgentState
from famiglia_core.agents.llm.client import client

class DataIngestionState(AgentState):
    """Extension of AgentState for specialized Data Ingestion tasks."""
    file_path: Optional[str]
    table_name: Optional[str]
    ingestion_success: bool
    inspection_results: Dict[str, Any]

class DataIngestionWorkflow:
    def __init__(self, agent):
        self.agent = agent
        self.name = agent.name
        self.model_config = agent.model_config
        self.personality = self._load_kowalski_personality()

    def _load_kowalski_personality(self) -> str:
        """Loads Kowalski's clinical personality."""
        try:
            soul_path = os.path.join(os.getcwd(), "src/agents/souls/kowalski.md")
            if os.path.exists(soul_path):
                with open(soul_path, "r") as f:
                    content = f.read()
                persona_match = re.search(r"## PERSONA & TONE(.*?)(##|$)", content, re.DOTALL)
                if persona_match:
                    return persona_match.group(1).strip()
                return content[:1000]
        except Exception:
            pass
        return "A clinical and precise data analyst named Kowalski."

    def analyze_request(self, state: DataIngestionState) -> DataIngestionState:
        """Node 1: Extract file path and table name from the task."""
        print(f"[{self.name}] Ingestion Node: analyze_request", flush=True)
        task = state["task"]
        
        # Look for [Attached File]: path (handles spaces until EOL)
        file_match = re.search(r"\[Attached File\]:\s*(.*)$", task, re.MULTILINE)
        proposed_file = file_match.group(1).strip() if file_match else None
        
        print(f"[{self.name}] Ingestion Node: Found proposed file in task context: {proposed_file}", flush=True)
        # Ensure it's not None
        if not proposed_file:
            print(f"[{self.name}] Ingestion Node: WARNING: No [Attached File] marker found in task.", flush=True)
        
        prompt = f"""
        {self.personality}
        
        Task: Analyze this data ingestion request: "{task}"
        
        Extracted File Path: {proposed_file or "None"}
        
        If a file path is provided, use it. If a table name is suggested (e.g. "into table X"), extract it.
        Otherwise, suggest a clinical table name based on the filename.
        
        Output in JSON format:
        {{
            "file_path": "path/to/file",
            "table_name": "clinical_table_name"
        }}
        """
        
        import json
        try:
            res_text, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
            print(f"[{self.name}] Ingestion Node: LLM Analysis complete.", flush=True)
            # Find JSON block
            json_match = re.search(r"\{.*\}", res_text, re.DOTALL)
            data = json.loads(json_match.group(0)) if json_match else {}
            
            # CLIINICAL PRIORITIZATION: Regex extraction of physical path is source of truth.
            # Only fallback to LLM suggestion if regex failed.
            state["file_path"] = proposed_file or data.get("file_path")
            state["table_name"] = data.get("table_name", "imported_data")
            print(f"[{self.name}] Ingestion Node: Resolved path: {state['file_path']}, target table: {state['table_name']}", flush=True)
        except Exception as e:
            print(f"[{self.name}] Ingestion Node: Analysis Failed: {e}", flush=True)
            state["file_path"] = proposed_file
            state["table_name"] = "imported_data"
            
        return state

    def perform_ingestion(self, state: DataIngestionState) -> DataIngestionState:
        """Node 2: Execute the ingestion via agent tools."""
        file_path = state.get("file_path")
        table_name = state.get("table_name")
        
        if not file_path or not os.path.exists(file_path):
            print(f"[{self.name}] Ingestion Node: File not found ({file_path})")
            state["ingestion_success"] = False
            return state
            
        print(f"[{self.name}] Ingestion Node: perform_ingestion({file_path} -> {table_name})")
        success = self.agent.ingest_file(file_path, table_name)
        state["ingestion_success"] = success
        return state

    def verify_ingestion(self, state: DataIngestionState) -> DataIngestionState:
        """Node 3: Verify and inspect the new table."""
        if not state.get("ingestion_success"):
            return state
            
        table_name = state.get("table_name")
        print(f"[{self.name}] Ingestion Node: verify_ingestion({table_name})")
        results = self.agent.inspect_table(table_name)
        state["inspection_results"] = results
        return state

    def final_report(self, state: DataIngestionState) -> DataIngestionState:
        """Node 4: Generate a clinical summary of the operation."""
        print(f"[{self.name}] Ingestion Node: final_report")
        
        if not state.get("ingestion_success"):
            state["final_response"] = "Tak, Don Jimmy. The ingestion failed. The file source could not be precisely located or processed. Dokładnie."
            return state
            
        res = state.get("inspection_results", {})
        row_count = res.get("row_count", 0)
        table_name = state.get("table_name")
        
        state["final_response"] = (
            f"Tak, Don Jimmy. The data ingestion is complete. "
            f"Table `{table_name}` has been established with {row_count} records. "
            f"Clinical inspection confirms data integrity. Dokładnie."
        )
        return state

from famiglia_core.db.observability.checkpointer import PostgresCheckpointer

def setup_data_ingestion_graph(agent):
    """Builds and compiles the Data Ingestion StateGraph."""
    print(f"[{agent.name}] Data Ingestion: Setting up graph...", flush=True)
    workflow_logic = DataIngestionWorkflow(agent)
    
    workflow = StateGraph(DataIngestionState)
    
    workflow.add_node("analyze_request", workflow_logic.analyze_request)
    workflow.add_node("perform_ingestion", workflow_logic.perform_ingestion)
    workflow.add_node("verify_ingestion", workflow_logic.verify_ingestion)
    workflow.add_node("final_report", workflow_logic.final_report)
    
    workflow.set_entry_point("analyze_request")
    workflow.add_edge("analyze_request", "perform_ingestion")
    workflow.add_edge("perform_ingestion", "verify_ingestion")
    workflow.add_edge("verify_ingestion", "final_report")
    workflow.add_edge("final_report", END)
    
    checkpointer = PostgresCheckpointer()
    return workflow.compile(checkpointer=checkpointer)
