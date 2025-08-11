"""
Core DOH functionality
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import DohConfig
from .git_stats import GitStats
from .colors import Colors

try:
    import click
except ImportError:
    # Fallback for environments without click
    class MockClick:
        def echo(self, message):
            print(message)

    click = MockClick()


class DohCore:
    """Core DOH functionality"""

    def __init__(self):
        self.config = DohConfig()

    def is_excluded(self, directory: Path) -> bool:
        """Check if directory or any parent is excluded"""
        data = self.config.load()
        exclusions = data.get("exclusions", {})

        # Check directory itself
        if str(directory) in exclusions:
            return True

        # Check parents
        for parent in directory.parents:
            if str(parent) in exclusions:
                return True

        return False

    def find_excluded_parent(self, directory: Path) -> Optional[Path]:
        """Find which excluded parent is blocking this directory"""
        data = self.config.load()
        exclusions = data.get("exclusions", {})

        # Check directory itself
        if str(directory) in exclusions:
            return directory

        # Check parents
        for parent in directory.parents:
            if str(parent) in exclusions:
                return parent

        return None

    def is_monitored(self, directory: Path) -> bool:
        """Check if directory is being monitored"""
        data = self.config.load()
        return str(directory) in data.get("directories", {})

    def _handle_exclusion_error(self, directory: Path, excluded_parent: Path) -> None:
        """Handle exclusion error messages"""
        if excluded_parent == directory:
            try:
                click.echo(
                    f"{Colors.RED}Directory is excluded from monitoring"
                    f"{Colors.RESET}"
                )
                click.echo("Use 'doh ex rm' to remove from exclusions first")
            except ImportError:
                print("Directory is excluded from monitoring")
                print("Use 'doh ex rm' to remove from exclusions first")
        else:
            try:
                click.echo(
                    f"{Colors.RED}Cannot monitor directory - parent "
                    f"directory is excluded{Colors.RESET}"
                )
                click.echo(
                    f"Parent directory '{excluded_parent}' is in the " "exclusions list"
                )
                click.echo("Options:")
                click.echo(
                    "  1. Move current directory outside of " f"'{excluded_parent}'"
                )
                click.echo(
                    f"  2. Remove '{excluded_parent}' from exclusions: "
                    f"doh ex rm '{excluded_parent}'"
                )
            except ImportError:
                print("Cannot monitor directory - parent directory is excluded")
                print(
                    f"Parent directory '{excluded_parent}' is in the " "exclusions list"
                )

    def _run_git_init(self, directory: Path) -> bool:
        """Run git init command and handle errors"""
        try:
            subprocess.run(
                ["git", "init"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True,
            )
            try:
                click.echo(
                    f"{Colors.GREEN}✓ Initialized git repository" f"{Colors.RESET}"
                )
            except ImportError:
                print("✓ Initialized git repository")
            return True
        except subprocess.CalledProcessError as e:
            try:
                click.echo(
                    f"{Colors.RED}Failed to initialize git "
                    f"repository: {e}{Colors.RESET}"
                )
            except ImportError:
                print(f"Failed to initialize git repository: {e}")
            return False
        except Exception as e:
            try:
                click.echo(
                    f"{Colors.RED}Error initializing git "
                    f"repository: {e}{Colors.RESET}"
                )
            except ImportError:
                print(f"Error initializing git repository: {e}")
            return False

    def _show_no_git_message(self) -> None:
        """Show message when directory is not a git repository"""
        try:
            click.echo(
                f"{Colors.RED}Directory is not a git repository" f"{Colors.RESET}"
            )
            click.echo("Use 'git init' to initialize a git repository first")
        except ImportError:
            print("Directory is not a git repository")
            print("Use 'git init' to initialize a git repository first")

    def _initialize_git_repository(self, directory: Path) -> bool:
        """Initialize git repository if auto_init is enabled"""
        data = self.config.load()
        auto_init = data.get("global_settings", {}).get("auto_init_git", True)

        if auto_init:
            return self._run_git_init(directory)
        else:
            self._show_no_git_message()
            return False

    def _add_directory_to_config(
        self, directory: Path, threshold: int, name: str
    ) -> bool:
        """Add directory to configuration"""
        data = self.config.load()
        timestamp = datetime.now(timezone.utc).isoformat()

        if not name:
            name = directory.name

        data["directories"][str(directory)] = {
            "name": name,
            "threshold": threshold,
            "added": timestamp,
            "last_checked": timestamp,
        }

        return self.config.save(data)

    def add_directory(self, directory: Path, threshold: int, name: str) -> bool:
        """Add directory to monitoring"""
        if self.is_excluded(directory):
            excluded_parent = self.find_excluded_parent(directory)
            self._handle_exclusion_error(directory, excluded_parent)
            return False

        # Check if git repo exists, auto-initialize if configured
        if not GitStats.is_git_repo(directory):
            if not self._initialize_git_repository(directory):
                return False

        return self._add_directory_to_config(directory, threshold, name)

    def remove_directory(self, directory: Path) -> bool:
        """Remove directory from monitoring"""
        data = self.config.load()
        dir_str = str(directory)

        removed = False
        if dir_str in data.get("directories", {}):
            del data["directories"][dir_str]
            removed = True

        if dir_str in data.get("exclusions", {}):
            del data["exclusions"][dir_str]
            removed = True

        if removed:
            return self.config.save(data)
        return True

    def add_exclusion(self, directory: Path) -> bool:
        """Add directory to exclusions"""
        # Remove from monitoring if it exists
        self.remove_directory(directory)

        data = self.config.load()
        timestamp = datetime.now(timezone.utc).isoformat()

        data["exclusions"][str(directory)] = {"excluded": timestamp}

        return self.config.save(data)

    def remove_exclusion(self, directory: Path) -> bool:
        """Remove directory from exclusions"""
        data = self.config.load()
        dir_str = str(directory)

        if dir_str in data.get("exclusions", {}):
            del data["exclusions"][dir_str]
            return self.config.save(data)
        return True
