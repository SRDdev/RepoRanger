# 🛡️ Code Quality Report

**Analyzed Files:** 6  
**Issues Found:** 5  
**Generated:** 2025-12-17 03:41:45

## ⚠️ Warnings

- **`src/agents/architect.py:16`**
  - Function 'architect_node' has complexity 11
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/scribe.py:54`**
  - Function '_generate_system_documentation' has complexity 11
  - 💡 *Consider breaking into smaller functions*
- **`src/agents/tactician.py:16`**
  - Function 'tactician_node' has complexity 17
  - 💡 *Consider breaking into smaller functions*

<details>
<summary>ℹ️ Info (2 items)</summary>

- `main.py:3`: Unused import: re
- `main.py:6`: Unused import: datetime

</details>

## 📊 Code Metrics

| File | LOC | Complexity | Functions | Classes |
|------|-----|------------|-----------|----------|
| main.py | 122 | 32 | 8 | 0 |
| architect.py | 78 | 11 | 1 | 0 |
| scribe.py | 120 | 44 | 10 | 0 |
| tactician.py | 95 | 26 | 3 | 0 |
| gitops.py | 101 | 33 | 10 | 1 |
| workspace.py | 16 | 4 | 2 | 0 |

## 💡 Recommendations

- **Complexity**: Break down complex functions into smaller, focused units

