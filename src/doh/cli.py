#!/usr/bin/env python3
"""
DOH - Directory Oh-no, Handle this!
A smart auto-commit monitoring system for git repositories.

This is a complete rewrite in Python for better performance, reliability,
and maintainability compared to the original bash implementation.
"""

import subprocess
from datetime import datetime
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
    directories = data.get('directories', {})
    
    if str(directory) not in directories:
        click.echo(f"{Colors.RED}Directory not monitored{Colors.RESET}")
        return
    
    info = directories[str(directory)]
    name = info.get('name', directory.name)
    threshold = info.get('threshold', DEFAULT_THRESHOLD)
    
    # Get git stats
    stats = GitStats.get_stats(directory)
    
    if stats is None:
        status = f"{Colors.RED}NOT A GIT REPO{Colors.RESET}"
    elif not directory.exists():
        status = f"{Colors.RED}DIRECTORY NOT FOUND{Colors.RESET}"
    else:
        total_changes = stats['total_changes']
        untracked = stats['untracked']
        total_all = total_changes + untracked
        
        if total_all == 0:
            status = f"{Colors.GREEN}CLEAN{Colors.RESET}"
        elif total_all >= threshold:
            status = f"{Colors.RED}OVER THRESHOLD ({total_all}/{threshold}){Colors.RESET}"
        else:
            status = f"{Colors.YELLOW}HAS CHANGES ({total_all}/{threshold}){Colors.RESET}"
    
    click.echo(f"  {Colors.BLUE}{name}{Colors.RESET}: {status}")
    if stats:
        click.echo(f"    Changes: +{stats['added']} -{stats['deleted']} (files: {stats['files_changed']})")
        if stats['untracked'] > 0:
            click.echo(f"    Untracked: {stats['untracked']} files")


def force_commit_directory(directory: Path) -> bool:
    """Force commit all changes in a directory"""
    if not GitStats.is_git_repo(directory):
        return False
    
    try:
        # Add all changes
        subprocess.run(['git', '-C', str(directory), 'add', '.'], check=True, capture_output=True)
        
        # Check if there's anything to commit
        result = subprocess.run(
            ['git', '-C', str(directory), 'diff', '--staged', '--quiet'],
            capture_output=True, check=False
        )
        
        if result.returncode == 0:
            # Nothing staged to commit
            return False
        
        # Create commit with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"DOH auto-commit: {timestamp}"
        
        subprocess.run(
            ['git', '-C', str(directory), 'commit', '-m', commit_msg],
            check=True, capture_output=True
        )
        return True
        
    except subprocess.CalledProcessError:
        return False


@click.group()
@click.version_option(version="2.0.0", prog_name="doh")
def main():
    """DOH - Directory Oh-no, Handle this!
    
    A smart auto-commit monitoring system for git repositories.
    """
    pass


@main.command()
@click.option('--threshold', '-t', default=DEFAULT_THRESHOLD, type=int,
              help=f'Change threshold (default: {DEFAULT_THRESHOLD})')
@click.option('--name', '-n', help='Name for this directory (defaults to directory name)')
@click.option('--force-commit', '-f', is_flag=True, help='Force commit changes if any exist')
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), 
                required=False)
def add(directory, threshold, name, force_commit):
    """Add a directory to monitoring"""
    if directory is None:
        directory = Path.cwd()
    
    directory = directory.resolve()
    
    # Smart behavior: if already monitored, show status instead
    if doh.is_monitored(directory):
        click.echo(f"{Colors.YELLOW}Directory already monitored. Showing current status:{Colors.RESET}")
        click.echo()
        _show_single_directory_status(directory)
        return
    
    # Handle force commit first if requested
    if force_commit:
        if force_commit_directory(directory):
            click.echo(f"{Colors.GREEN}Changes committed successfully{Colors.RESET}")
        else:
            click.echo(f"{Colors.YELLOW}No changes to commit or commit failed{Colors.RESET}")
    
    if doh.add_directory(directory, threshold, name):
        display_name = name or directory.name
        click.echo(f"{Colors.GREEN}✓ Added '{display_name}' to monitoring{Colors.RESET}")
        click.echo(f"  Path: {directory}")
        click.echo(f"  Threshold: {threshold} lines")
        click.echo()
        click.echo("Current status:")
        _show_single_directory_status(directory)
    else:
        click.echo(f"{Colors.RED}Failed to add directory{Colors.RESET}")


@main.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
                required=False)
