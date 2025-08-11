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
        click.echo(f"  {Colors.BLUE}{name}{Colors.RESET}: {status}")
    elif not directory.exists():
        status = f"{Colors.RED}DIRECTORY NOT FOUND{Colors.RESET}"
        click.echo(f"  {Colors.BLUE}{name}{Colors.RESET}: {status}")
    else:
        total_changes = stats['total_changes']
        untracked = stats['untracked']
        untracked_lines = stats.get('untracked_lines', stats['untracked'])
        total_all = total_changes + untracked_lines
        
        if total_all == 0:
            status = f"{Colors.GREEN}CLEAN{Colors.RESET}"
        elif total_all >= threshold:
            status = f"{Colors.RED}OVER THRESHOLD ({total_all}/{threshold}){Colors.RESET}"
        else:
            status = f"{Colors.YELLOW}HAS CHANGES ({total_all}/{threshold}){Colors.RESET}"
        
        click.echo(f"  {Colors.BLUE}{name}{Colors.RESET}: {status}")
        click.echo(f"    Changes: +{stats['added']} -{stats['deleted']} (files: {stats['files_changed']})")
        if stats['untracked'] > 0:
            click.echo(f"    Untracked: {stats['untracked']} files")
        
        # Show enhanced file details if there are changes
        file_stats = stats.get('file_stats', [])
        if file_stats:
            file_summary = GitStats.format_file_changes(file_stats, max_files=5)
            click.echo(f"    Files: {file_summary}")
            
            # Show warning if approaching threshold
            if total_all >= threshold * 0.8 and total_all < threshold:
                click.echo(f"    {Colors.YELLOW}⚠ Approaching threshold - {threshold - total_all} lines remaining{Colors.RESET}")


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
        name = directory.name
        threshold = 0  # Force commit regardless of threshold
        
        # Get git profile from config if set
        data = doh.config.load()
        git_profile = data.get('global_settings', {}).get('git_profile', '')
        
        git_cmd = ['git', '-C', str(directory)]
        
        # Add git profile config if specified
        if git_profile:
            profile_path = Path(git_profile).expanduser()
            if profile_path.exists():
                git_cmd.extend(['-c', f'include.path={profile_path}'])
        
        # Add all changes
        subprocess.run(git_cmd + ['add', '.'], check=True, capture_output=True)
        
        # Check if there's anything to commit
        result = subprocess.run(
            git_cmd + ['diff', '--staged', '--quiet'],
            capture_output=True, check=False
        )
        
        if result.returncode == 0:
            # Nothing staged to commit
            return False
        
        # Create enhanced commit message for force commit
        commit_msg = f"Manual commit: {GitStats.format_file_changes(stats.get('file_stats', []), max_files=5)}"
        
        subprocess.run(
            git_cmd + ['commit', '-m', commit_msg],
            check=True, capture_output=True
        )
        return True
        
    except subprocess.CalledProcessError:
        return False


@click.group(invoke_without_command=True)
@click.version_option(version="2.0.0", prog_name="doh")
@click.option('--force', '-f', is_flag=True, help='Force commit any changes before adding directory')
@click.option('--threshold', '-t', default=DEFAULT_THRESHOLD, type=int,
              help=f'Change threshold (default: {DEFAULT_THRESHOLD})')
