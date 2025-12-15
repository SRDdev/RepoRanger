# src/agents/scribe.py
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import RepoState
from src.utils.llm import get_llm
from src.utils.workspace import save_artifact
from src.tools.gitops import GitOps
from src.utils.config import cfg

# You can move this to src/prompts/scribe.yaml later if you like
SCRIBE_SYSTEM_PROMPT = """You are the 'Contextual Scribe'.
Your goal is to write clear, context-aware PR documentation.
Focus on the 'Why' and the architectural impact, not just line-by-line changes.
"""

def scribe_node(state: RepoState) -> RepoState:
    print("--- ✍️  Scribe: Drafting Documentation ---")
    
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    target_branch = state.get("target_branch", "HEAD")
    
    # 1. Get Context (Diff)
    git_ops = GitOps(repo_path)
    diff = git_ops.get_diff()
    
    if not diff:
        return {"messages": [HumanMessage(content="Scribe found no changes to document.")]}

    # 2. Call LLM (Creative Mode)
    # We use a 'creative' profile if available in config, else default
    llm = get_llm("creative") 
    
    prompt = [
        SystemMessage(content=SCRIBE_SYSTEM_PROMPT),
        HumanMessage(content=f"""
        Generate a Pull Request description for these changes:
        
        {diff[:8000]} # Truncate to prevent token overflow if huge
        """)
    ]
    
    response = llm.invoke(prompt)
    
    # 3. Save Artifact
    doc_path = save_artifact(response.content, "md")
    
    print("--- ✍️  Scribe: Documentation Generated ---")

    return {
        "artifacts": [{
            "id": "pr_docs",
            "type": "markdown_doc",
            "file_path": doc_path,
            "description": "Generated PR Documentation",
            "created_by": "scribe"
        }],
        "messages": [response]
    }