"""
Docstring for src.agents.steward
"""
import json
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage

from src.state import RepoState, Artifact
from src.tools.gitops import GitOps
from src.tools.parser import PythonCodeParser, FileAnalysis, ImportType
from src.utils.llm import get_llm
from src.utils.prompts import load_prompt_from_yaml
from src.utils.workspace import save_artifact
from src.utils.config import cfg

# --- Architect Thresholds ---
THRESHOLDS = {
    "complexity": 10,       # Max Cyclomatic Complexity
    "nesting": 4,           # Max Nesting Depth (Arrowhead anti-pattern)
    "methods_in_class": 15, # God Class detection
    "file_lines": 500,      # File size warning
    "high_impact": 5        # Warn if file has > 5 dependent files
}

prompt_kwargs = {
    "max_complexity": 10,
    "max_nesting": 4,
    "max_methods": 15,
    "repo_name": "RepoRanger",
    "target_branch": "HEAD",
    "file_list": ["src/tools/gitops.py", "src/state.py"]
}

STEWARD_SYSTEM_PROMPT = f"""
You are the **'Code Steward'**, a Senior Software Architect specializing in Python.

Your mission is to **analyze code quality** and **propose actionable improvements**.
You focus strictly on structural and maintainability issues, not stylistic preferences.

-------------------------------
Focus Areas:
1. Cyclomatic Complexity:
   - Max allowed: {prompt_kwargs["max_complexity"]}
2. Nesting Depth:
   - Max allowed: {prompt_kwargs["max_nesting"]}
3. God Classes:
   - Max methods allowed per class: {prompt_kwargs["max_methods"]}
4. Circular Dependencies
5. Imports

-------------------------------
Repository Context:
- Repository Name: {prompt_kwargs["repo_name"]}
- Target Branch: {prompt_kwargs["target_branch"]}
- Files Under Review: {prompt_kwargs["file_list"]}

-------------------------------
Metrics Thresholds:
- Complexity: {prompt_kwargs["max_complexity"]}
- Nesting: {prompt_kwargs["max_nesting"]}
- Methods in class: {prompt_kwargs["max_methods"]}
"""


def steward_node(state: RepoState) -> RepoState:
    """
    Advanced Steward Analysis:
    1. Identifies CHANGED files.
    2. Runs comprehensive Static Analysis (Metrics, AST, Dependencies).
    3. Calculates Impact Analysis (Ripple effect of changes).
    4. Detects Anti-patterns (Wildcards, God Classes, Nesting).
    5. Drafts auto-fixes for the worst offenders.
    """
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    target_branch = state.get("target_branch", "HEAD")

    # 1. Initialize Tools
    git_ops = GitOps(repo_path)
    parser = PythonCodeParser(repo_path)

    # 2. Determine Scope
    changed_files = _get_changed_python_files(git_ops, target_branch)
    if not changed_files:
        print("No Python files changed. Skipping audit.")
        return {"messages": [HumanMessage(content="Steward found no Python changes to audit.")], "code_issues": []}
    
    print(f"Targeting {len(changed_files)} file(s) for Deep Analysis...")

    # 3. Targeted Analysis
    issues_found = []
    refactoring_candidates = []
    
    # Pre-calculate dependency graph for impact analysis
    print("Building dependency graph for impact analysis...")
    parser.get_dependency_graph(changed_files)

    for rel_path in changed_files:
        analysis = parser.analyze_file(rel_path)
        
        # A. Fatal Parse Errors
        if analysis.errors:
            for err in analysis.errors:
                issues_found.append(f"[Syntax Error] `{rel_path}`: {err}")
            continue # Cannot analyze logic if syntax is broken

        # B. Impact Analysis (Ripple Effect)
        impact = parser.get_file_impact_analysis(rel_path)
        if impact['total_impact'] > THRESHOLDS['high_impact']:
            issues_found.append(
                f"[High Risk Change] Modifying `{rel_path}` affects {impact['total_impact']} other files. "
                f"Direct dependents: {', '.join(impact['direct_dependents'][:3])}..."
            )

        # C. Import Health (Unused & Wildcards)
        unused_imports = parser.find_unused_imports(rel_path)
        for u in unused_imports:
            issues_found.append(f"[Unused Import] `{rel_path}`: `{u.module}` is imported but never used.")
        
        for imp in analysis.imports:
            if imp.import_type == ImportType.WILDCARD:
                 issues_found.append(f"[Wildcard Import] `{rel_path}`: Avoid `from {imp.module} import *`. explicit is better than implicit.")

        # D. Complexity & Nesting (Function Level)
        for func in analysis.functions:
            # Cyclomatic Complexity
            if func.complexity > THRESHOLDS['complexity']:
                issues_found.append(
                    f"[Complexity] `{rel_path}::{func.name}` score is {func.complexity} (Limit: {THRESHOLDS['complexity']})."
                )
                _add_refactor_candidate(refactoring_candidates, rel_path, func.name, "complexity", func.complexity, func.line_number)

        # Nesting Depth (File/Function proxy) - Parser calculates this file-wide
        if analysis.metrics.max_nesting_depth > THRESHOLDS['nesting']:
            issues_found.append(
                f"[Deep Nesting] `{rel_path}` contains logic nested {analysis.metrics.max_nesting_depth} levels deep (Limit: {THRESHOLDS['nesting']})."
            )
            # We add the file as a generic candidate if nesting is high
            _add_refactor_candidate(refactoring_candidates, rel_path, "entire_file", "nesting", analysis.metrics.max_nesting_depth, 0)

        # E. Class Design (God Objects)
        for cls in analysis.classes:
            if len(cls.methods) > THRESHOLDS['methods_in_class']:
                issues_found.append(
                    f"[God Class] `{rel_path}::{cls.name}` has {len(cls.methods)} methods (Limit: {THRESHOLDS['methods_in_class']}). Consider breaking it up."
                )

    # F. Circular Dependencies (Repo-wide check involving changed files)
    cycles = parser.find_circular_dependencies()
    for cycle in cycles:
        # Only report if a changed file is involved in the cycle
        if any(f in cycle for f in changed_files):
            issues_found.append(f"[Circular Dependency] Cycle detected: {' -> '.join(cycle)}")

    # 4. Agentic Refactoring (The "Fixer" Mode)
    new_artifacts = []
    if refactoring_candidates:
        # Prioritize: Sort by score (descending)
        worst_offender = sorted(refactoring_candidates, key=lambda x: x['score'], reverse=True)[0]
        
        print(f"Attempting Auto-Fix for: {worst_offender['file']} ({worst_offender['reason']}={worst_offender['score']})")
        
        fix_artifact = _generate_ai_fix(git_ops, worst_offender)
        if fix_artifact:
            new_artifacts.append(fix_artifact)

    # 5. Generate Audit Report
    if issues_found:
        report_content = _generate_markdown_report(issues_found, changed_files)
        report_path = save_artifact(report_content, "md")
        new_artifacts.append({
            "id": "audit_report",
            "type": "markdown_doc",
            "file_path": report_path,
            "description": f"Steward Report ({len(issues_found)} issues)",
            "created_by": "steward"
        })

    print(f"--- Steward: Finished. Found {len(issues_found)} issues. ---")

    return {
        "artifacts": new_artifacts,
        "code_issues": issues_found,
        "messages": [HumanMessage(content=f"Steward Analysis: {len(issues_found)} issues found.")] if issues_found else []
    }

