"""
Git Tactician - Smart Git Operations Handler
"""
from langchain_core.messages import HumanMessage
from src.state import RepoState
from src.tools.gitops import GitOps
from src.utils.workspace import save_artifact
from src.utils.config import cfg
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

def tactician_node(state: RepoState) -> RepoState:
    """
    Handles Git operations intelligently:
    - Provides structured next steps and command suggestions
    - Uses Rich for professional console formatting
    """
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    git_ops = GitOps(repo_path)
    
    artifacts = state.get("artifacts", [])
    code_issues = state.get("code_issues", [])
    
    # Get branch info
    current_branch = git_ops.get_current_branch()
    target_branch = state.get("target_branch", "main")
    
    recommendations = []
    git_commands = []
    
    # Logic Checks
    pr_docs = [a for a in artifacts if a.get("created_by") == "scribe"]
    has_pr_doc = len(pr_docs) > 0
    
    critical_issues = [i for i in code_issues if i.get("severity") == "critical"]
    has_critical = len(critical_issues) > 0
    
    refactor_plans = [a for a in artifacts if a.get("type") == "refactor_plan"]
    has_refactors = len(refactor_plans) > 0
    
    # Build Recommendations
    if has_critical:
        recommendations.append("Critical issues detected - Fix before pushing")
    
    if has_refactors:
        recommendations.append("Refactor suggestions available - Review before committing")
    
    if has_pr_doc:
        pr_path = pr_docs[0]["file_path"]
        recommendations.append(f"PR documentation generated: {pr_path}")
        git_commands.extend([
            f"cp {pr_path} PR_Document.md",
            "git add PR_Document.md"
        ])
    
    # Standard Git Workflow
    if not has_critical:
        git_commands.extend([
            "git add .",
            "git commit -m 'docs: Update from RepoRanger analysis'",
            f"git push origin {current_branch}"
        ])
        
        if current_branch not in ["main", "master", target_branch]:
            git_commands.append(
                f"gh pr create --base {target_branch} --title 'Update from RepoRanger' --body-file PR_Document.md"
            )
    
    # Generate instructions file
    instructions = _generate_instructions(
        current_branch=current_branch,
        target_branch=target_branch,
        recommendations=recommendations,
        git_commands=git_commands,
        artifacts=artifacts,
        has_critical=has_critical
    )
    instructions_path = save_artifact(instructions, "md", "Git")
    
    # --- Rich Console Output ---
    content = []
    
    if recommendations:
        rec_table = Table.grid(padding=(0, 1))
        rec_table.add_column(style="bold yellow")
        for rec in recommendations:
            rec_table.add_row(f"* {rec}")
        content.append(rec_table)
        content.append("")

    if git_commands and not has_critical:
        content.append(Text("Suggested Commands:", style="bold cyan"))
        for cmd in git_commands:
            content.append(Text(f"  $ {cmd}", style="bright_white"))
        content.append("")

    content.append(Text(f"Full instructions saved to: {instructions_path}", style="dim"))

    console.print(Panel(
        Group(*content),
        title="Tactician: Recommended Next Steps",
        title_align="left",
        border_style="blue"
    ))
    
    return {
        "artifacts": [{
            "id": "git_instructions",
            "type": "markdown_doc",
            "file_path": instructions_path,
            "description": "Git workflow instructions",
            "created_by": "tactician"
        }],
        "messages": [HumanMessage(
            content=f"Tactician prepared workflow instructions. Status: {'Action required' if has_critical else 'Ready'}."
        )]
    }

def _generate_instructions(
    current_branch: str,
    target_branch: str,
    recommendations: list,
    git_commands: list,
    artifacts: list,
    has_critical: bool
) -> str:
    """Generate professional markdown instructions without emojis"""
    instructions = [
        "# Git Workflow Instructions",
        f"**Current Branch:** {current_branch}",
        f"**Target Branch:** {target_branch}",
        f"**Generated:** {_get_timestamp()}",
        "---",
        ""
    ]
    
    if recommendations:
        instructions.append("## Recommendations")
        for rec in recommendations:
            instructions.append(f"* {rec}")
        instructions.append("")
    
    if has_critical:
        instructions.append("## Critical Issues Detected")
        instructions.append("Action Required: Fix critical issues before pushing.")
        instructions.append("Review the Steward report and re-run analysis after fixing.")
        return "\n".join(instructions)
    
    if git_commands:
        instructions.append("## Git Workflow")
        instructions.append("```bash")
        for cmd in git_commands:
            instructions.append(cmd)
        instructions.append("```")
        instructions.append("")
    
    if artifacts:
        instructions.append("## Generated Artifacts")
        for art in artifacts:
            instructions.append(f"* **{art['description']}** ({art['type']})")
            instructions.append(f"  * Path: {art['file_path']}")
        instructions.append("")

    return "\n".join(instructions)

def _get_timestamp():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

from rich.console import Group