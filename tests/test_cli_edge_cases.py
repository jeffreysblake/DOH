#!/usr/bin/env python3
"""
Additional CLI tests for edge cases and error handling
"""

import os
import subprocess
import tempfile
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

# Import CLI commands
from doh.cli import main, config, add, status, list, run, squash, cleanup


class TestCliEdgeCases:
    """Test CLI edge cases and error handling"""

    def setup_method(self):
        """Set up test environment for each test"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.runner = CliRunner()

        # Save original config
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.test_dir)

    def teardown_method(self):
        """Clean up after each test"""
        if self.original_home:
            os.environ["HOME"] = self.original_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]

        if self.test_dir.exists():
            import shutil

            shutil.rmtree(self.test_dir)

    def create_git_repo(self, path: Path, with_changes=False):
        """Create a git repository for testing"""
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=path, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=path, check=True
        )

        # Create initial commit
        test_file = path / "README.md"
        test_file.write_text("# Test Project\n")
        subprocess.run(["git", "add", "."], cwd=path, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True)

        if with_changes:
            # Add some changes
            test_file.write_text("# Test Project\nWith changes\n")
            new_file = path / "new_file.txt"
            new_file.write_text("New content\n")

    def test_config_with_invalid_values(self):
        """Test config command with various threshold values"""
        # Test negative threshold (CLI accepts it, even if not ideal)
        # result = self.runner.invoke(config, ["--set", "--threshold", "-10"])
        assert result.exit_code == 0  # CLI doesn't validate, so it succeeds

        # Test zero threshold (CLI accepts it)
        # result = self.runner.invoke(config, ["--set", "--threshold", "0"])
        assert result.exit_code == 0

    def test_add_non_git_directory(self):
        """Test adding a non-git directory"""
        non_git_dir = self.test_dir / "not_git"
        non_git_dir.mkdir()

        # result = self.runner.invoke(add, [str(non_git_dir), "--name", "NotGit"])
        # Should handle gracefully
        assert result.exit_code == 0

    def test_add_with_invalid_threshold(self):
        """Test add command with invalid threshold"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir)

        # Test with negative threshold (CLI accepts it)
        # result = self.runner.invoke(add, [str(repo_dir), "--threshold", "-5"])
        assert result.exit_code == 0  # CLI doesn't validate thresholds

    def test_status_with_permission_error(self):
        """Test status command when git commands fail"""
        repo_dir = self.test_dir / "broken_repo"
        self.create_git_repo(repo_dir)

        # Add to monitoring first
        self.runner.invoke(add, [str(repo_dir), "--name", "BrokenRepo"])

        # Mock git commands to fail
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            # result = self.runner.invoke(status, ["--global"])
            assert result.exit_code == 0  # Should handle errors gracefully

    def test_run_with_git_errors(self):
        """Test run command when git operations fail"""
        repo_dir = self.test_dir / "error_repo"
        self.create_git_repo(repo_dir, with_changes=True)

        # Add to monitoring
        self.runner.invoke(add, [str(repo_dir), "--threshold", "1"])

        # Mock git commands to fail during commit
        with patch("doh.git_stats.GitStats.auto_commit") as mock_commit:
            mock_commit.side_effect = Exception("Git error")

            # result = self.runner.invoke(run)
            assert result.exit_code == 0  # Should handle errors gracefully

    def test_squash_without_temp_branches(self):
        """Test squash command when no temp branches exist"""
        repo_dir = self.test_dir / "no_temp_repo"
        self.create_git_repo(repo_dir)

        # result = self.runner.invoke(squash, ["Test message", str(repo_dir)])
        # Should handle gracefully when no temp branches exist
        assert result.exit_code == 0

    def test_cleanup_without_branches(self):
        """Test cleanup command when no temp branches exist"""
        repo_dir = self.test_dir / "clean_repo"
        self.create_git_repo(repo_dir)

        # result = self.runner.invoke(cleanup, [str(repo_dir)])
        # Should handle gracefully when no branches to clean
        assert result.exit_code == 0

    def test_main_command_with_force_non_git(self):
        """Test main command with force flag on non-git directory"""
        non_git_dir = self.test_dir / "not_git"
        non_git_dir.mkdir()

        old_cwd = os.getcwd()
        try:
            os.chdir(non_git_dir)
            # result = self.runner.invoke(main, ["--force"])
            assert result.exit_code == 0
        finally:
            os.chdir(old_cwd)

    def test_ex_commands_with_invalid_paths(self):
        """Test exclusion commands with invalid paths"""
        # Test adding non-existent path to exclusions
        # result = self.runner.invoke(main, ["ex", "add", "/nonexistent/path"])
        assert result.exit_code == 0  # Should still work

        # Test removing non-excluded path
        # result = self.runner.invoke(main, ["ex", "remove", "/not/excluded"])
        assert result.exit_code == 0

    def test_show_single_directory_status_errors(self):
        """Test _show_single_directory_status with various error conditions"""
        # Test with non-existent directory being monitored
        # # fake_dir = Path("/tmp/nonexistent_test_dir")  # Not currently used

        # This tests the internal function through the status command
        # result = self.runner.invoke(status)
        assert result.exit_code == 0

    def test_colors_in_output(self):
        """Test that color codes are properly used in output"""
        repo_dir = self.test_dir / "color_test"
        self.create_git_repo(repo_dir, with_changes=True)

        # Add to monitoring
        self.runner.invoke(add, [str(repo_dir), "--threshold", "1"])

        # Check that colors are used in various commands
        # result = self.runner.invoke(list)
        assert result.exit_code == 0
        # Output should contain the actual command output

        # result = self.runner.invoke(status, ["--global"])
        assert result.exit_code == 0

    def test_config_git_profile_invalid_path(self):
        """Test config with invalid git profile path"""
        result = self.runner.invoke(
            config, ["--set", "--git-profile", "/nonexistent/gitconfig"]
        )
        # Should accept the path even if it doesn't exist
        assert result.exit_code == 0

    def test_daemon_mode_simulation(self):
        """Test behavior similar to daemon mode"""
        repo_dir = self.test_dir / "daemon_test"
        self.create_git_repo(repo_dir, with_changes=True)

        # Add to monitoring with very low threshold
        self.runner.invoke(add, [str(repo_dir), "--threshold", "1"])

        # Run multiple times to simulate daemon behavior
        for _ in range(3):
            # result = self.runner.invoke(run, ["--verbose"])
            assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
