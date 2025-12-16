# main.py - RepoRanger Autonomous Code Steward
import os
import argparse
import subprocess
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
  python main.py branch --intent "Add user authentication"
  
  # Full analysis
  python main.py --mode full --target-branch main
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # --- BRANCH COMMAND ---
    branch_parser = subparsers.add_parser('branch', help='Create smart branch')
    branch_parser.add_argument('--intent', '-m', required=True, help='Branch purpose/intent')
    branch_parser.add_argument('--type', '-t', choices=[
        'feat', 'fix', 'hotfix', 'refactor', 'perf', 
        'docs', 'test', 'chore', 'style', 'ci', 'build'
    ], help='Branch type')
    branch_parser.add_argument('--no-commit', action='store_true', help='Skip initial commit')

    # --- GLOBAL ARGUMENTS ---
    parser.add_argument("--target-branch", default="main", help="Target branch")
    parser.add_argument("--mode", choices=["full", "pr", "commit", "audit", "docs"], default="full")
    parser.add_argument("--commit-intent", help="Commit intent")
    
    args = parser.parse_args()
    
    # Header
    console.print(Panel(
        f"[bold blue]{cfg.get('project.name', 'RepoRanger').upper()}[/bold blue] | System Analysis Engine",
        border_style="blue"
    ))
    
    if args.command == 'branch':
        _handle_branch_creation(args)
        return

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
# COMMAND HANDLERS
# ========================================================================

def _handle_branch_creation(args):
    """Logic for smart branch creation and checkout"""
    console.print("[bold yellow]Mode: Smart Branch Creator[/bold yellow]")
    
    git_ops = GitOps(os.getcwd())
    manager = BranchManager(git_ops)
    
    console.print(f"Intent: [cyan]{args.intent}[/cyan]")
    
    with console.status("[dim]Analyzing intent and generating branch name...", spinner="dots"):
        try:
            branch_name, branch_type = manager.create_smart_branch(
                user_intent=args.intent,
                auto_detect_type=(args.type is None),
                suggested_type=args.type,
                create_initial_commit=(not args.no_commit)
            )
            
            output = [
                f"Branch Created: [cyan]{branch_name}[/cyan]",
                f"Branch Type:    [yellow]{branch_type}[/yellow]",
                "",
                "[bold]Next Steps:[/bold]",
                "1. git add .",
                "2. rr commit"
            ]
            
            console.print(Panel("\n".join(output), title="Success", border_style="green"))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

def _execute_commit_mode(args):
    """Directly calls the scribe agent for commit messages"""
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

def _execute_graph_mode(args, current_branch):
    """Runs pipeline and formats per-agent results"""
    initial_state = {
        "repo_path": os.getcwd(),
        "target_branch": args.target_branch,
        "source_branch": current_branch,
        "mode": args.mode,
        "artifacts": [], "messages": [], "code_issues": []
    }
    
    console.print("\n[bold]STARTING ANALYSIS PIPELINE[/bold]\n", style="dim")
    
    final_state = None
    with console.status("[dim]Processing pipeline nodes...", spinner="dots"):
        for event in app.stream(initial_state):
            node_name = list(event.keys())[0]
            final_state = event[node_name]
            _render_node_summary(node_name, final_state)
    
    if args.mode in ["pr", "full"]:
        _handle_pr_output(final_state, args.target_branch)
    
    console.print(f"\n[bold green]Pipeline execution finished successfully.[/bold green]")

# ========================================================================
# OUTPUT FORMATTERS
# ========================================================================

def _render_node_summary(node_name: str, state: dict):
    """Prints a clean, boxed summary of what each agent produced"""
    artifacts = state.get("artifacts", [])
    issues = state.get("code_issues", [])
    
    if not artifacts and not issues:
        return

    content = []
    
    # List Artifacts
    for art in artifacts:
        if art.get("created_by") == node_name:
            content.append(f"Artifact: [bold]{art['description']}[/bold]")
            content.append(f"Path:     [dim]{art['file_path']}[/dim]\n")

    # List Code Issues (for Steward)
    if node_name == "steward" and issues:
        content.append("[bold red]Analysis Findings:[/bold red]")
        for issue in issues[:5]:
            sev = issue.get('severity', 'info').upper()
            content.append(f"[{sev}] {issue['file']}: {issue['message']}")
        if len(issues) > 5:
            content.append(f"[dim]... and {len(issues)-5} more issues in full report.[/dim]")

    if content:
        console.print(Panel("\n".join(content).strip(), title=f"Agent: {node_name.capitalize()}", title_align="left", border_style="dim"))

def _handle_commit_output(state):
    artifacts = state.get("artifacts", [])
    if any(a.get("type") == "commit_msg" for a in artifacts):
        console.print(Panel(
            "Commit message ready.\n\n"
            "Review: [cyan]cat COMMIT_MESSAGE.txt[/cyan]\n"
            "Apply:  [cyan]git commit -F COMMIT_MESSAGE.txt[/cyan]",
            title="Success",
            border_style="green"
        ))
    else:
        console.print("[red]Error:[/red] No commit message generated.")

def _handle_pr_output(state, target_branch):
    """Final summary for PR creation"""
    actual_state = state.get('scribe', state) if isinstance(state, dict) else state
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    
    try:
        gh_user = subprocess.check_output(["gh", "api", "user", "-q", ".login"], text=True).strip()
    except:
        gh_user = "USER"

    suggested_title = actual_state.get("pr_title", f"Update: {current_branch}")

    output = [
        "[bold cyan]STEP 1: PUSH CHANGES[/bold cyan]",
        f"git push origin {current_branch}",
        "",
        "[bold cyan]STEP 2: CREATE PULL REQUEST[/bold cyan]",
        f"gh pr create --base {target_branch} --head {gh_user}:{current_branch} --title '{suggested_title}' --body-file PR_Document.md",
        "",
        "[dim]Note: If permissions fail, append --web to the gh command.[/dim]"
    ]
    
    console.print(Panel("\n".join(output), title="DEPLOYMENT STEPS", title_align="left", border_style="green", expand=False))

if __name__ == "__main__":
    main()