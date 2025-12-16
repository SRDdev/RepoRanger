# src/graph.py - COMPLETELY REWRITTEN FOR CLARITY
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


# Routing function for START
def route_start(state: RepoState) -> str:
    """Determine first node based on mode"""
    mode = state.get("mode", "full")
    
    if mode == "commit":
        return "scribe"  # Commit mode: Skip everything, go to Scribe
    elif mode == "audit":
        return "steward"  # Audit mode: Only Steward
    elif mode == "pr":
        return "steward"  # PR mode: Steward → Scribe (skip Architect for speed)
    else:  # "full"
        return "architect"  # Full analysis: Start from Architect


# Routing function for Steward
def route_steward(state: RepoState) -> str:
    """Determine next node after Steward"""
    mode = state.get("mode", "full")
    
    if mode == "audit":
        return "END"  # Audit mode: Stop after Steward
    elif mode == "pr":
        return "scribe"  # PR mode: Go directly to Scribe
    else:  # "full"
        return "tactician"  # Full mode: Continue to Tactician


# Routing function for Tactician
def route_tactician(state: RepoState) -> str:
    """After Tactician, always go to Scribe"""
    return "scribe"


# Routing function for Scribe
def route_scribe(state: RepoState) -> str:
    """After Scribe, always end"""
    return "END"


# Define conditional edges
workflow.add_conditional_edges(
    START,
    route_start,
    {
        "architect": "architect",
        "steward": "steward",
        "scribe": "scribe"
    }
)

# Architect always goes to Steward
workflow.add_edge("architect", "steward")

# Steward routing
workflow.add_conditional_edges(
    "steward",
    route_steward,
    {
        "tactician": "tactician",
        "scribe": "scribe",
        "END": END
    }
)

# Tactician routing
workflow.add_conditional_edges(
    "tactician",
    route_tactician,
    {
        "scribe": "scribe"
    }
)

# Scribe routing (always END)
workflow.add_conditional_edges(
    "scribe",
    route_scribe,
    {
        "END": END
    }
)

# Compile
app = workflow.compile()