"""Unit tests for RepoCloner adapter."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from troller.worker.adapters.repo_cloner import RepoCloner


class TestRepoCloner:
    """Test suite for RepoCloner adapter."""

    @pytest.mark.asyncio
    async def test_clone_to_temp_clones_repository_with_default_branch(self) -> None:
        """clone_to_temp clones repository using main branch by default."""
        with patch("troller.worker.adapters.repo_cloner.subprocess.run") as mock_run:
            with patch(
                "troller.worker.adapters.repo_cloner.tempfile.mkdtemp"
            ) as mock_mkdtemp:
                # Setup mocks
                mock_mkdtemp.return_value = "/tmp/troller_testrepo_abc123"
                mock_run.return_value = MagicMock(returncode=0)

                # Test
                cloner = RepoCloner()
                temp_dir, clone_path = await cloner.clone_to_temp(
                    "testowner", "testrepo"
                )

                # Verify
                assert temp_dir == Path("/tmp/troller_testrepo_abc123")
                assert clone_path == Path("/tmp/troller_testrepo_abc123/testrepo")

                # Verify git clone was called correctly
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert call_args[0] == "git"
                assert call_args[1] == "clone"
                assert "--depth" in call_args
                assert "1" in call_args
                assert "--branch" in call_args
                assert "main" in call_args
                assert "https://github.com/testowner/testrepo.git" in call_args

    @pytest.mark.asyncio
    async def test_clone_to_temp_uses_specified_branch(self) -> None:
        """clone_to_temp uses target_branch when provided."""
        with patch("troller.worker.adapters.repo_cloner.subprocess.run") as mock_run:
            with patch("troller.worker.adapters.repo_cloner.tempfile.mkdtemp"):
                mock_run.return_value = MagicMock(returncode=0)

                cloner = RepoCloner()
                await cloner.clone_to_temp("owner", "repo", target_branch="develop")

                # Verify branch is used
                call_args = mock_run.call_args[0][0]
                assert "develop" in call_args

    @pytest.mark.asyncio
    async def test_clone_to_temp_falls_back_to_master_when_main_fails(self) -> None:
        """clone_to_temp tries master if main branch doesn't exist."""
        with patch("troller.worker.adapters.repo_cloner.subprocess.run") as mock_run:
            with patch("troller.worker.adapters.repo_cloner.tempfile.mkdtemp"):
                with patch("troller.worker.adapters.repo_cloner.shutil.rmtree"):
                    # First call (main) fails, second call (master) succeeds
                    mock_run.side_effect = [
                        subprocess.CalledProcessError(
                            1, "git", stderr="branch 'main' not found"
                        ),
                        MagicMock(returncode=0),
                    ]

                    cloner = RepoCloner()
                    temp_dir, clone_path = await cloner.clone_to_temp("owner", "repo")

                    # Verify both branches were tried
                    assert mock_run.call_count == 2
                    first_call_args = mock_run.call_args_list[0][0][0]
                    second_call_args = mock_run.call_args_list[1][0][0]
                    assert "main" in first_call_args
                    assert "master" in second_call_args

    @pytest.mark.asyncio
    async def test_clone_to_temp_raises_error_when_both_branches_fail(self) -> None:
        """clone_to_temp raises RuntimeError when both main and master fail."""
        with patch("troller.worker.adapters.repo_cloner.subprocess.run") as mock_run:
            with patch("troller.worker.adapters.repo_cloner.tempfile.mkdtemp"):
                with patch("troller.worker.adapters.repo_cloner.shutil.rmtree"):
                    # Both calls fail
                    mock_run.side_effect = subprocess.CalledProcessError(
                        1, "git", stderr="repository not found"
                    )

                    cloner = RepoCloner()
                    with pytest.raises(RuntimeError, match="Failed to clone"):
                        await cloner.clone_to_temp("owner", "repo")

    @pytest.mark.asyncio
    async def test_clone_to_temp_cleans_up_on_failure(self) -> None:
        """clone_to_temp cleans up temp directory when clone fails."""
        with patch("troller.worker.adapters.repo_cloner.subprocess.run") as mock_run:
            with patch("troller.worker.adapters.repo_cloner.tempfile.mkdtemp"):
                with patch(
                    "troller.worker.adapters.repo_cloner.shutil.rmtree"
                ) as mock_rmtree:
                    # Both calls fail
                    mock_run.side_effect = subprocess.CalledProcessError(
                        1, "git", stderr="error"
                    )

                    cloner = RepoCloner()
                    with pytest.raises(RuntimeError):
                        await cloner.clone_to_temp("owner", "repo")

                    # Verify cleanup was called
                    assert mock_rmtree.called

    @pytest.mark.asyncio
    async def test_clone_to_temp_does_not_fallback_when_specific_branch_fails(
        self,
    ) -> None:
        """clone_to_temp does not try master when specific branch is requested."""
        with patch("troller.worker.adapters.repo_cloner.subprocess.run") as mock_run:
            with patch("troller.worker.adapters.repo_cloner.tempfile.mkdtemp"):
                with patch("troller.worker.adapters.repo_cloner.shutil.rmtree"):
                    mock_run.side_effect = subprocess.CalledProcessError(
                        1, "git", stderr="branch not found"
                    )

                    cloner = RepoCloner()
                    with pytest.raises(RuntimeError):
                        await cloner.clone_to_temp(
                            "owner", "repo", target_branch="feature-x"
                        )

                    # Verify only one attempt was made
                    assert mock_run.call_count == 1

    def test_cleanup_removes_directory(self) -> None:
        """cleanup removes temporary directory."""
        with patch("troller.worker.adapters.repo_cloner.shutil.rmtree") as mock_rmtree:
            cloner = RepoCloner()
            cloner.cleanup(Path("/tmp/test_dir"))

            mock_rmtree.assert_called_once_with(
                Path("/tmp/test_dir"), ignore_errors=True
            )

    def test_cleanup_handles_nonexistent_directory(self) -> None:
        """cleanup handles cleanup of non-existent directory gracefully."""
        with patch("troller.worker.adapters.repo_cloner.shutil.rmtree") as mock_rmtree:
            cloner = RepoCloner()
            cloner.cleanup(Path("/tmp/nonexistent"))

            # Verify cleanup was called with ignore_errors
            mock_rmtree.assert_called_once()
            call_kwargs = mock_rmtree.call_args.kwargs
            assert call_kwargs.get("ignore_errors") is True