@click.option('--name', '-n', help='Name for this directory (defaults to directory name)')
@click.pass_context
def main(ctx, force, threshold, name):
    """DOH - Directory Oh-no, Handle this!
    
    A smart auto-commit monitoring system for git repositories.
    
    When run without a command, adds current directory to monitoring (or shows status if already monitored).
    """
    # First-run setup
    doh.config.setup_first_run()
    
    # Store context data for subcommands
    ctx.ensure_object(dict)
    ctx.obj['force'] = force
    
    # If no subcommand was invoked, act like 'add' for current directory
    if ctx.invoked_subcommand is None:
        directory = Path.cwd().resolve()
        
        # Smart behavior: if already monitored, check if auto-commit is needed
        if doh.is_monitored(directory):
            click.echo(f"{Colors.YELLOW}Directory already monitored. Checking status:{Colors.RESET}")
            click.echo()
            
            # Get current stats and threshold for this directory
            data = doh.config.load()
            directories = data.get('directories', {})
            dir_info = directories.get(str(directory), {})
            dir_threshold = dir_info.get('threshold', DEFAULT_THRESHOLD)
            
            stats = GitStats.get_stats(directory)
            if stats:
                total_changes = stats['total_changes'] + stats.get('untracked_lines', stats['untracked'])
                
                # Auto-commit if over threshold (even without -f flag)
                if total_changes >= dir_threshold:
                    click.echo(f"{Colors.RED}Threshold exceeded ({total_changes}/{dir_threshold}). Auto-committing...{Colors.RESET}")
                    if force_commit_directory(directory):
                        click.echo(f"{Colors.GREEN}✓ Changes committed successfully{Colors.RESET}")
                    else:
                        click.echo(f"{Colors.YELLOW}⚠ Auto-commit failed or no changes to commit{Colors.RESET}")
                    click.echo()
            
            _show_single_directory_status(directory)
            return
        
        # Handle force commit first if requested (for new directories)
        if force:
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
            _show_single_directory_status(directory)
        else:
            click.echo(f"{Colors.RED}✗ Failed to add directory to monitoring{Colors.RESET}")


@main.command()
@click.option('--threshold', '-t', default=DEFAULT_THRESHOLD, type=int,
              help=f'Change threshold (default: {DEFAULT_THRESHOLD})')
@click.option('--name', '-n', help='Name for this directory (defaults to directory name)')
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), 
                required=False)
@click.pass_context
def add(ctx, directory, threshold, name):
    """Add a directory to monitoring"""
    if directory is None:
        directory = Path.cwd()
    
    directory = directory.resolve()
    
    # Get force flag from context
    force_commit = ctx.obj.get('force', False)
    
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
            untracked_lines = stats.get('untracked_lines', stats['untracked'])
            
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
    click.echo(f"Git profile: {settings.get('git_profile', 'None')}")
    click.echo(f"Auto git init: {settings.get('auto_init_git', True)}")
    click.echo(f"Use temp branches: {settings.get('use_temp_branches', True)}")
    click.echo(f"Temp branch prefix: {settings.get('temp_branch_prefix', 'doh-auto-commits')}")
    click.echo(f"Temp branch cleanup days: {settings.get('max_temp_branch_age_days', 7)}")
    
    if doh.config.config_file.exists():
        size = doh.config.config_file.stat().st_size
        click.echo(f"Config file size: {size} bytes")


@main.command()
@click.option('--git-profile', help='Path to git config file to use for commits (e.g., ~/.gitconfig-personal)')
@click.option('--threshold', type=int, help='Set default threshold for new directories')
@click.option('--auto-init-git/--no-auto-init-git', default=None, help='Enable/disable automatic git init for non-git directories')
@click.option('--temp-branches/--no-temp-branches', default=None, help='Enable/disable temporary branch strategy')
@click.option('--temp-branch-prefix', help='Set prefix for temporary branch names (default: doh-auto-commits)')
@click.option('--temp-branch-cleanup-days', type=int, help='Days after which to clean up old temp branches (default: 7)')
def configure(git_profile, threshold, auto_init_git, temp_branches, temp_branch_prefix, temp_branch_cleanup_days):
    """Configure global DOH settings"""
    data = doh.config.load()
    settings = data.setdefault('global_settings', {})
    
    changed = False
    
    if git_profile is not None:
        settings['git_profile'] = git_profile
        changed = True
        click.echo(f"{Colors.GREEN}✓ Git profile set to: {git_profile}{Colors.RESET}")
        
        # Verify the profile exists
        profile_path = Path(git_profile).expanduser()
        if not profile_path.exists():
            click.echo(f"{Colors.YELLOW}⚠ Warning: Git profile file does not exist: {profile_path}{Colors.RESET}")
    
    if threshold is not None:
        settings['default_threshold'] = threshold
        changed = True
        click.echo(f"{Colors.GREEN}✓ Default threshold set to: {threshold}{Colors.RESET}")
    
    if auto_init_git is not None:
        settings['auto_init_git'] = auto_init_git
        changed = True
        status = "enabled" if auto_init_git else "disabled"
        click.echo(f"{Colors.GREEN}✓ Auto git init {status}{Colors.RESET}")
    
    if temp_branches is not None:
        settings['use_temp_branches'] = temp_branches
        changed = True
        status = "enabled" if temp_branches else "disabled"
        click.echo(f"{Colors.GREEN}✓ Temporary branch strategy {status}{Colors.RESET}")
    
    if temp_branch_prefix is not None:
        settings['temp_branch_prefix'] = temp_branch_prefix
        changed = True
        click.echo(f"{Colors.GREEN}✓ Temporary branch prefix set to: {temp_branch_prefix}{Colors.RESET}")
    
    if temp_branch_cleanup_days is not None:
        settings['max_temp_branch_age_days'] = temp_branch_cleanup_days
        changed = True
        click.echo(f"{Colors.GREEN}✓ Temporary branch cleanup age set to: {temp_branch_cleanup_days} days{Colors.RESET}")
    
    if not changed:
        click.echo(f"{Colors.YELLOW}No changes specified. Use --help to see available options.{Colors.RESET}")
        return
    
    if doh.config.save(data):
        click.echo(f"{Colors.GREEN}Configuration saved successfully{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}Failed to save configuration{Colors.RESET}")


