#!/usr/bin/env python3
"""
Command handlers for DOH CLI.

This module contains the Click command handler functions
that implement the main CLI commands.
"""

import subprocess
from pathlib import Path
from typing import Any, Optional
import click
from .colors import Colors
from .config import DEFAULT_THRESHOLD
from .git_stats import GitStats
from .status_display import (
    show_single_directory_status,
    show_global_status,
    show_local_status
)
from .git_operations import (
    force_commit_directory,
    process_monitored_directories
)
from .config_management import (
    update_config_settings,
    show_config_display
)


def handle_add_command(
    ctx: click.Context,
    directory: Optional[Path],
    threshold: int,
    name: Optional[str],
    doh_core: Any
) -> None:
    """Handle the add command logic"""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    # Get force flag from context
    force_commit = ctx.obj.get("force", False) if ctx.obj else False

    # Smart behavior: if already monitored, show status instead
    if doh_core.is_monitored(directory):
        click.echo(
            f"{Colors.YELLOW}Directory already monitored. "
            f"Showing current status:{Colors.RESET}"
        )
        click.echo()
        show_single_directory_status(directory, doh_core)
        return

    # Handle force commit first if requested
    if force_commit:
        if force_commit_directory(directory, doh_core):
            click.echo(
                f"{Colors.GREEN}Changes committed successfully{Colors.RESET}"
            )
        else:
            click.echo(
                f"{Colors.YELLOW}No changes to commit or commit failed"
                f"{Colors.RESET}"
            )

    if doh_core.add_directory(directory, threshold, name):
        display_name = name or directory.name
        click.echo(
            f"{Colors.GREEN}✓ Added '{display_name}' to monitoring"
            f"{Colors.RESET}"
        )
        click.echo(f"  Path: {directory}")
        click.echo(f"  Threshold: {threshold} lines")
        click.echo()
        click.echo("Current status:")
        show_single_directory_status(directory, doh_core)
    else:
        click.echo(f"{Colors.RED}Failed to add directory{Colors.RESET}")


def handle_remove_command(directory: Optional[Path], doh_core: Any) -> None:
    """Handle the remove command logic"""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    is_monitored = doh_core.is_monitored(directory)
    is_excluded = doh_core.is_excluded(directory)
    if not is_monitored and not is_excluded:
        click.echo(
            f"{Colors.YELLOW}Directory not being monitored or excluded"
            f"{Colors.RESET}"
        )
        return

    if doh_core.remove_directory(directory):
        click.echo(
            f"{Colors.GREEN}Removed '{directory}' from monitoring/exclusions"
            f"{Colors.RESET}"
        )
    else:
        click.echo(f"{Colors.RED}Failed to remove directory{Colors.RESET}")


def handle_list_command(doh_core: Any) -> None:
    """Handle the list command logic"""
    data = doh_core.config.load()
    directories = data.get("directories", {})

    if not directories:
        click.echo(
            f"{Colors.YELLOW}No directories being monitored{Colors.RESET}"
        )
        return

    click.echo(f"{Colors.BOLD}Monitored Directories:{Colors.RESET}")
    click.echo("-" * 80)

    for dir_path, info in directories.items():
        directory = Path(dir_path)
        name = info.get("name", directory.name)
        threshold = info.get("threshold", DEFAULT_THRESHOLD)

        # Get git stats
        stats = GitStats.get_stats(directory)

        if stats is None:
            status = f"{Colors.RED}NOT A GIT REPO{Colors.RESET}"
        elif not directory.exists():
            status = f"{Colors.RED}DIRECTORY NOT FOUND{Colors.RESET}"
        else:
            total_changes = stats["total_changes"]
            untracked_lines = stats.get("untracked_lines", stats["untracked"])

            if total_changes + untracked_lines == 0:
                status = f"{Colors.GREEN}CLEAN{Colors.RESET}"
            elif total_changes + untracked_lines >= threshold:
                total_all = total_changes + untracked_lines
                status = (
                    f"{Colors.RED}THRESHOLD EXCEEDED ({total_all})"
                    f"{Colors.RESET}"
                )
            else:
                total_all = total_changes + untracked_lines
                status = f"{Colors.YELLOW}CHANGES ({total_all}){Colors.RESET}"

        click.echo(f"{Colors.BLUE}{name:<30}{Colors.RESET} {status}")
        click.echo(f"  Path: {dir_path}")
        click.echo(f"  Threshold: {threshold}")

        if stats:
            changes_info = (
                f"  Changes: +{stats['added']} -{stats['deleted']} "
                f"(files: {stats['files_changed']})"
            )
            click.echo(changes_info)
            if stats["untracked"] > 0:
                click.echo(f"  Untracked: {stats['untracked']} files")

        click.echo()


