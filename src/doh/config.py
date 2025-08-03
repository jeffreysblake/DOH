"""
Configuration management for DOH
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from .colors import Colors

try:
    import click
except ImportError:
    # Fallback for environments without click
    class MockClick:
        def echo(self, message):
            print(message)
    click = MockClick()

# Constants
DEFAULT_THRESHOLD = 30
DOH_CONFIG_DIR = Path.home() / ".doh"
DOH_CONFIG_FILE = DOH_CONFIG_DIR / "config.json"

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
            "global_settings": {
                "default_threshold": DEFAULT_THRESHOLD,
                "git_profile": "",
                "auto_init_git": True,
                "git_init_command": "git init"
            },
            "directories": {},
            "exclusions": []
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
            try:
                click.echo(f"{Colors.YELLOW}WARNING: Could not read config ({e}), using defaults{Colors.RESET}")
            except:
                print(f"WARNING: Could not read config ({e}), using defaults")
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
            try:
                click.echo(f"{Colors.RED}ERROR: Could not save config: {e}{Colors.RESET}")
            except:
                print(f"ERROR: Could not save config: {e}")
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