@main.command()
@click.option('--once', is_flag=True, help='Run once and exit (perfect for cron jobs)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging output')
@click.option('--interval', '-i', default=600, type=int, help='Check interval in seconds (default: 600 = 10 minutes)')
def daemon(once, verbose, interval):
    """Monitor all directories and auto-commit when thresholds are exceeded
    
    This daemon checks all monitored directories for changes and automatically
    commits when the change threshold is exceeded. Perfect for running as a 
    cron job with --once flag.
    
    Examples:
        doh daemon --once     # Run once (good for cron)
        doh daemon -v         # Run continuously with verbose output
        doh daemon --interval 300  # Check every 5 minutes
    """
    import time
    import logging
    import os
    from datetime import datetime
    
    # Set up logging
    log_dir = doh.config.config_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"daemon_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler() if verbose else logging.NullHandler()
        ]
    )
    
    logger = logging.getLogger('doh-daemon')
    
    def should_log_threshold_status(directory: Path, total_changes: int, threshold: int) -> bool:
        """Check if we should log threshold status to prevent spam"""
        log_dir = Path.home() / '.doh' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Check logs from last 10 days
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=10)
        
        dir_str = str(directory)
        status = "OVER" if total_changes >= threshold else "BELOW"
        
        # Look through recent log files
        for log_file in log_dir.glob("daemon_*.log"):
            try:
                # Extract date from filename (daemon_YYYY-MM-DD.log)
                date_str = log_file.stem.split('_', 1)[1]
                log_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                if log_date < cutoff_date:
                    continue
                    
                # Check if this directory + status was already logged
                with open(log_file, 'r') as f:
                    for line in f:
                        if dir_str in line and f"STATUS: {status}" in line:
                            return False  # Already logged recently
                            
            except (ValueError, OSError):
                continue  # Skip malformed log files
        
        return True  # Not found in recent logs, should log
    
    def auto_commit_directory(directory: Path, stats: dict, threshold: int, name: str) -> bool:
        """Perform auto-commit for a directory"""
        try:
            # Get configuration settings
            data = doh.config.load()
            global_settings = data.get('global_settings', {})
            use_temp_branches = global_settings.get('use_temp_branches', True)
            temp_branch_prefix = global_settings.get('temp_branch_prefix', 'doh-auto-commits')
            git_profile = global_settings.get('git_profile', '')
            
            git_cmd = ['git', '-C', str(directory)]
            
            # Add git profile config if specified
            if git_profile:
                profile_path = Path(git_profile).expanduser()
                if profile_path.exists():
                    git_cmd.extend(['-c', f'include.path={profile_path}'])
            
            # Handle temporary branch strategy
            original_branch = None
            temp_branch = None
            
            if use_temp_branches:
                try:
                    # Get current branch
                    result = subprocess.run(
                        git_cmd + ['branch', '--show-current'],
                        capture_output=True, text=True, check=True
                    )
                    original_branch = result.stdout.strip()
                    
                    # Get or create temp branch
                    temp_branch = GitStats.get_or_create_temp_branch(directory, temp_branch_prefix)
                    
                    # Switch to temp branch if not already on it
                    if original_branch != temp_branch:
                        GitStats.switch_to_temp_branch(directory, temp_branch)
                        
                except subprocess.CalledProcessError:
                    # Fallback to direct commits if temp branch fails
                    use_temp_branches = False
                    logger.warning(f"Failed to create temp branch for {name}, falling back to direct commits")
            
            # Stage all changes
            subprocess.run(
                git_cmd + ['add', '.'],
                capture_output=True, check=True
            )
            
            # Check if there's anything to commit
            result = subprocess.run(
                git_cmd + ['diff', '--staged', '--quiet'],
                capture_output=True, check=False
            )
            
            if result.returncode == 0:
                # Nothing staged to commit
                logger.info(f"No changes to commit in {name} ({directory})")
                return False
            
            # Use enhanced commit message format
            commit_msg = GitStats.create_enhanced_commit_message(name, stats, threshold)
            
            # Commit changes
            subprocess.run(
                git_cmd + ['commit', '-m', commit_msg],
                capture_output=True, check=True
            )
            
            # Create enhanced log message with file details
            file_summary = GitStats.format_file_changes(stats.get('file_stats', []), max_files=3)
            total_changes = stats['total_changes'] + stats.get('untracked_lines', stats['untracked'])
            
            branch_info = f" (temp branch: {temp_branch})" if use_temp_branches else ""
            logger.info(f"✓ Auto-commit successful in '{name}': {file_summary} ({total_changes} total changes){branch_info}")
            
            if verbose:
                if use_temp_branches:
                    click.echo(f"{Colors.GREEN}✓ Auto-committed '{name}' to temp branch '{temp_branch}': {file_summary}{Colors.RESET}")
                else:
                    click.echo(f"{Colors.GREEN}✓ Auto-committed '{name}': {file_summary}{Colors.RESET}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to commit changes in '{name}' ({directory}): {e}")
            if verbose:
                click.echo(f"{Colors.RED}✗ Failed to commit '{name}': {e}{Colors.RESET}")
            return False
    
    def cleanup_old_logs():
        """Clean up logs older than 30 days"""
        try:
            retention_days = 30
            import time
            cutoff = time.time() - (retention_days * 24 * 60 * 60)
            
            for log_file_path in log_dir.glob("daemon_*.log"):
                if log_file_path.stat().st_mtime < cutoff:
                    log_file_path.unlink()
                    logger.info(f"Cleaned up old log: {log_file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old logs: {e}")
    
    def monitor_cycle() -> tuple[int, int]:
        """Run one monitoring cycle, return (processed, committed)"""
        data = doh.config.load()
        directories = data.get('directories', {})
        
        if not directories:
            logger.warning("No directories to monitor. Run 'doh add' to add directories.")
            if verbose:
                click.echo(f"{Colors.YELLOW}No directories being monitored{Colors.RESET}")
            return 0, 0
        
        processed = 0
        committed = 0
        
        for dir_path, info in directories.items():
            directory = Path(dir_path)
            threshold = info.get('threshold', DEFAULT_THRESHOLD)
            name = info.get('name', directory.name)
            
            processed += 1
            
            if not directory.exists():
                logger.warning(f"Directory not found: {name} ({directory})")
                continue
            
            stats = GitStats.get_stats(directory)
            if stats is None:
                logger.warning(f"Not a git repository: {name} ({directory})")
                continue
            
            total_changes = stats['total_changes'] + stats.get('untracked_lines', stats['untracked'])
            
            if total_changes >= threshold:
                if should_log_threshold_status(directory, total_changes, threshold):
                    logger.info(f"'{name}': {total_changes} changes >= {threshold} threshold - STATUS: OVER - {directory}")
                if auto_commit_directory(directory, stats, threshold, name):
                    committed += 1
            else:
                # Only log if we haven't logged this status recently
                if should_log_threshold_status(directory, total_changes, threshold):
                    logger.debug(f"'{name}': {total_changes} changes < {threshold} threshold - STATUS: BELOW - {directory}")
                elif verbose:
                    # Still show in verbose output but don't log to file
                    click.echo(f"{Colors.YELLOW}'{name}': {total_changes} changes (under threshold {threshold}){Colors.RESET}")
        
        return processed, committed
    
    # Main daemon logic
    cycle_count = 0
    
    logger.info(f"Starting DOH daemon (PID: {os.getpid()})")
    logger.info(f"Run mode: {'single run' if once else 'continuous'}")
    logger.info(f"Check interval: {interval} seconds")
    logger.info(f"Verbose: {verbose}")
    
    if verbose:
        click.echo(f"{Colors.BLUE}DOH Daemon starting...{Colors.RESET}")
        click.echo(f"Mode: {'Single run' if once else 'Continuous'}")
        click.echo(f"Interval: {interval} seconds")
        click.echo()
    
    try:
        while True:
            cycle_count += 1
            
            # Clean up old logs every 10 cycles
            if cycle_count % 10 == 1:
                cleanup_old_logs()
            
            if verbose:
                click.echo(f"{Colors.BLUE}Starting monitoring cycle #{cycle_count}...{Colors.RESET}")
            
            processed, committed = monitor_cycle()
            
            if verbose or committed > 0:
                status_color = Colors.GREEN if committed > 0 else Colors.YELLOW
                click.echo(f"{status_color}Cycle #{cycle_count}: {committed}/{processed} directories auto-committed{Colors.RESET}")
            
            logger.info(f"Monitoring cycle #{cycle_count} complete: {committed}/{processed} directories auto-committed")
            
            # Exit if running once (cron mode)
            if once:
                logger.info("Single run complete")
                if verbose:
                    click.echo(f"{Colors.GREEN}Single run complete{Colors.RESET}")
                break
            
            # Wait for next cycle
            if verbose:
                click.echo(f"Waiting {interval} seconds until next check...")
                click.echo()
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
        if verbose:
            click.echo(f"\n{Colors.YELLOW}Daemon stopped by user{Colors.RESET}")
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        if verbose:
            click.echo(f"{Colors.RED}Daemon error: {e}{Colors.RESET}")
        raise


