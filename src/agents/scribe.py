# src/agents/scribe.py - PROFESSIONAL VERSION WITH COMMIT TRACKING
import os
import json
import textwrap
import re
from pathlib import Path
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import RepoState
from src.tools.gitops import GitOps
from src.utils.llm import get_llm
from src.utils.workspace import save_artifact
from src.utils.config import cfg
from rich.console import Console

console = Console()

# Constants
COMMIT_DOCS_DIR = ".gitworkspace/commit_docs"
COMMIT_INDEX_FILE = ".gitworkspace/commit_index.json"

def scribe_node(state: RepoState) -> RepoState:
    """
    The Contextual Scribe generates:
    1. Commit messages (if in commit mode) + stores commit documentation
    2. System Documentation (if in docs mode)
    3. PR documentation (if in pr or full mode) + reads all commit docs
    """
    console.print("[bold blue]--- Scribe: Drafting Documentation ---[/bold blue]")
    
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    target_branch = state.get("target_branch", "main")
    mode = state.get("mode", "pr")
    
    git_ops = GitOps(repo_path)
    artifacts = []
    
    # Ensure commit docs directory exists
    _ensure_commit_docs_dir(repo_path)
    
    if mode == "commit":
        artifacts = _generate_commit_message(git_ops, state)
    elif mode == "docs":
        artifacts = _generate_system_documentation(git_ops, state)
    elif mode == "pr":
        artifacts = _generate_pr_documentation(git_ops, state, target_branch)
    else:
        console.print(f"[red]Error:[/red] Unknown mode '{mode}'.")
        return state
        
    console.print("[bold blue]--- Scribe: Documentation Complete ---[/bold blue]\n")
    
    return {
        "artifacts": artifacts,
        "messages": [HumanMessage(
            content=f"Scribe generated {len(artifacts)} documentation artifact(s)"
        )]
    }


# ============================================================================
# COMMIT DOCUMENTATION TRACKING
# ============================================================================

def _ensure_commit_docs_dir(repo_path: str):
    """Ensure the commit docs directory exists"""
    docs_dir = Path(repo_path) / COMMIT_DOCS_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    index_file = Path(repo_path) / COMMIT_INDEX_FILE
    if not index_file.exists():
        with open(index_file, 'w') as f:
            json.dump({"commits": []}, f)


def _save_commit_documentation(repo_path: str, commit_hash: str, commit_data: dict) -> str:
    """
    Save detailed commit documentation to .gitworkspace/commit_docs/
    
    Args:
        repo_path: Repository root path
        commit_hash: Short commit hash (7 chars)
        commit_data: Dictionary containing commit details
    
    Returns:
        Path to saved markdown file
    """
    docs_dir = Path(repo_path) / COMMIT_DOCS_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{commit_hash}.md"
    filepath = docs_dir / filename
    
    # Generate detailed commit documentation
    llm = get_llm("creative")
    
    prompt = textwrap.dedent(f"""
    You are a Senior Software Engineer documenting a code commit for future PR generation.
    
    COMMIT CONTEXT:
    Hash: {commit_data.get('hash', commit_hash)}
    Author: {commit_data.get('author', 'Unknown')}
    Date: {commit_data.get('date', 'Unknown')}
    Message: {commit_data.get('subject', 'No message')}
    
    Files Changed:
    {commit_data.get('files_changed', 'No files listed')}
    
    Diff Preview:
    {commit_data.get('diff_preview', 'No diff available')}
    
    Code Quality Issues Addressed:
    {commit_data.get('issues_fixed', 'None reported')}
    
    REQUIREMENTS:
    Generate a detailed technical document that explains:
    1. **What Changed**: Specific modifications made (files, functions, classes)
    2. **Why It Changed**: Business or technical rationale
    3. **How It Works**: Brief explanation of the implementation approach
    4. **Impact**: What systems/modules are affected
    5. **Technical Debt**: Any known limitations or follow-up needed
    
    OUTPUT FORMAT (Pure Markdown, NO code fences):
    
    # Commit: {commit_data.get('subject', 'Commit Documentation')}
    
    **Hash:** `{commit_hash}`  
    **Author:** {commit_data.get('author', 'Unknown')}  
    **Date:** {commit_data.get('date', 'Unknown')}
    
    ## Changes Overview
    [High-level summary in 2-3 sentences]
    
    ## Technical Details
    
    ### Modified Components
    [List specific files/modules and what changed in each]
    
    ### Implementation Approach
    [Explain how the solution works]
    
    ### Code Quality Improvements
    [If applicable, list issues resolved]
    
    ## Impact Analysis
    
    ### Affected Systems
    [Which parts of the codebase are impacted]
    
    ### Breaking Changes
    [If any, list them clearly]
    
    ### Performance Implications
    [Any performance changes, positive or negative]
    
    ## Technical Debt & Follow-ups
    [Any known limitations or future improvements needed]
    
    CRITICAL: Output ONLY the markdown content. NO preambles, NO code fences wrapping the entire response.
    """)
    
    response = llm.invoke([
        SystemMessage(content="You are a technical documentation expert. Output pure markdown only."),
        HumanMessage(content=prompt)
    ])
    
    # Clean the response
    clean_content = response.content.strip()
    clean_content = re.sub(r'^```(?:markdown|md)?\n', '', clean_content)
    clean_content = re.sub(r'\n```$', '', clean_content)
    
    # Save to file
    with open(filepath, 'w') as f:
        f.write(clean_content)
    
    # Update index
    index_file = Path(repo_path) / COMMIT_INDEX_FILE
    with open(index_file, 'r') as f:
        index_data = json.load(f)
    
    index_data["commits"].append({
        "hash": commit_hash,
        "timestamp": timestamp,
        "filepath": str(filepath.relative_to(repo_path)),
        "subject": commit_data.get('subject', 'Unknown'),
        "author": commit_data.get('author', 'Unknown')
    })
    
    with open(index_file, 'w') as f:
        json.dump(index_data, f, indent=2)
    
    console.print(f"    [green]✓[/green] Saved commit doc: {filename}")
    return str(filepath)


