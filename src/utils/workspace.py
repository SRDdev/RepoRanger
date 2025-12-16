"""
Utility for managing the RepoRanger workspace and artifact persistence.
Optimized to overwrite existing artifacts to maintain a clean workspace.
"""
import os
from typing import Optional
from src.utils.config import cfg

# Load workspace directory from config or default
WORKSPACE_DIR = cfg.get("paths.workspace", "./.reporanger_workspace")

def save_artifact(content: str, extension: str, prefix: Optional[str] = None) -> str:
    """
    Saves content to the workspace. Overwrites existing files with the same prefix.
    
    Args:
        content: The string content to save.
        extension: File extension (e.g., 'md', 'mmd', 'txt').
        prefix: Optional descriptive name for the filename.
    """
    if not os.path.exists(WORKSPACE_DIR):
        os.makedirs(WORKSPACE_DIR)
    
    if prefix:
        # Example: code_quality_report.md
        filename = f"{prefix}.{extension}"
    else:
        # Fallback if no prefix is provided
        filename = f"latest_artifact.{extension}"
    
    filepath = os.path.join(WORKSPACE_DIR, filename)
    
    # Writing with 'w' naturally overwrites the existing file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    return filepath

def load_artifact(filepath: str) -> str:
    """Reads artifact data from disk back into memory."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()