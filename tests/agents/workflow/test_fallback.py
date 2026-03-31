import os
from famiglia_core.agents.riccado import Riccado
from famiglia_core.agents.alfredo import Alfredo
from famiglia_core.agents.llm.client import client
from famiglia_core.db.init_db import init_db

if __name__ == "__main__":
    init_db()
    agents = {"riccado": Riccado(), "alfredo": Alfredo()}
    client.allocate_resources(list(agents.values()))
    
    res1 = agents["riccado"].review_code("def foo():\n    pass")
    print(res1)
    
    res2 = agents["alfredo"].coordinate("test request")
    print(res2)
