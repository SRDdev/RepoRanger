# main.py - RepoRanger Autonomous Code Steward
import os
import re
import argparse
import subprocess
from datetime import datetime
from dotenv import load_dotenv

from src.graph import app
from src.utils.config import cfg
from src.tools.gitops import GitOps
from src.tools.branch_manager import BranchManager

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule

console = Console()
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="RepoRanger - Autonomous Code Steward",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create smart branch
  python main.py branch --intent "Refactor parser logic"
  
  # Full analysis and README sync
  python main.py --mode full --target-branch master
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # --- BRANCH COMMAND ---
    branch_parser = subparsers.add_parser('branch', help='Create semantic branch')
    branch_parser.add_argument('--intent', '-m', required=True, help='Branch purpose')
    branch_parser.add_argument('--type', '-t', choices=[
        'feat', 'fix', 'hotfix', 'refactor', 'perf', 
        'docs', 'test', 'chore', 'style', 'ci', 'build'
    ], help='Override branch type')
    branch_parser.add_argument('--no-commit', action='store_true', help='Skip initial commit')

    # --- GLOBAL ARGUMENTS ---
    parser.add_argument("--target-branch", default="master", help="Base branch for comparison")
    parser.add_argument("--mode", choices=["full", "pr", "commit", "audit", "docs"], default="full")
    parser.add_argument("--commit-intent", help="Intent for generated commit message")
    
    args = parser.parse_args()
    
    # Header
    console.print(Panel(
        f"[bold blue]{cfg.get('project.name', 'RepoRanger').upper()}[/bold blue] | System Analysis Engine",
        border_style="blue"
    ))
    
    if args.command == 'branch':
        _handle_branch_creation(args)
        return

    # Initialize GitOps with CI-safe branch detection
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    
    # Session Info Table
    info_table = Table.grid(padding=(0, 2))
    info_table.add_column(style="dim")
    info_table.add_column()
    info_table.add_row("Active Branch:", f"[cyan]{current_branch}[/cyan]")
    info_table.add_row("Target Branch:", f"[cyan]{args.target_branch}[/cyan]")
    info_table.add_row("Execution Mode:", f"[yellow]{args.mode.upper()}[/yellow]")
    console.print(info_table)
    console.print(Rule(style="dim"))

    if args.mode == "commit":
        _execute_commit_mode(args)
        return

    _execute_graph_mode(args, current_branch)

# ========================================================================
# EXECUTION LOGIC
# ========================================================================

def _execute_graph_mode(args, current_branch):
    """Runs the multi-agent pipeline and formats results"""
    initial_state = {
        "repo_path": os.getcwd(),
        "target_branch": args.target_branch,
        "source_branch": current_branch,
        "mode": args.mode,
        "artifacts": [], 
        "messages": [], 
        "code_issues": []
    }
    
    console.print("\n[bold]STARTING ANALYSIS PIPELINE[/bold]\n", style="dim")
    
    final_state = initial_state
    with console.status("[dim]Processing pipeline nodes...", spinner="dots"):
        for event in app.stream(initial_state):
            node_name = list(event.keys())[0]
            final_state = event[node_name]
            _render_node_summary(node_name, final_state)
    
    # Post-Processing: Sync Architecture to README if in Full mode
    if args.mode == "full":
        _update_readme_with_analysis(final_state)

    # Post-Processing: Generate Deployment Instructions
    if args.mode in ["pr", "full"]:
        _handle_pr_output(final_state, args.target_branch)
    
    console.print(f"\n[bold green]Pipeline execution finished successfully.[/bold green]")

def _execute_commit_mode(args):
    """Directly invokes Scribe for a commit message"""
    from src.agents.scribe import scribe_node
    console.print("[bold yellow]Mode: Commit Message Generation[/bold yellow]")
    
    intent = args.commit_intent
    if not intent:
        from rich.prompt import Prompt
        intent = Prompt.ask("Enter commit intent", default="General improvements")
    
    state = {
        "repo_path": os.getcwd(),
        "mode": "commit",
        "commit_intent": intent,
        "artifacts": [], "messages": [], "code_issues": []
    }
    
    with console.status("[dim]Generating commit message...", spinner="dots"):
        result = scribe_node(state)
        _handle_commit_output(result)