@main.command()
@click.argument('commit_message')
@click.option('--target', '-t', default='master', help='Target branch to squash into (default: master)')
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), 
                required=False)
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
        click.echo(f"{Colors.YELLOW}No temporary branches found to squash{Colors.RESET}")
        return
    
    # Find current branch or most recent temp branch
    try:
        current_branch = subprocess.run(
            ['git', '-C', str(directory), 'branch', '--show-current'],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        temp_branch = None
        if current_branch.startswith('doh-auto-commits'):
            temp_branch = current_branch
        elif temp_branches:
            # Use most recent temp branch
            temp_branch = sorted(temp_branches, key=lambda b: b['name'])[-1]['name']
        
        if not temp_branch:
            click.echo(f"{Colors.YELLOW}No temporary branch to squash{Colors.RESET}")
            return
        
        if GitStats.squash_temp_commits(directory, target, commit_message, temp_branch):
            click.echo(f"{Colors.GREEN}✓ Successfully squashed temp commits into '{target}'{Colors.RESET}")
            click.echo(f"  Commit message: {commit_message}")
        else:
            click.echo(f"{Colors.RED}✗ Failed to squash temporary branch{Colors.RESET}")
            
    except subprocess.CalledProcessError as e:
        click.echo(f"{Colors.RED}Git error: {e}{Colors.RESET}")


@main.command()
@click.option('--cleanup-days', '-d', default=7, type=int, help='Remove temp branches older than N days')
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), 
                required=False)
def cleanup(cleanup_days, directory):
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
    
    click.echo(f"{Colors.BLUE}Found {len(branches)} temporary branches{Colors.RESET}")
    for branch in branches:
        click.echo(f"  {Colors.GREEN}{branch['name']}{Colors.RESET} ({branch['commit_count']} commits, {branch['last_commit']})")
    
    # TODO: Implement age-based cleanup
    click.echo(f"Cleanup logic for branches older than {cleanup_days} days - Coming soon!")


# Hide the daemon command but keep it functional for systemd


if __name__ == "__main__":
    main()
