# main.py - COMPLETE WORKING VERSION
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
  # Generate commit message
  python main.py --mode commit
  
  # Generate PR documentation
  python main.py --mode pr --target-branch main
  
  # Code quality audit only
  python main.py --mode audit
  
  # Full analysis
  python main.py --mode full --target-branch main
        """
    )
    
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
    
    # Get current branch
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    
    console.print(f"📍 Current Branch: [cyan]{current_branch}[/cyan]")
    
    # ========================================================================
    # COMMIT MODE - Direct execution (bypass graph)
    # ========================================================================
    if args.mode == "commit":
        console.print(f"🎯 Mode: [yellow]Commit Message Generation[/yellow]\n")
        
        # Ask for intent if not provided
        if not args.commit_intent:
            commit_intent = Prompt.ask(
                "🧠 What is the main purpose of this commit?",
                default="General improvements"
            )
        else:
            commit_intent = args.commit_intent
        
        # Direct call to scribe (no graph complexity needed)
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
    
    # ========================================================================
    # ALL OTHER MODES - Use graph
    # ========================================================================
    
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
        _handle_pr_output(final_state, args.target_branch)
    
    console.print("\n[bold green]✓ RepoRanger execution complete![/bold green]")


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
            console.print(f"[dim]Check: {commit_artifact['file_path']}[/dim]")
    else:
        console.print("\n[yellow]⚠️  No commit message generated[/yellow]")
        console.print("[dim]Hint: Make sure you have staged changes:[/dim]")
        console.print("[dim]  git add <files>[/dim]")


def _handle_pr_output(state, target_branch):
    """Handle PR mode output"""
    artifacts = state.get("artifacts", [])
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