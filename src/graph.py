# src/graph.py - UPDATED FOR INTEGRATED DOCUMENTATION FLOW
from langgraph.graph import StateGraph, START, END
from src.state import RepoState
from src.agents.architect import architect_node
from src.agents.steward import steward_node
from src.agents.scribe import scribe_node
from src.agents.tactician import tactician_node

# Initialize the Graph
workflow = StateGraph(RepoState)

# Add all nodes
workflow.add_node("architect", architect_node)
workflow.add_node("steward", steward_node)
workflow.add_node("tactician", tactician_node)
workflow.add_node("scribe", scribe_node)

# --- Routing Functions ---

def route_start(state: RepoState) -> str:
    """Determine first node based on mode"""
    mode = state.get("mode", "full")
    
    if mode == "commit":
        # Commit mode: Jump straight to Scribe for message generation
        return "scribe"
    elif mode == "docs":
        # Docs mode: Skip Architect/Tactician for a direct system overview
        return "steward" 
    elif mode == "audit":
        return "steward"
    elif mode == "pr":
        return "steward"
    else:  # "full"
        return "architect"

def route_steward(state: RepoState) -> str:
    """Determine next node after Steward analysis"""
    mode = state.get("mode", "full")
    
    if mode == "audit":
        return "END"
    elif mode in ["pr", "docs"]:
        # PR and Docs modes go directly to Scribe for drafting
        return "scribe"
    else:
        return "tactician"

def route_tactician(state: RepoState) -> str:
    """Tactician always leads to the Scribe for final documentation"""
    return "scribe"

def route_scribe(state: RepoState) -> str:
    """Scribe is the final step in the documentation and commit workflow"""
    return "END"

# --- Define Edges ---

workflow.add_conditional_edges(
    START,
    route_start,
    {
        "architect": "architect",
        "steward": "steward",
        "scribe": "scribe"
    }
)

# Standard flow: Architect -> Steward
workflow.add_edge("architect", "steward")

# Steward conditional routing
workflow.add_conditional_edges(
    "steward",
    route_steward,
    {
        "tactician": "tactician",
        "scribe": "scribe",
        "END": END
    }
)

# Tactician to Scribe
workflow.add_edge("tactician", "scribe")

# Scribe to END
workflow.add_edge("scribe", END)

# Compile the application
app = workflow.compile()