def handle_status_command(
    show_global: bool, directory: Optional[Path], doh_core: Any
) -> None:
    """Handle the status command logic"""
    if show_global:
        show_global_status(doh_core)
    else:
        show_local_status(directory, doh_core)


def handle_exclusions_add_command(
    directory: Optional[Path], doh_core: Any
) -> None:
    """Handle the exclusions add command logic"""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    if doh_core.is_excluded(directory):
        click.echo(f"{Colors.YELLOW}Directory already excluded{Colors.RESET}")
        return

    if doh_core.add_exclusion(directory):
        click.echo(
            f"{Colors.GREEN}Added '{directory}' to exclusions{Colors.RESET}"
        )
    else:
        click.echo(f"{Colors.RED}Failed to add exclusion{Colors.RESET}")


def handle_exclusions_remove_command(
    directory: Optional[Path], doh_core: Any
) -> None:
    """Handle the exclusions remove command logic"""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    if not doh_core.is_excluded(directory):
        click.echo(f"{Colors.YELLOW}Directory not in exclusions{Colors.RESET}")
        return

    if doh_core.remove_exclusion(directory):
        click.echo(
            f"{Colors.GREEN}Removed '{directory}' from exclusions"
            f"{Colors.RESET}"
        )
    else:
        click.echo(f"{Colors.RED}Failed to remove exclusion{Colors.RESET}")


def handle_exclusions_list_command(doh_core: Any) -> None:
    """Handle the exclusions list command logic"""
    data = doh_core.config.load()
    exclusions_dict = data.get("exclusions", {})

    if not exclusions_dict:
        click.echo(f"{Colors.YELLOW}No directories excluded{Colors.RESET}")
        return

    click.echo(f"{Colors.BOLD}Excluded Directories:{Colors.RESET}")
    click.echo("-" * 80)

    for dir_path, info in exclusions_dict.items():
        directory = Path(dir_path)
        excluded_date = info.get("excluded", "Unknown")

        if directory.exists():
            status = f"{Colors.GREEN}EXISTS{Colors.RESET}"
        else:
            status = f"{Colors.RED}NOT FOUND{Colors.RESET}"

        click.echo(f"{Colors.BLUE}{directory.name:<30}{Colors.RESET} {status}")
        click.echo(f"  Path: {dir_path}")
        click.echo(f"  Excluded: {excluded_date}")
        click.echo()


def handle_config_command(
    set_config: bool,
    git_profile: Optional[str],
    threshold: Optional[int],
    auto_init_git: Optional[bool],
    temp_branches: Optional[bool],
    temp_branch_prefix: Optional[str],
    temp_branch_cleanup_days: Optional[int],
    doh_core: Any
) -> None:
    """Handle the config command logic"""
    # Check if any configuration options are provided
    has_config_options = any([
        git_profile,
        threshold,
        auto_init_git is not None,
        temp_branches is not None,
        temp_branch_prefix,
        temp_branch_cleanup_days,
    ])

    if has_config_options and not set_config:
        click.echo(
            f"{Colors.YELLOW}To modify configuration, use --set flag with "
            f"your options.{Colors.RESET}"
        )
        click.echo("Example: doh config --set --threshold 100")
        return

    if set_config or has_config_options:
        # Configuration mode
        data = doh_core.config.load()
        settings = data.setdefault("global_settings", {})

        changed = update_config_settings(
            settings,
            git_profile,
            threshold,
            auto_init_git,
            temp_branches,
            temp_branch_prefix,
            temp_branch_cleanup_days,
        )

        if not changed:
            click.echo(
                f"{Colors.YELLOW}No changes specified. Use --help to see "
                f"available options.{Colors.RESET}"
            )
            return

        if doh_core.config.save(data):
            click.echo(
                f"{Colors.GREEN}Configuration saved successfully{Colors.RESET}"
            )
        else:
            click.echo(
                f"{Colors.RED}Failed to save configuration{Colors.RESET}"
            )
    else:
        # Display mode (default behavior)
        show_config_display(doh_core)


