#!/usr/bin/env python3
"""
Status display functions for DOH CLI.

This module contains all the functions responsible for displaying
status information in various formats (local, global, detailed).
"""

from pathlib import Path
import click
from .colors import Colors
from .config import DEFAULT_THRESHOLD
from .git_stats import GitStats


def show_single_directory_status(directory: Path, doh_core):
    """Helper function to show status of a single directory"""
    data = doh_core.config.load()
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


def show_global_status_summary(total, over_threshold, clean, issues, temp_branches):
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


def show_over_threshold_directories(over_threshold):
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


def show_directory_issues(issues):
    """Show directories with issues."""
    if not issues:
        return

    click.echo(f"{Colors.YELLOW}{Colors.BOLD}⚠ ISSUES:{Colors.RESET}")
    for name, path, issue in issues:
        click.echo(f"  {Colors.YELLOW}{name}: {issue}{Colors.RESET}")
        click.echo(f"    {path}")
    click.echo()


def show_temp_branches_global(temp_branches):
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


def show_clean_directories(clean):
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


def categorize_directories(directories):
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


def show_global_status(doh_core):
    """Show global status of all monitored directories."""
    data = doh_core.config.load()
    directories = data.get("directories", {})

    if not directories:
        click.echo(f"{Colors.YELLOW}No directories being monitored{Colors.RESET}")
        return

    over_threshold, clean, issues, temp_branches = categorize_directories(directories)

    # Show global summary and details
    show_global_status_summary(
        len(directories), over_threshold, clean, issues, temp_branches
    )
    show_over_threshold_directories(over_threshold)
    show_directory_issues(issues)
    show_temp_branches_global(temp_branches)
    show_clean_directories(clean)


def show_local_not_monitored(directory):
    """Show message when local directory is not monitored."""
    click.echo(f"{Colors.YELLOW}Current directory is not being monitored{Colors.RESET}")
    click.echo(f"Directory: {directory}")
    click.echo(f"{Colors.BLUE}💡 Use 'doh add' to add it to monitoring{Colors.RESET}")


def show_local_status_header(name, directory, threshold):
    """Show local status header."""
    click.echo(f"{Colors.BOLD}DOH Local Status: {name}{Colors.RESET}")
    click.echo(f"Directory: {directory}")
    click.echo(f"Threshold: {threshold} lines")
    click.echo()


def show_local_threshold_status(total_changes, threshold):
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


def show_local_change_details(stats):
    """Show local change details."""
    click.echo(f"\n{Colors.BOLD}Change Details:{Colors.RESET}")
    click.echo(f"  Modified files: {stats['files_changed']}")
    click.echo(f"  Lines added: {stats['added']}")
    click.echo(f"  Lines deleted: {stats['deleted']}")
    click.echo(f"  Untracked files: {stats['untracked']}")


def show_local_temp_branches(directory):
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


def show_local_file_changes(stats):
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


def show_local_status(directory, doh_core):
    """Show local status of a specific directory."""
    if directory is None:
        directory = Path.cwd()

    directory = directory.resolve()

    # Check if directory is monitored
    data = doh_core.config.load()
    directories = data.get("directories", {})

    if str(directory) not in directories:
        show_local_not_monitored(directory)
        return

    # Get directory info
    dir_info = directories[str(directory)]
    name = dir_info.get("name", directory.name)
    threshold = dir_info.get("threshold", DEFAULT_THRESHOLD)

    show_local_status_header(name, directory, threshold)

    if not GitStats.is_git_repo(directory):
        click.echo(f"{Colors.RED}❌ Not a git repository{Colors.RESET}")
        return

    # Get git stats
    stats = GitStats.get_stats(directory)
    if stats is None:
        click.echo(f"{Colors.RED}❌ Failed to get git statistics{Colors.RESET}")
        return

    total_changes = stats["total_changes"] + stats["untracked"]

    show_local_threshold_status(total_changes, threshold)
    show_local_change_details(stats)
    show_local_temp_branches(directory)
    show_local_file_changes(stats)

    click.echo(
        f"\n{Colors.BLUE}💡 Use 'doh status --global' to see all monitored directories{Colors.RESET}"
    )
