"""
Utility for managing the RepoRanger workspace and artifact persistence.
"""
import os
import uuid
from typing import Optional
from src.utils.config import cfg

# Load workspace directory from config or default
WORKSPACE_DIR = cfg.get("paths.workspace", "./.reporanger_workspace")

def save_artifact(content: str, extension: str, prefix: Optional[str] = None) -> str:
    """
    Saves content to the workspace with a descriptive filename.
    
    Args:
        content: The string content to save.
        extension: File extension (e.g., 'md', 'mmd', 'txt').
        prefix: Optional descriptive prefix for the filename.
    """
    if not os.path.exists(WORKSPACE_DIR):
        os.makedirs(WORKSPACE_DIR)
    
    if prefix:
        # Create a readable name: prefix_shortid.extension
        short_id = str(uuid.uuid4())[:8]
        filename = f"{prefix}_{short_id}.{extension}"
    else:
        # Fallback to standard UUID
        filename = f"{uuid.uuid4()}.{extension}"
    
    filepath = os.path.join(WORKSPACE_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    return filepath

def load_artifact(filepath: str) -> str:
    """Reads artifact data from disk back into memory."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()