# src/agents/scribe.py - ENHANCED VERSION
from datetime import datetime
import textwrap
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import RepoState
from src.tools.gitops import GitOps
from src.utils.llm import get_llm
from src.utils.workspace import save_artifact
from src.utils.config import cfg


def scribe_node(state: RepoState) -> RepoState:
    """
    The Contextual Scribe generates:
    1. Commit messages (if in commit mode)
    2. PR documentation (if in PR mode)
    """
    print("--- ✍️  Scribe: Drafting Documentation ---")
    
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    target_branch = state.get("target_branch", "main")
    mode = state.get("mode", "pr")  # "pr" or "commit"
    
    git_ops = GitOps(repo_path)
    artifacts = []
    
    # MODE 1: Commit Message Generation
    if mode == "commit":
        artifacts = _generate_commit_message(git_ops, state)
    
    # MODE 2: PR Documentation Generation
    else:  # mode == "pr"
        artifacts = _generate_pr_documentation(git_ops, state, target_branch)
    
    print("--- ✍️  Scribe: Documentation Complete ---\n")
    
    return {
        "artifacts": artifacts,
        "messages": [HumanMessage(
            content=f"Scribe generated {len(artifacts)} documentation artifact(s)"
        )]
    }


# ============================================================================
# COMMIT MESSAGE GENERATION
# ============================================================================

# src/agents/scribe.py - FIX _generate_commit_message

def _generate_commit_message(git_ops: GitOps, state: RepoState) -> list:
    """Generate commit message for staged changes"""
    print("    Mode: Commit Message Generation")
    
    # Check for staged changes using GitOps
    if not git_ops.has_staged_changes():
        print("    ⚠️  No staged changes found")
        print("    💡 Hint: Use 'git add <files>' first")
        print("\n    To check what's modified:")
        print("      git status")
        return []
    
    # Get staged diff
    diff = git_ops.get_staged_diff()
    
    if not diff:
        print("    ⚠️  Could not retrieve staged diff")
        return []
    
    # Get changed files for context
    try:
        staged_files = git_ops.repo.git.diff("--cached", name_only=True).split('\n')
        staged_files = [f.strip() for f in staged_files if f.strip()]
        print(f"    📝 Analyzing {len(staged_files)} staged file(s):")
        for f in staged_files[:5]:  # Show first 5
            print(f"       • {f}")
        if len(staged_files) > 5:
            print(f"       ... and {len(staged_files) - 5} more")
    except:
        staged_files = []
    
    # Get code issues for context (if Steward ran)
    code_issues = state.get("code_issues", [])
    
    # Extract user intent
    user_intent = state.get("commit_intent", "General improvements")
    
    print("    🤖 Generating commit message with LLM...")
    
    # Generate commit message
    try:
        commit_msg = _generate_commit_with_llm(
            diff=diff,
            files=staged_files,
            user_intent=user_intent,
            code_issues=code_issues
        )
    except Exception as e:
        print(f"    ❌ Error generating commit message: {e}")
        return []
    
    # Save to workspace
    commit_path = save_artifact(commit_msg, "txt")
    
    # Also save as COMMIT_MESSAGE.txt in root
    try:
        with open("COMMIT_MESSAGE.txt", "w") as f:
            f.write(commit_msg)
        print("    ✅ Saved to: COMMIT_MESSAGE.txt")
    except Exception as e:
        print(f"    ⚠️  Could not save to root: {e}")
    
    return [{
        "id": "commit_message",
        "type": "commit_msg",
        "file_path": commit_path,
        "description": "Generated commit message",
        "created_by": "scribe"
    }]

