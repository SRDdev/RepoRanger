# src/agents/architect.py
import os
from datetime import datetime
from rich.console import Console
from langchain_core.messages import HumanMessage

from src.state import RepoState
from src.tools.parser import PythonCodeParser
from src.tools.diagram import MermaidGenerator
from src.tools.gitops import GitOps
from src.utils.workspace import save_artifact
from src.utils.config import cfg

console = Console()

def architect_node(state: RepoState) -> RepoState:
    """
    The Visual Architect Agent.
    Visualizes codebase structure and complexity using Mermaid.js.
    Uses overwrite logic for clean workspace management.
    """
    console.print("[bold blue]--- Architect: Visualizing System ---[/bold blue]")
    
    # 1. Setup and Tool Initialization
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    git_ops = GitOps(repo_path)
    parser = PythonCodeParser(repo_path)
    viz = MermaidGenerator(parser)
    
    # Gather all tracked Python files to ensure the graph isn't empty
    try:
        py_files = git_ops.repo.git.ls_files("*.py").splitlines()
    except Exception:
        # Fallback to manual walk if git fails
        py_files = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.relpath(os.path.join(root, file), repo_path))

    new_artifacts = []
    
    # 2. Generate System Architecture (The "Big Picture")
    console.print(f"    Analyzing {len(py_files)} modules for dependency graph...")
    # Passing the file list ensures the generator has data to map
    dep_graph_code = viz.generate_architecture_map(py_files)
    
    if dep_graph_code:
        # Saves as .reporanger_workspace/dependency_graph.mmd (Overwrites)
        path = save_artifact(dep_graph_code, "mmd", prefix="dependency_graph")
        new_artifacts.append({
            "id": "arch_dependency_graph",
            "type": "diagram",
            "file_path": path,
            "description": "System-wide dependency graph",
            "created_by": "architect"
        })

    # 3. Generate Complexity Heatmap (The "Quality Check")
    console.print("    Generating complexity heatmap...")
    heatmap_code = viz.generate_complexity_heatmap()
    
    if heatmap_code:
        # Saves as .reporanger_workspace/complexity_heatmap.mmd (Overwrites)
        path = save_artifact(heatmap_code, "mmd", prefix="complexity_heatmap")
        new_artifacts.append({
            "id": "arch_complexity_map",
            "type": "diagram",
            "file_path": path,
            "description": "Cyclomatic Complexity Heatmap",
            "created_by": "architect"
        })

    # 4. Bundle Documentation
    if dep_graph_code or heatmap_code:
        doc_lines = [
            "# RepoRanger Architecture Snapshot",
            f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
            "",
            "## Dependency Graph",
            "```mermaid",
            dep_graph_code or "graph TD\n    Empty[No dependency graph generated]",
            "```",
            "",
            "## Complexity Heatmap",
            "```mermaid",
            heatmap_code or "graph TD\n    Empty[No complexity heatmap generated]",
            "```",
            "",
            "> Tip: These Mermaid blocks are compatible with GitHub, Obsidian, and Notion.",
        ]
        
        # Saves as .reporanger_workspace/architecture_overview.md (Overwrites)
        doc_path = save_artifact("\n".join(doc_lines), "md", prefix="architecture_overview")
        new_artifacts.append({
            "id": "arch_overview_doc",
            "type": "markdown_doc",
            "file_path": doc_path,
            "description": "Architecture overview report",
            "created_by": "architect"
        })

    console.print(f"[bold blue]--- Architect: Generated {len(new_artifacts)} visualization(s) ---[/bold blue]\n")
    
    return {
        "artifacts": new_artifacts,
        "messages": [HumanMessage(content=f"Architect generated {len(new_artifacts)} visualization artifacts.")]
    }