# src/tools/diagram.py
from collections import defaultdict
from typing import List, Dict, Any, Set

from src.tools.parser import PythonCodeParser, ClassInfo, FileAnalysis

class MermaidGenerator:
    """
    Translates the rich metadata from PythonCodeParser into Mermaid.js visualizations.
    """

    def __init__(self, parser: PythonCodeParser):
        self.parser = parser

    def generate_architecture_map(self, files: List[str] = None) -> str:
        """
        Generates a high-level dependency graph of the modules with folder groupings.
        """
        graph = self.parser.get_dependency_graph(files)
        if not graph:
            return ""

        nodes: Set[str] = set()
        for src, targets in graph.items():
            nodes.add(src)
            nodes.update(targets)

        sections: Dict[str, List[str]] = defaultdict(list)
        for node in sorted(nodes):
            sections[self._classify_node(node)].append(node)

        mermaid = [
            "%% RepoRanger Dependency Graph",
            "graph TD",
            "    %% Styles",
            "    classDef Agents fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px;",
            "    classDef Tools fill:#e1f5fe,stroke:#0277bd,stroke-width:1.5px;",
            "    classDef Utils fill:#e8f5e9,stroke:#2e7d32;",
            "    classDef Core fill:#fff3e0,stroke:#ef6c00;",
            "    classDef Other fill:#eceff1,stroke:#455a64;",
            "    %% Legend",
            "    subgraph Legend[Legend]",
            "        LA[Agent Modules]:::Agents",
            "        LT[Tooling]:::Tools",
            "        LU[Utilities]:::Utils",
            "        LC[Core/Graph]:::Core",
            "        LO[Misc]:::Other",
            "    end",
        ]

        for section, items in sections.items():
            mermaid.append(f"    subgraph {section}")
            for path in items:
                node_id = self._clean_id(path)
                label = path.replace('src/', '')
                style = self._style_for_node(path)
                mermaid.append(f"        {node_id}[\"{label}\"]:::{style}")
            mermaid.append("    end")

        for source, targets in graph.items():
            src_id = self._clean_id(source)
            for target in targets:
                tgt_id = self._clean_id(target)
                mermaid.append(f"    {src_id} --> {tgt_id}")

        return "\n".join(mermaid)

    def generate_class_hierarchy(self, file_path: str) -> str:
        """
        Generates a detailed Class Diagram for a specific file.
        Uses the ClassInfo dataclass to show methods and attributes.
        """
        analysis = self.parser.analyze_file(file_path)
        if not analysis.classes:
            return ""

        mermaid = ["classDiagram"]
        
        for cls in analysis.classes:
            # 1. Define Class
            cls_name = cls.name
            mermaid.append(f"    class {cls_name}")
            
            # 2. Inheritance
            for base in cls.bases:
                mermaid.append(f"    {base} <|-- {cls_name}")
            
            # 3. Attributes (Fields)
            for attr in cls.attributes:
                mermaid.append(f"    {cls_name} : +{attr}")
                
            # 4. Methods
            for method in cls.methods:
                mermaid.append(f"    {cls_name} : +{method}()")
                
            # 5. Metadata Note (Complexity/Lines)
            # This is where your deep metrics shine!
            mermaid.append(f"    note for {cls_name} \"Line: {cls.line_number}\"")

        return "\n".join(mermaid)

    def generate_complexity_heatmap(self) -> str:
        """
        Uses the parser's metrics to create a visual heatmap.
        Files with high complexity are colored RED.
        """
        files = list(self.parser.file_analyses.keys())
        if not files:
            self.parser.get_dependency_graph()
            files = list(self.parser.file_analyses.keys())

        mermaid = [
            "%% RepoRanger Complexity Heatmap",
            "graph TD",
            "    %% Styles",
            "    classDef safe fill:#a5d6a7,stroke:#2e7d32;",
            "    classDef warning fill:#fff59d,stroke:#fbc02d;",
            "    classDef danger fill:#ef9a9a,stroke:#c62828;",
            "    classDef missing fill:#eceff1,stroke:#90a4ae,stroke-dasharray:5 5;",
            "    %% Legend",
            "    subgraph Legend[Legend]",
            "        LS[CC < 10]:::safe",
            "        LW[10 <= CC < 20]:::warning",
            "        LD[CC >= 20]:::danger",
            "    end",
        ]

        for f in sorted(files):
            analysis = self.parser.file_analyses[f]
            score = analysis.metrics.cyclomatic_complexity

            if score < 10:
                style = "safe"
            elif score < 20:
                style = "warning"
            else:
                style = "danger"

            clean_id = self._clean_id(f)
            label = f"{f} (CC: {score})"
            mermaid.append(f"    {clean_id}[\"{label}\"]:::{style}")

        return "\n".join(mermaid)

    def _clean_id(self, text: str) -> str:
        """Helper to sanitize strings for Mermaid IDs"""
        return text.replace("/", "_").replace(".", "_").replace("-", "_").replace("\\", "_")

    def _classify_node(self, path: str) -> str:
        if path.startswith("src/agents"):
            return "Agents"
        if path.startswith("src/tools"):
            return "Tools"
        if path.startswith("src/utils"):
            return "Utilities"
        if path.startswith("src/graph") or path.startswith("src/state") or path == "main.py":
            return "Core"
        return "Other"

    def _style_for_node(self, path: str) -> str:
        if path.startswith("src/agents"):
            return "Agents"
        if path.startswith("src/tools"):
            return "Tools"
        if path.startswith("src/utils"):
            return "Utils"
        if path.startswith("src/graph") or path.startswith("src/state") or path == "main.py":
            return "Core"
        return "Other"
