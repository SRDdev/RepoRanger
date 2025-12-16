# src/tools/diagram.py
from collections import defaultdict
from typing import List, Dict, Any, Set
import os

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

    def generate_module_overview(self, file_path: str) -> str:
        """
        Generates a flowchart showing the internal structure of a module 
        (Classes and Functions). Perfect for folder-level documentation.
        """
        analysis = self.parser.analyze_file(file_path)
        if not analysis.classes and not analysis.functions:
            return ""

        clean_file_id = self._clean_id(file_path)
        mermaid = [
            f"%% Module Overview: {file_path}",
            "graph LR",
            "    classDef classNode fill:#e1f5fe,stroke:#01579b,stroke-width:2px;",
            "    classDef funcNode fill:#f1f8e9,stroke:#33691e,stroke-width:1px;",
        ]

        mermaid.append(f"    subgraph {clean_file_id}[\"{os.path.basename(file_path)}\"]")
        
        # Add Classes
        for cls in analysis.classes:
            cls_id = f"{clean_file_id}_{self._clean_id(cls.name)}"
            mermaid.append(f"        {cls_id}[[\"class: {cls.name}\"]]:::classNode")
            for method in cls.methods:
                method_id = f"{cls_id}_{self._clean_id(method)}"
                mermaid.append(f"        {cls_id} -.-> {method_id}(\"{method}()\")")

        # Add Standalone Functions
        for func in analysis.functions:
            func_id = f"{clean_file_id}_{self._clean_id(func.name)}"
            mermaid.append(f"        {func_id}(\"fn: {func.name}()\"):::funcNode")

        mermaid.append("    end")
        return "\n".join(mermaid)

    def generate_class_hierarchy(self, file_path: str) -> str:
        """
        Generates a detailed Class Diagram for a specific file.
       
        """
        analysis = self.parser.analyze_file(file_path)
        if not analysis.classes:
            return ""

        mermaid = ["classDiagram"]
        
        for cls in analysis.classes:
            cls_name = cls.name
            mermaid.append(f"    class {cls_name}")
            
            for base in cls.bases:
                mermaid.append(f"    {base} <|-- {cls_name}")
            
            for attr in cls.attributes:
                mermaid.append(f"    {cls_name} : +{attr}")
                
            for method in cls.methods:
                mermaid.append(f"    {cls_name} : +{method}()")
                
            mermaid.append(f"    note for {cls_name} \"Complexity Score: {cls.metrics.cyclomatic_complexity if hasattr(cls, 'metrics') else 'N/A'}\"")

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