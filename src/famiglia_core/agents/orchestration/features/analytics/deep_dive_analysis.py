from typing import Any, Dict, List, Optional, TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END
import os
import re
import json
import operator

from famiglia_core.agents.orchestration.utils.state import AgentState
from famiglia_core.agents.llm.client import client
from famiglia_core.agents.tools.notion import notion_client
from famiglia_core.db.observability.checkpointer import PostgresCheckpointer

class DeepDiveAnalysisState(AgentState):
    """Extension of AgentState for iterative, hypothesis-driven Data Analysis."""
    candidate_tables: List[str]
    discovery_metadata: Optional[str]
    hypotheses: List[Dict[str, str]]
    query_history: Annotated[List[Dict[str, Any]], operator.add]
    success_count: int
    fail_count: int
    findings: List[str]
    executive_summary: Optional[str]
    notion_markdown: Optional[str]
    notion_url: Optional[str]
    notion_success: bool
    disclaimer: Optional[str]
    discovery_reasoning: Optional[str]
    notion_title: Optional[str]

class DeepDiveAnalysisWorkflow:
    def __init__(self, agent):
        self.agent = agent
        self.name = agent.name
        self.model_config = agent.model_config
        self.personality = self._load_kowalski_personality()
        self.template_path = os.path.join(
            os.getcwd(), 
            "src/agents/orchestration/features/templates/deep_dive_template.md"
        )
        # Ensure template directory exists or handle missing template
        os.makedirs(os.path.dirname(self.template_path), exist_ok=True)

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

    def run_discovery(self, state: DeepDiveAnalysisState) -> DeepDiveAnalysisState:
        """Node 1: Identify all relevant tables across all schemas."""
        print(f"[{self.name}] Deep Dive: run_discovery", flush=True)
        task = state["task"]
        
        try:
            # Multi-schema discovery
            schema_info = self.agent.query_dwh(
                "SELECT table_schema, table_name, column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_name NOT ILIKE '%cache%' "
                "AND table_schema NOT IN ('information_schema', 'pg_catalog')"
            )
            schema_str = str(schema_info)
        except Exception as e:
            print(f"[{self.name}] Deep Dive: Discovery Query Failed: {e}", flush=True)
            schema_str = "Unknown"

        prompt = f"""
        {self.personality}
        
        Task: {task}
        DuckDB Inventory: {schema_str}
        
        Instruction: Identify ALL tables that are relevant for a deep-dive analysis. 
        Include primary data tables and potential dimension/lookup tables for joins.
        
        Output in JSON format:
        {{
            "candidate_tables": ["schema.table1", "schema.table2"],
            "discovery_reasoning": "Clinical justification for inclusion."
        }}
        """
        
        try:
            res_text, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
            json_match = re.search(r"\{.*\}", res_text, re.DOTALL)
            data = json.loads(json_match.group(0)) if json_match else {}
            state["candidate_tables"] = data.get("candidate_tables", [])
            state["discovery_reasoning"] = data.get("discovery_reasoning", "Clinical data identification based on task relevance.")
            state["success_count"] = 0
            state["fail_count"] = 0
            state["query_history"] = []
            state["findings"] = []
            print(f"[{self.name}] Deep Dive: Candidates: {state['candidate_tables']}", flush=True)
            print(f"[{self.name}] Deep Dive: Reasoning: {state['discovery_reasoning']}", flush=True)
        except Exception as e:
            print(f"[{self.name}] Deep Dive: Discovery LLM Failed: {e}", flush=True)
            state["candidate_tables"] = []
            
        return state

    def form_hypotheses(self, state: DeepDiveAnalysisState) -> DeepDiveAnalysisState:
        """Node 2: Form analytical hypotheses based on discovered schema."""
        print(f"[{self.name}] Deep Dive: form_hypotheses", flush=True)
        if not state.get("candidate_tables"):
            return state

        # Get snippets for candidates
        discovery_context = []
        for table in state["candidate_tables"]:
            try:
                summary = self.agent.query_dwh(f"SUMMARIZE {table}")
                discovery_context.append(f"Table {table} summary: {summary}")
            except: pass

        prompt = f"""
        {self.personality}
        
        Task: {state['task']}
        Data Context: {" ".join(discovery_context)}
        
        Instruction: Form 2-3 clinical hypotheses to investigate during this deep dive.
        Each hypothesis should be testable via SQL.
        
        Output in JSON format:
        {{
            "hypotheses": [
                {{"id": "H1", "statement": "Description", "expected_indicator": "What metrics to look for"}},
                ...
            ]
        }}
        """
        try:
            res_text, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
            json_match = re.search(r"\{.*\}", res_text, re.DOTALL)
            state["hypotheses"] = json.loads(json_match.group(0)).get("hypotheses", [])
            print(f"[{self.name}] Deep Dive: Hypotheses formed: {[h['id'] for h in state['hypotheses']]}", flush=True)
        except Exception as e:
            print(f"[{self.name}] Deep Dive: Hypothesis logic failed: {e}", flush=True)
            state["hypotheses"] = []

        return state

    def execute_drilldown_queries(self, state: DeepDiveAnalysisState) -> DeepDiveAnalysisState:
        """Node 3: Iteratively execute queries to test hypotheses."""
        print(f"[{self.name}] Deep Dive: execute_drilldown (Success: {state['success_count']}, Fail: {state['fail_count']})", flush=True)
        
        # Determine next query based on hypotheses and history
        history_summary = ""
        for q in state["query_history"]:
            history_summary += f"Query: {q['query']}\nResult: {str(q['result'])[:500]}...\n"

        prompt = f"""
        {self.personality}
        
        Task: {state['task']}
        Hypotheses: {json.dumps(state['hypotheses'])}
        Previous Clinical History: {history_summary}
        Verified Tables: {state['candidate_tables']}
        
        Analytical Mandate:
        You are in a DRILLDOWN phase. You must generate a precise SQL query to extract evidence for the hypotheses.
        - If you have enough evidence for all hypotheses, output "FINISH".
        - Otherwise, output the NEXT logical DuckDB SQL query.
        
        CRITICAL RE-EVALUATION:
        - Review the "Previous Clinical History" below carefully. 
        - If a query FAILED (returned ERROR), you MUST debug the syntax and generate a DIFFERENT, valid query.
        - DO NOT repeat the exact same SQL that failed.
        - If a query was successful but didn't provide the depth needed, drill down further with a more specific query.
        
        Successes so far: {state['success_count']}
        Failures so far: {state['fail_count']}
        
        Output ONLY raw SQL or "FINISH". No markdown.
        """
        
        res_text, _ = client.complete(prompt, self.model_config, agent_name=self.name)
        sql_text = res_text.strip()
        
        if "FINISH" in sql_text.upper():
            print(f"[{self.name}] Deep Dive: Drilldown signaled FINISH.", flush=True)
            # Add a sentinel to query_history to signal FINISH to graph
            state["query_history"] = [{"query": "FINISH", "result": "SIGNAL"}]
            return state

        # Clean SQL
        sql_match = re.search(r"```sql\s*(.*?)\s*```", sql_text, re.DOTALL | re.IGNORECASE)
        sql = sql_match.group(1).strip() if sql_match else sql_text.strip()
        sql = re.sub(r"^(sql|query)\s*=\s*", "", sql, flags=re.IGNORECASE)

        try:
            results = self.agent.query_dwh(sql)
            state["query_history"] = [{"query": sql, "result": results}]
            state["success_count"] += 1
            print(f"[{self.name}] Deep Dive: SUCCESS ({state['success_count']}) SQL executed.", flush=True)
        except Exception as e:
            print(f"[{self.name}] Deep Dive: FAIL ({state['fail_count']+1}) SQL Error: {e}", flush=True)
            state["fail_count"] += 1
            # Still record the fail in history to avoid repeating it
            state["query_history"] = [{"query": sql, "result": f"ERROR: {e}"}]

        return state

    def synthesize_findings(self, state: DeepDiveAnalysisState) -> DeepDiveAnalysisState:
        """Node 4: Synthesize all query results into clinical findings."""
        print(f"[{self.name}] Deep Dive: synthesize_findings", flush=True)
        
        history_summary = ""
        for q in state["query_history"]:
            history_summary += f"Analysis Step:\nSQL: {q['query']}\nData: {q['result']}\n\n"

        prompt = f"""
        {self.personality}
        
        Task: {state['task']}
        Hypotheses: {json.dumps(state['hypotheses'])}
        Evidence: {history_summary}
        
        Instruction: Synthesize the evidence. For each hypothesis, determine if it was supported, refuted, or remains inconclusive.
        Extract concrete metrics and clinical insights.
        
        CRITICAL: Also identify any data limitations, such as small sample sizes (e.g. fewer than 100 rows), unreliable timestamps, or potential biases.
        
        Output a list of clinical findings, including a section on data limitations.
        """
        
        res, _ = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        state["findings"] = [res]
        return state

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

    def _to_classic_markdown(self, text: str) -> str:
        """Converts Slack bolding (*bold*) to standard Markdown (**bold**)."""
        if not text: return ""
        lines = text.split('\n')
        processed_lines = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith('• ') or stripped.startswith('- '):
                # It's a bullet point, only replace bolding in the rest of the line
                prefix = line[:line.find(stripped[0])] + "- "
                content = stripped[2:]
                content = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'**\1**', content)
                processed_lines.append(f"{prefix}{content}")
            else:
                processed_lines.append(re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'**\1**', line))
        return '\n'.join(processed_lines)

    def generate_report(self, state: DeepDiveAnalysisState) -> DeepDiveAnalysisState:
        """Node 5: Create the final Deep Dive report and prepare Notion formatting."""
        print(f"[{self.name}] Deep Dive: generate_report", flush=True)
        findings = "\n".join(state["findings"])
        
        prompt = f"""
        {self.personality}
        
        Task: {state['task']}
        Synthesized Findings: {findings}
        
        Instruction: Format a *Clinical Deep-Dive Analysis*.
        
        Structure:
        1. *Executive Summary*: A list of 8-10 actionable insights. DO NOT include any introductory paragraphs, preamble, or greeting. Start directly with bullets.
        2. *Disclaimer*: Mention data limitations, small sample sizes (if fewer than 100 rows), and timestamp reliability here.
        
        Formatting RULES (CRITICAL):
        - DO NOT USE any `#` (Markdown H1, H2, etc.) headers. Slack DOES NOT support them.
        - Use ONLY `*` for BOLD (e.g. `*Executive Summary*`).
        - Use `• ` (bullet point symbol) for ALL list items. Ensure every single insight is a bullet point.
        - You MUST use backticks (`` ` ``) for ALL column names, numbers, percentages, and specific data values (e.g. `GMV`, `14,200`, `Africa`).
        - Ensure `Executive Summary` title is on its OWN line.
        - Ensure DOUBLE LINE BREAKS between headers and lists.
        - Ensure DOUBLE LINE BREAKS between individual bullet points for readability.
        - No greetings, no preamble. NO SIGN-OFFS.
        """
        
        res, used_model = client.complete(prompt, self.agent.get_model_config(state), agent_name=self.name)
        state["used_model"] = used_model
        
        # --- Heavy Lifting: Prepare Notion Markdown ---
        # 1. Parse Sections (Executive Summary vs Disclaimer)
        # More robust splitting using a flexible regex for Disclaimer header
        disclaimer_header_regex = r"\n[\s\-]*\*?\s*Disclaimer\*?[:\s]*\n"
        parts = re.split(disclaimer_header_regex, res, flags=re.IGNORECASE)
        
        summary_all = parts[0].strip()
        # Split by Executive Summary to isolate the actual content and ignore preamble
        summary_parts = re.split(r"\*?\s*(?:\d\.\s*)?Executive Summary\*?[:\s]*", summary_all, flags=re.IGNORECASE)
        summary_uncleaned = summary_parts[-1].strip() 
        exec_summary_clean = self._clean_kowalski_talk(summary_uncleaned)
        
        disclaimer_raw = parts[1] if len(parts) > 1 else "No specific data limitations identified."
        disclaimer_clean = self._clean_kowalski_talk(disclaimer_raw)
        # Aggressively remove any lingering "Disclaimer" text from the beginning
        disclaimer_clean = re.sub(r"^\*?\s*\d?\.*?\s*Disclaimer\*?[:\s]*", "", disclaimer_clean, flags=re.IGNORECASE).strip()

        state["executive_summary"] = exec_summary_clean
        state["disclaimer"] = disclaimer_clean
        
        # 2. Set Slack Response (Restoring Header + Code-managed Sign-off)
        # Adding double newlines to ensure separation from any caller greeting and force Slack header onto its own line
        state["final_response"] = f"\n\n*Executive Summary*\n\n{exec_summary_clean}\n\nDokładnie. Analiza zakończona."
        
        # 3. Generate a punchy Notion Title
        title_prompt = f"Based on this analysis task: '{state['task']}', generate a short, clinical, and punchy title for a report (max 6-8 words). Output ONLY the title text."
        notion_title, _ = client.complete(title_prompt, self.agent.get_model_config(state), agent_name=self.name)
        state["notion_title"] = notion_title.strip().strip('"').strip("'")
        
        # 3. Prepare Notion formatting (Classic Markdown)
        exec_summary_classic = self._to_classic_markdown(exec_summary_clean)
        disclaimer_classic = self._to_classic_markdown(disclaimer_clean)

        # 4. Load Template
        template_content = "# Data Analysis Report\n\n## 1. Executive Summary\n\n{{executive_summary}}\n\n## 2. Disclaimer\n\n{{disclaimer}}"
        template_path = "./src/agents/orchestration/features/analytics/templates/data_analysis_template.md"
        try:
            if os.path.exists(template_path):
                with open(template_path, "r") as f:
                    template_content = f.read()
        except Exception as e:
            print(f"[{self.name}] Template Load Failed: {e}", flush=True)

        # 5. Assemble Business Context & Analysis
        business_context = f"**Task:** {state.get('task')}\n\n**Data Context:** {state.get('discovery_reasoning', 'No reasoning provided.')}\n\n"
        if state.get("candidate_tables"):
            business_context += f"**Tables Analyzed:** {', '.join(state['candidate_tables'])}"

        analysis_content = "### 4.1 Methodology\nIterative clinical examination of DuckDB schemas based on formed hypotheses.\n\n"
        analysis_content += "### 4.2 Drill-down Steps\n"
        for i, q in enumerate(state.get("query_history", []), 1):
             if q.get("query") == "FINISH": continue
             analysis_content += f"#### Step {i}: Query Execution\n"
             analysis_content += f"**SQL:**\n```sql\n{q['query']}\n```\n"
             res_str = str(q.get("result", ""))
             if len(res_str) > 500: res_str = res_str[:500] + "... [truncated]"
             analysis_content += f"**Finding:**\n{res_str}\n\n"

        appendix_content = "### 5.1 Hypotheses Status\n"
        for h in state.get("hypotheses", []):
             appendix_content += f"- **{h.get('id', 'H')}**: {h.get('statement', '')} -> {h.get('expected_indicator', '')}\n"
        appendix_content += "\n### 5.2 External Links / Queries Used\n"
        for q in state.get("query_history", []):
            if q.get("query") == "FINISH": continue
            appendix_content += f"```sql\n{q['query']}\n```\n\n"

        # 6. Populate Final Markdown
        notion_md = template_content
        notion_md = notion_md.replace("Executive Summary is a list of actionable insights in 8-10 bulletpoints supported with key stats.\nThe goal of this part is to shorten the reading time and let the readers grasp the key ideas of the analysis in the shortest time possible.", exec_summary_classic)
        # Ensure disclaimer is included if the template has a placeholder or if it's missing
        if "{{disclaimer}}" in notion_md:
            notion_md = notion_md.replace("{{disclaimer}}", disclaimer_classic)
        elif "## 2. Disclaimer" in notion_md:
             # Assume standard template has a section for disclaimer
             pass # Logic for template specific replacement would go here if needed
        
        notion_md = notion_md.replace("The motivation why this analysis is needed, and important concepts to understand BEFORE reading the details of the analysis. This section is particularly for laymen readers who are not familiar with the topic of the analysis. Hence, it is vital to have brief explanation of the important concepts that may not be known by the audience.", business_context)
        notion_md = notion_md.replace("The content of the analysis itself. The important thing to bear in mind here is, always start with the highest level of concept, then drill down to lower granularity step by step.", analysis_content)
        notion_md = notion_md.replace("The Appendix is the content (e.g. Data Visualizations) that does not fit into the key storytelling of the analysis, but is still relevant to keep. Use high-level descriptions or tables to represent data findings.", appendix_content)
        notion_md = notion_md.replace("It is vital to store ALL analytical resources used (e.g. Tableau Workbook, queries, Jupyter Notebooks etc.) and attach them in the analysis as well. The creditability of an analysis could be greatly improved if the same results can be re-produced and re-used by the other analysts.", "See Section 5.2 for all SQL queries used.")
        
        state["notion_markdown"] = notion_md
        return state

    def save_to_notion(self, state: DeepDiveAnalysisState) -> DeepDiveAnalysisState:
        """Node 6: Finalize report by saving prepared markdown to Notion."""
        print(f"[{self.name}] Deep Dive: save_to_notion", flush=True)
        parent_page_id = os.getenv("NOTION_ANALYSIS_PARENT_ID", "32ef5d41fe97809c9a73ce7f83c1fa27")
        title = state.get("notion_title") or f"Deep-Dive Analysis: {state.get('task')[:50]}..."
        notion_markdown = state.get("notion_markdown", "# Data Analysis Report")

        try:
            result_str = notion_client.create_page(parent_page_id, title, notion_markdown, agent_name=self.name)
            url_match = re.search(r"URL:\s*([^\s]+)", result_str)
            if url_match:
                state["notion_url"] = url_match.group(1)
            state["notion_success"] = True
            
            if state.get("notion_url"):
                if state["notion_url"] not in state.get("final_response", ""):
                    state["final_response"] += f"\n\n🔗 *Full Deep-Dive saved to Notion:* {state['notion_url']}"
                      
        except Exception as e:
            state["notion_success"] = False
            state["final_response"] += f"\n\n⚠️ *Notion Save Failed: {e}*"
            
        return state

