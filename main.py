# main.py
import os
from dotenv import load_dotenv
from src.graph import app
from src.utils.config import cfg

# Load environment variables (API keys)
load_dotenv()

def main():
    print(f"🚀 Starting {cfg.get('project.name')}...")
    
    # Define initial state
    initial_state = {
        "repo_path": os.getcwd(),  # Run on current repo
        "target_branch": "HEAD",
        "artifacts": [],
        "messages": [],
        "code_issues": []
    }
    
    # Run the graph
    # stream_mode="values" prints the state after every step
    for event in app.stream(initial_state):
        pass # The agents already print to console, so we just let it flow

if __name__ == "__main__":
    main()