"""
Code Steward - Deterministic Code Quality Analysis
"""
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage

from src.state import RepoState
from src.tools.gitops import GitOps
from src.tools.parser import PythonCodeParser, ImportType
from src.utils.workspace import save_artifact
from src.utils.config import cfg

# Thresholds
THRESHOLDS = {
    "complexity": 10,
    "nesting": 4,
    "methods_in_class": 15,
    "file_lines": 500,
    "high_impact": 5
}


def steward_node(state: RepoState) -> RepoState:
    """
    Performs deterministic code quality analysis on changed files.
    No LLM calls - pure static analysis.
    """
    print("--- 🛡️  Steward: Analyzing Code Quality ---")
    
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    target_branch = state.get("target_branch", "main")

    git_ops = GitOps(repo_path)
    parser = PythonCodeParser(repo_path)

    # Get changed Python files
    changed_files = _get_changed_python_files(git_ops, target_branch)
    
    if not changed_files:
        print("    No Python files changed. Skipping audit.")
        return {
            "code_issues": [],
            "messages": [HumanMessage(content="No Python changes detected.")]
        }
    
    print(f"    Analyzing {len(changed_files)} file(s)...")

    # Analyze each file
    issues_found = []
    file_metrics = {}
    
    # Build dependency graph once
    try:
        parser.get_dependency_graph(changed_files)
    except Exception as e:
        print(f"    Warning: Could not build dependency graph: {e}")

    for file_path in changed_files:
        print(f"    • {file_path}")
        
        try:
            analysis = parser.analyze_file(file_path)
            
            # Skip files with parse errors
            if analysis.errors:
                issues_found.append({
                    "file": file_path,
                    "type": "syntax_error",
                    "severity": "critical",
                    "message": analysis.errors[0]
                })
                continue
            
            # Store metrics for summary
            file_metrics[file_path] = {
                "loc": analysis.metrics.code_lines,
                "complexity": analysis.metrics.cyclomatic_complexity,
                "functions": len(analysis.functions),
                "classes": len(analysis.classes)
            }
            
            # Check 1: Impact Analysis
            try:
                impact = parser.get_file_impact_analysis(file_path)
                if impact['total_impact'] > THRESHOLDS['high_impact']:
                    issues_found.append({
                        "file": file_path,
                        "type": "high_impact",
                        "severity": "warning",
                        "message": f"Changes affect {impact['total_impact']} other files",
                        "details": {
                            "direct_dependents": impact['direct_dependents'][:5]
                        }
                    })
            except:
                pass  # Skip if dependency graph unavailable
            
            # Check 2: Complexity
            for func in analysis.functions:
                if func.complexity > THRESHOLDS['complexity']:
                    issues_found.append({
                        "file": file_path,
                        "type": "high_complexity",
                        "severity": "warning",
                        "message": f"Function '{func.name}' has complexity {func.complexity}",
                        "line": func.line_number,
                        "threshold": THRESHOLDS['complexity'],
                        "suggestion": "Consider breaking into smaller functions"
                    })
            
            # Check 3: Deep Nesting
            if analysis.metrics.max_nesting_depth > THRESHOLDS['nesting']:
                issues_found.append({
                    "file": file_path,
                    "type": "deep_nesting",
                    "severity": "warning",
                    "message": f"Max nesting depth is {analysis.metrics.max_nesting_depth}",
                    "threshold": THRESHOLDS['nesting'],
                    "suggestion": "Use guard clauses or extract methods"
                })
            
            # Check 4: God Classes
            for cls in analysis.classes:
                if len(cls.methods) > THRESHOLDS['methods_in_class']:
                    issues_found.append({
                        "file": file_path,
                        "type": "god_class",
                        "severity": "warning",
                        "message": f"Class '{cls.name}' has {len(cls.methods)} methods",
                        "line": cls.line_number,
                        "threshold": THRESHOLDS['methods_in_class'],
                        "suggestion": "Consider splitting responsibilities"
                    })
            
            # Check 5: Unused Imports
            unused = parser.find_unused_imports(file_path)
            if unused and len(unused) > 0:
                for imp in unused[:3]:  # Limit to first 3
                    issues_found.append({
                        "file": file_path,
                        "type": "unused_import",
                        "severity": "info",
                        "message": f"Unused import: {imp.module or ', '.join(imp.names)}",
                        "line": imp.line_number
                    })
            
            # Check 6: Wildcard Imports
            for imp in analysis.imports:
                if imp.import_type == ImportType.WILDCARD and not imp.is_future_import:
                    issues_found.append({
                        "file": file_path,
                        "type": "wildcard_import",
                        "severity": "info",
                        "message": f"Wildcard import: from {imp.module} import *",
                        "line": imp.line_number,
                        "suggestion": "Import specific names instead"
                    })
        
        except Exception as e:
            print(f"    ⚠️  Error analyzing {file_path}: {e}")
            issues_found.append({
                "file": file_path,
                "type": "analysis_error",
                "severity": "error",
                "message": str(e)
            })
    
    # Check 7: Circular Dependencies (repo-wide)
    try:
        cycles = parser.find_circular_dependencies()
        for cycle in cycles:
            if any(f in cycle for f in changed_files):
                issues_found.append({
                    "type": "circular_dependency",
                    "severity": "warning",
                    "message": f"Circular dependency detected",
                    "details": {"cycle": cycle}
                })
    except:
        pass

    # Generate Report
    report_content = _generate_report(issues_found, file_metrics, changed_files)
    report_path = save_artifact(report_content, "md")
    
    artifact = {
        "id": "steward_report",
        "type": "markdown_doc",
        "file_path": report_path,
        "description": f"Code Quality Report ({len(issues_found)} issues)",
        "created_by": "steward"
    }
    
    # Summary
    critical = len([i for i in issues_found if i.get("severity") == "critical"])
    warnings = len([i for i in issues_found if i.get("severity") == "warning"])
    
    print(f"    ✓ Found {len(issues_found)} issues ({critical} critical, {warnings} warnings)")
    print("--- 🛡️  Steward: Analysis Complete ---\n")
    
    return {
        "artifacts": [artifact],
        "code_issues": issues_found,  # Structured data for Scribe
        "messages": [HumanMessage(
            content=f"Steward analyzed {len(changed_files)} files: "
                    f"{len(issues_found)} issues found "
                    f"({critical} critical, {warnings} warnings)"
        )]
    }


