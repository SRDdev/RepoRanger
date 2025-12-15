# RepoRanger

**Your Autonomous DevOps & Documentation Partner.**

RepoRanger is an agentic AI system built with **LangChain** and **LangGraph**. It doesn't just chat with your code; it actively maintains it. It acts as a Senior Engineer that lives in your repository, handling documentation, code quality, git operations, and system visualization autonomously.

## 🧠 Skills (Agents)

RepoRanger operates using a multi-agent orchestration graph. Each node in the graph represents a specialized skill:

### 1. The Contextual Scribe ✍️
* **Role:** Documentation & PR Storytelling.
* **Capability:** Analyzes the *intent* behind code changes, not just the diff. Generates rich PR descriptions, updates `CHANGELOG.md` based on semantic analysis, and ensures documentation stays in sync with code logic.

### 2. The Code Steward 🛡️
* **Role:** Proactive Maintenance.
* **Capability:** Audits dependencies for security risks, identifies dead code, and enforces code style. It can auto-fix linting errors and push the clean-up commits directly to your branch.

### 3. The Git Tactician ⚔️
* **Role:** Complex Version Control.
* **Capability:** Handles "messy" git operations. Capable of semantic merge conflict resolution, smart cherry-picking across branches, and cleaning up stale feature branches safely.

### 4. The Visual Architect 📐
* **Role:** Dynamic Visualization.
* **Capability:** Auto-generates Mermaid.js diagrams for class hierarchies, dependency graphs, and logic flows. If the code structure changes, the diagrams in your docs update automatically.

## 🛠️ Tech Stack

* **Orchestration:** LangGraph (Stateful multi-agent workflows)
* **Framework:** LangChain
* **LLM:** GPT-4o / Claude 3.5 Sonnet
* **Git Operations:** GitPython
* **Parsing:** Tree-sitter / AST

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* Poetry (recommended) or Pip
* GitHub Personal Access Token (PAT)

### Installation

1.  **Clone the RepoRanger:**
    ```bash
    git clone [https://github.com/yourusername/reporanger.git](https://github.com/yourusername/reporanger.git)
    cd reporanger
    ```

2.  **Install Dependencies:**
    ```bash
    poetry install
    # OR
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    ```bash
    cp .env.example .env
    # Add your OPENAI_API_KEY and GITHUB_ACCESS_TOKEN
    ```

4.  **Run the Agent:**
    ```bash
    python main.py
    ```

## 🤝 Contributing
Contributions are welcome! Please ensure that any PR includes updated tests.

## 📄 License
MIT