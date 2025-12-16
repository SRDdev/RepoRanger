# main.py - RepoRanger Autonomous Code Steward
import os
import argparse
import subprocess
from dotenv import load_dotenv

from src.graph import app
from src.utils.config import cfg
from src.tools.gitops import GitOps

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

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
  
  # Generate commit message
  python main.py --mode commit
  
  # Generate PR documentation
  python main.py --mode pr --target-branch main
        """
    )
    
    # Subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # --- BRANCH COMMAND ---
    branch_parser = subparsers.add_parser('branch', help='Create smart branch')
    branch_parser.add_argument('--intent', '-m', required=True, help='Branch purpose/intent')
    branch_parser.add_argument('--type', '-t', choices=[
        'feat', 'fix', 'hotfix', 'refactor', 'perf', 
        'docs', 'test', 'chore', 'style', 'ci', 'build'
    ], help='Branch type (auto-detected if not specified)')
    branch_parser.add_argument('--no-commit', action='store_true', help='Skip initial commit')

    # --- GLOBAL ARGUMENTS ---
    parser.add_argument(
        "--target-branch",
        default="main",
        help="Branch to compare against (for PR/full modes)"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "pr", "commit", "audit"],
        default="full",
        help="Execution mode"
    )
    parser.add_argument(
        "--commit-intent",
        help="Your intent for the commit (used with --mode commit)"
    )
    
    args = parser.parse_args()
    
    # Banner
    console.print(Panel(
        f"🚀 [bold green]{cfg.get('project.name', 'RepoRanger')}[/bold green] - Autonomous Code Steward",
        border_style="green"
    ))
    
    # 1. Handle Branch Creation Command
    if args.command == 'branch':
        _handle_branch_creation(args)
        return

    # 2. Setup Git Context for Analysis Modes
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    console.print(f"📍 Current Branch: [cyan]{current_branch}[/cyan]")
    
    # 3. Handle Commit Mode (Direct Node Execution)
    if args.mode == "commit":
        _execute_commit_mode(args)
        return

    # 4. Handle Analysis Modes (Graph Execution)
    _execute_graph_mode(args, current_branch)


# ========================================================================
# COMMAND HANDLERS
# ========================================================================

def _handle_branch_creation(args):
    """Logic for smart branch creation and checkout"""
    from src.tools.branch_manager import BranchManager
    
    console.print(Panel("🌿 [bold green]Smart Branch Creator[/bold green]", border_style="green"))
    
    git_ops = GitOps(os.getcwd())
    manager = BranchManager(git_ops)
    
    console.print(f"\n💭 Intent: [cyan]{args.intent}[/cyan]")
    if not args.type:
        console.print("🤖 Detecting branch type...")

    with console.status("[bold yellow]Generating branch name...[/bold yellow]"):
        try:
            branch_name, branch_type = manager.create_smart_branch(
                user_intent=args.intent,
                auto_detect_type=(args.type is None),
                suggested_type=args.type,
                create_initial_commit=(not args.no_commit)
            )
            
            console.print(Panel(
                f"[bold green]✅ Branch created and checked out![/bold green]\n\n"
                f"🌿 Branch: [cyan]{branch_name}[/cyan]\n"
                f"🏷️  Type: [yellow]{branch_type}[/yellow]\n\n"
                f"Usage:\n"
                f"  [dim]git add .[/dim]\n"
                f"  [dim]python main.py --mode commit[/dim]",
                border_style="green",
                title="🎉 Success"
            ))
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")


def _execute_commit_mode(args):
    """Directly calls the scribe agent for commit messages"""
    from src.agents.scribe import scribe_node
    
    console.print(f"🎯 Mode: [yellow]Commit Message Generation[/yellow]\n")
    intent = args.commit_intent or Prompt.ask("🧠 Commit intent?", default="General improvements")
    
    state = {
        "repo_path": os.getcwd(),
        "mode": "commit",
        "commit_intent": intent,
        "artifacts": [], "messages": [], "code_issues": []
    }
    
    console.print("[bold yellow]Generating message...[/bold yellow]\n")
    result = scribe_node(state)
    _handle_commit_output(result)
    console.print("\n[bold green]✓ Execution complete![/bold green]")


def _execute_graph_mode(args, current_branch):
    """Runs the LangGraph pipeline for audit/pr/full modes"""
    initial_state = {
        "repo_path": os.getcwd(),
        "target_branch": args.target_branch,
        "source_branch": current_branch,
        "mode": args.mode,
        "artifacts": [], "messages": [], "code_issues": []
    }
    
    console.print(f"🎯 Mode: [yellow]{args.mode.upper()}[/yellow]")
    console.print(f"🎯 Target: [cyan]{args.target_branch}[/cyan]\n")
    console.print("[bold yellow]Running Analysis Pipeline...[/bold yellow]\n")
    
    final_state = None
    for event in app.stream(initial_state):
        final_state = event
    
    if args.mode == "pr" and final_state:
        _handle_pr_output(final_state, args.target_branch)
    
    console.print("\n[bold green]✓ Execution complete![/bold green]")


# ========================================================================
# OUTPUT FORMATTERS
# ========================================================================

def _handle_commit_output(state):
    artifacts = state.get("artifacts", [])
    if any(a.get("type") == "commit_msg" for a in artifacts) and os.path.exists("COMMIT_MESSAGE.txt"):
        console.print(Panel(
            "✨ [bold green]Commit message ready![/bold green]\n\n"
            "Review: [cyan]cat COMMIT_MESSAGE.txt[/cyan]\n"
            "Apply:  [cyan]git commit -F COMMIT_MESSAGE.txt[/cyan]",
            border_style="green"
        ))
    else:
        console.print("[yellow]⚠️  No commit message generated.[/yellow]")


def _handle_pr_output(state, target_branch):
    """Dynamic PR command output with fork-safety"""
    actual_state = state.get('scribe', state) if isinstance(state, dict) else state
    
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    
    # Try to get GitHub username for fork-safe commands
    try:
        gh_user = subprocess.check_output(["gh", "api", "user", "-q", ".login"], text=True).strip()
    except:
        gh_user = "YOUR_USERNAME"

    suggested_title = actual_state.get("pr_title", f"PR: {current_branch}")

    console.print(Panel(
        f"[bold green]✅ PR documentation generated![/bold green]\n\n"
        f"[bold white]1. Push changes:[/bold white]\n"
        f"   [cyan]git push origin {current_branch}[/cyan]\n\n"
        f"[bold white]2. Create Pull Request:[/bold white]\n"
        f"   [cyan]gh pr create --base {target_branch} --head {current_branch} --title '{suggested_title}' --body-file PR_Document.md[/cyan]\n\n"
        f"[yellow]💡 Note:[/yellow] If this is a fork and you lack permissions, use:\n"
        f"[dim]gh pr create --base {target_branch} --head {gh_user}:{current_branch} ...[/dim]",
        border_style="green",
        title="PR Ready"
    ))


if __name__ == "__main__":
    main()