def remove(directory):
    """Remove a directory from monitoring and exclusions"""
    if directory is None:
        directory = Path.cwd()
    
    directory = directory.resolve()
    
    if not doh.is_monitored(directory) and not doh.is_excluded(directory):
        click.echo(f"{Colors.YELLOW}Directory not being monitored or excluded{Colors.RESET}")
        return
    
    if doh.remove_directory(directory):
        click.echo(f"{Colors.GREEN}Removed '{directory}' from monitoring/exclusions{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}Failed to remove directory{Colors.RESET}")


@main.command()
def list():
    """List all monitored directories"""
    data = doh.config.load()
    directories = data.get('directories', {})
    
    if not directories:
        click.echo(f"{Colors.YELLOW}No directories being monitored{Colors.RESET}")
        return
    
    click.echo(f"{Colors.BOLD}Monitored Directories:{Colors.RESET}")
    click.echo("-" * 80)
    
    for dir_path, info in directories.items():
        directory = Path(dir_path)
        name = info.get('name', directory.name)
        threshold = info.get('threshold', DEFAULT_THRESHOLD)
        
        # Get git stats
        stats = GitStats.get_stats(directory)
        
        if stats is None:
            status = f"{Colors.RED}NOT A GIT REPO{Colors.RESET}"
        elif not directory.exists():
            status = f"{Colors.RED}DIRECTORY NOT FOUND{Colors.RESET}"
        else:
            total_changes = stats['total_changes']
            untracked = stats['untracked']
            
            if total_changes + untracked == 0:
                status = f"{Colors.GREEN}CLEAN{Colors.RESET}"
            elif total_changes + untracked >= threshold:
                status = f"{Colors.RED}THRESHOLD EXCEEDED ({total_changes + untracked}){Colors.RESET}"
            else:
                status = f"{Colors.YELLOW}CHANGES ({total_changes + untracked}){Colors.RESET}"
        
        click.echo(f"{Colors.BLUE}{name:<30}{Colors.RESET} {status}")
        click.echo(f"  Path: {dir_path}")
        click.echo(f"  Threshold: {threshold}")
        
        if stats:
            click.echo(f"  Changes: +{stats['added']} -{stats['deleted']} (files: {stats['files_changed']})")
            if stats['untracked'] > 0:
                click.echo(f"  Untracked: {stats['untracked']} files")
        
        click.echo()


@main.command()
def status():
    """Show status of all monitored directories"""
    data = doh.config.load()
    directories = data.get('directories', {})
    
    if not directories:
        click.echo(f"{Colors.YELLOW}No directories being monitored{Colors.RESET}")
        return
    
    over_threshold = []
    clean = []
    issues = []
    
    for dir_path, info in directories.items():
        directory = Path(dir_path)
        name = info.get('name', directory.name)
        threshold = info.get('threshold', DEFAULT_THRESHOLD)
        
        if not directory.exists():
            issues.append((name, dir_path, "Directory not found"))
            continue
        
        stats = GitStats.get_stats(directory)
        if stats is None:
            issues.append((name, dir_path, "Not a git repository"))
            continue
        
        total_changes = stats['total_changes'] + stats['untracked']
        
        if total_changes >= threshold:
            over_threshold.append((name, dir_path, total_changes, threshold))
        else:
            clean.append((name, dir_path, total_changes))
    
    # Show summary
    total = len(directories)
    click.echo(f"{Colors.BOLD}DOH Status Summary:{Colors.RESET}")
    click.echo(f"Total directories: {total}")
    click.echo(f"{Colors.RED}Over threshold: {len(over_threshold)}{Colors.RESET}")
    click.echo(f"{Colors.GREEN}Clean: {len(clean)}{Colors.RESET}")
    click.echo(f"{Colors.YELLOW}Issues: {len(issues)}{Colors.RESET}")
    click.echo()
    
    # Show over threshold
    if over_threshold:
        click.echo(f"{Colors.RED}{Colors.BOLD}⚠ OVER THRESHOLD:{Colors.RESET}")
        for name, path, changes, threshold in over_threshold:
            click.echo(f"  {Colors.RED}{name}: {changes} changes (threshold: {threshold}){Colors.RESET}")
            click.echo(f"    {path}")
        click.echo()
    
    # Show issues
    if issues:
        click.echo(f"{Colors.YELLOW}{Colors.BOLD}⚠ ISSUES:{Colors.RESET}")
        for name, path, issue in issues:
            click.echo(f"  {Colors.YELLOW}{name}: {issue}{Colors.RESET}")
            click.echo(f"    {path}")
        click.echo()
    
    # Show clean (abbreviated)
    if clean:
        click.echo(f"{Colors.GREEN}{Colors.BOLD}✓ CLEAN ({len(clean)} directories):{Colors.RESET}")
        for name, path, changes in clean[:5]:  # Show first 5
            if changes > 0:
                click.echo(f"  {Colors.GREEN}{name}: {changes} changes{Colors.RESET}")
            else:
                click.echo(f"  {Colors.GREEN}{name}: No changes{Colors.RESET}")
        
        if len(clean) > 5:
            click.echo(f"  {Colors.GREEN}... and {len(clean) - 5} more{Colors.RESET}")


