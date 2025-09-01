#!/usr/bin/env python3
"""
Configuration management functions for DOH CLI.

This module contains functions for displaying and modifying
DOH configuration settings.
"""

from pathlib import Path
from typing import Any, Optional
import click
from .colors import Colors
from .config import DEFAULT_THRESHOLD


def update_git_profile_setting(
    settings: dict, git_profile: Optional[str]
) -> bool:
    """Update git profile setting and show result."""
    if git_profile is None:
        return False

    settings["git_profile"] = git_profile
    click.echo(
        f"{Colors.GREEN}✓ Git profile set to: {git_profile}{Colors.RESET}"
    )

    # Verify the profile exists
    profile_path = Path(git_profile).expanduser()
    if not profile_path.exists():
        warning_msg = (
            f"{Colors.YELLOW}⚠ Warning: Git profile file does not "
            f"exist: {profile_path}{Colors.RESET}"
        )
        click.echo(warning_msg)

    return True


def update_config_settings(
    settings: dict,
    git_profile: Optional[str],
    threshold: Optional[int],
    auto_init_git: Optional[bool],
    temp_branches: Optional[bool],
    temp_branch_prefix: Optional[str],
    temp_branch_cleanup_days: Optional[int],
) -> bool:
    """Update all configuration settings.

    Returns True if any changes were made.
    """
    changed = False

    changed |= update_git_profile_setting(settings, git_profile)

    if threshold is not None:
        settings["default_threshold"] = threshold
        changed = True
        click.echo(
            f"{Colors.GREEN}✓ Default threshold set to: "
            f"{threshold}{Colors.RESET}"
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
        click.echo(
            f"{Colors.GREEN}✓ Temporary branch strategy {status}{Colors.RESET}"
        )

    if temp_branch_prefix is not None:
        settings["temp_branch_prefix"] = temp_branch_prefix
        changed = True
        click.echo(
            f"{Colors.GREEN}✓ Temporary branch prefix set to: "
            f"{temp_branch_prefix}{Colors.RESET}"
        )

    if temp_branch_cleanup_days is not None:
        settings["max_temp_branch_age_days"] = temp_branch_cleanup_days
        changed = True
        click.echo(
            f"{Colors.GREEN}✓ Temporary branch cleanup age set to: "
            f"{temp_branch_cleanup_days} days{Colors.RESET}"
        )

    return changed


def show_config_display(doh_core: Any) -> None:
    """Show current configuration in display mode."""
    click.echo(f"{Colors.BOLD}DOH Configuration:{Colors.RESET}")
    click.echo(f"Config file: {doh_core.config.config_file}")
    click.echo(f"Config dir: {doh_core.config.config_dir}")
    click.echo()

    data = doh_core.config.load()

    directories = data.get("directories", {})
    exclusions_dict = data.get("exclusions", {})
    settings = data.get("global_settings", {})

    click.echo(f"Monitored directories: {len(directories)}")
    click.echo(f"Excluded directories: {len(exclusions_dict)}")
    default_threshold = settings.get('default_threshold', DEFAULT_THRESHOLD)
    click.echo(f"Default threshold: {default_threshold}")
    click.echo(f"Git profile: {settings.get('git_profile', 'None')}")
    click.echo(f"Auto git init: {settings.get('auto_init_git', True)}")
    click.echo(f"Use temp branches: {settings.get('use_temp_branches', True)}")
    temp_prefix = settings.get('temp_branch_prefix', 'doh-auto-commits')
    click.echo(f"Temp branch prefix: {temp_prefix}")
    temp_cleanup_days = settings.get('max_temp_branch_age_days', 365)
    click.echo(f"Temp branch cleanup days: {temp_cleanup_days}")

    if doh_core.config.config_file.exists():
        size = doh_core.config.config_file.stat().st_size
        click.echo(f"Config file size: {size} bytes")
