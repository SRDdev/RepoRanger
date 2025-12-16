"""
State.py

Tiny Context: The LLM prompt looks like this:
"I have generated a diagram. Reference: {type: 'diagram', description: 'Auth Flow', path: './tmp/diagram.mmd'}" It does not see the 400 lines of Mermaid code unless it explicitly asks to read that file.
Persistance: If the script crashes, your artifacts are safe on disk (file_path), not lost in Python memory.
Modularity: The "Visual Architect" writes to a file. The "Scribe" reads that file later to include it in the README. They don't need to pass the string to each other.
"""
from typing import Annotated, List, TypedDict, Union, Dict, Any
import operator
from langchain_core.messages import BaseMessage


class Artifact(TypedDict):
    """
    Represents a heavy object (doc, diagram, diff) by reference.
    The LLM sees this summary, not the full content.
    """
    id: str             # Unique ID (e.g., "diff_1023")
    type: str           # e.g., "diff", "diagram_mermaid", "markdown_doc"
    file_path: str      # Location on disk where the actual data sits
    description: str    # Short summary: "Diff for auth.py (500 lines)"
    created_by: str     # Which agent made this?

class RepoState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    repo_path: str
    target_branch: str
    source_branch: str  # ADD THIS - current branch being merged
    artifacts: Annotated[List[Artifact], operator.add]
    next_node: str
    errors: Annotated[List[str], operator.add]
    code_issues: Annotated[List[str], operator.add]  # ADD THIS - for Steward output
    pr_metadata: Dict[str, Any]  # ADD THIS - commit counts, authors, etc.