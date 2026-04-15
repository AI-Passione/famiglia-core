from famiglia_core.agents.base_agent import BaseAgent
from famiglia_core.agents.llm.models_registry import GEMMA3_4B

class Bella(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="bella",
            name="Bella",
            role="Meeting notes, Notion updates, project management, scheduling",
            model_config={
                "primary": "gemini-2.0-flash",
                "secondary": GEMMA3_4B,
            }
        )

    def schedule_meeting(self, details: str) -> str:
        if self.propose_action(f"Scheduling meeting: {details}"):
             print(f"[Bella 💋] Certo, tesoro. Scheduling that right away: {details}")
             prompt = f"Draft a calendar invite and agenda for this meeting: {details}"
             return self.complete_task(prompt)

    def summarize_weekly(self) -> str:
         if self.propose_action("Drafting weekly summary for Notion"):
             print(f"[Bella 💋] Drafting your weekly summary, Boss. You were brilliant this week 🔥.")
             prompt = f"Draft a weekly wrap-up summary for Don Jimmy highlighting key projects, portfolio growth, and agent performance."
             return self.complete_task(prompt)
