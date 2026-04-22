import os
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class GraphNode(BaseModel):
    id: str
    label: str
    type: str = "node" # node, conditional, entry, end
    code: Optional[str] = None
    description: Optional[str] = None

class GraphEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None

class GraphDefinition(BaseModel):
    id: str
    name: str
    category: str = "General"
    nodes: List[GraphNode]
    edges: List[GraphEdge]

class GraphParser:
    def __init__(self, features_dir: str):
        self.features_dir = features_dir

    def parse_all_graphs(self) -> List[GraphDefinition]:
        graphs = []
        if not os.path.exists(self.features_dir):
            return graphs

        for root, dirs, files in os.walk(self.features_dir):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            
            # Category name from subdirectory
            rel_path = os.path.relpath(root, self.features_dir)
            category = "General" if rel_path == "." else rel_path.replace("_", " ").title()
            
            for filename in files:
                if filename.endswith(".py") and filename != "__init__.py":
                    file_path = os.path.join(root, filename)
                    graph_def = self.parse_file(file_path, category=category)
                    if graph_def:
                        graphs.append(graph_def)
        
        return graphs

    def parse_file(self, file_path: str, category: str = "General") -> Optional[GraphDefinition]:
        with open(file_path, "r") as f:
            content = f.read()

        # Extract graph name from the file name
        graph_id = os.path.basename(file_path).replace(".py", "")
        graph_name = graph_id.replace("_", " ").title()

        nodes = []
        edges = []
        seen_nodes = set()
        
        # Extract Node Source Code using AST
        try:
            import ast
            tree = ast.parse(content)
            func_details = {}
            for node_ast in ast.walk(tree):
                if isinstance(node_ast, ast.FunctionDef):
                    # Get the source code for this function
                    # Note: this is a simple extraction, might need refinement for complex files
                    start_line = node_ast.lineno - 1
                    end_line = getattr(node_ast, "end_lineno", node_ast.lineno)
                    lines = content.splitlines()[start_line:end_line]
                    func_details[node_ast.name] = {
                        "code": "\n".join(lines),
                        "description": ast.get_docstring(node_ast)
                    }
        except Exception as e:
            print(f"Error parsing AST for {file_path}: {e}")
            func_details = {}

        # 1. Add START node
        nodes.append(GraphNode(id="START", label="Start", type="entry"))
        seen_nodes.add("START")

        # 2. Extract Nodes
        node_matches = re.finditer(r'workflow\.add_node\(\s*["\']([^"\']+)["\']', content)
        for match in node_matches:
            node_id = match.group(1)
            if node_id not in seen_nodes:
                details = func_details.get(node_id, {})
                nodes.append(GraphNode(
                    id=node_id, 
                    label=node_id.replace("_", " ").title(),
                    code=details.get("code"),
                    description=details.get("description")
                ))
                seen_nodes.add(node_id)

        # 3. Add END node  
        # We always add END to ensure terminal nodes have a consistent sink
        if "END" not in seen_nodes:
            nodes.append(GraphNode(id="END", label="End", type="end"))
            seen_nodes.add("END")

        # 4. Extract Entry Point
        entry_match = re.search(r'workflow\.set_entry_point\(\s*["\']([^"\']+)["\']\)', content)
        if entry_match:
            entry_id = entry_match.group(1)
            edges.append(GraphEdge(source="START", target=entry_id))
            
        # 5. Extract Conditional Entry Point
        cond_entry_match = re.search(r'workflow\.set_conditional_entry_point\(\s*[^,]+,\s*(\{.*?\})\s*\)', content, re.DOTALL)
        if cond_entry_match:
            mapping_str = cond_entry_match.group(1)
            map_matches = re.finditer(r'["\']([^"\']+)["\']\s*:\s*([^,}]+)', mapping_str)
            for map_match in map_matches:
                target = map_match.group(2).strip().strip("'\"").strip()
                if target == "END":
                    edges.append(GraphEdge(source="START", target="END"))
                else:
                    edges.append(GraphEdge(source="START", target=target))

        # 6. Extract Edges
        edge_matches = re.finditer(r'workflow\.add_edge\(\s*["\']([^"\']+)["\']\s*,\s*([^)]+)\)', content)
        for match in edge_matches:
            target = match.group(2).strip().strip("'\"").strip()
            edges.append(GraphEdge(source=match.group(1), target=target))

        # 7. Extract Conditional Edges
        cond_matches = re.finditer(r'workflow\.add_conditional_edges\(\s*["\']([^"\']+)["\']\s*,\s*[^,]+\s*,\s*(\{.*?\})\s*\)', content, re.DOTALL)
        for match in cond_matches:
            source = match.group(1)
            mapping_str = match.group(2)
            map_matches = re.finditer(r'["\']([^"\']+)["\']\s*:\s*([^,}]+)', mapping_str)
            for map_match in map_matches:
                label = map_match.group(1)
                target = map_match.group(2).strip().strip("'\"").strip()
                edges.append(GraphEdge(source=source, target=target, label=label))
                
        # 8. Auto-connect implicit sinks to END so it places properly at the bottom
        sources = {e.source for e in edges}
        for node in nodes:
            if node.id not in ["START", "END"] and node.id not in sources:
                edges.append(GraphEdge(source=node.id, target="END"))

        if len(nodes) <= 2:
            return None

        return GraphDefinition(
            id=graph_id,
            name=graph_name,
            category=category,
            nodes=nodes,
            edges=edges
        )

# Simple test
if __name__ == "__main__":
    parser = GraphParser("src/agents/orchestration/features")
    all_graphs = parser.parse_all_graphs()
    import json
    print(json.dumps([g.dict() for g in all_graphs], indent=2))
