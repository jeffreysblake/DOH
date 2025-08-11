#!/usr/bin/env python3
"""
DOH - Directory Oh-no, Handle this!
A smart auto-commit monitoring system for git repositories.

This is a complete rewrite in Python for better performance, reliability,
and maintainability compared to the original bash implementation.

This refactored version separates concerns into dedicated modules:
- status_display: All status display functionality
- git_operations: Git-related operations and auto-commit logic
- config_management: Configuration display and modification
- command_handlers: Click command handler implementations
"""

from pathlib import Path
import click

from .core import DohCore
from .config import DEFAULT_THRESHOLD
from .git_stats import GitStats
from .colors import Colors
from .status_display import show_single_directory_status
from .git_operations import force_commit_directory
from .command_handlers import (
    handle_add_command,
    handle_remove_command,
    handle_list_command,
    handle_status_command,
    handle_exclusions_add_command,
    handle_exclusions_remove_command,
    handle_exclusions_list_command,
    handle_config_command,
    handle_run_command,
    handle_squash_command,
    handle_cleanup_command,
)


# Initialize core
doh = DohCore()


@click.group(invoke_without_command=True)
@click.version_option(version="2.0.0", prog_name="doh")
@click.option(
    "--force",
    "-",
    is_flag=True,
    help="Force commit any changes before adding directory",
)
@click.option(
    "--threshold",
    "-t",
    default=DEFAULT_THRESHOLD,
    type=int,
    help=f"Change threshold (default: {DEFAULT_THRESHOLD})",
)
@click.option(
    "--name", "-n", help="Name for this directory (defaults to directory name)"
)
@click.pass_context
def main(ctx, force, threshold, name):
    """DOH - Directory Oh-no, Handle this!

    A smart auto-commit monitoring system for git repositories.

    When run without a command, adds current directory to monitoring
    (or shows status if already monitored).
    """
    # First-run setup
    doh.config.setup_first_run()

    # Store context data for subcommands
    ctx.ensure_object(dict)
    ctx.obj["force"] = force

    # If no subcommand was invoked, act like 'add' for current directory
    if ctx.invoked_subcommand is None:
        directory = Path.cwd().resolve()

        # Smart behavior: if already monitored, check if auto-commit is needed
        if doh.is_monitored(directory):
            msg = (
                f"{Colors.YELLOW}Directory already monitored. "
                f"Checking status:{Colors.RESET}"
            )
            click.echo(msg)
            click.echo()

            # Get current stats and threshold for this directory
            data = doh.config.load()
            directories = data.get("directories", {})
            dir_info = directories.get(str(directory), {})
            dir_threshold = dir_info.get("threshold", DEFAULT_THRESHOLD)

            stats = GitStats.get_stats(directory)
            if stats:
                untracked_lines = stats.get("untracked_lines", stats["untracked"])
                total_changes = stats["total_changes"] + untracked_lines

                # Auto-commit if over threshold (even without -f flag)
                if total_changes >= dir_threshold:
                    threshold_msg = (
                        f"{Colors.RED}Threshold exceeded "
                        f"({total_changes}/{dir_threshold}). "
                        f"Auto-committing...{Colors.RESET}"
                    )
                    click.echo(threshold_msg)
                    if force_commit_directory(directory, doh):
                        success_msg = (
                            f"{Colors.GREEN}✓ Changes committed "
                            f"successfully{Colors.RESET}"
                        )
                        click.echo(success_msg)
                    else:
                        fail_msg = (
                            f"{Colors.YELLOW}⚠ Auto-commit failed or "
                            f"no changes to commit{Colors.RESET}"
                        )
                        click.echo(fail_msg)
                    click.echo()

            show_single_directory_status(directory, doh)
            return

        # Handle force commit first if requested (for new directories)
        if force:
            if force_commit_directory(directory, doh):
                click.echo(
                    f"{Colors.GREEN}Changes committed successfully{Colors.RESET}"
                )
            else:
                click.echo(
                    f"{Colors.YELLOW}No changes to commit or commit failed"
                    f"{Colors.RESET}"
                )

        if doh.add_directory(directory, threshold, name):
            display_name = name or directory.name
            click.echo(
                f"{Colors.GREEN}✓ Added '{display_name}' to monitoring"
                f"{Colors.RESET}"
            )
            click.echo(f"  Path: {directory}")
            click.echo(f"  Threshold: {threshold} lines")
            click.echo()
            show_single_directory_status(directory, doh)
        else:
            click.echo(
                f"{Colors.RED}✗ Failed to add directory to monitoring"
                f"{Colors.RESET}"
            )