def _generate_commit_with_llm(diff: str, files: list, user_intent: str, code_issues: list) -> str:
    """Generate commit message using LLM"""
    
    llm = get_llm("creative")
    
    # Truncate diff if too large (keep first 3000 chars)
    if len(diff) > 3000:
        diff = diff[:3000] + "\n... [truncated]"
    
    # Format code issues
    issues_context = ""
    if code_issues:
        critical = [i for i in code_issues if i.get("severity") == "critical"]
        warnings = [i for i in code_issues if i.get("severity") == "warning"]
        
        if critical or warnings:
            issues_context = "\n\nCode Quality Context:\n"
            if critical:
                issues_context += f"- {len(critical)} critical issues addressed\n"
            if warnings:
                issues_context += f"- {len(warnings)} warnings resolved\n"
    
    # Format files
    files_list = "\n".join(f"  - {f}" for f in files[:10])
    if len(files) > 10:
        files_list += f"\n  ... and {len(files) - 10} more"
    
    prompt = textwrap.dedent(f"""
    You are a senior engineer writing a **professional commit message**.
    
    **Developer Intent:**
    {user_intent}
    
    **Changed Files:**
    {files_list}
    {issues_context}
    
    **Git Diff:**{diff}
    
    **Requirements:**
    1. Use Conventional Commits format: `type(scope): subject`
       - Types: feat, fix, refactor, chore, docs, style, test, perf
       - Example: `feat(auth): add OAuth2 support`
    
    2. Subject line (first line):
       - Max 72 characters
       - Imperative mood ("add" not "added")
       - No period at end
    
    3. Body (optional, separate with blank line):
       - Explain WHAT changed and WHY
       - Wrap at 72 characters
       - Use bullet points for multiple changes
    
    4. DO NOT include:
       - File lists (already visible in git)
       - Raw diff content
       - Reviewer names
    
    **Output Format:**
    Just return the commit message directly (no markdown backticks, no "Here's the commit message", etc.)
    
    Example:feat(parser): add support for TypeScript parsing- Implement AST traversal for TS syntax
- Add type annotation extraction
- Handle generic types and interfacesThis enables full TypeScript codebase analysis for the Steward agent.
Closes #42
    """)
    
    response = llm.invoke([
        SystemMessage(content="You are a senior software engineer writing commit messages."),
        HumanMessage(content=prompt)
    ])
    
    # Clean up response (remove markdown if present)
    commit_text = response.content.strip()
    
    # Remove markdown code blocks if LLM added them
    if commit_text.startswith("```"):
        lines = commit_text.split('\n')
        commit_text = '\n'.join(lines[1:-1])
    
    return commit_text.strip()


# ============================================================================
# PR DOCUMENTATION GENERATION (Your existing logic)
# ============================================================================

def _generate_pr_documentation(git_ops: GitOps, state: RepoState, target_branch: str) -> list:
    """Generate PR documentation for branch (your existing PR generator logic)"""
    print("    Mode: PR Documentation Generation")
    
    # Get commits since target branch
    commits, actual_target = _get_commits_since(git_ops, target_branch)
    
    if not commits:
        print("    ⚠️  No commits found")
        return []
    
    print(f"    Found {len(commits)} commits")
    
    # Extract commit details
    commits_data = [_get_commit_details(git_ops, c) for c in commits]
    
    # Get context from other agents
    code_issues = state.get("code_issues", [])
    artifacts = state.get("artifacts", [])
    source_branch = git_ops.get_current_branch()
    
    # Generate PR document
    pr_text = _generate_pr_with_llm(
        commits_data=commits_data,
        source_branch=source_branch,
        target_branch=target_branch,
        code_issues=code_issues,
        artifacts=artifacts
    )
    
    # Save artifact
    pr_path = save_artifact(pr_text, "md")
    
    # Also save as PR_Document.md in root
    try:
        with open("PR_Document.md", "w") as f:
            f.write(pr_text)
        print("    ✓ Saved to: PR_Document.md")
    except:
        pass
    
    return [{
        "id": "pr_document",
        "type": "markdown_doc",
        "file_path": pr_path,
        "description": f"PR Documentation ({len(commits)} commits)",
        "created_by": "scribe"
    }]


def _get_commits_since(git_ops: GitOps, base_branch: str):
    """Get commits in current branch not in base branch"""
    try:
        # Try local branch first
        if _branch_exists(git_ops, base_branch):
            target = base_branch
        elif _branch_exists(git_ops, f"origin/{base_branch}"):
            target = f"origin/{base_branch}"
        else:
            return [], base_branch
        
        commits = git_ops.repo.git.log(
            f"{target}..HEAD", 
            pretty="format:%H"
        ).splitlines()
        
        return commits, target
    except:
        return [], base_branch