def _get_changed_python_files(git_ops: GitOps, target_branch: str) -> List[str]:
    """Get Python files that changed compared to target branch"""
    try:
        # Try to get diff
        if git_ops.has_commits():
            # Check if target branch exists
            try:
                git_ops.repo.git.rev_parse("--verify", target_branch)
                diff_output = git_ops.repo.git.diff(
                    target_branch, 
                    name_only=True
                )
            except:
                # Target branch doesn't exist, try origin/target
                try:
                    git_ops.repo.git.rev_parse("--verify", f"origin/{target_branch}")
                    diff_output = git_ops.repo.git.diff(
                        f"origin/{target_branch}", 
                        name_only=True
                    )
                except:
                    # Fallback: just get all Python files
                    print(f"    ⚠️  Branch '{target_branch}' not found, analyzing all files")
                    diff_output = git_ops.repo.git.ls_files("*.py")
        else:
            # No commits yet, get all tracked Python files
            diff_output = git_ops.repo.git.ls_files("*.py")
        
        files = [
            f.strip() 
            for f in diff_output.split('\n') 
            if f.strip().endswith('.py')
        ]
        return files
    
    except Exception as e:
        print(f"    ⚠️  Error getting changed files: {e}")
        # Last resort: scan filesystem
        import os
        py_files = []
        for root, dirs, files in os.walk(git_ops.repo_path):
            # Skip common ignore patterns
            dirs[:] = [d for d in dirs if d not in [
                '.git', '__pycache__', 'venv', '.venv', 'env'
            ]]
            for file in files:
                if file.endswith('.py'):
                    rel_path = os.path.relpath(
                        os.path.join(root, file), 
                        git_ops.repo_path
                    )
                    py_files.append(rel_path)
        return py_files[:20]  # Limit to 20 files max


def _generate_report(issues: List[Dict], metrics: Dict, files: List[str]) -> str:
    """Generate markdown report"""
    
    # Header
    report = f"# 🛡️ Code Quality Report\n\n"
    report += f"**Analyzed Files:** {len(files)}  \n"
    report += f"**Issues Found:** {len(issues)}  \n"
    report += f"**Generated:** {_get_timestamp()}\n\n"
    
    # Summary by severity
    by_severity = {
        "critical": [],
        "warning": [],
        "info": [],
        "error": []
    }
    
    for issue in issues:
        sev = issue.get("severity", "info")
        by_severity[sev].append(issue)
    
    # Critical Issues
    if by_severity["critical"]:
        report += "## 🚨 Critical Issues\n\n"
        for issue in by_severity["critical"]:
            report += f"- **{issue['file']}**: {issue['message']}\n"
        report += "\n"
    
    # Warnings
    if by_severity["warning"]:
        report += "## ⚠️ Warnings\n\n"
        for issue in by_severity["warning"]:
            file = issue.get('file', 'N/A')
            line = issue.get('line', '')
            loc = f":{line}" if line else ""
            report += f"- **`{file}{loc}`**\n"
            report += f"  - {issue['message']}\n"
            if 'suggestion' in issue:
                report += f"  - 💡 *{issue['suggestion']}*\n"
        report += "\n"
    
    # Info (less prominent)
    if by_severity["info"]:
        report += "<details>\n<summary>ℹ️ Info ({} items)</summary>\n\n".format(
            len(by_severity["info"])
        )
        for issue in by_severity["info"]:
            file = issue.get('file', 'N/A')
            line = issue.get('line', '')
            loc = f":{line}" if line else ""
            report += f"- `{file}{loc}`: {issue['message']}\n"
        report += "\n</details>\n\n"
    
    # Metrics Summary
    if metrics:
        report += "## 📊 Code Metrics\n\n"
        report += "| File | LOC | Complexity | Functions | Classes |\n"
        report += "|------|-----|------------|-----------|----------|\n"
        for file, m in metrics.items():
            short_file = file.split('/')[-1]
            report += f"| {short_file} | {m['loc']} | {m['complexity']} | {m['functions']} | {m['classes']} |\n"
        report += "\n"
    
    # Recommendations
    if by_severity["warning"] or by_severity["critical"]:
        report += "## 💡 Recommendations\n\n"
        
        if any(i['type'] == 'high_complexity' for i in issues):
            report += "- **Complexity**: Break down complex functions into smaller, focused units\n"
        if any(i['type'] == 'deep_nesting' for i in issues):
            report += "- **Nesting**: Use early returns (guard clauses) to reduce nesting\n"
        if any(i['type'] == 'god_class' for i in issues):
            report += "- **Class Design**: Apply Single Responsibility Principle - split large classes\n"
        if any(i['type'] == 'high_impact' for i in issues):
            report += "- **Impact**: High-impact changes detected - ensure thorough testing\n"
        
        report += "\n"
    
    return report


def _get_timestamp():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")