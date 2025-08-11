#!/usr/bin/env python3
"""
Git operations for DOH CLI.

This module contains functions for performing git operations
like force commits, auto-commits, and branch management.
"""

import subprocess
from pathlib import Path
from typing import Any
import click
from .colors import Colors
from .git_stats import GitStats


def force_commit_directory(directory: Path, doh_core: Any) -> bool:
    """Force commit all changes in a directory"""
    if not GitStats.is_git_repo(directory):
        return False

    try:
        # Get current stats for enhanced commit message
        stats = GitStats.get_stats(directory)
        if not stats:
            return False

        # Get git profile from config if set
        data = doh_core.config.load()
        git_profile = data.get("global_settings", {}).get("git_profile", "")

        git_cmd = ["git", "-C", str(directory)]

        # Add git profile config if specified
        if git_profile:
            profile_path = Path(git_profile).expanduser()
            if profile_path.exists():
                git_cmd.extend(["-c", f"include.path={profile_path}"])

        # Add all changes
        subprocess.run(git_cmd + ["add", "."], check=True, capture_output=True)

        # Check if there's anything to commit
        result = subprocess.run(
            git_cmd + ["diff", "--staged", "--quiet"],
            capture_output=True,
            check=False
        )

        if result.returncode == 0:
            # Nothing staged to commit
            return False

        # Create enhanced commit message for force commit
        file_changes = GitStats.format_file_changes(
            stats.get("file_stats", []), max_files=5
        )
        commit_msg = f"Manual commit: {file_changes}"

        subprocess.run(
            git_cmd + ["commit", "-m", commit_msg],
            check=True,
            capture_output=True
        )
        return True

    except subprocess.CalledProcessError:
        return False


def handle_temp_branch_strategy(
    directory: Path,
    name: str,
    git_cmd: list,
    use_temp_branches: bool,
    temp_branch_prefix: str,
    verbose: bool,
) -> bool:
    """Handle temporary branch creation and switching"""
    if use_temp_branches:
        try:
            # Get or create temp branch
            temp_branch = GitStats.get_or_create_temp_branch(
                directory, temp_branch_prefix
            )

            # Switch to temp branch if not already on it
            current_branch = subprocess.run(
                git_cmd + ["branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            if current_branch != temp_branch:
                GitStats.switch_to_temp_branch(directory, temp_branch)
            return True

        except subprocess.CalledProcessError:
            # Fallback to direct commits if temp branch fails
            if verbose:
                click.echo(
                    f"{Colors.YELLOW}⚠ Failed to create temp branch for "
                    f"{name}, using direct commits{Colors.RESET}"
                )
            return False
    return use_temp_branches


def stage_and_check_changes(git_cmd: list, name: str, verbose: bool) -> bool:
    """Stage changes and check if there's anything to commit"""
    # Stage all changes
    subprocess.run(git_cmd + ["add", "."], capture_output=True, check=True)

    # Check if there's anything to commit
    result = subprocess.run(
        git_cmd + ["diff", "--staged", "--quiet"],
        capture_output=True,
        check=False
    )

    if result.returncode == 0:
        # Nothing staged to commit
        if verbose:
            click.echo(
                f"{Colors.YELLOW}• {name}: No changes to commit"
                f"{Colors.RESET}"
            )
        return False
    return True


def create_commit_and_log(
    git_cmd: list,
    name: str,
    stats: dict,
    threshold: int,
    use_temp_branches: bool,
    temp_branch_prefix: str,
) -> None:
    """Create commit and display success log"""
    # Use enhanced commit message format
    commit_msg = GitStats.create_enhanced_commit_message(
        name, stats, threshold
    )

    # Commit changes
    subprocess.run(
        git_cmd + ["commit", "-m", commit_msg], capture_output=True, check=True
    )

    # Create enhanced log message with file details
    file_summary = GitStats.format_file_changes(
        stats.get("file_stats", []), max_files=3
    )

    if use_temp_branches:
        temp_branch = GitStats.get_or_create_temp_branch(
            Path(git_cmd[2]), temp_branch_prefix
        )
        click.echo(
            f"{Colors.GREEN}✓ Auto-committed '{name}' to temp branch "
            f"'{temp_branch}': {file_summary}{Colors.RESET}"
        )
    else:
        click.echo(
            f"{Colors.GREEN}✓ Auto-committed '{name}': "
            f"{file_summary}{Colors.RESET}"
        )


def auto_commit_directory(
    directory: Path,
    stats: dict,
    threshold: int,
    name: str,
    verbose: bool,
    doh_core: Any
) -> bool:
    """Perform auto-commit for a directory"""
    try:
        # Get configuration settings
        data = doh_core.config.load()
        global_settings = data.get("global_settings", {})
        use_temp_branches = global_settings.get("use_temp_branches", True)
        temp_branch_prefix = global_settings.get(
            "temp_branch_prefix", "doh-auto-commits"
        )
        git_profile = global_settings.get("git_profile", "")

        git_cmd = ["git", "-C", str(directory)]

        # Add git profile config if specified
        if git_profile:
            profile_path = Path(git_profile).expanduser()
            if profile_path.exists():
                git_cmd.extend(["-c", f"include.path={profile_path}"])

        # Handle temporary branch strategy
        use_temp_branches = handle_temp_branch_strategy(
            directory,
            name,
            git_cmd,
            use_temp_branches,
            temp_branch_prefix,
            verbose
        )

        # Stage and check for changes
        if not stage_and_check_changes(git_cmd, name, verbose):
            return False

        # Create commit and log success
        create_commit_and_log(
            git_cmd,
            name,
            stats,
            threshold,
            use_temp_branches,
            temp_branch_prefix
        )

        return True

    except subprocess.CalledProcessError as e:
        if verbose:
            click.echo(
                f"{Colors.RED}✗ Failed to commit '{name}': "
                f"{e}{Colors.RESET}"
            )
        return False


def process_monitored_directories(
    directories: dict, verbose: bool, doh_core: Any
) -> int:
    """Process all monitored directories and return commit count"""
    from .config import DEFAULT_THRESHOLD
    
    committed = 0

    for dir_path, info in directories.items():
        directory = Path(dir_path)
        # Get threshold and name from directory info
        threshold = info.get("threshold", DEFAULT_THRESHOLD)
        name = info.get("name", directory.name)

        if not directory.exists():
            if verbose:
                click.echo(
                    f"{Colors.RED}✗ Directory not found: {name} "
                    f"({directory}){Colors.RESET}"
                )
            continue

        stats = GitStats.get_stats(directory)
        if stats is None:
            if verbose:
                click.echo(
                    f"{Colors.RED}✗ Not a git repository: {name} "
                    f"({directory}){Colors.RESET}"
                )
            continue

        total_changes = stats["total_changes"] + stats.get(
            "untracked_lines", stats["untracked"]
        )

        if total_changes >= threshold:
            if auto_commit_directory(
                directory, stats, threshold, name, verbose, doh_core
            ):
                committed += 1
        elif verbose:
            click.echo(
                f"{Colors.GREEN}• {name}: {total_changes} changes "
                f"(under threshold {threshold}){Colors.RESET}"
            )

    return committed