# ========================================================================
# README SYNCHRONIZATION
# ========================================================================
def _update_readme_with_analysis(state):
    """
    Triggers Scribe's AI rewrite of the README.md.
    This replaces the old manual marker logic with full AI generation.
    """
    from src.agents.scribe import _generate_enhanced_readme
    from src.tools.gitops import GitOps
    
    console.print("    [blue]Agent Scribe: Reimagining README.md with Gemini...[/blue]")
    
    git_ops = GitOps(os.getcwd())
    
    # Generate the new content using AI
    new_readme_content = _generate_enhanced_readme(git_ops, state)
    
    if not new_readme_content:
        console.print("    [red]Error: AI failed to generate README content.[/red]")
        return

    try:
        # Backup old readme just in case
        if os.path.exists("README.md"):
            os.rename("README.md", "README.md.bak")
            
        with open("README.md", "w") as f:
            f.write(new_readme_content)
            
        console.print("    [green]Success: README.md has been fully updated by Scribe.[/green]")
        
        # Clean up backup if successful
        if os.path.exists("README.md.bak"):
            os.remove("README.md.bak")
            
    except Exception as e:
        console.print(f"    [red]Error writing README: {e}[/red]")
        if os.path.exists("README.md.bak"):
            os.rename("README.md.bak", "README.md")

# ========================================================================
# OUTPUT HANDLERS
# ========================================================================

def _render_node_summary(node_name: str, state: dict):
    """Prints a clean, boxed summary of agent output"""
    artifacts = state.get("artifacts", [])
    issues = state.get("code_issues", [])
    
    if not artifacts and not issues:
        return

    content = []
    for art in artifacts:
        if art.get("created_by") == node_name:
            content.append(f"Artifact: [bold]{art['description']}[/bold]")
            content.append(f"Path:     [dim]{art['file_path']}[/dim]\n")

    if node_name == "steward" and issues:
        content.append("[bold red]Analysis Findings:[/bold red]")
        for issue in issues[:5]:
            sev = issue.get('severity', 'info').upper()
            content.append(f"  - [{sev}] {issue['file']}: {issue['message']}")
        if len(issues) > 5:
            content.append(f"  [dim]... and {len(issues)-5} more issues in full report.[/dim]")

    if content:
        console.print(Panel("\n".join(content).strip(), title=f"Agent: {node_name.capitalize()}", border_style="dim"))

def _handle_branch_creation(args):
    """Manages Smart Branching flow"""
    console.print("[bold yellow]Mode: Smart Branch Creator[/bold yellow]")
    git_ops = GitOps(os.getcwd())
    manager = BranchManager(git_ops)
    
    with console.status("[dim]Generating semantic branch name...", spinner="dots"):
        try:
            branch_name, branch_type = manager.create_smart_branch(
                user_intent=args.intent,
                auto_detect_type=(args.type is None),
                suggested_type=args.type,
                create_initial_commit=(not args.no_commit)
            )
            
            summary = [
                f"Branch: [cyan]{branch_name}[/cyan]",
                f"Type:   [yellow]{branch_type}[/yellow]",
                "",
                "1. git add .",
                "2. python main.py --mode commit"
            ]
            console.print(Panel("\n".join(summary), title="Success", border_style="green"))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

def _handle_commit_output(state):
    artifacts = state.get("artifacts", [])
    if any(a.get("type") == "commit_msg" for a in artifacts):
        console.print(Panel(
            "Commit message saved to: [cyan]COMMIT_MESSAGE.txt[/cyan]\n"
            "Apply: [bold]git commit -F COMMIT_MESSAGE.txt[/bold]",
            title="Success", border_style="green"
        ))

def _handle_pr_output(state, target_branch):
    """Final summary for deployment"""
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    
    try:
        gh_user = subprocess.check_output(["gh", "api", "user", "-q", ".login"], text=True).strip()
    except Exception:
        gh_user = "YOUR_USERNAME"

    output = [
        "[bold cyan]STEP 1: PUSH[/bold cyan]",
        f"git push origin {current_branch}",
        "",
        "[bold cyan]STEP 2: CREATE PR[/bold cyan]",
        f"gh pr create --base {target_branch} --head {gh_user}:{current_branch} --body-file PR_Document.md",
        "",
        "[dim]Tip: Add --web if you face authentication issues.[/dim]"
    ]
    console.print(Panel("\n".join(output), title="DEPLOYMENT STEPS", border_style="green"))

if __name__ == "__main__":
    main()