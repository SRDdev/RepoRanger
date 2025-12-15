# src/tools/diagram.py
from typing import List, Dict, Any
from src.tools.parser import PythonCodeParser, ClassInfo, FileAnalysis

class MermaidGenerator:
    """
    Translates the rich metadata from PythonCodeParser into Mermaid.js visualizations.
    """

    def __init__(self, parser: PythonCodeParser):
        self.parser = parser

    def generate_architecture_map(self, files: List[str] = None) -> str:
        """
        Generates a high-level dependency graph of the modules.
        """
        # Get the dependency graph from your powerful parser
        graph = self.parser.get_dependency_graph(files)
        
        mermaid = ["graph TD"]
        mermaid.append("    %% Styles")
        mermaid.append("    classDef component fill:#f9f,stroke:#333,stroke-width:2px;")
        mermaid.append("    classDef util fill:#e1f5fe,stroke:#01579b,stroke-dasharray: 5 5;")

        for source, targets in graph.items():
            # Clean paths for ID generation (src/utils/llm.py -> src_utils_llm)
            src_id = self._clean_id(source)
            src_label = source.split("/")[-1] # Show just filename
            
            # Apply styling logic based on path
            style = "component" if "agents" in source else "util"
            mermaid.append(f"    {src_id}[\"{src_label}\"]:::{style}")

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
            # Force analysis of all files if not done
            self.parser.get_dependency_graph()
            files = list(self.parser.file_analyses.keys())

        mermaid = ["graph TD"]
        mermaid.append("    %% Complexity Heatmap")
        mermaid.append("    classDef safe fill:#a5d6a7,stroke:#2e7d32;")
        mermaid.append("    classDef warning fill:#fff59d,stroke:#fbc02d;")
        mermaid.append("    classDef danger fill:#ef9a9a,stroke:#c62828;")

        for f in files:
            analysis = self.parser.file_analyses[f]
            score = analysis.metrics.cyclomatic_complexity
            
            # Classify based on your parser's complexity score
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