def _load_all_commit_docs(repo_path: str, commits_to_include: list = None) -> str:
    """
    Load all commit documentation from .gitworkspace/commit_docs/
    
    Args:
        repo_path: Repository root path
        commits_to_include: Optional list of commit hashes to include (if None, includes all)
    
    Returns:
        Combined markdown content from all commit docs
    """
    index_file = Path(repo_path) / COMMIT_INDEX_FILE
    
    if not index_file.exists():
        return ""
    
    with open(index_file, 'r') as f:
        index_data = json.load(f)
    
    commits = index_data.get("commits", [])
    
    # Filter by commit hashes if provided
    if commits_to_include:
        commits = [c for c in commits if c['hash'] in commits_to_include]
    
    if not commits:
        return ""
    
    console.print(f"    [cyan]Loading {len(commits)} commit documentation(s)...[/cyan]")
    
    combined_content = "# Detailed Commit History\n\n"
    combined_content += f"This PR includes {len(commits)} commit(s) with the following detailed changes:\n\n"
    combined_content += "---\n\n"
    
    for commit in commits:
        filepath = Path(repo_path) / commit['filepath']
        if filepath.exists():
            with open(filepath, 'r') as f:
                content = f.read()
                combined_content += content + "\n\n---\n\n"
    
    return combined_content


def _cleanup_commit_docs(repo_path: str):
    """
    Remove all commit documentation after PR is created
    This should be called after successful PR generation
    """
    docs_dir = Path(repo_path) / COMMIT_DOCS_DIR
    index_file = Path(repo_path) / COMMIT_INDEX_FILE
    
    if docs_dir.exists():
        import shutil
        shutil.rmtree(docs_dir)
        console.print("    [yellow]Cleaned up commit documentation files[/yellow]")
    
    if index_file.exists():
        os.remove(index_file)
        console.print("    [yellow]Cleaned up commit index[/yellow]")
    
    # Recreate empty structure
    _ensure_commit_docs_dir(repo_path)


# ============================================================================
# SYSTEM DOCUMENTATION GENERATION
# ============================================================================

