import os
from typing import List, Optional
from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError


class GitOps:
    """
    High-level Git operations wrapper using GitPython.

    This class is designed to safely handle:
    - Normal repositories
    - Repositories with no commits (unborn HEAD)
    """

    def __init__(self, repo_path: str):
        """
        Initialize with the path to the local repository.
        """
        self.repo_path = repo_path

        try:
            self.repo = Repo(repo_path)
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise ValueError(f"Invalid git repository at '{repo_path}': {e}")
        except Exception as e:
            raise ValueError(f"Could not load repository at '{repo_path}': {e}")

    # ------------------------------------------------------------------
    # Repository State Helpers
    # ------------------------------------------------------------------

    def has_commits(self) -> bool:
        """
        Returns True if the repository has at least one commit.
        """
        return self.repo.head.is_valid()

    # ------------------------------------------------------------------
    # Branch Operations
    # ------------------------------------------------------------------

    def get_current_branch(self) -> str:
        """
        Returns the current branch name.
        """
        if not self.has_commits():
            return "UNBORN_HEAD"
        return self.repo.active_branch.name

    def switch_branch(self, branch_name: str, create_new: bool = False) -> str:
        """
        Switches to an existing branch or creates a new one.

        Branch creation and switching are not allowed if the repo
        has no commits yet.
        """
        try:
            if not self.has_commits():
                return (
                    "Repository has no commits yet. "
                    "Create an initial commit before switching branches."
                )

            if create_new:
                if branch_name in self.repo.heads:
                    self.repo.heads[branch_name].checkout()
                else:
                    new_branch = self.repo.create_head(branch_name)
                    new_branch.checkout()
            else:
                self.repo.git.checkout(branch_name)

            return f"Successfully switched to branch: {branch_name}"

        except GitCommandError as e:
            return f"Error switching branch: {e}"

    # ------------------------------------------------------------------
    # Diff & File Inspection
    # ------------------------------------------------------------------

    def get_diff(self, target_branch: Optional[str] = None) -> str:
        """
        Returns the diff of the working tree.

        - If target_branch is provided: diff against it
        - If commits exist: diff against HEAD
        - If no commits exist: diff of staged/working tree
        """
        try:
            if target_branch:
                return self.repo.git.diff(target_branch)
            if self.has_commits():
                return self.repo.git.diff("HEAD")
            return self.repo.git.diff()
        except GitCommandError as e:
            return f"Error getting diff: {e}"

    def get_file_content(self, file_path: str) -> str:
        """
        Reads and returns the content of a file in the repository.
        """
        full_path = os.path.join(self.repo_path, file_path)

        if not os.path.exists(full_path):
            return "File does not exist."

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    # ------------------------------------------------------------------
    # Commit & Push
    # ------------------------------------------------------------------

    def commit_changes(self, message: str, files: Optional[List[str]] = None) -> str:
        """
        Stages and commits changes.
        Handles initial commit (unborn HEAD) correctly.
        """
        try:
            if files:
                self.repo.index.add(files)
            else:
                self.repo.git.add(A=True)

            # ---- Initial commit (no HEAD yet) ----
            if not self.has_commits():
                self.repo.index.commit(message)
                return f"Initial commit created with message: '{message}'"

            # ---- Normal repo ----
            if not self.repo.index.diff("HEAD"):
                return "No changes to commit."

            self.repo.index.commit(message)
            return f"Committed changes with message: '{message}'"

        except Exception as e:
            return f"Error committing changes: {e}"

    def push_changes(
        self,
        remote_name: str = "origin",
        branch_name: Optional[str] = None,
    ) -> str:
        """
        Pushes the current branch to the specified remote.
        """
        try:
            if not self.has_commits():
                return "Cannot push: repository has no commits."

            if not branch_name:
                branch_name = self.repo.active_branch.name

            remote = self.repo.remote(name=remote_name)
            remote.push(branch_name)

            return f"Pushed '{branch_name}' to remote '{remote_name}'"

        except GitCommandError as e:
            return f"Error pushing changes: {e}"