@main.group()
def exclusions():
    """Manage directory exclusions"""
    pass


@exclusions.command('add')
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
                required=False)
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


@exclusions.command('remove')
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
                required=False)
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


@exclusions.command('list')
def exclusions_list():
    """List all excluded directories"""
    data = doh.config.load()
    exclusions_dict = data.get('exclusions', {})
    
    if not exclusions_dict:
        click.echo(f"{Colors.YELLOW}No directories excluded{Colors.RESET}")
        return
    
    click.echo(f"{Colors.BOLD}Excluded Directories:{Colors.RESET}")
    click.echo("-" * 80)
    
    for dir_path, info in exclusions_dict.items():
        directory = Path(dir_path)
        excluded_date = info.get('excluded', 'Unknown')
        
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
ex.add_command(exclusions_add, name='add')
ex.add_command(exclusions_remove, name='remove') 
ex.add_command(exclusions_remove, name='rm')  # Alias for remove
ex.add_command(exclusions_list, name='list')
ex.add_command(exclusions_list, name='ls')    # Alias for list


@main.command()
def config():
    """Show configuration file location and contents"""
    click.echo(f"{Colors.BOLD}DOH Configuration:{Colors.RESET}")
    click.echo(f"Config file: {doh.config.config_file}")
    click.echo(f"Config dir: {doh.config.config_dir}")
    click.echo()
    
    data = doh.config.load()
    
    directories = data.get('directories', {})
    exclusions_dict = data.get('exclusions', {})
    settings = data.get('global_settings', {})
    
    click.echo(f"Monitored directories: {len(directories)}")
    click.echo(f"Excluded directories: {len(exclusions_dict)}")
    click.echo(f"Default threshold: {settings.get('default_threshold', DEFAULT_THRESHOLD)}")
    
    if doh.config.config_file.exists():
        size = doh.config.config_file.stat().st_size
        click.echo(f"Config file size: {size} bytes")


if __name__ == "__main__":
    main()

# CLI Commands
@click.group(invoke_without_command=True)
@click.option('--threshold', '-t', type=int, default=DEFAULT_THRESHOLD, 
              help=f'Lines threshold (default: {DEFAULT_THRESHOLD})')
@click.option('--name', '-n', help='Set a name for this directory')
@click.pass_context
def cli(ctx, threshold, name):
    """DOH - Directory Oh-no, Handle this!
    
    Quick command to add current directory to auto-commit monitoring.
    If directory is already monitored, shows status instead.
    """
    if ctx.invoked_subcommand is None:
        # Default action: add current directory or show status
        current_dir = Path.cwd()
        doh = DohCore()
        
        if doh.is_monitored(current_dir):
            click.echo(f"{Colors.YELLOW}Directory already monitored. Showing current status:{Colors.RESET}")
            click.echo()
            ctx.invoke(status)
        else:
            # Add directory
            if doh.add_directory(current_dir, threshold, name or ""):
                display_name = name or current_dir.name
                click.echo(f"{Colors.GREEN}✓ Added '{display_name}' to monitoring{Colors.RESET}")
                click.echo(f"  Path: {current_dir}")
                click.echo(f"  Threshold: {threshold} lines")
                click.echo()
                click.echo("Current status:")
                ctx.invoke(status)

