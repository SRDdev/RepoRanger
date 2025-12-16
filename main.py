# main.py - GitMentor Autonomous Code Steward
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
from rich.prompt import Prompt

console = Console()
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="GitMentor - Autonomous Code Steward",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gm branch -m "Refactor parser logic"
  gm full -m "Major version 1.0 release prep"
  gm pr --target master -m "Syncing refactored workspace"
  gm commit -m "Fix buffer overflow in auth"
  gm audit
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Helper to create consistent parsers for all modes
    def add_standard_subcommand(name, help_text):
        p = subparsers.add_parser(name, help=help_text)
        p.add_argument('--intent', '-m', help='Context or intent for the AI agents')
        # Added here so it works AFTER the command (e.g., gm pr --target master)
        p.add_argument("--target-branch", "--target", default="main", help="Base branch for comparison")
        return p

    # --- DEFINE COMMANDS ---
    add_standard_subcommand('full', 'Full analysis and AI README synchronization')
    add_standard_subcommand('audit', 'Deep quality and security audit')
    add_standard_subcommand('docs', 'Generate/update documentation based on code')
    add_standard_subcommand('pr', 'Analyze changes and prepare PR description')
    add_standard_subcommand('commit', 'Generate a Conventional Commit message')

    # --- BRANCH COMMAND (Unique logic) ---
    branch_parser = subparsers.add_parser('branch', help='Create semantic branch')
    branch_parser.add_argument('--intent', '-m', required=True, help='Branch purpose/intent')
    branch_parser.add_argument('--type', '-t', choices=[
        'feat', 'fix', 'hotfix', 'refactor', 'perf', 
        'docs', 'test', 'chore', 'style', 'ci', 'build'
    ], help='Override branch type')
    branch_parser.add_argument('--no-commit', action='store_true', help='Skip initial commit')

    args = parser.parse_args()

    # Fallback to help if no command provided
    if not args.command:
        parser.print_help()
        return

    # Header
    console.print(Panel(
        f"[bold blue]{cfg.get('project.name', 'GITMENTOR').upper()}[/bold blue] | {args.command.upper()} ENGINE",
        border_style="blue"
    ))

    # --- EXECUTION ROUTING ---
    
    # 1. Branch Mode (Special Case)
    if args.command == 'branch':
        _handle_branch_creation(args)
        return

    # Initialize Git Environment
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    
    # Extract target branch and intent safely from the subcommand args
    target_branch = getattr(args, 'target_branch', 'main')
    user_intent = getattr(args, 'intent', None)
    
    # Session Summary Table
    info_table = Table.grid(padding=(0, 2))
    info_table.add_column(style="dim")
    info_table.add_column()
    info_table.add_row("Active Branch:", f"[cyan]{current_branch}[/cyan]")
    info_table.add_row("Target Branch:", f"[cyan]{target_branch}[/cyan]")
    info_table.add_row("Intent:", f"[yellow]{user_intent or 'None provided'}[/yellow]")
    console.print(info_table)
    console.print(Rule(style="dim"))

    # 2. Commit Mode
    if args.command == "commit":
        _execute_commit_mode(args)
        return

    # 3. Graph Modes (Full, Audit, Docs, PR)
    _execute_graph_mode(args, current_branch, target_branch, user_intent)


# ========================================================================
# EXECUTION LOGIC
# ========================================================================

def _execute_graph_mode(args, current_branch, target_branch, user_intent):
    """Runs the multi-agent pipeline and formats results"""
    initial_state = {
        "repo_path": os.getcwd(),
        "target_branch": target_branch,
        "source_branch": current_branch,
        "mode": args.command, 
        "intent": user_intent,
        "artifacts": [], 
        "messages": [], 
        "code_issues": []
    }
    
    console.print(f"\n[bold]STARTING {args.command.upper()} PIPELINE[/bold]\n", style="dim")
    
    final_state = initial_state
    with console.status(f"[dim]Processing {args.command} nodes...", spinner="dots"):
        for event in app.stream(initial_state):
            node_name = list(event.keys())[0]
            final_state = event[node_name]
            _render_node_summary(node_name, final_state)
    
    # Post-Processing
    if args.command == "full":
        _update_readme_with_analysis(final_state)

    if args.command in ["pr", "full"]:
        _handle_pr_output(final_state, target_branch)
    
    console.print(f"\n[bold green]{args.command.capitalize()} pipeline finished successfully.[/bold green]")


