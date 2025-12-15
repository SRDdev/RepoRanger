# src/graph.py
from langgraph.graph import StateGraph, START, END

# Import the State
from src.state import RepoState

# Import the Nodes (Skills)
from src.agents.architect import architect_node
from src.agents.steward import steward_node
from src.agents.scribe import scribe_node
from src.agents.tactician import tactician_node

# 1. Initialize the Graph
workflow = StateGraph(RepoState)

# 2. Add Nodes
workflow.add_node("architect", architect_node)
workflow.add_node("steward", steward_node)
workflow.add_node("tactician", tactician_node)
workflow.add_node("scribe", scribe_node)

# 3. Define Edges (The Logic Flow)
# Start -> Architect
workflow.add_edge(START, "architect")

# Architect -> Steward
workflow.add_edge("architect", "steward")

# Steward -> Tactician 
# (Tactician decides if it needs to branch based on Steward's output)
workflow.add_edge("steward", "tactician")

# Tactician -> Scribe 
# (Scribe writes the final summary of everything that happened)
workflow.add_edge("tactician", "scribe")

# Scribe -> End
workflow.add_edge("scribe", END)

# 4. Compile the Graph
app = workflow.compile()