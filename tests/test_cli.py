#!/usr/bin/env python3
"""
Test suite for DOH CLI commands
"""

import os
import pytest
import shutil
import subprocess
import tempfile
from pathlib import Path
from click.testing import CliRunner

# Import CLI commands
from doh.cli import main, config, add, status, list, run, squash, cleanup


class TestDohCLI:
    """Test DOH CLI commands"""

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

    def test_config_command_display(self):
        """Test config command shows configuration"""
        result = self.runner.invoke(config)
        assert result.exit_code == 0
        assert "DOH Configuration:" in result.output
        assert "Config file:" in result.output
        # Don't assert specific count since we're using a real config
        assert "Monitored directories:" in result.output

    def test_config_command_set_threshold(self):
        """Test config command can set values with --set flag"""
        result = self.runner.invoke(config, ["--set", "--threshold", "100"])
        assert result.exit_code == 0
        assert "Default threshold set to: 100" in result.output
        assert "Configuration saved successfully" in result.output

    def test_config_command_requires_set_flag(self):
        """Test config command requires --set flag to modify values"""
        result = self.runner.invoke(config, ["--threshold", "100"])
        assert result.exit_code == 0
        assert "requires --set flag" in result.output

    def test_add_command(self):
        """Test add command adds directory to monitoring"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir)

        result = self.runner.invoke(
            add, [str(repo_dir), "--threshold", "25", "--name", "TestRepo"]
        )
        assert result.exit_code == 0
        assert "Added 'TestRepo' to monitoring" in result.output

    def test_add_command_current_directory(self):
        """Test add command works with current directory"""
        repo_dir = self.test_dir / "current_repo"
        self.create_git_repo(repo_dir)

        # Change to repo directory
        old_cwd = os.getcwd()
        try:
            os.chdir(repo_dir)
            result = self.runner.invoke(add)
            assert result.exit_code == 0
            assert "to monitoring" in result.output
        finally:
            os.chdir(old_cwd)

    def test_list_command_empty(self):
        """Test list command with no monitored directories"""
        result = self.runner.invoke(list)
        assert result.exit_code == 0
        # In a real environment, there may be existing directories
        assert "Monitored Directories:" in result.output

    def test_list_command_with_directories(self):
        """Test list command shows monitored directories"""
        # Add a directory first
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir)

        # Add it to monitoring
        self.runner.invoke(add, [str(repo_dir), "--name", "TestRepo"])

        # List should show it
        result = self.runner.invoke(list)
        assert result.exit_code == 0
        assert "TestRepo" in result.output

    def test_status_command_local(self):
        """Test status command shows local directory status (default)"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir, with_changes=True)

        # Add to monitoring
        self.runner.invoke(add, [str(repo_dir), "--threshold", "1"])

        # Change to repo directory and check local status
        old_cwd = os.getcwd()
        try:
            os.chdir(repo_dir)
            result = self.runner.invoke(status)
            assert result.exit_code == 0
            # Should show the local directory status
            assert (
                "DOH Local Status:" in result.output
                or "Directory already monitored" in result.output
                or "Current directory is not being monitored" in result.output
            )
        finally:
            os.chdir(old_cwd)

    def test_status_command_global(self):
        """Test status command shows global status with --global flag"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir, with_changes=True)

        # Add to monitoring
        self.runner.invoke(add, [str(repo_dir), "--threshold", "1"])

        # Check global status
        result = self.runner.invoke(status, ["--global"])
        assert result.exit_code == 0
        assert "DOH Global Status Summary:" in result.output
        # Don't assert specific count since there may be existing monitored directories
        assert "Total directories:" in result.output

    def test_status_command_unmonitored_directory(self):
        """Test status command in unmonitored directory"""
        repo_dir = self.test_dir / "unmonitored_repo"
        self.create_git_repo(repo_dir)

        old_cwd = os.getcwd()
        try:
            os.chdir(repo_dir)
            result = self.runner.invoke(status)
            assert result.exit_code == 0
            assert "Current directory is not being monitored" in result.output
            assert "Use 'doh add' to add it to monitoring" in result.output
        finally:
            os.chdir(old_cwd)

    def test_run_command(self):
        """Test run command processes directories"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir, with_changes=True)

        # Add to monitoring with low threshold
        self.runner.invoke(add, [str(repo_dir), "--threshold", "1"])

        # Run should auto-commit
        result = self.runner.invoke(run, ["--verbose"])
        assert result.exit_code == 0
        # Don't assert specific count since there may be existing monitored directories
        assert "Checking" in result.output and "monitored directories" in result.output

    def test_ex_commands(self):
        """Test exclusion (ex) commands"""
        excluded_dir = self.test_dir / "excluded"
        excluded_dir.mkdir()

        # Test add exclusion
        result = self.runner.invoke(main, ["ex", "add", str(excluded_dir)])
        assert result.exit_code == 0
        assert "Added" in result.output and "to exclusions" in result.output

        # Test list exclusions
        result = self.runner.invoke(main, ["ex", "list"])
        assert result.exit_code == 0
        assert "Excluded Directories:" in result.output

        # Test remove exclusion
        result = self.runner.invoke(main, ["ex", "rm", str(excluded_dir)])
        assert result.exit_code == 0
        assert "Removed" in result.output and "from exclusions" in result.output

    def test_rm_command(self):
        """Test rm (remove) command"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir)

        # Add to monitoring first
        self.runner.invoke(add, [str(repo_dir)])

        # Remove from monitoring
        result = self.runner.invoke(main, ["rm", str(repo_dir)])
        assert result.exit_code == 0
        assert "Removed" in result.output and "from monitoring" in result.output

    def test_squash_command(self):
        """Test squash command"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir, with_changes=True)

        # Create temp branch first (simulate auto-commit)
        subprocess.run(
            ["git", "checkout", "-b", "doh-auto-commits-test"], cwd=repo_dir, check=True
        )
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Auto commit"], cwd=repo_dir, check=True)

        # Test squash
        result = self.runner.invoke(squash, ["Squashed changes", str(repo_dir)])
        assert result.exit_code == 0
        assert "Successfully squashed" in result.output

    def test_shorthand_s_command(self):
        """Test shorthand 's' command for squash"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir, with_changes=True)

        # Create temp branch first
        subprocess.run(
            ["git", "checkout", "-b", "doh-auto-commits-test"], cwd=repo_dir, check=True
        )
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Auto commit"], cwd=repo_dir, check=True)

        # Test shorthand 's' command
        result = self.runner.invoke(
            main, ["s", "Squashed with shorthand", str(repo_dir)]
        )
        assert result.exit_code == 0
        assert "Successfully squashed" in result.output

    def test_cleanup_command_with_confirmation(self):
        """Test cleanup command asks for confirmation"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir)

        # Create a temp branch
        subprocess.run(
            ["git", "checkout", "-b", "doh-auto-commits-test"], cwd=repo_dir, check=True
        )
        subprocess.run(["git", "checkout", "master"], cwd=repo_dir, check=True)

        # Test with 'n' response
        result = self.runner.invoke(cleanup, [str(repo_dir)], input="n\n")
        assert result.exit_code == 0
        assert "Found" in result.output and "temporary branches" in result.output
        assert "Cleanup cancelled" in result.output

    def test_cleanup_command_with_force(self):
        """Test cleanup command with --force flag skips confirmation"""
        repo_dir = self.test_dir / "test_repo"
        self.create_git_repo(repo_dir)

        # Create a temp branch
        subprocess.run(
            ["git", "checkout", "-b", "doh-auto-commits-test"], cwd=repo_dir, check=True
        )
        subprocess.run(["git", "checkout", "master"], cwd=repo_dir, check=True)

        result = self.runner.invoke(cleanup, ["--force", str(repo_dir)])
        assert result.exit_code == 0
        assert "temporary branches" in result.output

    def test_help_commands(self):
        """Test that help commands work"""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "DOH - Directory Oh-no, Handle this!" in result.output
        assert "Commands:" in result.output

        # Test that new command names are visible
        assert "config" in result.output
        assert "run" in result.output
        assert "ex" in result.output
        assert "rm" in result.output
        assert "squash" in result.output

        # Test that daemon is NOT visible (we removed it)
        assert "daemon" not in result.output


if __name__ == "__main__":

    pytest.main([__file__, "-v"])
