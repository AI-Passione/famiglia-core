from famiglia_core.agents.base_agent import BaseAgent
from famiglia_core.agents.llm.client import DEFAULT_OLLAMA_FALLBACK_MODEL

class Vito(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="vito",
            name="Vito",
            role="Personal finance guardian, investment advisor, expense tracking, tax management",
            model_config={
                "primary": "perplexity-sonar-pro",
                "secondary": "gemini-2.0-flash",
            }
        )

    def review_expense(self, amount: float, description: str) -> str:
        if self.propose_action(f"Reviewing expense: €{amount} for {description}"):
             if amount > 100:
                 print(f"[Vito 🦅] FERMA! €{amount} for {description}? I need to review this closely.")
             else:
                 print(f"[Vito 🦅] Recording expense: €{amount} for {description}. Porca miseria.")
                 
             prompt = f"Analyze this expense for Don Jimmy: €{amount} for {description}. Is it justified?"
             return self.complete_task(prompt)

    def daily_close(self, portfolio_value: float, daily_expenses: float) -> str:
         if self.propose_action("Preparing daily financial close"):
             print(f"[Vito 🦅] Don Jimmy, daily close ready. Portfolio: €{portfolio_value}. Expenses today: €{daily_expenses}.")
             prompt = f"Generate a daily financial summary given Portfolio value: €{portfolio_value} and Expenses: €{daily_expenses}."
             return self.complete_task(prompt)
