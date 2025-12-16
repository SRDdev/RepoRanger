"""
Smart Branch Manager - AI-Powered Branch Creation
"""
import re
from typing import Optional, Tuple
from src.tools.gitops import GitOps
from src.utils.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
import textwrap


class BranchManager:
    """
    Intelligent branch name generator and manager.
    Follows semantic branching conventions.
    """
    
    BRANCH_TYPES = {
        "feat": "New feature or enhancement",
        "fix": "Bug fix",
        "hotfix": "Critical production fix",
        "refactor": "Code refactoring (no functionality change)",
        "perf": "Performance improvement",
        "docs": "Documentation only",
        "test": "Adding or updating tests",
        "chore": "Maintenance tasks (dependencies, config, etc.)",
        "style": "Code style/formatting changes",
        "ci": "CI/CD pipeline changes",
        "build": "Build system changes",
        "revert": "Revert previous changes"
    }
    
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops
        self.llm = get_llm("default")
    
    def create_smart_branch(
        self, 
        user_intent: str,
        auto_detect_type: bool = True,
        suggested_type: Optional[str] = None,
        create_initial_commit: bool = False
    ) -> Tuple[str, str]:
        """
        Create a smart branch with AI-generated name.
        
        Args:
            user_intent: User's description of what they want to do
            auto_detect_type: Let AI determine branch type
            suggested_type: Override AI detection with specific type
            create_initial_commit: Create an initial commit documenting intent
            
        Returns:
            Tuple of (branch_name, branch_type)
        """
        # 1. Determine branch type
        if suggested_type and suggested_type in self.BRANCH_TYPES:
            branch_type = suggested_type
        elif auto_detect_type:
            branch_type = self._detect_branch_type(user_intent)
        else:
            branch_type = "feat"  # Default
        
        # 2. Generate clean branch name
        branch_name = self._generate_branch_name(user_intent, branch_type)
        
        # 3. Validate branch name
        branch_name = self._sanitize_branch_name(branch_name)
        
        # 4. Check if branch already exists
        branch_name = self._ensure_unique_name(branch_name)
        
        # 5. Create the branch
        result = self.git_ops.switch_branch(branch_name, create_new=True)
        
        # 6. Optionally create initial commit
        if create_initial_commit and "Successfully" in result:
            self._create_initial_commit(user_intent, branch_type, branch_name)
        
        return branch_name, branch_type
    
    def _detect_branch_type(self, user_intent: str) -> str:
        """
        Use LLM to intelligently detect branch type from user intent.
        """
        prompt = textwrap.dedent(f"""
        You are a Git expert. Analyze the user's intent and determine the branch type.
        
        Available branch types:
        {self._format_branch_types()}
        
        User Intent:
        "{user_intent}"
        
        Rules:
        - Return ONLY the branch type keyword (e.g., "feat", "fix", "refactor")
        - Choose the most appropriate type
        - Default to "feat" if unclear
        
        Examples:
        Intent: "Add user authentication"           → feat
        Intent: "Fix login crash on iOS"            → fix
        Intent: "Improve database query performance" → perf
        Intent: "Update README installation steps"   → docs
        Intent: "Production API is down"             → hotfix
        Intent: "Clean up code in parser module"     → refactor
        
        Output only the type keyword, nothing else.
        """)
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="You are a Git branching expert."),
                HumanMessage(content=prompt)
            ])
            
            detected_type = response.content.strip().lower()
            
            # Validate response
            if detected_type in self.BRANCH_TYPES:
                return detected_type
            else:
                # Fallback: check if response contains a valid type
                for branch_type in self.BRANCH_TYPES.keys():
                    if branch_type in detected_type:
                        return branch_type
                
                return "feat"  # Default fallback
        
        except Exception as e:
            print(f"Warning: Could not detect branch type: {e}")
            return "feat"
    
    def _generate_branch_name(self, user_intent: str, branch_type: str) -> str:
        """
        Generate semantic branch name using LLM.
        """
        prompt = textwrap.dedent(f"""
        Generate a clean, semantic Git branch name.
        
        Branch Type: {branch_type}
        User Intent: "{user_intent}"
        
        Rules:
        1. Format: {branch_type}/scope-description
        2. Use kebab-case (lowercase with hyphens)
        3. Be concise but descriptive (3-6 words max)
        4. Use technical terms when appropriate
        5. No special characters except hyphens
        6. Maximum 50 characters total
        
        Examples:
        Type: feat, Intent: "Add OAuth2 login" 
        → feat/auth-oauth2-integration
        
        Type: fix, Intent: "Null pointer error in API"
        → fix/api-null-pointer-handling
        
        Type: refactor, Intent: "Improve parser performance"
        → refactor/parser-performance-optimization
        
        Type: docs, Intent: "Update installation guide"
        → docs/readme-installation-guide
        
        Output ONLY the branch name, nothing else.
        """)
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="You are a Git naming expert."),
                HumanMessage(content=prompt)
            ])
            
            branch_name = response.content.strip()
            
            # Remove any markdown formatting
            branch_name = branch_name.replace('`', '').replace('*', '')
            
            return branch_name
        
        except Exception as e:
            print(f"Warning: Could not generate branch name: {e}")
            # Fallback: create simple name from intent
            return self._fallback_branch_name(user_intent, branch_type)
    
    def _fallback_branch_name(self, user_intent: str, branch_type: str) -> str:
        """
        Create branch name without LLM (fallback).
        """
        # Clean and truncate intent
        clean_intent = re.sub(r'[^a-zA-Z0-9\s]', '', user_intent.lower())
        words = clean_intent.split()[:4]  # Max 4 words
        description = '-'.join(words)
        
        return f"{branch_type}/{description}"
    
    def _sanitize_branch_name(self, branch_name: str) -> str:
        """
        Ensure branch name follows Git naming rules.
        """
        # Remove invalid characters
        branch_name = re.sub(r'[^a-z0-9/_-]', '-', branch_name.lower())
        
        # Remove consecutive hyphens
        branch_name = re.sub(r'-+', '-', branch_name)
        
        # Remove leading/trailing hyphens or slashes
        branch_name = branch_name.strip('-/')
        
        # Ensure it starts with type/
        if '/' not in branch_name:
            branch_name = f"feat/{branch_name}"
        
        # Limit length
        if len(branch_name) > 50:
            parts = branch_name.split('/')
            if len(parts) == 2:
                type_part = parts[0]
                desc_part = parts[1][:40]  # Truncate description
                branch_name = f"{type_part}/{desc_part}"
        
        return branch_name
    
    def _ensure_unique_name(self, branch_name: str) -> str:
        """
        Ensure branch name is unique. Append number if exists.
        """
        original_name = branch_name
        counter = 1
        
        while self._branch_exists(branch_name):
            branch_name = f"{original_name}-{counter}"
            counter += 1
        
        return branch_name
    
    def _branch_exists(self, branch_name: str) -> bool:
        """Check if branch exists locally or remotely."""
        try:
            # Check local
            self.git_ops.repo.git.rev_parse("--verify", branch_name)
            return True
        except:
            try:
                # Check remote
                self.git_ops.repo.git.rev_parse("--verify", f"origin/{branch_name}")
                return True
            except:
                return False
    
    def _create_initial_commit(self, user_intent: str, branch_type: str, branch_name: str):
        """
        Create an initial commit documenting the branch purpose.
        """
        commit_message = textwrap.dedent(f"""
        {branch_type}: Initialize {branch_name.split('/')[-1]} branch
        
        Purpose: {user_intent}
        
        This branch was created to: {user_intent}
        Branch type: {branch_type} ({self.BRANCH_TYPES[branch_type]})
        """).strip()
        
        # Create .branch_context file
        context_content = textwrap.dedent(f"""
        # Branch Context
        
        **Branch:** `{branch_name}`
        **Type:** `{branch_type}` - {self.BRANCH_TYPES[branch_type]}
        **Created:** {self._get_timestamp()}
        
        ## Purpose
        {user_intent}
        
        ## Checklist
        - [ ] Implement core functionality
        - [ ] Add tests
        - [ ] Update documentation
        - [ ] Code review
        """).strip()
        
        try:
            with open(".branch_context", "w") as f:
                f.write(context_content)
            
            self.git_ops.commit_changes(commit_message, [".branch_context"])
            print(f"    ✅ Created initial commit with branch context")
        except Exception as e:
            print(f"    ⚠️  Could not create initial commit: {e}")
    
    def _format_branch_types(self) -> str:
        """Format branch types for prompt."""
        lines = []
        for key, desc in self.BRANCH_TYPES.items():
            lines.append(f"  - {key}: {desc}")
        return "\n".join(lines)
    
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")