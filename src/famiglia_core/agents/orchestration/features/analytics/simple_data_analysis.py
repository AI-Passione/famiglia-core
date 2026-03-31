from typing import Any, Dict, List, Optional, TypedDict, Literal
from langgraph.graph import StateGraph, END
import os
import re
import json

from famiglia_core.agents.orchestration.utils.state import AgentState
from famiglia_core.agents.llm.client import client
from famiglia_core.agents.tools.notion import notion_client
# from famiglia_core.agents.orchestration.features.data_ingestion import setup_data_ingestion_graph

class DataAnalysisState(AgentState):
    """Extension of AgentState for specialized Data Analysis tasks."""
    ingestion_needed: bool
    report_type: Literal["adhoc", "in_depth"]
    analysis_results: Optional[str]
    notion_url: Optional[str]
    notion_success: bool
    ingestion_status: Optional[str]
    candidate_tables: List[str]
    discovery_metadata: Optional[str]
    disclaimer: Optional[str]
    tables_to_use: List[str]

class DataAnalysisWorkflow:
    def __init__(self, agent):
        self.agent = agent
        self.name = agent.name
        self.model_config = agent.model_config
        self.personality = self._load_kowalski_personality()
        self.template_path = os.path.join(
            os.getcwd(), 
            "src/agents/orchestration/features/templates/data_analysis_template.md"
        )

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

    def _clean_kowalski_talk(self, text: str) -> str:
        """Strips Slack mentions, common LLM preambles, and greetings."""
        if not text: return ""
        # 1. Strip Slack mentions (@Username)
        text = re.sub(r"@[\w\.-]+", "", text)
        # 2. Strip common intro phrases (Multi-line)
        intro_patterns = [
            r"^(?:Tak, Don Jimmy|Okay|Sure|Here is|Based on|Analysis).*?[!:\.]\s*(\n|$)",
            r"^.*?(?:reveal[s]?|show[s]?|suggest[s]?|provide[s]?|include[s]?|following).*?[:\.!]\s*(\n|$)"
        ]
        for pattern in intro_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)
        
        # 3. Strip Kowalski sign-off markers
        text = text.replace("Analiza zakończona.", "").replace("Dokładnie.", "").strip()
        # 4. Remove leading lines that are JUST a lone star, dash or whitespace artifact
        text = re.sub(r"^\s*[\*\-\s:]+\n", "", text, flags=re.MULTILINE).strip()
        # 5. Strip any leading dashes or colons left over from introductory cleanup
        # but preserve bullets (checks if there's text after the symbol)
        text = re.sub(r"^[-\s:]+(?![^\s])", "", text).strip()
        return text

    def detect_intent(self, state: DataAnalysisState) -> DataAnalysisState:
        """Node 1: Determine the type of analysis."""
        print(f"[{self.name}] Analysis Node: detect_intent", flush=True)
        task = state["task"]
        
        prompt = f"""
        {self.personality}
        
        Task: Analyze this data analysis request: "{task}"
        
        Determine:
        Is this an "adhoc" analysis (quick insights, simple summary) or an "in_depth" analysis (deep dive, requires formal report)?
        
        Output in JSON format:
        {{
            "report_type": "adhoc" or "in_depth"
        }}
        """
        
        try:
            res_text, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
            json_match = re.search(r"\{.*\}", res_text, re.DOTALL)
            data = json.loads(json_match.group(0)) if json_match else {}
            
            state["report_type"] = data.get("report_type", "adhoc")
            print(f"[{self.name}] Analysis Node: Report type: {state['report_type']}", flush=True)
        except Exception as e:
            print(f"[{self.name}] Analysis Node: Intent Detection Failed: {e}", flush=True)
            state["report_type"] = "adhoc"
            
        return state

    def run_discovery(self, state: DataAnalysisState) -> DataAnalysisState:
        """Node 2: Identify candidate tables from schema metadata."""
        print(f"[{self.name}] Analysis Node: run_discovery", flush=True)
        task = state["task"]
        
        # Step A: Get schema information
        try:
            # Get tables and columns
            schema_info = self.agent.query_dwh("SELECT table_schema, table_name, column_name, data_type FROM information_schema.columns WHERE table_name NOT ILIKE '%cache%'")
            schema_str = str(schema_info)
        except Exception as e:
            print(f"[{self.name}] Analysis Node: Discovery Query Failed: {e}", flush=True)
            schema_str = "Unknown"

        prompt = f"""
        {self.personality}
        
        Task: {task}
        DuckDB Schema: {schema_str}
        
        Instruction: Identify any tables in the schema that MIGHT be relevant to the analytical request.
        A table is relevant if its name or columns suggest it contains the required data.
        
        Output in JSON format with a list of candidate tables:
        {{
            "candidate_tables": ["schema.table1", "schema.table2"],
            "reasoning": "Quick explanation why these were chosen"
        }}
        If no tables look even remotely relevant, return an empty list.
        """
        
        try:
            res_text, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
            json_match = re.search(r"\{.*\}", res_text, re.DOTALL)
            data = json.loads(json_match.group(0)) if json_match else {}
            
            state["candidate_tables"] = data.get("candidate_tables", [])
            state["ingestion_needed"] = len(state["candidate_tables"]) == 0
            print(f"[{self.name}] Analysis Node: Candidates identified: {state['candidate_tables']} (Needed: {state['ingestion_needed']})", flush=True)
        except Exception as e:
            print(f"[{self.name}] Analysis Node: Discovery LLM Failed: {e}", flush=True)
            state["candidate_tables"] = []
            state["ingestion_needed"] = True

        return state

    def verify_data(self, state: DataAnalysisState) -> DataAnalysisState:
        """Node 2.5: Run clinical verification queries on candidate tables."""
        print(f"[{self.name}] Analysis Node: verify_data", flush=True)
        candidates = state.get("candidate_tables", [])
        if not candidates:
            state["ingestion_needed"] = True
            return state

        discovery_results = []
        for table in candidates:
            print(f"[{self.name}] Analysis Node: Verifying {table}...", flush=True)
            table_meta = {"table": table}
            
            try:
                # 1. Clinical Profiling (Consolidated: includes type, min, max, count, nulls)
                summary = self.agent.query_dwh(f"SUMMARIZE {table}")
                table_meta["summary"] = str(summary)
                
                # 2. Sample
                sample = self.agent.query_dwh(f"SELECT * FROM {table} LIMIT 5")
                table_meta["sample_data"] = str(sample)
                
            except Exception as e:
                print(f"[{self.name}] Analysis Node: Verification of {table} failed: {e}", flush=True)
                table_meta["error"] = str(e)
            
            discovery_results.append(table_meta)

        state["discovery_metadata"] = json.dumps(discovery_results, indent=2)
        
        # Final Decision LLM
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        prompt = f"""
        {self.personality}
        
        Current Time: {current_time}
        Task: {state['task']}
        Candidate Tables Verification:
        {state['discovery_metadata']}
        
        Instruction: Based on the clinical evidence above, determine if the existing data in the DWH is sufficient to answer the user's request.
        
        Clinical Guidelines:
        1. **Slow Changing Dimensions (SCD)**: For tables containing static or slow-changing metadata (e.g., Countries, Continents, ISO codes, Regions), data staleness is acceptable. Do NOT request ingestion if such a table exists and contains relevant rows, even if the ingestion date is old.
        2. **Transactional/Dynamic Data**: For tables containing fast-moving data (e.g., Prices, Sales, Weather), freshness is critical.
        3. **Data Sufficiency**: Ensure the columns and a sample of the data actually match the task's requirements.
        
        Output in JSON format:
        {{
            "ingestion_needed": true/false,
            "reasoning": "Clinical justification. Mention why staleness is or isn't an issue for this specific dataset.",
            "disclaimer": "Optional clinical disclaimer if using stale SCD data.",
            "tables_to_use": ["Exact", "Table", "Names", "from", "the", "Candidates", "list", "to", "be", "used", "in", "analysis"]
        }}
        """
        
        try:
            res_text, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
            json_match = re.search(r"\{.*\}", res_text, re.DOTALL)
            data = json.loads(json_match.group(0)) if json_match else {}
            state["ingestion_needed"] = data.get("ingestion_needed", True)
            state["disclaimer"] = data.get("disclaimer")
            state["tables_to_use"] = data.get("tables_to_use", [])
            print(f"[{self.name}] Analysis Node: Verification decision - Ingestion needed: {state['ingestion_needed']} ({data.get('reasoning')})", flush=True)
            if state["disclaimer"]:
                print(f"[{self.name}] Analysis Node: Disclaimer captured: {state['disclaimer']}", flush=True)
            if state["tables_to_use"]:
                print(f"[{self.name}] Analysis Node: Persisting verified tables: {state['tables_to_use']}", flush=True)
        except Exception as e:
            print(f"[{self.name}] Analysis Node: Verification LLM Failed: {e}", flush=True)
            state["ingestion_needed"] = True

        return state

    def inform_missing_data(self, state: DataAnalysisState) -> DataAnalysisState:
        """Node 3: Inform the user that data is missing and requires ingestion planning."""
        print(f"[{self.name}] Analysis Node: inform_missing_data", flush=True)
        task = state["task"]
        
        prompt = f"""
        {self.personality}
        
        Task: {task}
        
        Status: You have discovered that the necessary data tables or files for this analysis are not present in the clinical DuckDB DWH.
        
        Instruction: Inform the user (Don Jimmy) that the analysis cannot proceed without data ingestion. 
        Explain that they should plan for a data ingestion feature or provide the data via the appropriate ingestion workflow.
        
        Be clinical, precise, and professional. Use "Analiza wstrzymana." (Analysis paused).
        """
        
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        state["final_response"] = res
        return state

    def query_duckdb(self, state: DataAnalysisState) -> DataAnalysisState:
        """Node 4: Execute clinical queries against the DWH."""
        print(f"[{self.name}] Analysis Node: query_duckdb", flush=True)
        task = state["task"]
        
        tables_to_use = state.get("tables_to_use", []) or state.get("candidate_tables", [])
        print(f"[{self.name}] Analysis Node: Verified tables: {tables_to_use}", flush=True)
        
        # Profiling: Aggregate "cell-count" check across ALL tables to use
        total_cells = 0
        table_stats = []
        for table in tables_to_use:
            try:
                # 1. Row count
                count_res = self.agent.query_dwh(f"SELECT count(*) FROM {table}")
                rows = count_res[0][0] if count_res else 0
                
                # 2. Column count and Names (via DESCRIBE)
                describe_res = self.agent.query_dwh(f"DESCRIBE {table}")
                cols = len(describe_res) if describe_res else 0
                col_names = [row[0] for row in describe_res] if describe_res else []
                
                total_cells += (rows * cols)
                table_stats.append({"table": table, "rows": rows, "cols": cols, "col_names": col_names})
            except Exception as e:
                print(f"[{self.name}] Analysis Node: Size check failed for {table}: {e}", flush=True)

        AGGREGATE_CELL_LIMIT = 50000 # roughly the upper limit of 128k tokens
        profiling_data = []
        use_full_context = total_cells < AGGREGATE_CELL_LIMIT
        print(f"[{self.name}] Analysis Node: Aggregate context check - Total cells: {total_cells}. Strategy: {'FULL_DATA' if use_full_context else 'SUMMARIZE'}", flush=True)

        for stats in table_stats:
            table = stats["table"]
            rows = stats["rows"]
            cols = stats["cols"]
            try:
                if use_full_context:
                    full_data = self.agent.query_dwh(f"SELECT * FROM {table}")
                    profiling_data.append(f"Table: `{table}` (Full Dataset, {rows} rows x {cols} cols)\nColumns: {stats['col_names']}\nData: {full_data}")
                else:
                    summary = self.agent.query_dwh(f"SUMMARIZE {table}")
                    sample = self.agent.query_dwh(f"SELECT * FROM {table} LIMIT 5")
                    profiling_data.append(f"Table: `{table}` (Summarized, {rows} rows x {cols} cols)\nColumns: {stats['col_names']}\nSummary Profile: {summary}\nSample Data (Top 5): {sample}")
            except Exception as e:
                print(f"[{self.name}] Analysis Node: Profiling failed for {table}: {e}", flush=True)

        profiling_text = "\n\n".join(profiling_data)

        # Generate and run query
        query_prompt = f"""
        {self.personality}
        
        Task: {task}
        Context: The following verified tables are available for analysis: {tables_to_use}
        
        Table Dimensional Profiling (Context):
        {profiling_text}
        
        Generate a single DuckDB SQL query to extract the necessary insights for this analysis.
        
        CRITICAL: 
        - Output ONLY the raw SQL query. 
        - DO NOT include variable assignments (e.g., `sql_query = ...`).
        - DO NOT include any preamble, preamble, or markdown outside the code block.
        - Ensure the query is valid DuckDB SQL.
        """
        query_text, _ = client.complete(query_prompt, self.agent.get_model_config(state), agent_name=self.name)
        
        # Robust SQL extraction: prefer content inside ```sql or ``` blocks
        sql_match = re.search(r"```sql\s*(.*?)\s*```", query_text, re.DOTALL | re.IGNORECASE)
        if not sql_match:
            sql_match = re.search(r"```\s*(.*?)\s*```", query_text, re.DOTALL)
            
        sql = sql_match.group(1).strip() if sql_match else query_text.strip()
        
        # Clean up common LLM prefixes if they leaked through (including variable assignments like 'shawl sql_query =')
        sql = re.sub(r"^(duckdb|sql|shawl|query|sql_query)\s*=\s*['\"]*|['\"]*$", "", sql, flags=re.IGNORECASE).strip()
        
        # Final fallback: If it still looks like it has preamble, find the first SQL keyword
        if not any(sql.upper().startswith(kw) for kw in ["SELECT", "WITH", "DESCRIBE", "SUMMARIZE"]):
            sql_logic_match = re.search(r"(SELECT|WITH|DESCRIBE|SUMMARIZE)\s+.*", sql, re.DOTALL | re.IGNORECASE)
            if sql_logic_match:
                sql = sql_logic_match.group(0).strip()
                # Remove trailing quotes if they leaked from a string assignment
                sql = re.sub(r"['\"]+$", "", sql).strip()
        
        try:
            results = self.agent.query_dwh(sql)
            state["analysis_results"] = str(results)
            print(f"[{self.name}] Analysis Node: Query executed successfully. Results length: {len(state['analysis_results'])}", flush=True)
        except Exception as e:
            print(f"[{self.name}] Analysis Node: Query Failed: {e}", flush=True)
            state["analysis_results"] = f"Error executing query: {e}"
            
        return state

    def generate_report(self, state: DataAnalysisState) -> DataAnalysisState:
        """Node 5: Format the results into the prescribed format."""
        print(f"[{self.name}] Analysis Node: generate_report", flush=True)
        report_type = state.get("report_type", "adhoc")
        results = state.get("analysis_results", "No data found.")
        task = state["task"]
        
        if report_type == "in_depth":
            # Load template
            template = ""
            if os.path.exists(self.template_path):
                with open(self.template_path, "r") as f:
                    template = f.read()
            
            prompt = f"""
            {self.personality}
            
            Task: {task}
            Data Results: {results}
            
            Instruction: Generate an in-depth clinical analysis report.
            
            Template to follow strictly:
            {template}
            
            Analytical Hierarchy (CRITICAL):
            1. **Actionable Insights**: High-level, direct clinical findings and evidence.
            2. **Interesting-to-know Insights**: Secondary or contextual observations.
            3. **Numerical Snapshot**: Concrete descriptive statistics (Total records, distinct counts). You MUST provide these counts here.
            4. **Analytical Gaps**: Mention missing data or enrichment needs ONLY AFTER giving the insights and numbers.
            
            CRITICAL FORMATTING RULES: 
            - **NO CODE BLOCKS**: DO NOT wrap the entire report in ``` blocks. Slack must render Markdown directly.
            - **ZERO PREAMBLE**: DO NOT output words like "markdown", "weltanschauung", or any meta-text.
            - **NO GREETINGS**: DO NOT output "@Mention" or "Don Jimmy".
            - Slack uses `*` for BOLD. Use `*Executive Summary*` as the header.
            - Executive Summary MUST have 8-10 bulletpoints (use `• ` for bullets) with stats.
            - Use backticks (`) ONLY for specific records, values, or table names.
            
            Persona & Slack Implementation:
            - Use "Dokładnie." and "Analiza zakończona." as the professional closing text.
            - CRITICAL: These phrases and the "Executive Summary" header must NEVER be bullet points.
            - CRITICAL: Ensure double line breaks between headers and lists for proper Slack rendering.
            
            Output ONLY the raw Slack-formatted Markdown text. No wrappers.
            """
        else:
            prompt = f"""
            {self.personality}
            
            Task: {task}
            Data Results: {results}
            
            Instruction: Provide a quick ad-hoc analysis.
            Output an *Executive Summary* (Bolded header using `*`, NEVER a bullet point, use `• ` for bulletpoints below it).
            
            Analytical Hierarchy (CRITICAL):
            1. **Actionable Insights**: High-level, direct clinical findings and evidence.
            2. **Interesting-to-know**: Secondary or contextual observations.
            3. **Numerical Snapshot**: Concrete descriptive statistics (e.g., "Table: `X` contains `N` records"). You MUST provide these counts here.
            4. **Analytical Gaps**: Mention missing data ONLY after the insights and numbers.
            
            CRITICAL FORMATTING RULES:
            - **NO CODE BLOCKS**: DO NOT wrap the entire report in ``` blocks. Slack must render Markdown directly.
            - **ZERO PREAMBLE**: DO NOT output words like "markdown", "weltanschauung", or any meta-text.
            - **NO GREETINGS**: DO NOT output "@Mention" or "Don Jimmy".
            - Use backticks (`) ONLY for specific records, values, or table names.
            
            Persona & Slack Implementation:
            - Use "Dokładnie." as a clinical transition or part of a paragraph. NEVER make it a standalone bullet point.
            - Use "Analiza zakończona." as the professional closing.
            - CRITICAL: Ensure a double line break before and after the *Executive Summary* header.
            
            Output ONLY the raw Slack-formatted Markdown text. No wrappers.
            """
            
        res, used_model = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        state["used_model"] = used_model
        
        # Clean response and isolate Executive Summary content
        res_all = res.strip()
        summary_parts = re.split(r"\*?\s*(?:\d\.\s*)?Executive Summary\*?[:\s]*", res_all, flags=re.IGNORECASE)
        summary_uncleaned = summary_parts[-1].strip()
        res_clean = self._clean_kowalski_talk(summary_uncleaned)
        
        # Reconstruct final response with proper header separation
        final_res = f"\n\n*Executive Summary*\n\n{res_clean}\n\nDokładnie. Analiza zakończona."
        
        # Append disclaimer if present
        if state.get("disclaimer"):
            final_res += f"\n\n_Clinical Disclaimer:_ {state['disclaimer']}"
            
        state["final_response"] = final_res
        return state

    def save_to_notion(self, state: DataAnalysisState) -> DataAnalysisState:
        """Node 6: Save in-depth reports to Notion."""
        if state.get("report_type") != "in_depth":
            return state
            
        print(f"[{self.name}] Analysis Node: save_to_notion", flush=True)
        parent_page_id = os.getenv("NOTION_ANALYSIS_PARENT_ID", "32ef5d41fe97809c9a73ce7f83c1fa27")
        title = f"Clinical Analysis: {state.get('task')[:50]}..."
        content = state.get("final_response", "")
        
        try:
            result_str = notion_client.create_page(parent_page_id, title, content, agent_name=self.name)
            url_match = re.search(r"URL:\s*([^\s]+)", result_str)
            if url_match:
                state["notion_url"] = url_match.group(1)
            state["notion_success"] = True
            
            # Append success message to final response
            state["final_response"] += f"\n\n🔗 *Deep-dive report saved to Notion:* {state['notion_url']}"
        except Exception as e:
            print(f"[{self.name}] Analysis Node: Notion Save Failed: {e}", flush=True)
            state["notion_success"] = False
            state["final_response"] += f"\n\n⚠️ *Warning:* Clinical analysis completed, but saving to Notion failed: {e}"
            
        return state

