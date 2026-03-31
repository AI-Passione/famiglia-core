from famiglia_core.agents.base_agent import BaseAgent
from famiglia_core.agents.llm.models_registry import GEMMA3_4B

class Tommy(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="tommy",
            name="Tommy",
            role="Operations executor, task completion, logistics consultant",
            model_config={
                "primary": "gemini-2.0-flash",
                "secondary": GEMMA3_4B,
            }
        )

    def execute_task(self, task: str):
        if self.propose_action(f"Execute task: {task}"):
            print(f"[Tommy 🔫] Capito, Don Jimmy.")
            # Implementation of execution logic would go here
            response = self.complete_task(task)
            print(f"[Tommy 🔫] Fatto.")
            return response
