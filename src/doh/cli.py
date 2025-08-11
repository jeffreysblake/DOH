#!/usr/bin/env python3
"""
DOH - Directory Oh-no, Handle this!
A smart auto-commit monitoring system for git repositories.

This is a complete rewrite in Python for better performance, reliability,
and maintainability compared to the original bash implementation.
"""

import subprocess
from pathlib import Path

import click

from .core import DohCore
from .config import DEFAULT_THRESHOLD
from .git_stats import GitStats
from .colors import Colors


# Initialize core
doh = DohCore()


def _show_single_directory_status(directory: Path):
    """Helper function to show status of a single directory"""
    data = doh.config.load()
    directories = data.get("directories", {})

    if str(directory) not in directories:
        click.echo(f"{Colors.RED}Directory not monitored{Colors.RESET}")
        return

    info = directories[str(directory)]
    name = info.get("name", directory.name)
    threshold = info.get("threshold", DEFAULT_THRESHOLD)

    # Get git stats
    stats = GitStats.get_stats(directory)

    if stats is None:
        status = f"{Colors.RED}NOT A GIT REPO{Colors.RESET}"
        click.echo(f"  {Colors.BLUE}{name}{Colors.RESET}: {status}")
    elif not directory.exists():
        status = f"{Colors.RED}DIRECTORY NOT FOUND{Colors.RESET}"
        click.echo(f"  {Colors.BLUE}{name}{Colors.RESET}: {status}")
    else:
        total_changes = stats["total_changes"]
        # untracked = stats['untracked']  # unused
        untracked_lines = stats.get("untracked_lines", stats["untracked"])
        total_all = total_changes + untracked_lines

        if total_all == 0:
            status = f"{Colors.GREEN}CLEAN{Colors.RESET}"
        elif total_all >= threshold:
            status = (
                f"{Colors.RED}OVER THRESHOLD "
                f"({total_all}/{threshold}){Colors.RESET}"
            )
        else:
            status = (
                f"{Colors.YELLOW}HAS CHANGES "
                f"({total_all}/{threshold}){Colors.RESET}"
            )

        click.echo(f"  {Colors.BLUE}{name}{Colors.RESET}: {status}")
        changes_msg = (
            f"    Changes: +{stats['added']} -{stats['deleted']} "
            f"(files: {stats['files_changed']})"
        )
        click.echo(changes_msg)
        if stats["untracked"] > 0:
            click.echo(f"    Untracked: {stats['untracked']} files")

        # Show enhanced file details if there are changes
        file_stats = stats.get("file_stats", [])
        if file_stats:
            file_summary = GitStats.format_file_changes(file_stats, max_files=5)
            click.echo(f"    Files: {file_summary}")

            # Show warning if approaching threshold
            if total_all >= threshold * 0.8 and total_all < threshold:
                warning_msg = (
                    f"    {Colors.YELLOW}⚠ Approaching threshold - "
                    f"{threshold - total_all} lines remaining"
                    f"{Colors.RESET}"
                )
                click.echo(warning_msg)


