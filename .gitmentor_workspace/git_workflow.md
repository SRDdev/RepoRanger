# Git Workflow Instructions
**Current Branch:** docs/pr-commit-log-clarity
**Target Branch:** main
**Generated:** 2025-12-25 04:55:30
---

## Git Workflow
```bash
git add .
git commit -m 'docs: Update from RepoRanger analysis'
git push origin docs/pr-commit-log-clarity
gh pr create --base main --title 'Update from RepoRanger' --body-file PR_Document.md
```

## Generated Artifacts
* **System-wide dependency graph** (diagram)
  * Path: ./.gitmentor_workspace/dependency_graph.mmd
* **Cyclomatic Complexity Heatmap** (diagram)
  * Path: ./.gitmentor_workspace/complexity_heatmap.mmd
* **Architecture overview report** (markdown_doc)
  * Path: ./.gitmentor_workspace/architecture_overview.md
* **Code Quality Report (18 issues)** (markdown_doc)
  * Path: ./.gitmentor_workspace/code_quality_report.md
