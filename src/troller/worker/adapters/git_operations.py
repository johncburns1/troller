"""Git operations adapter for branch creation, commits, and pushes.

Adapter for executing Git commands in repository directories.
"""

import subprocess


class GitOperations:
    """Adapter for Git branch, commit, and push operations.

    This adapter handles git operations for creating branches, committing
    changes, and pushing to remote repositories. All operations execute in
    the specified repository directory.
    """

    async def create_branch(
        self, repo_path: str, branch_name: str, base_branch: str
    ) -> None:
        """Create a new Git branch from a base branch.

        Args:
            repo_path: Path to the Git repository.
            branch_name: Name of the new branch to create.
            base_branch: Name of the branch to branch from (e.g., 'main').

        Raises:
            RuntimeError: If git checkout command fails.
        """
        try:
            subprocess.run(
                ["git", "-C", repo_path, "checkout", "-b", branch_name, base_branch],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to create branch {branch_name} from {base_branch}: {e.stderr}"
            ) from e

    async def commit_changes(
        self, repo_path: str, message: str, files: list[str] | None
    ) -> None:
        """Commit changes to the Git repository.

        Args:
            repo_path: Path to the Git repository.
            message: Commit message.
            files: List of file paths to commit, or None to commit all changes.

        Raises:
            RuntimeError: If git add or git commit commands fail.
        """
        # Stage changes
        try:
            if files is None:
                # Add all changes
                subprocess.run(
                    ["git", "-C", repo_path, "add", "-A"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            else:
                # Add specific files
                subprocess.run(
                    ["git", "-C", repo_path, "add"] + files,
                    capture_output=True,
                    text=True,
                    check=True,
                )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to stage changes: {e.stderr}") from e

        # Commit staged changes
        try:
            subprocess.run(
                ["git", "-C", repo_path, "commit", "-m", message],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to commit changes: {e.stderr}") from e

    async def push_branch(
        self,
        repo_path: str,
        branch_name: str,
        force: bool = False,
        set_upstream: bool = False,
    ) -> None:
        """Push a branch to the remote repository.

        Args:
            repo_path: Path to the Git repository.
            branch_name: Name of the branch to push.
            force: Whether to force push (default: False).
            set_upstream: Whether to set upstream tracking (default: False).

        Raises:
            RuntimeError: If git push command fails.
        """
        try:
            cmd = ["git", "-C", repo_path, "push"]
            if force:
                cmd.append("--force")
            if set_upstream:
                cmd.append("--set-upstream")
            cmd.extend(["origin", branch_name])

            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to push branch {branch_name}: {e.stderr}"
            ) from e

    async def get_current_sha(self, repo_path: str) -> str:
        """Get the current HEAD commit SHA.

        Args:
            repo_path: Path to the Git repository.

        Returns:
            The full 40-character SHA-1 hash of the current HEAD commit.

        Raises:
            RuntimeError: If git rev-parse command fails.
        """
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get current commit SHA: {e.stderr}") from e
