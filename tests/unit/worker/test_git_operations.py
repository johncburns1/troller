"""Unit tests for GitOperations adapter."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from troller.worker.adapters.git_operations import GitOperations


class TestGitOperations:
    """Test suite for GitOperations adapter."""

    @pytest.mark.asyncio
    async def test_create_branch_creates_new_branch_from_base(self) -> None:
        """create_branch creates a new branch from the specified base branch."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            git_ops = GitOperations()
            await git_ops.create_branch(
                repo_path="/tmp/test_repo",
                branch_name="feature/test-branch",
                base_branch="main",
            )

            # Verify git checkout command was called
            assert mock_run.call_count == 1
            call_args = mock_run.call_args[0][0]
            assert call_args == [
                "git",
                "-C",
                "/tmp/test_repo",
                "checkout",
                "-b",
                "feature/test-branch",
                "main",
            ]
            assert mock_run.call_args[1]["capture_output"] is True
            assert mock_run.call_args[1]["text"] is True
            assert mock_run.call_args[1]["check"] is True

    @pytest.mark.asyncio
    async def test_create_branch_raises_error_on_failure(self) -> None:
        """create_branch raises RuntimeError when git command fails."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "git", stderr="branch already exists"
            )

            git_ops = GitOperations()
            with pytest.raises(
                RuntimeError, match="Failed to create branch feature/test"
            ):
                await git_ops.create_branch(
                    repo_path="/tmp/test_repo",
                    branch_name="feature/test",
                    base_branch="main",
                )

    @pytest.mark.asyncio
    async def test_commit_changes_commits_specific_files(self) -> None:
        """commit_changes commits only the specified files."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            # First call (add) succeeds, second call (diff --cached) returns 1 (has changes),
            # third call (commit) succeeds
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git add
                MagicMock(returncode=1),  # git diff --cached --quiet (1 = has changes)
                MagicMock(returncode=0),  # git commit
            ]

            git_ops = GitOperations()
            await git_ops.commit_changes(
                repo_path="/tmp/test_repo",
                message="Test commit message",
                files=["file1.py", "file2.py"],
            )

            # Verify git add, git diff --cached, and git commit were called
            assert mock_run.call_count == 3

            # Check git add call
            add_call_args = mock_run.call_args_list[0][0][0]
            assert add_call_args[:3] == ["git", "-C", "/tmp/test_repo"]
            assert add_call_args[3] == "add"
            assert "file1.py" in add_call_args
            assert "file2.py" in add_call_args

            # Check git diff --cached --quiet call (verifies staged changes exist)
            diff_call_args = mock_run.call_args_list[1][0][0]
            assert diff_call_args == [
                "git",
                "-C",
                "/tmp/test_repo",
                "diff",
                "--cached",
                "--quiet",
            ]

            # Check git commit call
            commit_call_args = mock_run.call_args_list[2][0][0]
            assert commit_call_args == [
                "git",
                "-C",
                "/tmp/test_repo",
                "commit",
                "-m",
                "Test commit message",
            ]

    @pytest.mark.asyncio
    async def test_commit_changes_commits_all_files_when_files_is_none(self) -> None:
        """commit_changes commits all changes when files parameter is None."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            # First call (add) succeeds, second call (diff --cached) returns 1 (has changes),
            # third call (commit) succeeds
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git add -A
                MagicMock(returncode=1),  # git diff --cached --quiet (1 = has changes)
                MagicMock(returncode=0),  # git commit
            ]

            git_ops = GitOperations()
            await git_ops.commit_changes(
                repo_path="/tmp/test_repo",
                message="Commit all changes",
                files=None,
            )

            # Verify git add, git diff --cached, and git commit were called
            assert mock_run.call_count == 3

            # Check git add call (should use -A for all files)
            add_call_args = mock_run.call_args_list[0][0][0]
            assert add_call_args == ["git", "-C", "/tmp/test_repo", "add", "-A"]

            # Check git diff --cached --quiet call (verifies staged changes exist)
            diff_call_args = mock_run.call_args_list[1][0][0]
            assert diff_call_args == [
                "git",
                "-C",
                "/tmp/test_repo",
                "diff",
                "--cached",
                "--quiet",
            ]

            # Check git commit call
            commit_call_args = mock_run.call_args_list[2][0][0]
            assert commit_call_args == [
                "git",
                "-C",
                "/tmp/test_repo",
                "commit",
                "-m",
                "Commit all changes",
            ]

    @pytest.mark.asyncio
    async def test_commit_changes_raises_error_on_add_failure(self) -> None:
        """commit_changes raises RuntimeError when git add fails."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "git", output="", stderr="file not found"
            )

            git_ops = GitOperations()
            with pytest.raises(RuntimeError, match="Failed to stage changes.*file not found"):
                await git_ops.commit_changes(
                    repo_path="/tmp/test_repo",
                    message="Test commit",
                    files=["missing.py"],
                )

    @pytest.mark.asyncio
    async def test_commit_changes_raises_error_on_commit_failure(self) -> None:
        """commit_changes raises RuntimeError when git commit fails."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            # First call (git add) succeeds, second call (diff --cached) returns 1 (has changes),
            # third call (git commit) fails
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git add
                MagicMock(returncode=1),  # git diff --cached --quiet (1 = has changes)
                subprocess.CalledProcessError(
                    1, "git", output="nothing to commit", stderr=""
                ),
            ]

            git_ops = GitOperations()
            with pytest.raises(RuntimeError, match="Failed to commit changes.*nothing to commit"):
                await git_ops.commit_changes(
                    repo_path="/tmp/test_repo",
                    message="Test commit",
                    files=None,
                )

    @pytest.mark.asyncio
    async def test_commit_changes_raises_error_when_no_changes_staged(self) -> None:
        """commit_changes raises RuntimeError when git add stages no changes."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            # First call (git add) succeeds, second call (diff --cached) returns 0 (no changes)
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git add
                MagicMock(returncode=0),  # git diff --cached --quiet (0 = no changes)
            ]

            git_ops = GitOperations()
            with pytest.raises(
                RuntimeError, match="No changes to commit after git add"
            ):
                await git_ops.commit_changes(
                    repo_path="/tmp/test_repo",
                    message="Test commit",
                    files=None,
                )

    @pytest.mark.asyncio
    async def test_push_branch_pushes_to_remote(self) -> None:
        """push_branch pushes the specified branch to remote."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            git_ops = GitOperations()
            await git_ops.push_branch(
                repo_path="/tmp/test_repo",
                branch_name="feature/test-branch",
                force=False,
            )

            # Verify git push command was called
            assert mock_run.call_count == 1
            call_args = mock_run.call_args[0][0]
            assert call_args == [
                "git",
                "-C",
                "/tmp/test_repo",
                "push",
                "origin",
                "feature/test-branch",
            ]

    @pytest.mark.asyncio
    async def test_push_branch_uses_force_flag_when_requested(self) -> None:
        """push_branch uses --force flag when force parameter is True."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            git_ops = GitOperations()
            await git_ops.push_branch(
                repo_path="/tmp/test_repo",
                branch_name="feature/test-branch",
                force=True,
            )

            # Verify git push command includes --force
            call_args = mock_run.call_args[0][0]
            assert call_args == [
                "git",
                "-C",
                "/tmp/test_repo",
                "push",
                "--force",
                "origin",
                "feature/test-branch",
            ]

    @pytest.mark.asyncio
    async def test_push_branch_raises_error_on_failure(self) -> None:
        """push_branch raises RuntimeError when git push fails."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "git", stderr="remote rejected"
            )

            git_ops = GitOperations()
            with pytest.raises(RuntimeError, match="Failed to push branch"):
                await git_ops.push_branch(
                    repo_path="/tmp/test_repo",
                    branch_name="feature/test-branch",
                )

    @pytest.mark.asyncio
    async def test_push_branch_uses_set_upstream_flag_when_requested(self) -> None:
        """push_branch uses --set-upstream flag when set_upstream parameter is True."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            git_ops = GitOperations()
            await git_ops.push_branch(
                repo_path="/tmp/test_repo",
                branch_name="feature/new-branch",
                set_upstream=True,
            )

            # Verify git push command includes --set-upstream
            call_args = mock_run.call_args[0][0]
            assert call_args == [
                "git",
                "-C",
                "/tmp/test_repo",
                "push",
                "--set-upstream",
                "origin",
                "feature/new-branch",
            ]

    @pytest.mark.asyncio
    async def test_push_branch_combines_force_and_set_upstream_flags(self) -> None:
        """push_branch uses both --force and --set-upstream when both are True."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            git_ops = GitOperations()
            await git_ops.push_branch(
                repo_path="/tmp/test_repo",
                branch_name="feature/branch",
                force=True,
                set_upstream=True,
            )

            # Verify both flags are included
            call_args = mock_run.call_args[0][0]
            assert call_args == [
                "git",
                "-C",
                "/tmp/test_repo",
                "push",
                "--force",
                "--set-upstream",
                "origin",
                "feature/branch",
            ]

    @pytest.mark.asyncio
    async def test_get_current_sha_returns_commit_sha(self) -> None:
        """get_current_sha returns the current HEAD commit SHA."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc123def456789012345678901234567890abcd\n",
            )

            git_ops = GitOperations()
            sha = await git_ops.get_current_sha(repo_path="/tmp/test_repo")

            # Verify the SHA is returned (stripped of whitespace)
            assert sha == "abc123def456789012345678901234567890abcd"

            # Verify git rev-parse command was called
            call_args = mock_run.call_args[0][0]
            assert call_args == ["git", "-C", "/tmp/test_repo", "rev-parse", "HEAD"]

    @pytest.mark.asyncio
    async def test_get_current_sha_raises_error_on_failure(self) -> None:
        """get_current_sha raises RuntimeError when git rev-parse fails."""
        with patch("troller.worker.adapters.git_operations.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "git", stderr="not a git repository"
            )

            git_ops = GitOperations()
            with pytest.raises(RuntimeError, match="Failed to get current commit SHA"):
                await git_ops.get_current_sha(repo_path="/tmp/test_repo")
