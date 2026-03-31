import os
from src.agents.riccado import Riccado
from src.agents.alfredo import Alfredo
from src.agents.llm.client import client
from src.db.init_db import init_db

if __name__ == "__main__":
    init_db()
    agents = {"riccado": Riccado(), "alfredo": Alfredo()}
    client.allocate_resources(list(agents.values()))
    
    res1 = agents["riccado"].review_code("def foo():\n    pass")
    print(res1)
    
    res2 = agents["alfredo"].coordinate("test request")
    print(res2)