def force_commit_directory(directory: Path) -> bool:
    """Force commit all changes in a directory"""
    if not GitStats.is_git_repo(directory):
        return False

    try:
        # Get current stats for enhanced commit message
        stats = GitStats.get_stats(directory)
        if not stats:
            return False

        # Use name from directory
        # name = directory.name  # unused
        # threshold = 0  # Force commit regardless of threshold  # unused

        # Get git profile from config if set
        data = doh.config.load()
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
            git_cmd + ["diff", "--staged", "--quiet"], capture_output=True, check=False
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
            git_cmd + ["commit", "-m", commit_msg], check=True, capture_output=True
        )
        return True

    except subprocess.CalledProcessError:
        return False


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
                    if force_commit_directory(directory):
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

            _show_single_directory_status(directory)
            return

        # Handle force commit first if requested (for new directories)
        if force:
            if force_commit_directory(directory):
                click.echo(
                    f"{Colors.GREEN}Changes committed successfully{Colors.RESET}"
                )
            else:
                click.echo(
                    f"{Colors.YELLOW}No changes to commit or commit failed{Colors.RESET}"
                )

        if doh.add_directory(directory, threshold, name):
            display_name = name or directory.name
            click.echo(
                f"{Colors.GREEN}✓ Added '{display_name}' to monitoring{Colors.RESET}"
            )
            click.echo(f"  Path: {directory}")
            click.echo(f"  Threshold: {threshold} lines")
            click.echo()
            _show_single_directory_status(directory)
        else:
            click.echo(
                f"{Colors.RED}✗ Failed to add directory to monitoring{Colors.RESET}"
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
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    # Get force flag from context
    force_commit = ctx.obj.get("force", False) if ctx.obj else False

    # Smart behavior: if already monitored, show status instead
    if doh.is_monitored(directory):
        click.echo(
            f"{Colors.YELLOW}Directory already monitored. Showing current status:{Colors.RESET}"
        )
        click.echo()
        _show_single_directory_status(directory)
        return

    # Handle force commit first if requested
    if force_commit:
        if force_commit_directory(directory):
            click.echo(f"{Colors.GREEN}Changes committed successfully{Colors.RESET}")
        else:
            click.echo(
                f"{Colors.YELLOW}No changes to commit or commit failed{Colors.RESET}"
            )

    if doh.add_directory(directory, threshold, name):
        display_name = name or directory.name
        click.echo(
            f"{Colors.GREEN}✓ Added '{display_name}' to monitoring{Colors.RESET}"
        )
        click.echo(f"  Path: {directory}")
        click.echo(f"  Threshold: {threshold} lines")
        click.echo()
        click.echo("Current status:")
        _show_single_directory_status(directory)
    else:
        click.echo(f"{Colors.RED}Failed to add directory{Colors.RESET}")


@main.command("rm")
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
def remove(directory):
    """Remove a directory from monitoring and exclusions"""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    if not doh.is_monitored(directory) and not doh.is_excluded(directory):
        click.echo(
            f"{Colors.YELLOW}Directory not being monitored or excluded{Colors.RESET}"
        )
        return

    if doh.remove_directory(directory):
        click.echo(
            f"{Colors.GREEN}Removed '{directory}' from monitoring/exclusions{Colors.RESET}"
        )
    else:
        click.echo(f"{Colors.RED}Failed to remove directory{Colors.RESET}")


@main.command()
def list():
    """List all monitored directories"""
    data = doh.config.load()
    directories = data.get("directories", {})

    if not directories:
        click.echo(f"{Colors.YELLOW}No directories being monitored{Colors.RESET}")
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
            # untracked = stats['untracked']  # unused
            untracked_lines = stats.get("untracked_lines", stats["untracked"])

            if total_changes + untracked_lines == 0:
                status = f"{Colors.GREEN}CLEAN{Colors.RESET}"
            elif total_changes + untracked_lines >= threshold:
                status = f"{Colors.RED}THRESHOLD EXCEEDED ({total_changes + untracked_lines}){Colors.RESET}"
            else:
                status = f"{Colors.YELLOW}CHANGES ({total_changes + untracked_lines}){Colors.RESET}"

        click.echo(f"{Colors.BLUE}{name:<30}{Colors.RESET} {status}")
        click.echo(f"  Path: {dir_path}")
        click.echo(f"  Threshold: {threshold}")

        if stats:
            click.echo(
                f"  Changes: +{stats['added']} -{stats['deleted']} (files: {stats['files_changed']})"
            )
            if stats["untracked"] > 0:
                click.echo(f"  Untracked: {stats['untracked']} files")

        click.echo()


def _show_global_status_summary(total, over_threshold, clean, issues, temp_branches):
    """Show the global status summary."""
    click.echo(f"{Colors.BOLD}DOH Global Status Summary:{Colors.RESET}")
    click.echo(f"Total directories: {total}")
    click.echo(f"{Colors.RED}Over threshold: {len(over_threshold)}{Colors.RESET}")
    click.echo(f"{Colors.GREEN}Clean: {len(clean)}{Colors.RESET}")
    click.echo(f"{Colors.YELLOW}Issues: {len(issues)}{Colors.RESET}")
    if temp_branches:
        click.echo(
            f"{Colors.BLUE}With temp branches: {len(temp_branches)}{Colors.RESET}"
        )
    click.echo()


def _show_over_threshold_directories(over_threshold):
    """Show directories that are over threshold."""
    if not over_threshold:
        return

    click.echo(f"{Colors.RED}{Colors.BOLD}⚠ OVER THRESHOLD:{Colors.RESET}")
    for name, path, changes, threshold in over_threshold:
        click.echo(
            f"  {Colors.RED}{name}: {changes} changes (threshold: {threshold}){Colors.RESET}"
        )
        click.echo(f"    {path}")
    click.echo()


def _show_directory_issues(issues):
    """Show directories with issues."""
    if not issues:
        return

    click.echo(f"{Colors.YELLOW}{Colors.BOLD}⚠ ISSUES:{Colors.RESET}")
    for name, path, issue in issues:
        click.echo(f"  {Colors.YELLOW}{name}: {issue}{Colors.RESET}")
        click.echo(f"    {path}")
    click.echo()


def _show_temp_branches_global(temp_branches):
    """Show directories with temp branches in global view."""
    if not temp_branches:
        return

    click.echo(
        f"{Colors.BLUE}{Colors.BOLD}🔀 TEMP BRANCHES ({len(temp_branches)} directories):{Colors.RESET}"
    )
    for name, path, branches in temp_branches:
        click.echo(f"  {Colors.BLUE}{name}:{Colors.RESET}")
        for branch_info in branches[:3]:  # Show first 3 branches
            branch_msg = (
                f"    {Colors.BLUE}• {branch_info['name']} "
                f"({branch_info['commit_count']} commits, "
                f"{branch_info['last_commit']}){Colors.RESET}"
            )
            click.echo(branch_msg)
        if len(branches) > 3:
            click.echo(
                f"    {Colors.BLUE}... and {len(branches) - 3} more branches{Colors.RESET}"
            )
        click.echo(
            f"    {Colors.BLUE}💡 Run 'doh squash \"message\"' in {path} to merge{Colors.RESET}"
        )
    click.echo()


def _show_clean_directories(clean):
    """Show clean directories (abbreviated)."""
    if not clean:
        return

    click.echo(
        f"{Colors.GREEN}{Colors.BOLD}✓ CLEAN ({len(clean)} directories):{Colors.RESET}"
    )
    for name, path, changes in clean[:5]:  # Show first 5
        if changes > 0:
            click.echo(f"  {Colors.GREEN}{name}: {changes} changes{Colors.RESET}")
        else:
            click.echo(f"  {Colors.GREEN}{name}: No changes{Colors.RESET}")

    if len(clean) > 5:
        click.echo(f"  {Colors.GREEN}... and {len(clean) - 5} more{Colors.RESET}")


def _categorize_directories(directories):
    """Categorize directories by status. Returns (over_threshold, clean, issues, temp_branches)."""
    over_threshold = []
    clean = []
    issues = []
    temp_branches = []

    for dir_path, info in directories.items():
        directory_path = Path(dir_path)
        # Get name and threshold from directory info
        name = info.get("name", directory_path.name)
        threshold = info.get("threshold", DEFAULT_THRESHOLD)

        if not directory_path.exists():
            issues.append((name, dir_path, "Directory not found"))
            continue

        stats = GitStats.get_stats(directory_path)
        if stats is None:
            issues.append((name, dir_path, "Not a git repository"))
            continue

        # Check for temp branches
        temp_branch_list = GitStats.list_temp_branches(directory_path)
        if temp_branch_list:
            temp_branches.append((name, dir_path, temp_branch_list))

        total_changes = stats["total_changes"] + stats["untracked"]

        if total_changes >= threshold:
            over_threshold.append((name, dir_path, total_changes, threshold))
        else:
            clean.append((name, dir_path, total_changes))

    return over_threshold, clean, issues, temp_branches


def _show_global_status():
    """Show global status of all monitored directories."""
    data = doh.config.load()
    directories = data.get("directories", {})

    if not directories:
        click.echo(f"{Colors.YELLOW}No directories being monitored{Colors.RESET}")
        return

    over_threshold, clean, issues, temp_branches = _categorize_directories(directories)

    # Show global summary and details
    _show_global_status_summary(
        len(directories), over_threshold, clean, issues, temp_branches
    )
    _show_over_threshold_directories(over_threshold)
    _show_directory_issues(issues)
    _show_temp_branches_global(temp_branches)
    _show_clean_directories(clean)


def _show_local_not_monitored(directory):
    """Show message when local directory is not monitored."""
    click.echo(f"{Colors.YELLOW}Current directory is not being monitored{Colors.RESET}")
    click.echo(f"Directory: {directory}")
    click.echo(f"{Colors.BLUE}💡 Use 'doh add' to add it to monitoring{Colors.RESET}")


def _show_local_status_header(name, directory, threshold):
    """Show local status header."""
    click.echo(f"{Colors.BOLD}DOH Local Status: {name}{Colors.RESET}")
    click.echo(f"Directory: {directory}")
    click.echo(f"Threshold: {threshold} lines")
    click.echo()


def _show_local_threshold_status(total_changes, threshold):
    """Show whether local directory is over/under threshold."""
    if total_changes >= threshold:
        msg = (
            f"{Colors.RED}🚨 OVER THRESHOLD: {total_changes} changes "
            f"(threshold: {threshold}){Colors.RESET}"
        )
        click.echo(msg)
    else:
        msg = (
            f"{Colors.GREEN}✅ CLEAN: {total_changes} changes "
            f"(under threshold: {threshold}){Colors.RESET}"
        )
        click.echo(msg)


def _show_local_change_details(stats):
    """Show local change details."""
    click.echo(f"\n{Colors.BOLD}Change Details:{Colors.RESET}")
    click.echo(f"  Modified files: {stats['files_changed']}")
    click.echo(f"  Lines added: {stats['added']}")
    click.echo(f"  Lines deleted: {stats['deleted']}")
    click.echo(f"  Untracked files: {stats['untracked']}")


def _show_local_temp_branches(directory):
    """Show temp branches for local directory."""
    temp_branch_list = GitStats.list_temp_branches(directory)
    if temp_branch_list:
        click.echo(f"\n{Colors.BLUE}{Colors.BOLD}🔀 TEMP BRANCHES:{Colors.RESET}")
        for branch_info in temp_branch_list:
            branch_msg = (
                f"  {Colors.BLUE}• {branch_info['name']} "
                f"({branch_info['commit_count']} commits, "
                f"{branch_info['last_commit']}){Colors.RESET}"
            )
            click.echo(branch_msg)
        click.echo(
            f"\n{Colors.BLUE}💡 Use 'doh squash \"message\"' to merge these commits{Colors.RESET}"
        )


def _show_local_file_changes(stats):
    """Show local file changes."""
    if not stats["file_stats"]:
        return

    click.echo(f"\n{Colors.BOLD}Files Changed:{Colors.RESET}")
    for file_stat in stats["file_stats"][:10]:  # Show first 10 files
        file_path = file_stat["file"]
        added = file_stat["added"]
        deleted = file_stat["deleted"]
        status = file_stat["status"]

        if status == "new":
            click.echo(f"  {Colors.GREEN}+ {file_path} (+{added}){Colors.RESET}")
        elif status == "deleted":
            click.echo(f"  {Colors.RED}- {file_path} (-{deleted}){Colors.RESET}")
        elif added > 0 and deleted > 0:
            click.echo(
                f"  {Colors.YELLOW}~ {file_path} (+{added}/-{deleted}){Colors.RESET}"
            )
        elif added > 0:
            click.echo(f"  {Colors.BLUE}~ {file_path} (~{added}){Colors.RESET}")
        else:
            click.echo(f"  {Colors.YELLOW}~ {file_path} (modified){Colors.RESET}")

    if len(stats["file_stats"]) > 10:
        remaining = len(stats["file_stats"]) - 10
        click.echo(f"  {Colors.YELLOW}... and {remaining} more files{Colors.RESET}")


def _show_local_status(directory):
    """Show local status of a specific directory."""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    # Check if directory is monitored
    data = doh.config.load()
    directories = data.get("directories", {})

    if str(directory) not in directories:
        _show_local_not_monitored(directory)
        return

    # Get directory info
    dir_info = directories[str(directory)]
    name = dir_info.get("name", directory.name)
    threshold = dir_info.get("threshold", DEFAULT_THRESHOLD)

    _show_local_status_header(name, directory, threshold)

    if not GitStats.is_git_repo(directory):
        click.echo(f"{Colors.RED}❌ Not a git repository{Colors.RESET}")
        return

    # Get git stats
    stats = GitStats.get_stats(directory)
    if stats is None:
        click.echo(f"{Colors.RED}❌ Failed to get git statistics{Colors.RESET}")
        return

    total_changes = stats["total_changes"] + stats["untracked"]

    _show_local_threshold_status(total_changes, threshold)
    _show_local_change_details(stats)
    _show_local_temp_branches(directory)
    _show_local_file_changes(stats)

    click.echo(
        f"\n{Colors.BLUE}💡 Use 'doh status --global' to see all monitored directories{Colors.RESET}"
    )


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

    if show_global:
        _show_global_status()
    else:
        _show_local_status(directory)


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
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    if doh.is_excluded(directory):
        click.echo(f"{Colors.YELLOW}Directory already excluded{Colors.RESET}")
        return

    if doh.add_exclusion(directory):
        click.echo(f"{Colors.GREEN}Added '{directory}' to exclusions{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}Failed to add exclusion{Colors.RESET}")


@exclusions.command("rm")
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
def exclusions_remove(directory):
    """Remove a directory from exclusions"""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    if not doh.is_excluded(directory):
        click.echo(f"{Colors.YELLOW}Directory not in exclusions{Colors.RESET}")
        return

    if doh.remove_exclusion(directory):
        click.echo(f"{Colors.GREEN}Removed '{directory}' from exclusions{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}Failed to remove exclusion{Colors.RESET}")


@exclusions.command("list")
def exclusions_list():
    """List all excluded directories"""
    data = doh.config.load()
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


def _update_git_profile_setting(settings, git_profile):
    """Update git profile setting and show result."""
    if git_profile is None:
        return False

    settings["git_profile"] = git_profile
    click.echo(f"{Colors.GREEN}✓ Git profile set to: {git_profile}{Colors.RESET}")

    # Verify the profile exists
    profile_path = Path(git_profile).expanduser()
    if not profile_path.exists():
        warning_msg = (
            f"{Colors.YELLOW}⚠ Warning: Git profile file does not "
            f"exist: {profile_path}{Colors.RESET}"
        )
        click.echo(warning_msg)

    return True


def _update_config_settings(
    settings,
    git_profile,
    threshold,
    auto_init_git,
    temp_branches,
    temp_branch_prefix,
    temp_branch_cleanup_days,
):
    """Update all configuration settings. Returns True if any changes were made."""
    changed = False

    changed |= _update_git_profile_setting(settings, git_profile)

    if threshold is not None:
        settings["default_threshold"] = threshold
        changed = True
        click.echo(
            f"{Colors.GREEN}✓ Default threshold set to: {threshold}{Colors.RESET}"
        )

    if auto_init_git is not None:
        settings["auto_init_git"] = auto_init_git
        changed = True
        status = "enabled" if auto_init_git else "disabled"
        click.echo(f"{Colors.GREEN}✓ Auto git init {status}{Colors.RESET}")

    if temp_branches is not None:
        settings["use_temp_branches"] = temp_branches
        changed = True
        status = "enabled" if temp_branches else "disabled"
        click.echo(f"{Colors.GREEN}✓ Temporary branch strategy {status}{Colors.RESET}")

    if temp_branch_prefix is not None:
        settings["temp_branch_prefix"] = temp_branch_prefix
        changed = True
        click.echo(
            f"{Colors.GREEN}✓ Temporary branch prefix set to: {temp_branch_prefix}{Colors.RESET}"
        )

    if temp_branch_cleanup_days is not None:
        settings["max_temp_branch_age_days"] = temp_branch_cleanup_days
        changed = True
        click.echo(
            f"{Colors.GREEN}✓ Temporary branch cleanup age set to: {temp_branch_cleanup_days} days{Colors.RESET}"
        )

    return changed


def _show_config_display():
    """Show current configuration in display mode."""
    click.echo(f"{Colors.BOLD}DOH Configuration:{Colors.RESET}")
    click.echo(f"Config file: {doh.config.config_file}")
    click.echo(f"Config dir: {doh.config.config_dir}")
    click.echo()

    data = doh.config.load()

    directories = data.get("directories", {})
    exclusions_dict = data.get("exclusions", {})
    settings = data.get("global_settings", {})

    click.echo(f"Monitored directories: {len(directories)}")
    click.echo(f"Excluded directories: {len(exclusions_dict)}")
    click.echo(
        f"Default threshold: {settings.get('default_threshold', DEFAULT_THRESHOLD)}"
    )
    click.echo(f"Git profile: {settings.get('git_profile', 'None')}")
    click.echo(f"Auto git init: {settings.get('auto_init_git', True)}")
    click.echo(f"Use temp branches: {settings.get('use_temp_branches', True)}")
    click.echo(
        f"Temp branch prefix: {settings.get('temp_branch_prefix', 'doh-auto-commits')}"
    )
    click.echo(
        f"Temp branch cleanup days: {settings.get('max_temp_branch_age_days', 7)}"
    )

    if doh.config.config_file.exists():
        size = doh.config.config_file.stat().st_size
        click.echo(f"Config file size: {size} bytes")


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

    # Check if any configuration options are provided
    has_config_options = any(
        [
            git_profile,
            threshold,
            auto_init_git is not None,
            temp_branches is not None,
            temp_branch_prefix,
            temp_branch_cleanup_days,
        ]
    )

    if has_config_options and not set:
        click.echo(
            f"{Colors.YELLOW}To modify configuration, use --set flag with your options.{Colors.RESET}"
        )
        click.echo("Example: doh config --set --threshold 100")
        return

    if set or has_config_options:
        # Configuration mode
        data = doh.config.load()
        settings = data.setdefault("global_settings", {})

        changed = _update_config_settings(
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

        if doh.config.save(data):
            click.echo(f"{Colors.GREEN}Configuration saved successfully{Colors.RESET}")
        else:
            click.echo(f"{Colors.RED}Failed to save configuration{Colors.RESET}")
    else:
        # Display mode (default behavior)
        _show_config_display()


@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def _handle_temp_branch_strategy(
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


def _stage_and_check_changes(git_cmd: list, name: str, verbose: bool) -> bool:
    """Stage changes and check if there's anything to commit"""
    # Stage all changes
    subprocess.run(git_cmd + ["add", "."], capture_output=True, check=True)

    # Check if there's anything to commit
    result = subprocess.run(
        git_cmd + ["diff", "--staged", "--quiet"], capture_output=True, check=False
    )

    if result.returncode == 0:
        # Nothing staged to commit
        if verbose:
            click.echo(
                f"{Colors.YELLOW}• {name}: No changes to commit" f"{Colors.RESET}"
            )
        return False
    return True


def _create_commit_and_log(
    git_cmd: list,
    name: str,
    stats: dict,
    threshold: int,
    use_temp_branches: bool,
    temp_branch_prefix: str,
) -> None:
    """Create commit and display success log"""
    # Use enhanced commit message format
    commit_msg = GitStats.create_enhanced_commit_message(name, stats, threshold)

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
            f"{Colors.GREEN}✓ Auto-committed '{name}': " f"{file_summary}{Colors.RESET}"
        )


def _auto_commit_directory(
    directory: Path, stats: dict, threshold: int, name: str, verbose: bool
) -> bool:
    """Perform auto-commit for a directory"""
    try:
        # Get configuration settings
        data = doh.config.load()
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
        use_temp_branches = _handle_temp_branch_strategy(
            directory, name, git_cmd, use_temp_branches, temp_branch_prefix, verbose
        )

        # Stage and check for changes
        if not _stage_and_check_changes(git_cmd, name, verbose):
            return False

        # Create commit and log success
        _create_commit_and_log(
            git_cmd, name, stats, threshold, use_temp_branches, temp_branch_prefix
        )

        return True

    except subprocess.CalledProcessError as e:
        if verbose:
            click.echo(
                f"{Colors.RED}✗ Failed to commit '{name}': " f"{e}{Colors.RESET}"
            )
        return False


def _process_monitored_directories(directories: dict, verbose: bool) -> int:
    """Process all monitored directories and return commit count"""
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
            if _auto_commit_directory(directory, stats, threshold, name, verbose):
                committed += 1
        elif verbose:
            click.echo(
                f"{Colors.GREEN}• {name}: {total_changes} changes "
                f"(under threshold {threshold}){Colors.RESET}"
            )

    return committed


def run(verbose):
    """Check all monitored directories and auto-commit if needed

    This command checks all monitored directories for changes and automatically
    commits when the change threshold is exceeded. Perfect for cron jobs.

    Examples:
        doh run           # Check all directories once
        doh run -v        # Check with verbose output
    """
    data = doh.config.load()
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

    committed = _process_monitored_directories(directories, verbose)

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
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    if not GitStats.is_git_repo(directory):
        click.echo(f"{Colors.RED}Not a git repository: {directory}{Colors.RESET}")
        return

    # Check if there are temp branches to squash
    temp_branches = GitStats.list_temp_branches(directory)
    if not temp_branches:
        click.echo(
            f"{Colors.YELLOW}No temporary branches found to squash{Colors.RESET}"
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
            temp_branch = sorted(temp_branches, key=lambda b: b["name"])[-1]["name"]

        if not temp_branch:
            click.echo(f"{Colors.YELLOW}No temporary branch to squash{Colors.RESET}")
            return

        if GitStats.squash_temp_commits(directory, target, commit_message, temp_branch):
            click.echo(
                f"{Colors.GREEN}✓ Successfully squashed temp commits into '{target}'{Colors.RESET}"
            )
            click.echo(f"  Commit message: {commit_message}")
        else:
            click.echo(f"{Colors.RED}✗ Failed to squash temporary branch{Colors.RESET}")

    except subprocess.CalledProcessError as e:
        click.echo(f"{Colors.RED}Git error: {e}{Colors.RESET}")


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
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    if not GitStats.is_git_repo(directory):
        click.echo(f"{Colors.RED}Not a git repository: {directory}{Colors.RESET}")
        return

    branches = GitStats.list_temp_branches(directory)

    if not branches:
        click.echo(f"{Colors.YELLOW}No temporary branches to clean up{Colors.RESET}")
        return

    click.echo(
        f"{Colors.BLUE}Found {len(branches)} temporary branches in {directory.name}:{Colors.RESET}"
    )
    for branch in branches:
        click.echo(
            f"  {Colors.GREEN}{branch['name']}{Colors.RESET} ({branch['commit_count']} commits, {branch['last_commit']})"
        )

    if not force:
        click.echo(
            f"\n{Colors.YELLOW}This will delete branches older than {cleanup_days} days.{Colors.RESET}"
        )
        if not click.confirm("Are you sure you want to continue?"):
            click.echo(f"{Colors.YELLOW}Cleanup cancelled{Colors.RESET}")
            return

    # TODO: Implement age-based cleanup logic
    click.echo(
        f"{Colors.GREEN}Cleanup logic for branches older than {cleanup_days} days - Coming soon!{Colors.RESET}"
    )
    click.echo(
        f"{Colors.BLUE}Use --force to skip this confirmation in the future{Colors.RESET}"
    )


# Hide the daemon command but keep it functional for systemd


if __name__ == "__main__":
    main()