def _generate_system_documentation(git_ops: GitOps, state: RepoState) -> list:
    """Generates comprehensive technical documentation for the entire codebase."""
    console.print("    [yellow]Mode: System Documentation Generation[/yellow]")
    
    from src.tools.parser import PythonCodeParser
    from src.tools.diagram import MermaidGenerator
    
    repo_path = state.get("repo_path", os.getcwd())
    parser = PythonCodeParser(repo_path)
    architect = MermaidGenerator(parser)
    
    py_files = git_ops.repo.git.ls_files("*.py").splitlines()
    console.print(f"    Analyzing {len(py_files)} modules for system overview...")
    
    dep_graph = architect.generate_architecture_map(py_files)
    complexity_map = architect.generate_complexity_heatmap()
    
    detailed_context = ""
    for file_path in py_files[:15]: 
        try:
            analysis = parser.analyze_file(file_path)
            if analysis.classes or analysis.functions:
                detailed_context += f"\n### File: {file_path}\n"
                for cls in analysis.classes:
                    methods_list = ", ".join([m for m in cls.methods])
                    detailed_context += f"- Class: {cls.name} (Methods: {methods_list})\n"
                for func in analysis.functions:
                    detailed_context += f"- Function: {func.name}\n"
        except Exception:
            continue

    llm = get_llm("creative")
    prompt = textwrap.dedent(f"""
        You are a Principal Software Architect. Your goal is to write a "System Blueprint" document.
        
        Analyze the following technical context:
        {detailed_context}
        
        Requirements:
        1. Executive Summary: Explain the "Why" behind this system.
        2. Component Analysis: Describe the interaction between high-level modules.
        3. Implementation Detail: Summarize the logic found in key files.
        4. Operational Flow: How does data move through this system?
        
        Tone: Highly technical, objective, and authoritative.
    """)
    
    response = llm.invoke([
        SystemMessage(content="You are a Technical Lead writing high-level system documentation."),
        HumanMessage(content=prompt)
    ])
    
    full_docs = f"# System Documentation\n\n{response.content}\n\n"
    
    if dep_graph:
        full_docs += f"## System Architecture Map\n```mermaid\n{dep_graph}\n```\n\n"
    
    if complexity_map:
        full_docs += f"## Complexity and Tech Debt Heatmap\n```mermaid\n{complexity_map}\n```\n"
    
    doc_path = save_artifact(full_docs, "md", prefix="documentation")
    
    try:
        with open("CODE_DOCS.md", "w") as f:
            f.write(full_docs)
        console.print("    [green]Success:[/green] Saved to CODE_DOCS.md")
    except Exception as e:
        console.print(f"    [red]Warning:[/red] Could not save to root: {e}")
    
    return [{
        "id": "system_docs",
        "type": "markdown_doc",
        "file_path": doc_path,
        "description": "System-wide technical documentation",
        "created_by": "scribe"
    }]


# ============================================================================
# COMMIT MESSAGE GENERATION
# ============================================================================

def _generate_commit_message(git_ops: GitOps, state: RepoState) -> list:
    """Generate commit message for staged changes and save detailed documentation"""
    console.print("    [yellow]Mode: Commit Message Generation[/yellow]")
    
    repo_path = state.get("repo_path", os.getcwd())
    
    if not git_ops.has_staged_changes():
        console.print("    [red]Error:[/red] No staged changes found. Use 'git add <files>' first.")
        return []
    
    diff = git_ops.get_staged_diff()
    if not diff:
        return []
    
    try:
        staged_files = git_ops.repo.git.diff("--cached", name_only=True).split('\n')
        staged_files = [f.strip() for f in staged_files if f.strip()]
        console.print(f"    Analyzing {len(staged_files)} staged file(s)")
    except Exception:
        staged_files = []
    
    user_intent = state.get("commit_intent", "General improvements")
    code_issues = state.get("code_issues", [])
    
    console.print("    Generating commit message with AI...")
    
    try:
        commit_msg = _generate_commit_with_llm(
            diff=diff,
            files=staged_files,
            user_intent=user_intent,
            code_issues=code_issues
        )
        
        commit_path = save_artifact(commit_msg, "txt", prefix="commit_message")
        with open("COMMIT_MESSAGE.txt", "w") as f:
            f.write(commit_msg)
        console.print("    [green]Success:[/green] Saved to COMMIT_MESSAGE.txt")
        
        # Generate a temporary commit hash for documentation (will be replaced after actual commit)
        temp_hash = datetime.now().strftime("%Y%m%d%H%M%S")[:7]
        
        # Prepare detailed commit data for documentation
        diff_preview = diff[:2000] + "\n... [truncated]" if len(diff) > 2000 else diff
        
        issues_fixed = ""
        if code_issues:
            critical = [i for i in code_issues if i.get("severity") == "critical"]
            high = [i for i in code_issues if i.get("severity") == "high"]
            issues_fixed = f"Critical: {len(critical)}, High: {len(high)}"
        
        commit_data = {
            "hash": temp_hash,
            "author": git_ops.repo.config_reader().get_value("user", "name", default="Unknown"),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "subject": commit_msg.split('\n')[0],
            "files_changed": ", ".join(staged_files),
            "diff_preview": diff_preview,
            "issues_fixed": issues_fixed
        }
        
        # Save detailed commit documentation
        doc_path = _save_commit_documentation(repo_path, temp_hash, commit_data)
        
        console.print("    [cyan]💡 Tip:[/cyan] After committing, the system will track this commit for PR generation")
        
        return [{
            "id": "commit_message",
            "type": "commit_msg",
            "file_path": commit_path,
            "description": "Generated commit message",
            "created_by": "scribe"
        }, {
            "id": "commit_documentation",
            "type": "commit_doc",
            "file_path": doc_path,
            "description": "Detailed commit documentation",
            "created_by": "scribe"
        }]
    except Exception as e:
        console.print(f"    [red]Error:[/red] {e}")
        return []


