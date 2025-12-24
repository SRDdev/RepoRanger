# 🛡️ Code Quality Report

**Analyzed Files:** 15  
**Issues Found:** 18  
**Generated:** 2025-12-25 04:55:30

## ⚠️ Warnings

- **`src/agents/architect.py:16`**
  - Function 'architect_node' has complexity 11
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/scribe.py:264`**
  - Function '_generate_system_documentation' has complexity 11
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/scribe.py:346`**
  - Function '_generate_commit_message' has complexity 12
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/scribe.py:633`**
  - Function '_generate_pr_with_llm' has complexity 25
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/steward.py:23`**
  - Function 'steward_node' has complexity 28
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/steward.py:212`**
  - Function '_get_changed_python_files' has complexity 12
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/steward.py:267`**
  - Function '_generate_report' has complexity 21
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/tactician.py:16`**
  - Function 'tactician_node' has complexity 17
  - 💡 *Consider breaking into smaller functions*
- **`src/tools/gitops.py`**
  - Changes affect 9 other files
- **`src/tools/history.py:23`**
  - Function 'track_variable_changes' has complexity 15
  - 💡 *Consider breaking into smaller functions*
- **`src/tools/history.py`**
  - Max nesting depth is 9
  - 💡 *Use guard clauses or extract methods*
- **`src/utils/config.py`**
  - Changes affect 11 other files
- **`src/utils/llm.py`**
  - Changes affect 6 other files
- **`src/utils/workspace.py`**
  - Changes affect 6 other files

<details>
<summary>ℹ️ Info (4 items)</summary>

- `main.py:4`: Unused import: subprocess
- `main.py:18`: Unused import: rich.rule
- `src/tools/history.py:8`: Unused import: git
- `src/utils/llm.py:5`: Unused import: typing

</details>

## 📊 Code Metrics

| File | LOC | Complexity | Functions | Classes |
|------|-----|------------|-----------|----------|
| cli.py | 56 | 16 | 10 | 0 |
| main.py | 206 | 41 | 12 | 0 |
| architect.py | 78 | 11 | 1 | 0 |
| explainer.py | 53 | 20 | 6 | 1 |
| scribe.py | 257 | 87 | 14 | 0 |
| steward.py | 222 | 62 | 4 | 0 |
| tactician.py | 95 | 26 | 3 | 0 |
| graph.py | 43 | 10 | 4 | 0 |
| branch_manager.py | 119 | 29 | 11 | 1 |
| diagram.py | 123 | 41 | 8 | 1 |
| gitops.py | 101 | 33 | 10 | 1 |
| history.py | 75 | 29 | 7 | 1 |
| config.py | 68 | 14 | 4 | 1 |
| llm.py | 48 | 6 | 1 | 0 |
| workspace.py | 17 | 4 | 2 | 0 |

## 💡 Recommendations

- **Complexity**: Break down complex functions into smaller, focused units
- **Nesting**: Use early returns (guard clauses) to reduce nesting
- **Impact**: High-impact changes detected - ensure thorough testing

