#!/usr/bin/env python3
"""
GitMentor CLI - Professional Version
Extended with History Tracking, AI Explanation, and Commit Documentation
"""
import click
import subprocess
import os
from rich.console import Console
from rich.panel import Panel

console = Console()

@click.group()
def cli():
    """🚀 GitMentor - Your Autonomous Code Steward"""
    pass


# ============================================================================
# CORE PIPELINE COMMANDS
# ============================================================================

@cli.command()
@click.option('--intent', '-m', help='Commit intent/rationale for the AI')
def commit(intent):
    """Generate Conventional Commit + detailed tracking documentation"""
    # Check for staged changes first
    result = subprocess.run(
        ['git', 'diff', '--cached', '--quiet'],
        capture_output=True
    )
    
    if result.returncode == 0:
        console.print("[red]❌ No staged changes found[/red]")
        console.print("[yellow]Hint: Use 'git add <files>' to stage changes first[/yellow]")
        return
    
    # Pass to main.py logic
    cmd = ['python', 'main.py', 'commit']
    if intent:
        cmd.extend(['--intent', intent])
    
    subprocess.run(cmd)


@cli.command()
@click.option('--target', '-t', default='main', help='Base branch for the PR')
@click.option('--intent', '-m', help='PR overarching intent')
def pr(target, intent):
    """Generate high-quality PR documentation using commit tracking history"""
    cmd = ['python', 'main.py', 'pr', '--target-branch', target]
    if intent:
        cmd.extend(['--intent', intent])
    subprocess.run(cmd)


@cli.command()
def docs():
    """Generate technical 'System Blueprint' documentation (CODE_DOCS.md)"""
    subprocess.run(['python', 'main.py', 'docs'])


@cli.command()
@click.option('--target', '-t', default='main', help='Comparison branch')
def audit(target):
    """Run professional quality and security audit (Steward)"""
    subprocess.run(['python', 'main.py', 'audit', '--target-branch', target])


@cli.command()
@click.option('--target', '-t', default='main', help='Comparison branch')
@click.option('--intent', '-m', help='Release/Project intent')
def full(target, intent):
    """Run full analysis swarm and sync README with codebase reality"""
    cmd = ['python', 'main.py', 'full', '--target-branch', target]
    if intent:
        cmd.extend(['--intent', intent])
    subprocess.run(cmd)


@cli.command()
@click.option('--intent', '-m', prompt='What is the purpose of this branch?', help='Branch purpose/intent')
@click.option('--type', '-t', type=click.Choice([
    'feat', 'fix', 'hotfix', 'refactor', 'perf', 
    'docs', 'test', 'chore', 'style', 'ci', 'build'
]), help='Explicitly set branch type')
@click.option('--no-commit', is_flag=True, help='Skip the initial semantic commit')
def branch(intent, type, no_commit):
    """Create a semantically named branch based on intent"""
    # Using python directly to leverage the BranchManager tool
    from src.tools.gitops import GitOps
    from src.tools.branch_manager import BranchManager
    
    console.print(Panel("🌿 [bold green]GitMentor: Smart Branch Creator[/bold green]", border_style="green"))
    
    git_ops = GitOps(os.getcwd())
    manager = BranchManager(git_ops)
    
    with console.status("[bold yellow]AI is determining branch strategy...[/bold yellow]"):
        try:
            branch_name, branch_type = manager.create_smart_branch(
                user_intent=intent,
                auto_detect_type=(type is None),
                suggested_type=type,
                create_initial_commit=(not no_commit)
            )
            
            console.print(Panel(
                f"[bold green]✅ Branch Ready![/bold green]\n\n"
                f"🌿 Branch: [cyan]{branch_name}[/cyan]\n"
                f"🏷️  Type: [yellow]{branch_type}[/yellow]\n\n"
                f"Next steps:\n"
                f"  [dim]1. Write code changes[/dim]\n"
                f"  [dim]2. git add .[/dim]\n"
                f"  [dim]3. gm commit[/dim]",
                border_style="green",
                title="Success"
            ))
        except Exception as e:
            console.print(f"[red]❌ Error creating branch: {e}[/red]")


# ============================================================================
# INTELLIGENCE & DISCOVERY COMMANDS
# ============================================================================

@cli.command(name='search-history')
@click.argument('query', nargs=-1, required=True)
def search_history(query):
    """Search git history for specific logic or variable evolutions"""
    query_text = ' '.join(query)
    # Forward to main.py routing
    subprocess.run(['python', 'main.py', 'search-history'] + list(query))


@cli.command()
@click.argument('name')
@click.option('--level', '-l', 
              type=click.Choice(['beginner', 'medium', 'hard']), 
              default='medium',
              help='Explanation depth')
@click.option('--file', '-f', help='Target specific file')
@click.option('--type', '-t', 
              type=click.Choice(['function', 'class', 'auto']),
              default='auto')
def explain(name, level, file, type):
    """Get a high-level or deep-dive AI explanation of code"""
    cmd = ['python', 'main.py', 'explain', name, '--level', level, '--type', type]
    if file:
        cmd.extend(['--file', file])
    subprocess.run(cmd)


@cli.command()
@click.argument('query', nargs=-1, required=True)
def where(query):
    """Find code locations using natural language queries"""
    subprocess.run(['python', 'main.py', 'where'] + list(query))


if __name__ == '__main__':
    cli()