def _generate_commit_with_llm(diff: str, files: list, user_intent: str, code_issues: list) -> str:
    llm = get_llm("creative")

    diff_snippet = diff[:3000] + "\n... [truncated]" if len(diff) > 3000 else diff

    issues_context = ""
    if code_issues:
        critical = len([i for i in code_issues if i.get("severity") == "critical"])
        warnings = len([i for i in code_issues if i.get("severity") == "warning"])
        issues_context = (
            f"\nCode Quality Context:\n"
            f"- Critical issues addressed: {critical}\n"
            f"- Warnings addressed: {warnings}\n"
        )

    prompt = textwrap.dedent(f"""
    You are a senior software engineer writing a high-quality Conventional Commit message.

    AVAILABLE CONTEXT:
    Developer Intent (may be incomplete or informal):
    {user_intent}

    Changed Files (use to infer scope, not to list verbatim):
    {', '.join(files[:10])}

    {issues_context}

    Diff Summary (may be truncated):
    {diff_snippet}

    HARD RULES:
    1. Output ONLY the raw commit message text. No markdown, no code blocks.
    2. Follow Conventional Commits strictly: type(scope): subject
    3. Use one of these types only:
    feat, fix, refactor, perf, test, chore, docs, ci, build
    4. Subject line:
    - Imperative mood (e.g., "add", "fix", "remove", "refactor")
    - Max 72 characters
    - Describe the primary change, not the implementation
    5. Scope:
    - Single, concise noun derived from the affected area (e.g., api, auth, config)
    - Omit scope only if it cannot be inferred
    6. Body (optional but preferred if non-trivial):
    - Explain WHAT changed and WHY
    - Mention behavior changes, risk, or compatibility impact if relevant
    - Do NOT describe low-level implementation details
    7. If this change primarily addresses code quality issues, prefer 'fix' or 'refactor' as the type.

    QUALITY BAR:
    - The message should be suitable for changelogs and release notes.
    - Assume this commit will be read months later with no additional context.
    """)

    response = llm.invoke([
        SystemMessage(content="You write precise, conventional, production-quality commit messages."),
        HumanMessage(content=prompt)
    ])

    msg = response.content.strip()

    # Safety cleanup in case the model still emits fences
    msg = re.sub(r'^```[\w]*\n', '', msg)
    msg = re.sub(r'\n```$', '', msg)

    return msg.strip()


# ============================================================================
# PR DOCUMENTATION GENERATION
# ============================================================================