@cli.command()
def status():
    """Show status of current directory"""
    current_dir = Path.cwd()
    doh = DohCore()
    
    stats = GitStats.get_stats(current_dir)
    if stats is None:
        click.echo(f"{Colors.RED}Not a git repository{Colors.RESET}")
        return
    
    # Get config values
    data = doh.config.load()
    dir_config = data.get('directories', {}).get(str(current_dir), {})
    threshold = dir_config.get('threshold', DEFAULT_THRESHOLD)
    name = dir_config.get('name', '')
    
    click.echo(f"{Colors.BLUE}Directory Status: {current_dir}{Colors.RESET}")
    if name:
        click.echo(f"{Colors.BLUE}Name: {name}{Colors.RESET}")
    
    click.echo(f"Changes: {stats['total_changes']} lines (+{stats['added']}/-{stats['deleted']}) in {stats['files_changed']} files")
    click.echo(f"Untracked files: {stats['untracked']}")
    click.echo(f"Threshold: {threshold} lines")
    
    # Status assessment
    if stats['total_changes'] > 0:
        if stats['total_changes'] >= threshold:
            click.echo(f"{Colors.YELLOW}⚠️  Status: THRESHOLD EXCEEDED - Auto-commit ready{Colors.RESET}")
            click.echo(f"   Would trigger: {stats['total_changes']} >= {threshold} lines")
        else:
            click.echo(f"{Colors.GREEN}✓ Status: THRESHOLD NOT MET{Colors.RESET}")
            progress = (stats['total_changes'] * 100) // threshold
            click.echo(f"   Progress: {stats['total_changes']}/{threshold} lines ({progress}%)")
    else:
        click.echo(f"{Colors.GREEN}✓ Status: CLEAN - No changes{Colors.RESET}")
    
    # Monitoring status
    if doh.is_excluded(current_dir):
        excluded_parent = doh.find_excluded_parent(current_dir)
        if excluded_parent == current_dir:
            click.echo(f"{Colors.RED}📍 Directory is EXCLUDED from monitoring{Colors.RESET}")
        else:
            click.echo(f"{Colors.RED}📍 Directory is EXCLUDED (parent '{excluded_parent}' is excluded){Colors.RESET}")
    elif doh.is_monitored(current_dir):
        click.echo(f"{Colors.GREEN}📍 Directory is being MONITORED{Colors.RESET}")
    else:
        click.echo(f"{Colors.YELLOW}📍 Directory NOT monitored (run 'doh' to add){Colors.RESET}")

@cli.command()
def remove():
    """Remove current directory from monitoring"""
    current_dir = Path.cwd()
    doh = DohCore()
    
    if doh.is_monitored(current_dir):
        if doh.remove_directory(current_dir):
            click.echo(f"{Colors.GREEN}✓ Removed {current_dir} from monitoring{Colors.RESET}")
        else:
            click.echo(f"{Colors.RED}Failed to remove directory{Colors.RESET}")
    else:
        click.echo(f"{Colors.YELLOW}Directory is not currently monitored{Colors.RESET}")

@cli.command()
def commit():
    """Force commit current changes"""
    current_dir = Path.cwd()
    stats = GitStats.get_stats(current_dir)
    
    if stats is None:
        click.echo(f"{Colors.RED}Not a git repository{Colors.RESET}")
        return
    
    if stats['total_changes'] == 0:
        click.echo(f"{Colors.YELLOW}No changes to commit{Colors.RESET}")
        return
    
    # Get threshold for commit message
    doh = DohCore()
    data = doh.config.load()
    threshold = data.get('directories', {}).get(str(current_dir), {}).get('threshold', DEFAULT_THRESHOLD)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    commit_msg = f"""Manual doh commit: Snapshot at {timestamp}

Changes detected:
- Lines added: {stats['added']}
- Lines deleted: {stats['deleted']}
- Total changes: {stats['total_changes']}
- Files modified: {stats['files_changed']}
- Untracked files: {stats['untracked']}

Manually triggered (threshold: {threshold} lines)"""
    
    click.echo(f"{Colors.BLUE}Committing changes...{Colors.RESET}")
    
    try:
        subprocess.run(['git', '-C', str(current_dir), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(current_dir), 'commit', '-m', commit_msg], check=True)
        click.echo(f"{Colors.GREEN}✓ Changes committed successfully{Colors.RESET}")
    except subprocess.CalledProcessError:
        click.echo(f"{Colors.RED}✗ Failed to commit changes{Colors.RESET}")

@cli.command()
def list():
    """List all monitored directories"""
    doh = DohCore()
    data = doh.config.load()
    directories = data.get('directories', {})
    
    click.echo(f"{Colors.BLUE}Monitored directories:{Colors.RESET}")
    
    if not directories:
        click.echo("No directories being monitored")
        return
    
    for dir_path, config in directories.items():
        path = Path(dir_path)
        name = config.get('name', '')
        threshold = config.get('threshold', DEFAULT_THRESHOLD)
        
        if path.exists():
            if name:
                click.echo(f"  {Colors.GREEN}✓{Colors.RESET} {name}: {dir_path} (threshold: {threshold})")
            else:
                click.echo(f"  {Colors.GREEN}✓{Colors.RESET} {dir_path} (threshold: {threshold})")
        else:
            if name:
                click.echo(f"  {Colors.RED}✗{Colors.RESET} {name}: {dir_path} (threshold: {threshold}) - Directory not found")
            else:
                click.echo(f"  {Colors.RED}✗{Colors.RESET} {dir_path} (threshold: {threshold}) - Directory not found")


if __name__ == "__main__":
    main()
