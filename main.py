# main.py - COMPLETE WORKING VERSION WITH BRANCH SUBCOMMAND
import os
import argparse
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
  
  # Specify branch type
  python main.py branch --intent "Fix login bug" --type fix
  
  # Generate commit message
  python main.py --mode commit
  
  # Generate PR documentation
  python main.py --mode pr --target-branch main
        """
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # --- BRANCH SUBCOMMAND ---
    branch_parser = subparsers.add_parser('branch', help='Create smart branch')
    branch_parser.add_argument('--intent', '-m', required=True, help='Branch purpose/intent')
    branch_parser.add_argument('--type', '-t', choices=[
        'feat', 'fix', 'hotfix', 'refactor', 'perf', 
        'docs', 'test', 'chore', 'style', 'ci', 'build'
    ], help='Branch type (auto-detected if not specified)')
    branch_parser.add_argument('--no-commit', action='store_true', help='Skip initial commit')

    # --- GLOBAL ARGUMENTS (For backward compatibility/Standard modes) ---
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
        f"🚀 [bold green]{cfg.get('project.name')}[/bold green] - Autonomous Code Steward",
        border_style="green"
    ))
    
    # ========================================================================
    # BRANCH COMMAND
    # ========================================================================
    if args.command == 'branch':
        _handle_branch_creation(args)
        return

    # ========================================================================
    # STANDARD MODES (Existing Logic)
    # ========================================================================
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    
    console.print(f"📍 Current Branch: [cyan]{current_branch}[/cyan]")
    
    # COMMIT MODE
    if args.mode == "commit":
        console.print(f"🎯 Mode: [yellow]Commit Message Generation[/yellow]\n")
        
        if not args.commit_intent:
            commit_intent = Prompt.ask(
                "🧠 What is the main purpose of this commit?",
                default="General improvements"
            )
        else:
            commit_intent = args.commit_intent
        
        from src.agents.scribe import scribe_node
        
        state = {
            "repo_path": os.getcwd(),
            "mode": "commit",
            "commit_intent": commit_intent,
            "artifacts": [],
            "messages": [],
            "code_issues": []
        }
        
        console.print("[bold yellow]Generating commit message...[/bold yellow]\n")
        result = scribe_node(state)
        _handle_commit_output(result)
        
        console.print("\n[bold green]✓ RepoRanger execution complete![/bold green]")
        return
    
    # SETUP INITIAL STATE FOR GRAPH MODES
    if args.mode == "pr":
        console.print(f"🎯 Mode: [yellow]PR Documentation[/yellow]")
        console.print(f"🎯 Target Branch: [cyan]{args.target_branch}[/cyan]\n")
        
        initial_state = {
            "repo_path": os.getcwd(),
            "target_branch": args.target_branch,
            "source_branch": current_branch,
            "mode": "pr",
            "artifacts": [],
            "messages": [],
            "code_issues": []
        }
    
    elif args.mode == "audit":
        console.print(f"🎯 Mode: [yellow]Code Quality Audit[/yellow]\n")
        
        initial_state = {
            "repo_path": os.getcwd(),
            "target_branch": args.target_branch,
            "mode": "audit",
            "artifacts": [],
            "messages": [],
            "code_issues": []
        }
    
    else:  # full mode
        console.print(f"🎯 Mode: [yellow]Full Analysis[/yellow]")
        console.print(f"🎯 Target Branch: [cyan]{args.target_branch}[/cyan]\n")
        
        initial_state = {
            "repo_path": os.getcwd(),
            "target_branch": args.target_branch,
            "source_branch": current_branch,
            "mode": "full",
            "artifacts": [],
            "messages": [],
            "code_issues": []
        }
    
    # Run the graph
    console.print("[bold yellow]Running Analysis Pipeline...[/bold yellow]\n")
    
    final_state = None
    for event in app.stream(initial_state):
        final_state = event
    
    # Post-processing
    if args.mode == "pr" and final_state:
        # Note: final_state is usually the last event dict from app.stream
        # You may need to extract the actual state depending on your graph implementation
        _handle_pr_output(final_state, args.target_branch)
    
    console.print("\n[bold green]✓ RepoRanger execution complete![/bold green]")


def _handle_branch_creation(args):
    """Handle smart branch creation"""
    from src.tools.gitops import GitOps
    from src.tools.branch_manager import BranchManager
    
    console.print(Panel(
        "🌿 [bold green]Smart Branch Creator[/bold green]",
        border_style="green"
    ))
    
    git_ops = GitOps(os.getcwd())
    manager = BranchManager(git_ops)
    
    console.print(f"\n💭 Intent: [cyan]{args.intent}[/cyan]")
    
    if args.type:
        console.print(f"🏷️  Type: [yellow]{args.type}[/yellow] (specified)")
    else:
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
                f"You can now start working on your changes.\n"
                f"When ready to commit:\n"
                f"  [dim]git add .[/dim]\n"
                f"  [dim]python main.py --mode commit[/dim]",
                border_style="green",
                title="🎉 Success"
            ))
        
        except Exception as e:
            console.print(f"[red]❌ Error creating branch: {e}[/red]")


def _handle_commit_output(state):
    """Handle commit mode output"""
    artifacts = state.get("artifacts", [])
    commit_artifact = next(
        (a for a in artifacts if a.get("type") == "commit_msg"),
        None
    )
    
    if commit_artifact:
        if os.path.exists("COMMIT_MESSAGE.txt"):
            console.print(Panel(
                "[bold green]✅ Commit message generated![/bold green]\n\n"
                "📄 Review the message:\n"
                "  [cyan]cat COMMIT_MESSAGE.txt[/cyan]\n\n"
                "✨ Use it to commit:\n"
                "  [cyan]git commit -F COMMIT_MESSAGE.txt[/cyan]\n\n"
                "📝 Or edit before committing:\n"
                "  [cyan]git commit -e -F COMMIT_MESSAGE.txt[/cyan]",
                border_style="green",
                title="✅ Commit Message Ready"
            ))
        else:
            console.print("[yellow]⚠️  Commit message generated but file not found[/yellow]")
    else:
        console.print("\n[yellow]⚠️  No commit message generated[/yellow]")


def _handle_pr_output(state, target_branch):
    """Handle PR mode output"""
    # Depending on graph output structure, extract state
    actual_state = state.get('scribe', state) if isinstance(state, dict) else state
    artifacts = actual_state.get("artifacts", [])
    
    pr_artifact = next(
        (a for a in artifacts if a.get("id") == "pr_document"),
        None
    )
    
    if pr_artifact and os.path.exists("PR_Document.md"):
        console.print(Panel(
            "[bold green]✅ PR documentation generated![/bold green]\n\n"
            "Next steps:\n"
            "  1. Review: [cyan]cat PR_Document.md[/cyan]\n"
            "  2. Push: [cyan]git push origin $(git branch --show-current)[/cyan]\n"
            f"  3. Create PR on GitHub: current → [cyan]{target_branch}[/cyan]",
            border_style="green",
            title="PR Documentation Ready"
        ))


if __name__ == "__main__":
    main()