def _generate_pr_documentation(git_ops: GitOps, state: RepoState, target_branch: str) -> list:
    console.print("    [yellow]Mode: PR Documentation Generation[/yellow]")
    
    repo_path = state.get("repo_path", os.getcwd())
    
    commits, actual_target = _get_commits_since(git_ops, target_branch)
    if not commits:
        console.print("    [red]Warning:[/red] No commits found to document.")
        return []
    
    commits_data = [_get_commit_details(git_ops, c) for c in commits]
    source_branch = git_ops.get_current_branch()
    
    # Load all detailed commit documentation
    commit_hashes = [c['hash'] for c in commits_data]
    detailed_commits_content = _load_all_commit_docs(repo_path, commit_hashes)
    
    pr_text = _generate_pr_with_llm(
        commits_data=commits_data,
        source_branch=source_branch,
        target_branch=target_branch,
        code_issues=state.get("code_issues", []),
        artifacts=state.get("artifacts", []),
        detailed_commit_docs=detailed_commits_content
    )
    
    pr_path = save_artifact(pr_text, "md", prefix="pr_documentation")
    with open("PR_Document.md", "w") as f:
        f.write(pr_text)
    console.print("    [green]Success:[/green] Saved to PR_Document.md")
    
    # Clean up commit docs after PR generation
    console.print("    [yellow]Cleaning up commit documentation...[/yellow]")
    _cleanup_commit_docs(repo_path)
    
    return [{
        "id": "pr_document",
        "type": "markdown_doc",
        "file_path": pr_path,
        "description": f"PR Documentation ({len(commits)} commits)",
        "created_by": "scribe"
    }]


def _get_commits_since(git_ops: GitOps, base_branch: str):
    try:
        target = base_branch if _branch_exists(git_ops, base_branch) else f"origin/{base_branch}"
        commits = git_ops.repo.git.log(f"{target}..HEAD", pretty="format:%H").splitlines()
        return commits, target
    except Exception:
        return [], base_branch


def _branch_exists(git_ops: GitOps, branch: str) -> bool:
    try:
        git_ops.repo.git.rev_parse("--verify", branch)
        return True
    except Exception:
        return False


def _get_commit_details(git_ops: GitOps, commit_hash: str) -> dict:
    repo = git_ops.repo
    commit = repo.commit(commit_hash)
    stats = repo.git.show("--stat", commit_hash, "--oneline")
    preview = repo.git.show(commit_hash, color="never").split('\n')[5:20]
    
    return {
        "hash": commit.hexsha[:7],
        "author": commit.author.name,
        "date": commit.authored_datetime.strftime("%Y-%m-%d %H:%M"),
        "subject": commit.message.split('\n')[0],
        "stats": stats,
        "preview": '\n'.join(preview)
    }

def _generate_enhanced_readme(git_ops: GitOps, state: RepoState) -> str:
    """Uses LLM to rewrite the README based on codebase reality and architecture."""
    console.print("    [yellow]Mode: AI README Transformation[/yellow]")
    
    current_readme = ""
    if os.path.exists("README.md"):
        with open("README.md", "r") as f:
            current_readme = f.read()
            
    # Gather architectural context from previous nodes
    arch_context = ""
    for art in state.get("artifacts", []):
        if "architecture_overview" in art.get("id", "") or "architecture" in art.get("file_path", ""):
            try:
                with open(art["file_path"], "r") as f:
                    arch_context += f"\n{f.read()}"
            except Exception:
                continue

    llm = get_llm("creative")
    prompt = textwrap.dedent(f"""
        You are a Principal Developer Advocate. Your task is to transform the project README.md 
        into a world-class documentation hub based on the latest architectural analysis.
        
        EXISTING README:
        {current_readme}
        
        CURRENT ARCHITECTURE CONTEXT:
        {arch_context}
        
        RECENT CODE QUALITY STATE:
        {state.get('code_issues', [])}
        
        REQUIREMENTS:
        1. Executive Summary: Retain or improve the core mission statement.
        2. System Vision: Embed insights from the provided architecture context.
        3. Feature Set: Update the list based on the actual modules detected.
        4. Quality Standard: Summarize the current health of the project.
        5. DO NOT wrap the entire response in markdown code blocks.
        6. Return raw markdown content only.
        
        Tone: Professional, inviting, and technically accurate.
    """)
    
    response = llm.invoke([
        SystemMessage(content="You are an expert technical documentarian. Output pure markdown only."),
        HumanMessage(content=prompt)
    ])
    
    # Cleaning Logic
    clean_content = response.content.strip()
    clean_content = re.sub(r'^```(?:markdown|md)?\n', '', clean_content)
    clean_content = re.sub(r'\n```$', '', clean_content)
    
    return clean_content
    