def _add_refactor_candidate(candidates: List, file: str, func: str, reason: str, score: int, line: int):
    candidates.append({
        "file": file,
        "function": func,
        "reason": reason,
        "score": score,
        "start_line": line
    })

def _generate_ai_fix(git_ops: GitOps, offender: Dict[str, Any]) -> Dict:
    """Delegates the fix generation to the LLM"""
    try:
        file_content = git_ops.get_file_content(offender['file'])
        llm = get_llm("default")

        prompt = [
            SystemMessage(content=STEWARD_SYSTEM_PROMPT),
            HumanMessage(content=f"""
            I have detected a code quality violation.
            
            **File:** {offender['file']}
            **Target:** {offender['function']}
            **Violation:** {offender['reason']} (Score: {offender['score']})
            
            Here is the file content:
            ```python
            {file_content}
            ```
            
            **Task:**
            1. Analyze the specific function/class.
            2. Refactor it to reduce {offender['reason']}.
            3. If it is deep nesting, use guard clauses or extract methods.
            4. If it is high complexity, decompose into private helpers (`_helper`).
            5. Output the Refactored Code block ONLY.
            """)
        ]
        
        response = llm.invoke(prompt)
        refactor_path = save_artifact(response.content, "md")
        
        return {
            "id": "refactor_proposal",
            "type": "refactor_plan",
            "file_path": refactor_path,
            "description": f"Proposed Fix for {offender['function']} in {offender['file']}",
            "created_by": "steward"
        }
    except Exception as e:
        print(f"Error generating AI fix: {e}")
        return None

def _generate_markdown_report(issues: List[str], scanned_files: List[str]) -> str:
    header = f"# Code Steward Report\n**Scanned:** {len(scanned_files)} files\n\n"
    
    # Group issues by type for readability
    grouped = {"Critical": [], "Maintainability": [], "Style": []}
    
    for i in issues:
        if "Syntax Error" in i or "Circular" in i or "High Risk" in i:
            grouped["Critical"].append(i)
        elif "Complexity" in i or "God Class" in i or "Nesting" in i:
            grouped["Maintainability"].append(i)
        else:
            grouped["Style"].append(i)

    body = ""
    for category, items in grouped.items():
        if items:
            body += f"## {category} Issues\n"
            body += "\n".join(f"- {item}" for item in items) + "\n\n"
            
    return header + body

def _get_changed_python_files(git_ops: GitOps, target_branch: str) -> List[str]:
    try:
        raw_files = git_ops.repo.git.diff(target_branch, name_only=True)
        files = [f.strip() for f in raw_files.split('\n') if f.strip().endswith('.py')]
        return files
    except Exception as e:
        print(f"    [Warning] Could not fetch changed files via Git: {e}")
        return []