def _execute_commit_mode(args):
    """Directly invokes Scribe for a commit message"""
    from src.agents.scribe import scribe_node
    console.print("[bold yellow]Mode: Commit Message Generation[/bold yellow]")
    
    intent = getattr(args, 'intent', None)
    if not intent:
        intent = Prompt.ask("Enter commit intent", default="General improvements")
    
    state = {
        "repo_path": os.getcwd(),
        "mode": "commit",
        "intent": intent,
        "artifacts": [], "messages": [], "code_issues": []
    }
    
    with console.status("[dim]Generating commit message...", spinner="dots"):
        result = scribe_node(state)
        _handle_commit_output(result)


# ========================================================================
# OUTPUT & UTILITY HANDLERS
# ========================================================================

def _update_readme_with_analysis(state):
    from src.agents.scribe import _generate_enhanced_readme
    from src.tools.gitops import GitOps
    
    console.print("    [blue]Agent Scribe: Reimagining README.md with AI...[/blue]")
    git_ops = GitOps(os.getcwd())
    new_readme_content = _generate_enhanced_readme(git_ops, state)
    
    if not new_readme_content:
        console.print("    [red]Error: AI failed to generate README content.[/red]")
        return

    try:
        if os.path.exists("README.md"):
            os.rename("README.md", "README.md.bak")
        with open("README.md", "w") as f:
            f.write(new_readme_content)
        console.print("    [green]Success: README.md synchronized.[/green]")
        if os.path.exists("README.md.bak"):
            os.remove("README.md.bak")
    except Exception as e:
        console.print(f"    [red]Error updating README: {e}[/red]")
        if os.path.exists("README.md.bak"):
            os.rename("README.md.bak", "README.md")


def _render_node_summary(node_name: str, state: dict):
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
        content.append("[bold red]Quality Audit Findings:[/bold red]")
        for issue in issues[:5]:
            sev = issue.get('severity', 'info').upper()
            content.append(f"  - [{sev}] {issue['file']}: {issue['message']}")

    if content:
        console.print(Panel("\n".join(content).strip(), title=f"Agent: {node_name.capitalize()}", border_style="dim"))


def _handle_branch_creation(args):
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
                f"Branch Created: [cyan]{branch_name}[/cyan]",
                f"Branch Type:    [yellow]{branch_type}[/yellow]",
                "",
                "[bold]Suggested Commands:[/bold]",
                "1. git add .",
                "2. gm commit"
            ]
            console.print(Panel("\n".join(summary), title="Success", border_style="green"))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def _handle_commit_output(state):
    artifacts = state.get("artifacts", [])
    if any(a.get("type") == "commit_msg" for a in artifacts):
        console.print(Panel(
            "Commit message saved to: [cyan]COMMIT_MESSAGE.txt[/cyan]\n"
            "Apply using: [bold]git commit -F COMMIT_MESSAGE.txt[/bold]",
            title="Success", border_style="green"
        ))


def _handle_pr_output(state, target_branch):
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    try:
        gh_user = subprocess.check_output(["gh", "api", "user", "-q", ".login"], text=True).strip()
    except:
        gh_user = "YOUR_GITHUB_USERNAME"

    output = [
        "[bold cyan]STEP 1: SYNC REMOTE[/bold cyan]",
        f"git push origin {current_branch}",
        "",
        "[bold cyan]STEP 2: OPEN PULL REQUEST[/bold cyan]",
        f"gh pr create --base {target_branch} --head {gh_user}:{current_branch} --body-file PR_Document.md"
    ]
    console.print(Panel("\n".join(output), title="DEPLOYMENT WORKFLOW", border_style="green"))


if __name__ == "__main__":
    main()