from famiglia_core.db.observability.checkpointer import PostgresCheckpointer

def setup_data_analysis_graph(agent):
    """Builds and compiles the Data Analysis StateGraph."""
    print(f"[{agent.name}] Data Analysis: Setting up graph...", flush=True)
    workflow_logic = DataAnalysisWorkflow(agent)
    
    workflow = StateGraph(DataAnalysisState)
    
    workflow.add_node("detect_intent", workflow_logic.detect_intent)
    workflow.add_node("run_discovery", workflow_logic.run_discovery)
    workflow.add_node("verify_data", workflow_logic.verify_data)
    workflow.add_node("inform_missing_data", workflow_logic.inform_missing_data)
    workflow.add_node("query_duckdb", workflow_logic.query_duckdb)
    workflow.add_node("generate_report", workflow_logic.generate_report)
    workflow.add_node("save_to_notion", workflow_logic.save_to_notion)
    
    workflow.set_entry_point("detect_intent")
    
    workflow.add_edge("detect_intent", "run_discovery")
    workflow.add_edge("run_discovery", "verify_data")
    
    workflow.add_conditional_edges(
        "verify_data",
        lambda x: "inform" if x.get("ingestion_needed") else "query",
        {
            "inform": "inform_missing_data",
            "query": "query_duckdb"
        }
    )
    
    workflow.add_edge("inform_missing_data", END)
    workflow.add_edge("query_duckdb", "generate_report")
    
    workflow.add_conditional_edges(
        "generate_report",
        lambda x: "save" if x.get("report_type") == "in_depth" else "finalize",
        {
            "save": "save_to_notion",
            "finalize": END
        }
    )
    
    workflow.add_edge("save_to_notion", END)
    
    checkpointer = PostgresCheckpointer()
    return workflow.compile(checkpointer=checkpointer)