def handle_run_command(verbose: bool, doh_core: Any) -> None:
    """Handle the run command logic"""
    data = doh_core.config.load()
    directories = data.get("directories", {})

    if not directories:
        click.echo(
            f"{Colors.YELLOW}No directories being monitored. Use "
            f"'doh add' to add directories.{Colors.RESET}"
        )
        return

    if verbose:
        click.echo(
            f"{Colors.BLUE}Checking {len(directories)} monitored "
            f"directories...{Colors.RESET}"
        )

    committed = process_monitored_directories(directories, verbose, doh_core)

    if committed > 0:
        click.echo(
            f"\n{Colors.GREEN}✓ Auto-committed {committed} "
            f"directories{Colors.RESET}"
        )
    elif verbose:
        click.echo(
            f"\n{Colors.GREEN}All directories are clean or under "
            f"threshold{Colors.RESET}"
        )
    else:
        click.echo("No directories needed auto-commit")


def handle_squash_command(
    commit_message: str,
    target: str,
    directory: Optional[Path]
) -> None:
    """Handle the squash command logic"""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    if not GitStats.is_git_repo(directory):
        click.echo(
            f"{Colors.RED}Not a git repository: {directory}{Colors.RESET}"
        )
        return

    # Check if there are temp branches to squash
    temp_branches = GitStats.list_temp_branches(directory)
    if not temp_branches:
        click.echo(
            f"{Colors.YELLOW}No temporary branches found to squash"
            f"{Colors.RESET}"
        )
        return

    # Find current branch or most recent temp branch
    try:
        current_branch = subprocess.run(
            ["git", "-C", str(directory), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        temp_branch = None
        if current_branch.startswith("doh-auto-commits"):
            temp_branch = current_branch
        elif temp_branches:
            # Use most recent temp branch
            sorted_branches = sorted(temp_branches, key=lambda b: b["name"])
            temp_branch = sorted_branches[-1]["name"]

        if not temp_branch:
            click.echo(
                f"{Colors.YELLOW}No temporary branch to squash{Colors.RESET}"
            )
            return

        if GitStats.squash_temp_commits(
            directory, target, commit_message, temp_branch
        ):
            click.echo(
                f"{Colors.GREEN}✓ Successfully squashed temp commits into "
                f"'{target}'{Colors.RESET}"
            )
            click.echo(f"  Commit message: {commit_message}")
        else:
            click.echo(
                f"{Colors.RED}✗ Failed to squash temporary branch"
                f"{Colors.RESET}"
            )

    except subprocess.CalledProcessError as e:
        click.echo(f"{Colors.RED}Git error: {e}{Colors.RESET}")


def handle_cleanup_command(
    cleanup_days: int,
    force: bool,
    directory: Optional[Path]
) -> None:
    """Handle the cleanup command logic"""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    if not GitStats.is_git_repo(directory):
        click.echo(
            f"{Colors.RED}Not a git repository: {directory}{Colors.RESET}"
        )
        return

    branches = GitStats.list_temp_branches(directory)

    if not branches:
        click.echo(
            f"{Colors.YELLOW}No temporary branches to clean up{Colors.RESET}"
        )
        return

    click.echo(
        f"{Colors.BLUE}Found {len(branches)} temporary branches in "
        f"{directory.name}:{Colors.RESET}"
    )
    for branch in branches:
        branch_info = (
            f"  {Colors.GREEN}{branch['name']}{Colors.RESET} "
            f"({branch['commit_count']} commits, {branch['last_commit']})"
        )
        click.echo(branch_info)

    if not force:
        click.echo(
            f"\n{Colors.YELLOW}This will delete branches older than "
            f"{cleanup_days} days.{Colors.RESET}"
        )
        if not click.confirm("Are you sure you want to continue?"):
            click.echo(f"{Colors.YELLOW}Cleanup cancelled{Colors.RESET}")
            return

    # TODO: Implement age-based cleanup logic
    click.echo(
        f"{Colors.GREEN}Cleanup logic for branches older than "
        f"{cleanup_days} days - Coming soon!{Colors.RESET}"
    )
    click.echo(
        f"{Colors.BLUE}Use --force to skip this confirmation in the future"
        f"{Colors.RESET}"
    )