@main.command()
@click.option(
    "--threshold",
    "-t",
    default=DEFAULT_THRESHOLD,
    type=int,
    help=f"Change threshold (default: {DEFAULT_THRESHOLD})",
)
@click.option(
    "--name", "-n", help="Name for this directory (defaults to directory name)"
)
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
@click.pass_context
def add(ctx, directory, threshold, name):
    """Add a directory to monitoring"""
    handle_add_command(ctx, directory, threshold, name, doh)


@main.command("rm")
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
def remove(directory):
    """Remove a directory from monitoring and exclusions"""
    handle_remove_command(directory, doh)


@main.command()
def list():
    """List all monitored directories"""
    handle_list_command(doh)


@main.command()
@click.option(
    "--global",
    "show_global",
    is_flag=True,
    help="Show status of all monitored directories",
)
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
def status(show_global, directory):
    """Show status of current directory (default) or all monitored directories (--global)"""
    handle_status_command(show_global, directory, doh)


@main.group("ex")
def exclusions():
    """Manage directory exclusions"""
    pass


@exclusions.command("add")
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
def exclusions_add(directory):
    """Add a directory to exclusions"""
    handle_exclusions_add_command(directory, doh)


@exclusions.command("rm")
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
def exclusions_remove(directory):
    """Remove a directory from exclusions"""
    handle_exclusions_remove_command(directory, doh)


@exclusions.command("list")
def exclusions_list():
    """List all excluded directories"""
    handle_exclusions_list_command(doh)


# Add aliases for common commands
@main.group(hidden=True)
def ex():
    """Alias for exclusions command"""
    pass


# Set up exclusions alias subcommands
ex.add_command(exclusions_add, name="add")
ex.add_command(exclusions_remove, name="remove")
ex.add_command(exclusions_remove, name="rm")  # Alias for remove
ex.add_command(exclusions_list, name="list")
ex.add_command(exclusions_list, name="ls")  # Alias for list


@main.command()
@click.option("--set", is_flag=True, help="Enter configuration mode to change settings")
@click.option(
    "--git-profile",
    help="Path to git config file to use for commits (e.g., ~/.gitconfig-personal)",
)
@click.option("--threshold", type=int, help="Set default threshold for new directories")
@click.option(
    "--auto-init-git/--no-auto-init-git",
    default=None,
    help="Enable/disable automatic git init for non-git directories",
)
@click.option(
    "--temp-branches/--no-temp-branches",
    default=None,
    help="Enable/disable temporary branch strategy",
)
@click.option(
    "--temp-branch-prefix",
    help="Set prefix for temporary branch names (default: doh-auto-commits)",
)
@click.option(
    "--temp-branch-cleanup-days",
    type=int,
    help="Days after which to clean up old temp branches (default: 7)",
)
def config(
    set,
    git_profile,
    threshold,
    auto_init_git,
    temp_branches,
    temp_branch_prefix,
    temp_branch_cleanup_days,
):
    """Show configuration or modify settings with --set"""
    handle_config_command(
        set,
        git_profile,
        threshold,
        auto_init_git,
        temp_branches,
        temp_branch_prefix,
        temp_branch_cleanup_days,
        doh,
    )


@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(verbose):
    """Check all monitored directories and auto-commit if needed

    This command checks all monitored directories for changes and automatically
    commits when the change threshold is exceeded. Perfect for cron jobs.

    Examples:
        doh run           # Check all directories once
        doh run -v        # Check with verbose output
    """
    handle_run_command(verbose, doh)


@main.command("squash", short_help="Squash auto-commits")
@click.argument("commit_message")
@click.option(
    "--target",
    "-t",
    default="master",
    help="Target branch to squash into (default: master)",
)
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
def squash(commit_message, target, directory):
    """Squash temporary auto-commits into a single commit with proper message"""
    handle_squash_command(commit_message, target, directory)


@main.command("s", hidden=True)
@click.argument("commit_message")
@click.option(
    "--target",
    "-t",
    default="master",
    help="Target branch to squash into (default: master)",
)
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
@click.pass_context
def s(ctx, commit_message, target, directory):
    """Shorthand for squash command"""
    # Use Click's invoke to call the squash command
    ctx.invoke(
        squash, commit_message=commit_message, target=target, directory=directory
    )


@main.command()
@click.option(
    "--cleanup-days",
    "-d",
    default=7,
    type=int,
    help="Remove temp branches older than N days",
)
@click.option("--force", "-", is_flag=True, help="Skip confirmation prompt")
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
def cleanup(cleanup_days, force, directory):
    """Clean up old temporary branches"""
    handle_cleanup_command(cleanup_days, force, directory)


if __name__ == "__main__":
    main()
