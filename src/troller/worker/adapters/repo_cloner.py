"""Repository cloning adapter.

Adapter for cloning Git repositories to temporary directories.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path


class RepoCloner:
    """Adapter for cloning Git repositories.

    This adapter handles git operations for cloning repositories
    to temporary directories with automatic branch fallback and cleanup.
    """

    async def clone_to_temp(
        self, repo_owner: str, repo_name: str, target_branch: str | None = None
    ) -> tuple[Path, Path, str]:
        """Clone repository to temporary directory with branch fallback.

        Clones a GitHub repository to a temporary directory using shallow clone
        for performance. If no branch is specified, tries 'main' first, then
        falls back to 'master' if 'main' doesn't exist.

        Args:
            repo_owner: GitHub repository owner (user or organization).
            repo_name: GitHub repository name.
            target_branch: Specific branch to clone. If None, tries main then master.

        Returns:
            Tuple of (temp_dir_path, cloned_repo_path, commit_sha) where
            temp_dir_path is the root temporary directory, cloned_repo_path is
            the repository directory inside it, and commit_sha is the HEAD
            commit SHA of the cloned repository.

        Raises:
            RuntimeError: If git clone fails for all attempted branches.
        """
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix=f"troller_{repo_name}_"))
        clone_path = temp_dir / repo_name

        # Construct repository URL
        repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"

        # Determine branch to clone
        branch = target_branch or "main"

        # Clone the repository (shallow clone for speed)
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    branch,
                    repo_url,
                    str(clone_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # Extract HEAD commit SHA
            commit_sha = self._get_head_commit(clone_path)

            return temp_dir, clone_path, commit_sha

        except subprocess.CalledProcessError:
            # If main branch doesn't exist and no specific branch was requested, try master
            if branch == "main" and target_branch is None:
                try:
                    subprocess.run(
                        [
                            "git",
                            "clone",
                            "--depth",
                            "1",
                            "--branch",
                            "master",
                            repo_url,
                            str(clone_path),
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )

                    # Extract HEAD commit SHA
                    commit_sha = self._get_head_commit(clone_path)

                    return temp_dir, clone_path, commit_sha

                except subprocess.CalledProcessError as e:
                    # Clean up and raise
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    raise RuntimeError(
                        f"Failed to clone {repo_url} on both main and master branches: {e.stderr}"
                    ) from e

            # Clean up and raise
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone {repo_url} on branch {branch}")

    def _get_head_commit(self, repo_path: Path) -> str:
        """Extract HEAD commit SHA from cloned repository.

        Args:
            repo_path: Path to cloned repository.

        Returns:
            Full 40-character SHA-1 hash of HEAD commit.

        Raises:
            RuntimeError: If git rev-parse fails.
        """
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def cleanup(self, temp_dir: Path) -> None:
        """Remove temporary directory safely.

        Args:
            temp_dir: Path to temporary directory to remove.
        """
        shutil.rmtree(temp_dir, ignore_errors=True)
