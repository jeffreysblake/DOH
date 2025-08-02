"""
Core DOH functionality
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import DohConfig, DEFAULT_THRESHOLD
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
                try:
                    click.echo(f"{Colors.RED}Directory is excluded from monitoring{Colors.RESET}")
                    click.echo("Use 'doh ex rm' to remove from exclusions first")
                except:
                    print("Directory is excluded from monitoring")
                    print("Use 'doh ex rm' to remove from exclusions first")
            else:
                try:
                    click.echo(f"{Colors.RED}Cannot monitor directory - parent directory is excluded{Colors.RESET}")
                    click.echo(f"Parent directory '{excluded_parent}' is in the exclusions list")
                    click.echo("Options:")
                    click.echo(f"  1. Move current directory outside of '{excluded_parent}'")
                    click.echo(f"  2. Remove '{excluded_parent}' from exclusions: doh ex rm '{excluded_parent}'")
                except:
                    print("Cannot monitor directory - parent directory is excluded")
                    print(f"Parent directory '{excluded_parent}' is in the exclusions list")
            return False
        
        if not GitStats.is_git_repo(directory):
            try:
                click.echo(f"{Colors.RED}Directory is not a git repository{Colors.RESET}")
                click.echo("Use 'git init' to initialize a git repository first")
            except:
                print("Directory is not a git repository")
                print("Use 'git init' to initialize a git repository first")
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
