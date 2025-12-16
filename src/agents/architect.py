# src/agents/architect.py
from datetime import datetime

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

    # 4. Bundle Documentation so humans can easily view the diagrams inline
    if dep_graph_code or heatmap_code:
        doc_lines = [
            "# RepoRanger Architecture Snapshot",
            f"_Generated: {datetime.utcnow().isoformat()}Z_",
            "",
            "## Dependency Graph",
            "```mermaid",
            dep_graph_code or "graph TD\n    Empty[\"No diagram generated\"]",
            "```",
            "",
            "## Complexity Heatmap",
            "```mermaid",
            heatmap_code or "graph TD\n    Empty[\"No heatmap generated\"]",
            "```",
            "",
            "> Tip: The Mermaid blocks above can be copied directly into PRs, Markdown docs, or tools like Obsidian/Notion.",
        ]
        doc_path = save_artifact("\n".join(doc_lines), "md")
        new_artifacts.append({
            "id": "arch_overview_doc",
            "type": "markdown_doc",
            "file_path": doc_path,
            "description": "Inline documentation for dependency graph and complexity heatmap",
            "created_by": "architect"
        })

    print(f"--- 📐 Architect: Generated {len(new_artifacts)} diagrams ---")
    
    # 5. Return State Update
    return {
        "artifacts": new_artifacts,
        "messages": [HumanMessage(content=f"Architect generated {len(new_artifacts)} visualization artifacts.")]
    }
