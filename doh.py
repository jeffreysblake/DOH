#!/usr/bin/env python3
"""
DOH - Directory Oh-no, Handle this!
A smart auto-commit monitoring system for git repositories.

This is a complete rewrite in Python for better performance, reliability,
and maintainability compared to the original bash implementation.
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Constants
DEFAULT_THRESHOLD = 50
DOH_CONFIG_DIR = Path.home() / ".doh"
DOH_CONFIG_FILE = DOH_CONFIG_DIR / "config.json"

class Colors:
    """Color constants for terminal output"""
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    BOLD = Style.BRIGHT
    RESET = Style.RESET_ALL

class DohConfig:
    """Handles all configuration management"""
    
    def __init__(self):
        self.config_file = DOH_CONFIG_FILE
        self.config_dir = DOH_CONFIG_DIR
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        self.config_dir.mkdir(exist_ok=True)
        (self.config_dir / "logs").mkdir(exist_ok=True)
    
    def _get_default_config(self) -> Dict:
        """Get default configuration structure"""
        return {
            "version": "1.0",
            "directories": {},
            "exclusions": {},
            "global_settings": {
                "log_retention_days": 30,
                "default_threshold": DEFAULT_THRESHOLD,
                "check_interval_minutes": 10,
                "git_profile": ""
            }
        }
    
    def load(self) -> Dict:
        """Load configuration, creating default if needed"""
        if not self.config_file.exists():
            return self._get_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            
            # Ensure all required sections exist
            default = self._get_default_config()
            for section in ["directories", "exclusions", "global_settings"]:
                if section not in data:
                    data[section] = default[section]
            
            # Merge global_settings with defaults
            for key, value in default["global_settings"].items():
                if key not in data["global_settings"]:
                    data["global_settings"][key] = value
            
            return data
        except Exception as e:
            click.echo(f"{Colors.YELLOW}WARNING: Could not read config ({e}), using defaults{Colors.RESET}")
            return self._get_default_config()
    
    def save(self, data: Dict) -> bool:
        """Save configuration to file"""
        try:
            # Backup existing config
            self._backup_config()
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            click.echo(f"{Colors.RED}ERROR: Could not save config: {e}{Colors.RESET}")
            return False
    
    def _backup_config(self):
        """Create backup of current config (keep last 2)"""
        if self.config_file.exists():
            backup1 = self.config_file.with_suffix('.json.backup.1')
            backup2 = self.config_file.with_suffix('.json.backup.2')
            
            # Rotate backups
            if backup1.exists():
                backup1.replace(backup2)
            self.config_file.replace(backup1)

class GitStats:
    """Handles git repository statistics"""
    
    @staticmethod
    def get_stats(directory: Path) -> Optional[Dict]:
        """Get git statistics for a directory"""
        if not GitStats.is_git_repo(directory):
            return None
        
        try:
            # Check if there are any changes
            result = subprocess.run(
                ['git', '-C', str(directory), 'diff', '--quiet', 'HEAD'],
                capture_output=True, check=False
            )
            
            if result.returncode == 0:
                # No changes
                return {
                    'total_changes': 0,
                    'added': 0,
                    'deleted': 0,
                    'files_changed': 0,
                    'untracked': GitStats._count_untracked(directory)
                }
            
            # Get detailed stats
            result = subprocess.run(
                ['git', '-C', str(directory), 'diff', '--numstat', 'HEAD'],
                capture_output=True, text=True, check=True
            )
            
            added = deleted = files_changed = 0
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        try:
                            if parts[0] != '-':
                                added += int(parts[0])
                            if parts[1] != '-':
                                deleted += int(parts[1])
                            files_changed += 1
                        except ValueError:
                            continue
            
            return {
                'total_changes': added + deleted,
                'added': added,
                'deleted': deleted,
                'files_changed': files_changed,
                'untracked': GitStats._count_untracked(directory)
            }
            
        except subprocess.CalledProcessError:
            return None
    
    @staticmethod
    def is_git_repo(directory: Path) -> bool:
        """Check if directory is a git repository"""
        try:
            subprocess.run(
                ['git', '-C', str(directory), 'rev-parse', '--git-dir'],
                capture_output=True, check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def _count_untracked(directory: Path) -> int:
        """Count untracked files"""
        try:
            result = subprocess.run(
                ['git', '-C', str(directory), 'ls-files', '--others', '--exclude-standard'],
                capture_output=True, text=True, check=True
            )
            return len([line for line in result.stdout.strip().split('\n') if line])
        except subprocess.CalledProcessError:
            return 0

class DohCore:
    """Core DOH functionality"""
    
    def __init__(self):
        self.config = DohConfig()
    
    def is_excluded(self, directory: Path) -> bool:
        """Check if directory or any parent is excluded"""
        data = self.config.load()
        exclusions = data.get('exclusions', {})
        
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
        exclusions = data.get('exclusions', {})
        
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
        return str(directory) in data.get('directories', {})
    
    def add_directory(self, directory: Path, threshold: int, name: str) -> bool:
        """Add directory to monitoring"""
        if self.is_excluded(directory):
            excluded_parent = self.find_excluded_parent(directory)
            if excluded_parent == directory:
                click.echo(f"{Colors.RED}Directory is excluded from monitoring{Colors.RESET}")
                click.echo("Use 'doh ex rm' to remove from exclusions first")
            else:
                click.echo(f"{Colors.RED}Cannot monitor directory - parent directory is excluded{Colors.RESET}")
                click.echo(f"Parent directory '{excluded_parent}' is in the exclusions list")
                click.echo("Options:")
                click.echo(f"  1. Move current directory outside of '{excluded_parent}'")
                click.echo(f"  2. Remove '{excluded_parent}' from exclusions: doh ex rm '{excluded_parent}'")
            return False
        
        if not GitStats.is_git_repo(directory):
            click.echo(f"{Colors.RED}Directory is not a git repository{Colors.RESET}")
            click.echo("Use 'git init' to initialize a git repository first")
            return False
        
        data = self.config.load()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if not name:
            name = directory.name
        
        data['directories'][str(directory)] = {
            'name': name,
            'threshold': threshold,
            'added': timestamp,
            'last_checked': timestamp
        }
        
        return self.config.save(data)
    
    def remove_directory(self, directory: Path) -> bool:
        """Remove directory from monitoring"""
        data = self.config.load()
        dir_str = str(directory)
        
        removed = False
        if dir_str in data.get('directories', {}):
            del data['directories'][dir_str]
            removed = True
        
        if dir_str in data.get('exclusions', {}):
            del data['exclusions'][dir_str]
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
        
        data['exclusions'][str(directory)] = {
            'excluded': timestamp
        }
        
        return self.config.save(data)
    
    def remove_exclusion(self, directory: Path) -> bool:
        """Remove directory from exclusions"""
        data = self.config.load()
        dir_str = str(directory)
        
        if dir_str in data.get('exclusions', {}):
            del data['exclusions'][dir_str]
            return self.config.save(data)
        return True

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

# Exclusion subcommands
@cli.group()
def ex():
    """Exclusion management commands"""
    pass

@ex.command()
def list():
    """List excluded directories"""
    doh = DohCore()
    data = doh.config.load()
    exclusions = data.get('exclusions', {})
    
    click.echo(f"{Colors.BLUE}Excluded directories:{Colors.RESET}")
    
    if not exclusions:
        click.echo("No directories are excluded")
        return
    
    for dir_path, config in exclusions.items():
        path = Path(dir_path)
        excluded_date = config.get('excluded', 'Unknown')
        
        if path.exists():
            click.echo(f"  {Colors.YELLOW}✗{Colors.RESET} {dir_path} (excluded: {excluded_date})")
        else:
            click.echo(f"  {Colors.RED}✗{Colors.RESET} {dir_path} (excluded: {excluded_date}) - Directory not found")

@ex.command()
@click.argument('path', required=False)
def add(path):
    """Add directory to exclusions (default: current directory)"""
    target_dir = Path(path) if path else Path.cwd()
    doh = DohCore()
    
    if doh.add_exclusion(target_dir):
        click.echo(f"{Colors.GREEN}✓ Added {target_dir} to exclusions{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}Failed to add exclusion{Colors.RESET}")

@ex.command()
@click.argument('path', required=False)
def rm(path):
    """Remove directory from exclusions (default: current directory)"""
    target_dir = Path(path) if path else Path.cwd()
    doh = DohCore()
    
    if doh.remove_exclusion(target_dir):
        click.echo(f"{Colors.GREEN}✓ Removed {target_dir} from exclusions{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}Failed to remove exclusion{Colors.RESET}")

if __name__ == '__main__':
    cli()
