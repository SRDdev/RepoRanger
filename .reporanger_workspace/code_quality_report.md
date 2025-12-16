# 🛡️ Code Quality Report

**Analyzed Files:** 11  
**Issues Found:** 10  
**Generated:** 2025-12-17 03:33:59

## ⚠️ Warnings

- **`src/agents/architect.py:16`**
  - Function 'architect_node' has complexity 11
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/scribe.py:54`**
  - Function '_generate_system_documentation' has complexity 11
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
  - Changes affect 8 other files
- **`src/utils/workspace.py`**
  - Changes affect 6 other files

<details>
<summary>ℹ️ Info (2 items)</summary>

- `main.py:3`: Unused import: re
- `main.py:6`: Unused import: datetime

</details>

## 📊 Code Metrics

| File | LOC | Complexity | Functions | Classes |
|------|-----|------------|-----------|----------|
| cli.py | 43 | 11 | 7 | 0 |
| main.py | 122 | 32 | 8 | 0 |
| architect.py | 78 | 11 | 1 | 0 |
| scribe.py | 120 | 44 | 10 | 0 |
| steward.py | 222 | 62 | 4 | 0 |
| tactician.py | 95 | 26 | 3 | 0 |
| graph.py | 43 | 10 | 4 | 0 |
| branch_manager.py | 119 | 29 | 11 | 1 |
| diagram.py | 123 | 41 | 8 | 1 |
| gitops.py | 101 | 33 | 10 | 1 |
| workspace.py | 16 | 4 | 2 | 0 |

## 💡 Recommendations

- **Complexity**: Break down complex functions into smaller, focused units
- **Impact**: High-impact changes detected - ensure thorough testing