def _generate_pr_with_llm(commits_data, source_branch, target_branch, code_issues, artifacts, detailed_commit_docs=""):
    """
    Generate comprehensive, production-ready Pull Request documentation.
    Now includes detailed commit documentation from saved files.
    """
    llm = get_llm("creative")
    
    # Build commits summary
    commits_text = "\n".join([
        f"- `{c['hash']}`: {c['subject']} ({c['author']})" 
        for c in commits_data
    ])
    
    # Analyze code issues for context
    issues_section = ""
    if code_issues:
        critical = len([i for i in code_issues if i.get("severity") == "critical"])
        high = len([i for i in code_issues if i.get("severity") == "high"])
        medium = len([i for i in code_issues if i.get("severity") == "medium"])
        
        issues_section = f"""
Code Quality Context:
This PR addresses {critical} critical, {high} high, and {medium} medium severity issues detected by automated quality scans.
"""
    
    # Extract file changes for context
    files_context = ""
    if artifacts:
        file_changes = []
        for art in artifacts:
            if "file_path" in art:
                file_changes.append(art["file_path"])
        if file_changes:
            files_context = f"\nFiles Modified: {len(file_changes)} files"

    # Include detailed commit documentation
    commit_docs_section = ""
    if detailed_commit_docs:
        commit_docs_section = f"""

DETAILED COMMIT DOCUMENTATION:
{detailed_commit_docs}

Use the above detailed commit documentation to understand the full context of each change.
Extract specific technical details, metrics, and implementation approaches from these docs.
"""

    prompt = textwrap.dedent(f"""
    You are a Principal Software Engineer writing production-grade Pull Request documentation.

    REPOSITORY CONTEXT:
    Branch Path: {source_branch} → {target_branch}
    
    Commits Summary:
    {commits_text}
    {files_context}
    {issues_section}
    {commit_docs_section}

    CRITICAL OUTPUT REQUIREMENTS:
    1. Output PURE Markdown - NO surrounding code fences, NO conversational text
    2. Begin IMMEDIATELY with content (no preamble)
    3. Use precise technical language with concrete metrics and details
    4. Extract specific information from the detailed commit documentation above
    5. Format for GitHub: proper headings, tables, code blocks, task lists
    6. Professional tone: no emojis, no casual language

    REQUIRED STRUCTURE:

    ## Executive Summary
    - 2-3 sentences summarizing this PR
    - Key metrics from commits (performance gains, issues fixed, coverage)
    - Status: Ready for Review

    ## 1. Problem Statement
    
    ### Background
    Explain what problems existed before these changes
    
    ### Current Pain Points
    List specific issues that were present (extract from commit docs)

    ## 2. Solution Architecture

    ### High-Level Approach
    Explain the overall strategy taken across all commits

    ### Key Components Modified
    Detail the main components changed (extract from commit documentation):
    
    #### [Component Name 1]
    - Purpose and changes
    - Design decisions
    - Integration points
    
    Use Mermaid diagrams if helpful:
    ```mermaid
    graph TD
        A[Component] --> B[Component]
    ```

    ## 3. Detailed Technical Changes

    ### 3.1 Commit-by-Commit Analysis
    
    For each major commit, provide a subsection:
    
    #### Commit: [Subject] (`hash`)
    - **What Changed**: Specific files and modifications
    - **Implementation**: How it works
    - **Impact**: Affected systems
    
    ### 3.2 Configuration Changes
    Document environment variables, dependencies, or infrastructure changes

    ## 4. Testing & Validation

    ### 4.1 Automated Tests
    | Test Type | Coverage | Status |
    |-----------|----------|--------|
    | Unit | Details | ✓ Pass |
    | Integration | Details | ✓ Pass |

    ### 4.2 Performance Benchmarks
    Extract actual numbers from commit documentation:
    ```
    Before: [metric]
    After: [metric]
    Improvement: [percentage]
    ```

    ### 4.3 Manual Validation
    - [ ] Scenario tested
    - [ ] Edge cases verified

    ## 5. Risk Assessment & Mitigation

    | Risk | Severity | Likelihood | Mitigation |
    |------|----------|------------|------------|
    | Specific risk | H/M/L | H/M/L | Strategy |

    ### Rollback Plan
    ```bash
    git revert <commit-range>
    # Additional steps
    ```

    ## 6. Performance Impact

    ### Latency Changes
    [Specific measurements from commits]

    ### Resource Utilization
    [CPU, memory, network impacts]

    ### Cost Implications
    [If applicable]

    ## 7. Deployment

    ### Prerequisites
    - Database migrations
    - Feature flags
    - Config updates

    ### Deployment Steps
    ```bash
    # Step-by-step commands
    ```

    ### Verification
    ```bash
    # Verification commands
    ```

    ## 8. Observability

    ### New Metrics
    ```
    metric_name{{labels}} - Description
    ```

    ### Logging Changes
    ```json
    {{"level": "INFO", "message": "Example"}}
    ```

    ## 9. Future Work

    ### Short-term (Next Sprint)
    - [ ] Item 1
    - [ ] Item 2

    ### Medium-term (Next Quarter)
    - Future improvements

    ## 10. Approval Checklist

    - [ ] Code review (2+ approvers)
    - [ ] Tests passing
    - [ ] Performance validated
    - [ ] Security reviewed
    - [ ] Documentation updated

    ## 11. Contributors

    **Authors:** {', '.join(set([c['author'] for c in commits_data]))}

    ---

    QUALITY RULES:
    1. Be specific: Use exact numbers, file names, function names from commit docs
    2. Show evidence: Include test results, benchmarks, metrics
    3. Explain tradeoffs: Why this approach vs alternatives
    4. Think scale: Concurrent load, data growth, geographic distribution
    5. Risk first: Be upfront about limitations
    6. Actionable: Recommendations should be ticketable
    7. Professional: Write for staff engineers and architects
    8. Scannable: Use tables, lists, code blocks effectively
    
    Remember: Extract and synthesize information from the detailed commit documentation.
    Don't just summarize commits - provide architectural insights and technical analysis.
    """)

    system_message = SystemMessage(content="""You are a Principal Software Engineer writing production documentation. 

Output MUST be:
- Pure markdown (NO code fence wrappers around the entire document)
- Technically precise with concrete details from commit documentation
- Comprehensive for production deployment decisions
- Formatted perfectly for GitHub

You NEVER:
- Add preambles ("Here's the PR...")
- Use vague qualifiers ("might", "various", "some")
- Include emojis
- Wrap entire response in code blocks

Begin IMMEDIATELY with document content.""")

    response = llm.invoke([
        system_message,
        HumanMessage(content=prompt)
    ])
    
    # Advanced content cleaning
    clean_content = response.content.strip()
    
    # Remove conversational preambles
    preamble_patterns = [
        r'^(?:Here\'?s|Here is|I\'?ve created|I\'?ve generated|Below is).*?(?:\n|:)\s*',
        r'^(?:Let me|I will|I can).*?(?:\n|:)\s*',
        r'^.*?(?:Pull Request|PR documentation).*?(?:\n|:)\s*'
    ]
    for pattern in preamble_patterns:
        clean_content = re.sub(pattern, '', clean_content, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove markdown code fences
    if clean_content.startswith('```'):
        clean_content = re.sub(r'^```(?:markdown|md)?\n', '', clean_content)
        clean_content = re.sub(r'\n```\s*$', '', clean_content)
    
    # Ensure we start with a header
    if not clean_content.startswith('#'):
        header_match = re.search(r'^#+\s', clean_content, re.MULTILINE)
        if header_match:
            clean_content = clean_content[header_match.start():]
    
    clean_content = clean_content.strip()
    
    # Build document header
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Determine PR type
    pr_type = "Feature Enhancement"
    if "fix" in source_branch.lower() or "hotfix" in source_branch.lower():
        pr_type = "Bug Fix"
    elif "refactor" in source_branch.lower():
        pr_type = "Refactoring"
    elif "docs" in source_branch.lower():
        pr_type = "Documentation"
    elif "perf" in source_branch.lower():
        pr_type = "Performance"
    
    header = (
        f"# Pull Request Documentation\n\n"
        f"**Generated:** {now}  \n"
        f"**Branch:** `{source_branch}` → `{target_branch}`  \n"
        f"**Type:** {pr_type}  \n"
        f"**Commits:** {len(commits_data)}  \n"
        f"**Status:** Ready for Review\n\n"
        f"---\n\n"
    )
    
    # Add collapsible commit history if many commits
    if len(commits_data) > 5:
        commits_section = (
            f"<details>\n"
            f"<summary>📋 Commit History ({len(commits_data)} commits)</summary>\n\n"
            f"{commits_text}\n\n"
            f"</details>\n\n"
            f"---\n\n"
        )
        return header + commits_section + clean_content
    
    return header + clean_content