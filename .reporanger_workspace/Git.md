# Git Workflow Instructions
**Current Branch:** ci/github-actions-configuration
**Target Branch:** main
**Generated:** 2025-12-17 03:23:13
---

## Git Workflow
```bash
git add .
git commit -m 'docs: Update from RepoRanger analysis'
git push origin ci/github-actions-configuration
gh pr create --base main --title 'Update from RepoRanger' --body-file PR_Document.md
```

## Generated Artifacts
* **System-wide dependency graph** (diagram)
  * Path: ./.reporanger_workspace/dependency_graph.mmd
* **Cyclomatic Complexity Heatmap** (diagram)
  * Path: ./.reporanger_workspace/complexity_heatmap.mmd
* **Architecture overview report** (markdown_doc)
  * Path: ./.reporanger_workspace/architecture_overview.md
* **Code Quality Report (9 issues)** (markdown_doc)
  * Path: ./.reporanger_workspace/code_quality_report.md
