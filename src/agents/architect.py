# src/agents/architect.py
from langchain_core.messages import HumanMessage
from src.state import RepoState
from src.tools.parser import PythonCodeParser
from src.tools.diagram import MermaidGenerator
from src.utils.workspace import save_artifact
from src.utils.config import cfg

def architect_node(state: RepoState) -> RepoState:
    """
    The Visual Architect Agent.
    It visualizes the codebase structure and complexity using Mermaid.js.
    """
    print("--- 📐 Architect: Visualizing System ---")
    
    # 1. Setup
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    
    # Initialize the tools we built
    parser = PythonCodeParser(repo_path)
    viz = MermaidGenerator(parser)
    
    new_artifacts = []
    
    # 2. Generate System Architecture (The "Big Picture")
    print("    Generating dependency graph...")
    # This triggers the parser to index the repo
    dep_graph_code = viz.generate_architecture_map()
    
    if dep_graph_code:
        path = save_artifact(dep_graph_code, "mmd")
        new_artifacts.append({
            "id": "arch_dependency_graph",
            "type": "diagram",
            "file_path": path,
            "description": "System-wide dependency graph (Mermaid)",
            "created_by": "architect"
        })

    # 3. Generate Complexity Heatmap (The "Quality Check")
    print("    Generating complexity heatmap...")
    heatmap_code = viz.generate_complexity_heatmap()
    
    if heatmap_code:
        path = save_artifact(heatmap_code, "mmd")
        new_artifacts.append({
            "id": "arch_complexity_map",
            "type": "diagram",
            "file_path": path,
            "description": "Cyclomatic Complexity Heatmap (Mermaid)",
            "created_by": "architect"
        })

    print(f"--- 📐 Architect: Generated {len(new_artifacts)} diagrams ---")
    
    # 4. Return State Update
    return {
        "artifacts": new_artifacts,
        "messages": [HumanMessage(content=f"Architect generated {len(new_artifacts)} visualization artifacts.")]
    }