def setup_deep_dive_analysis_graph(agent):
    """Builds the Deep Dive Analysis graph."""
    print(f"[{agent.name}] Deep Dive: Setting up graph...", flush=True)
    workflow_logic = DeepDiveAnalysisWorkflow(agent)
    
    workflow = StateGraph(DeepDiveAnalysisState)
    
    workflow.add_node("run_discovery", workflow_logic.run_discovery)
    workflow.add_node("form_hypotheses", workflow_logic.form_hypotheses)
    workflow.add_node("execute_drilldown", workflow_logic.execute_drilldown_queries)
    workflow.add_node("synthesize_findings", workflow_logic.synthesize_findings)
    workflow.add_node("generate_report", workflow_logic.generate_report)
    workflow.add_node("save_to_notion", workflow_logic.save_to_notion)
    
    workflow.set_entry_point("run_discovery")
    
    workflow.add_edge("run_discovery", "form_hypotheses")
    workflow.add_edge("form_hypotheses", "execute_drilldown")
    
    # Conditional loop for drilldown
    workflow.add_conditional_edges(
        "execute_drilldown",
        lambda x: "continue" if (
            x["success_count"] < 3 and 
            x["fail_count"] < 5 and 
            not any(q.get("query") == "FINISH" for q in x["query_history"])
        ) else "synthesize",
        {
            "continue": "execute_drilldown",
            "synthesize": "synthesize_findings"
        }
    )
    
    workflow.add_edge("synthesize_findings", "generate_report")
    workflow.add_edge("generate_report", "save_to_notion")
    workflow.add_edge("save_to_notion", END)
    
    checkpointer = PostgresCheckpointer()
    return workflow.compile(checkpointer=checkpointer)
