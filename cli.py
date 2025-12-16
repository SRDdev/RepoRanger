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


if __name__ == '__main__':
    cli()