def _branch_exists(git_ops: GitOps, branch: str) -> bool:
    """Check if branch exists"""
    try:
        git_ops.repo.git.rev_parse("--verify", branch)
        return True
    except:
        return False


def _get_commit_details(git_ops: GitOps, commit_hash: str) -> dict:
    """Extract commit metadata"""
    repo = git_ops.repo
    commit = repo.commit(commit_hash)
    
    # Get diff stats
    stats = repo.git.show("--stat", commit_hash, "--oneline")
    
    # Get diff preview (first 15 lines)
    preview = repo.git.show(commit_hash, color="never")
    preview_lines = preview.split('\n')[5:20]
    
    return {
        "hash": commit.hexsha[:7],
        "author": commit.author.name,
        "date": commit.authored_datetime.strftime("%Y-%m-%d %H:%M"),
        "subject": commit.message.split('\n')[0],
        "stats": stats,
        "preview": '\n'.join(preview_lines)
    }


def _generate_pr_with_llm(commits_data, source_branch, target_branch, code_issues, artifacts):
    """Generate PR documentation using LLM"""
    
    llm = get_llm("creative")
    
    # Format commits
    commits_text = ""
    for c in commits_data:
        commits_text += textwrap.dedent(f"""
        Commit: {c['hash']} — {c['subject']}
        Author: {c['author']}
        Date: {c['date']}
        
        Changed Files:
        {c['stats']}
        
        Diff Snippet:
        {c['preview']}
        """)
    
    # Add code quality findings
    issues_section = ""
    if code_issues:
        critical = [i for i in code_issues if i.get("severity") == "critical"]
        warnings = [i for i in code_issues if i.get("severity") == "warning"]
        
        if critical or warnings:
            issues_section = "\n\n## Code Quality Analysis\n"
            if critical:
                issues_section += f"- ⚠️ {len(critical)} critical issues detected\n"
            if warnings:
                issues_section += f"- 💡 {len(warnings)} improvement suggestions\n"
    
    # Add architecture diagrams
    diagrams_section = ""
    diagram_artifacts = [a for a in artifacts if a.get("type") == "diagram"]
    if diagram_artifacts:
        diagrams_section = "\n\n## Architecture Artifacts\n"
        for diag in diagram_artifacts:
            diagrams_section += f"- [{diag['description']}]({diag['file_path']})\n"
    
    prompt = textwrap.dedent(f"""
    You are a **Principal Software Engineer** writing executive-level Pull Request documentation.
    
    **Context:**
    - Source Branch: `{source_branch}`
    - Target Branch: `{target_branch}`
    - Total Commits: {len(commits_data)}
    
    **Commits:**
    {commits_text}
    
    {issues_section}
    {diagrams_section}
    
    **Instructions:**
    Write a comprehensive PR description in Markdown for senior engineers and tech leads.
    
    Structure:
    1. **Overview** (2-3 sentences)
       - What changed and why
       - Business/technical motivation
    
    2. **Key Changes** (bullet points)
       - Major modifications with file references
       - New features or fixes
    
    3. **Technical Details** (if complex)
       - Architecture decisions
       - Implementation approach
    
    4. **Code Quality** (if issues found)
       - Automated analysis findings
       - Recommendations
    
    5. **Testing** (brief)
       - What needs testing
       - Any breaking changes
    
    6. **Reviewer Checklist**
       - Key areas to review
       - Potential concerns
    
    **Style:**
    - Professional but concise
    - Use bullet points for clarity
    - Reference files with backticks: `src/agents/scribe.py`
    - Use emojis sparingly (✅ ⚠️ 💡)
    """)
    
    response = llm.invoke([
        SystemMessage(content="You are a senior engineer writing PR documentation."),
        HumanMessage(content=prompt)
    ])
    
    # Add header
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = textwrap.dedent(f"""
    # 🚀 Pull Request Documentation
    
    **Generated:** {now}  
    **From:** `{source_branch}`  
    **Into:** `{target_branch}`  
    **Commits:** {len(commits_data)}
    
    ---
    
    """)
    
    return header + response.content