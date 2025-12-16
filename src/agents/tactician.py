"""
Git Tactician - Smart Git Operations Handler
"""
from langchain_core.messages import HumanMessage
from src.state import RepoState
from src.tools.gitops import GitOps
from src.utils.workspace import save_artifact
from src.utils.config import cfg


def tactician_node(state: RepoState) -> RepoState:
    """
    Handles Git operations intelligently:
    - Does NOT auto-create branches
    - Does NOT auto-commit
    - Provides clear instructions for user
    """
    print("--- ⚔️  Tactician: Preparing Git Operations ---")
    
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    git_ops = GitOps(repo_path)
    
    artifacts = state.get("artifacts", [])
    code_issues = state.get("code_issues", [])
    
    # Get current branch info
    current_branch = git_ops.get_current_branch()
    target_branch = state.get("target_branch", "main")
    
    # Determine what actions are recommended
    recommendations = []
    git_commands = []
    
    # 1. Check if PR documentation exists
    pr_docs = [a for a in artifacts if a.get("created_by") == "scribe"]
    has_pr_doc = len(pr_docs) > 0
    
    # 2. Check if there are critical issues
    critical_issues = [i for i in code_issues if i.get("severity") == "critical"]
    has_critical = len(critical_issues) > 0
    
    # 3. Check if we have refactor suggestions
    refactor_plans = [a for a in artifacts if a.get("type") == "refactor_plan"]
    has_refactors = len(refactor_plans) > 0
    
    # Build recommendations
    if has_critical:
        recommendations.append(
            "⚠️  **Critical issues detected** - Fix before pushing"
        )
    
    if has_refactors:
        recommendations.append(
            "💡 **Refactor suggestions available** - Review before committing"
        )
    
    # Generate git workflow
    if has_pr_doc:
        pr_path = pr_docs[0]["file_path"]
        
        recommendations.append(
            f"📄 **PR documentation generated**: `{pr_path}`"
        )
        
        # Suggest adding PR doc to commit
        git_commands.extend([
            f"# Add PR documentation to commit",
            f"cp {pr_path} PR_Document.md",
            f"git add PR_Document.md"
        ])
    
    # Standard git workflow
    if not has_critical:
        git_commands.extend([
            "",
            "# Standard workflow",
            "git add .",
            f"git commit -m 'docs: Update from RepoRanger analysis'",
            f"git push origin {current_branch}"
        ])
        
        if current_branch not in ["main", "master", target_branch]:
            git_commands.extend([
                "",
                "# Create PR (GitHub CLI)",
                f"gh pr create --base {target_branch} --title 'Your PR Title' --body-file PR_Document.md"
            ])
    
    # Generate instructions file
    instructions = _generate_instructions(
        current_branch=current_branch,
        target_branch=target_branch,
        recommendations=recommendations,
        git_commands=git_commands,
        artifacts=artifacts,
        has_critical=has_critical
    )
    
    instructions_path = save_artifact(instructions, "md")
    
    # Also print to console for immediate visibility
    print("\n" + "="*60)
    print("📋 NEXT STEPS")
    print("="*60)
    
    for rec in recommendations:
        print(f"  {rec}")
    
    if git_commands and not has_critical:
        print("\n💻 Suggested Commands:")
        for cmd in git_commands:
            if cmd and not cmd.startswith('#'):
                print(f"  $ {cmd}")
    
    print(f"\n📄 Full instructions: {instructions_path}")
    print("="*60 + "\n")
    
    print("--- ⚔️  Tactician: Ready ---\n")
    
    return {
        "artifacts": [{
            "id": "git_instructions",
            "type": "markdown_doc",
            "file_path": instructions_path,
            "description": "Git workflow instructions",
            "created_by": "tactician"
        }],
        "messages": [HumanMessage(
            content=f"Tactician prepared workflow instructions. "
                    f"{'⚠️ Address critical issues first.' if has_critical else '✅ Ready to commit.'}"
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
    """Generate detailed markdown instructions"""
    
    instructions = f"""# ⚔️ Git Workflow Instructions

**Current Branch:** `{current_branch}`  
**Target Branch:** `{target_branch}`  
**Generated:** {_get_timestamp()}

---

"""
    
    # Recommendations section
    if recommendations:
        instructions += "## 📋 Recommendations\n\n"
        for rec in recommendations:
            instructions += f"{rec}\n\n"
    
    # Critical blocker
    if has_critical:
        instructions += """## 🚨 CRITICAL ISSUES DETECTED

**Action Required:** Fix critical issues before pushing

Review the Steward report for details, then re-run RepoRanger:
```bash
# Fix issues, then re-run
python main.py --target-branch {target}
```

""".format(target=target_branch)
        return instructions
    
    # Git workflow
    if git_commands:
        instructions += "## 💻 Git Workflow\n\n"
        instructions += "```bash\n"
        for cmd in git_commands:
            instructions += f"{cmd}\n"
        instructions += "```\n\n"
    
    # Artifacts reference
    if artifacts:
        instructions += "## 📦 Generated Artifacts\n\n"
        for art in artifacts:
            instructions += f"- **{art['description']}**\n"
            instructions += f"  - Type: `{art['type']}`\n"
            instructions += f"  - Path: `{art['file_path']}`\n"
            instructions += f"  - Creator: `{art['created_by']}`\n\n"
    
    # Manual PR creation (GitHub web)
    instructions += """## 🌐 Create PR Manually (GitHub Web)

1. Push your branch:
```bash
   git push origin {current}
```

2. Go to GitHub and create PR from `{current}` → `{target}`

3. Copy content from `PR_Document.md` as PR description

""".format(current=current_branch, target=target_branch)
    
    return instructions


def _get_timestamp():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")