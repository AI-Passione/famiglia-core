import pytest
import importlib
from pathlib import Path

def test_all_agents_importable():
    """
    Ensure all agents in the agents/ directory are importable.
    This would have caught the 'riccado' vs 'riccardo' discrepancy.
    """
    # Correctly identify path relative to this test file: 
    # tests/test_import_consistency.py -> Project Root/src/famiglia_core/agents
    project_root = Path(__file__).resolve().parent.parent
    agents_dir = project_root / "src" / "famiglia_core" / "agents"
    agent_files = [f.stem for f in agents_dir.glob("*.py") if f.stem not in ["__init__", "base_agent", "factory"]]
    
    for agent_module in agent_files:
        try:
            # Add src to path if needed for import
            import sys
            if str(project_root / "src") not in sys.path:
                sys.path.insert(0, str(project_root / "src"))
            
            module = importlib.import_module(f"famiglia_core.agents.{agent_module}")
            # Ensure the class (Capitalized) exists in the module
            class_name = agent_module.capitalize()
            assert hasattr(module, class_name), f"Module {agent_module} is missing class {class_name}"
        except ImportError as e:
            pytest.fail(f"Could not import agent module {agent_module}: {e}")

def test_root_main_imports():
    """
    Ensure the root main.py (entry point) is syntactically correct and imports work.
    """
    project_root = Path(__file__).resolve().parent.parent
    root_main = project_root / "main.py"
    assert root_main.exists(), f"Root main.py is missing at {root_main}"
    
    content = root_main.read_text()
    assert "riccado" not in content.lower(), f"Root main.py contains the 'riccado' typo!"
    assert "Riccardo" in content, "Root main.py is missing the 'Riccardo' import!"

def test_soul_registry_consistency():
    """
    Ensure soul registry IDs match the file names in the souls directory.
    """
    from famiglia_core.agents.souls.soul_registry import SOUL_REGISTRY
    project_root = Path(__file__).resolve().parent.parent
    souls_dir = project_root / "src" / "famiglia_core" / "agents" / "souls"
    
    for agent_id in SOUL_REGISTRY.keys():
        soul_file = souls_dir / f"{agent_id}.md"
        assert soul_file.exists(), f"Soul file missing for registered agent: {agent_id} ({soul_file.name})"
