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
    # --- CONVERSATION (The Context) ---
    # Standard chat history. We still keep this, but we carefully manage what goes in.
    messages: Annotated[List[BaseMessage], operator.add]

    # --- CONFIGURATION (Lightweight) ---
    repo_path: str
    target_branch: str
    
    # --- THE REGISTRY (The "Library Card Catalog") ---
    # Instead of 'diff_context: str', we have a list of available artifacts.
    # The LLM can ask to "read" a specific artifact if it really needs to.
    artifacts: Annotated[List[Artifact], operator.add]

    # --- FLOW CONTROL ---
    # Used to route between nodes (e.g., "scribe", "architect", "end")
    next_node: str
    errors: Annotated[List[str], operator.add]