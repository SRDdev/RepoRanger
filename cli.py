# cli.py
#!/usr/bin/env python3
"""
RepoRanger CLI - Friendly Git-aware interface
"""
import click
import subprocess
import os
from rich.console import Console

console = Console()

@click.group()
def cli():
    """RepoRanger - Your Autonomous Code Steward"""
    pass


@cli.command()
@click.option('--intent', '-m', help='Commit intent/message')
def commit(intent):
    """Generate commit message for staged changes"""
    
    # Check for staged changes
    result = subprocess.run(
        ['git', 'diff', '--cached', '--quiet'],
        capture_output=True
    )
    
    if result.returncode == 0:
        console.print("[red]❌ No staged changes found[/red]")
        console.print("[yellow]Hint: Use 'git add <files>' first[/yellow]")
        return
    
    # Build command
    cmd = ['python', 'main.py', '--mode', 'commit']
    if intent:
        cmd.extend(['--commit-intent', intent])
    
    subprocess.run(cmd)


@cli.command()
@click.option('--target', '-t', default='main', help='Target branch')
def pr(target):
    """Generate PR documentation"""
    subprocess.run([
        'python', 'main.py',
        '--mode', 'pr',
        '--target-branch', target
    ])


@cli.command()
@click.option('--target', '-t', default='main', help='Target branch')
def audit(target):
    """Run code quality audit"""
    subprocess.run([
        'python', 'main.py',
        '--mode', 'audit',
        '--target-branch', target
    ])


@cli.command()
@click.option('--intent', '-m', prompt='What do you want to work on?', help='Branch purpose/intent')
@click.option('--type', '-t', type=click.Choice([
    'feat', 'fix', 'hotfix', 'refactor', 'perf', 
    'docs', 'test', 'chore', 'style', 'ci', 'build'
]), help='Branch type (auto-detected if not specified)')
@click.option('--no-commit', is_flag=True, help='Skip initial commit')
def branch(intent, type, no_commit):
    """Create a smart branch with AI-generated name"""
    from src.tools.gitops import GitOps
    from src.tools.branch_manager import BranchManager
    from rich.panel import Panel
    
    console.print(Panel(
        "🌿 [bold green]Smart Branch Creator[/bold green]",
        border_style="green"
    ))
    
    git_ops = GitOps(os.getcwd())
    manager = BranchManager(git_ops)
    
    console.print(f"\n💭 Intent: [cyan]{intent}[/cyan]")
    
    if type:
        console.print(f"🏷️  Type: [yellow]{type}[/yellow] (specified)")
    else:
        console.print("🤖 Detecting branch type...")
    
    # Create branch
    with console.status("[bold yellow]Generating branch name...[/bold yellow]"):
        branch_name, branch_type = manager.create_smart_branch(
            user_intent=intent,
            auto_detect_type=(type is None),
            suggested_type=type,
            create_initial_commit=(not no_commit)
        )
    
    console.print(Panel(
        f"[bold green]✅ Branch created and checked out![/bold green]\n\n"
        f"🌿 Branch: [cyan]{branch_name}[/cyan]\n"
        f"🏷️  Type: [yellow]{branch_type}[/yellow]\n\n"
        f"You can now start working on your changes.\n"
        f"When ready to commit:\n"
        f"  [dim]git add .[/dim]\n"
        f"  [dim]rr commit[/dim]",
        border_style="green",
        title="🎉 Success"
    ))

if __name__ == '__main__':
    cli()
