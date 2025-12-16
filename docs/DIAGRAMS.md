# RepoRanger Diagram Guide

RepoRanger's Visual Architect agent produces fully embeddable Mermaid diagrams every time you run `python main.py`. The generated files are stored in `.reporanger_workspace/` and also collected in an inline Markdown artifact so you can copy/paste them into PRs, wikis, or dashboards.

## Artifacts produced
- `arch_dependency_graph.mmd` (ID: `arch_dependency_graph`): module dependency map with folder-based subgraphs and a legend.
- `arch_complexity_map.mmd` (ID: `arch_complexity_map`): cyclomatic complexity heatmap broken into safe/warning/danger buckets.
- `arch_overview_doc.md` (ID: `arch_overview_doc`): Markdown file that embeds both diagrams and explains how to reuse them.

## Viewing the diagrams
1. Open the Markdown artifact (look for `arch_overview_doc` in `.reporanger_workspace`).
2. Copy the ` ```mermaid ... ``` ` block into your documentation tool of choice.
3. If your viewer does not render Mermaid, use https://mermaid.live/ and paste the block to see the graph.

## Regenerating
Any code change will alter the diagrams automatically. Re-run `python main.py` and the artifacts will refresh with the latest dependency graph and complexity scores.
