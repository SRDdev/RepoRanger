"""
Docstring for src.utils.workspace
"""
import os
import uuid
from typing import Dict

# TODO : This should come from config
WORKSPACE_DIR = "./.reporanger_workspace"

def save_artifact(content:str, extension:str):
    """
    Saves a string to a file and returns the path.
    Used by agents to dump heavy data.
    """
    if not os.path.exists(WORKSPACE_DIR):
        os.makedirs(WORKSPACE_DIR)
    
    filename = f"{uuid.uuid4()}.{extension}"
    filepath = os.path.join(WORKSPACE_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    return filepath

def load_artifact(filepath: str) -> str:
    """
    Reads the heavy data back into memory only when needed.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()