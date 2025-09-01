"""
Configuration management for DOH
"""

import json
import subprocess
import shutil
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
DEFAULT_THRESHOLD = 50
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
                "git_init_command": "git init",
                "use_temp_branches": True,
                "temp_branch_prefix": "doh-auto-commits",
                "auto_cleanup_temp_branches": True,
                "max_temp_branch_age_days": 365,
            },
            "directories": {},
            "exclusions": [],
        }

    def load(self) -> Dict:
        """Load configuration, creating default if needed"""
        if not self.config_file.exists():
            return self._get_default_config()

        try:
            with open(self.config_file, "r") as f:
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
                click.echo(
                    f"{Colors.YELLOW}WARNING: Could not read config ({e}), using defaults{Colors.RESET}"
                )
            except Exception:
                print(f"WARNING: Could not read config ({e}), using defaults")
            return self._get_default_config()

    def save(self, data: Dict) -> bool:
        """Save configuration to file"""
        try:
            # Backup existing config
            self._backup_config()

            with open(self.config_file, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            try:
                click.echo(
                    f"{Colors.RED}ERROR: Could not save config: {e}{Colors.RESET}"
                )
            except Exception:
                print(f"ERROR: Could not save config: {e}")
            return False

    def _backup_config(self):
        """Create backup of current config (keep last 2)"""
        if self.config_file.exists():
            backup1 = self.config_file.with_suffix(".json.backup.1")
            backup2 = self.config_file.with_suffix(".json.backup.2")

            # Rotate backups
            if backup1.exists():
                backup1.replace(backup2)
            self.config_file.replace(backup1)

    def setup_first_run(self):
        """Setup DOH for first run - create config and systemd daemon"""
        try:
            # Ensure config directory and basic config
            self._ensure_config_dir()
            if not self.config_file.exists():
                self.save(self._get_default_config())

            # Setup systemd daemon if available
            self._setup_systemd_daemon()

            return True
        except Exception as e:
            try:
                click.echo(
                    f"{Colors.YELLOW}Warning: First-run setup had issues: {e}{Colors.RESET}"
                )
            except Exception:
                print(f"Warning: First-run setup had issues: {e}")
            return False

    def _setup_systemd_daemon(self):
        """Setup user-level systemd daemon for DOH monitoring"""
        # Check if systemctl is available
        if not shutil.which("systemctl"):
            return False

        try:
            # Create systemd user directory
            systemd_dir = Path.home() / ".config" / "systemd" / "user"
            systemd_dir.mkdir(parents=True, exist_ok=True)

            # Find doh executable path
            doh_path = shutil.which("doh")
            if not doh_path:
                # Try ~/.local/bin/doh
                local_doh = Path.home() / ".local" / "bin" / "doh"
                if local_doh.exists():
                    doh_path = str(local_doh)
                else:
                    return False

            # Create service file
            service_content = """[Unit]
Description=DOH Git Repository Monitor
After=graphical-session.target

[Service]
Type=oneshot
ExecStart={doh_path} daemon --once
Environment=HOME={Path.home()}
WorkingDirectory={Path.home()}

[Install]
WantedBy=default.target
"""

            # Create timer file
            timer_content = """[Unit]
Description=Run DOH Git Repository Monitor every 10 minutes
Requires=doh-monitor.service

[Timer]
OnCalendar=*:0/10
Persistent=true

[Install]
WantedBy=timers.target
"""

            service_file = systemd_dir / "doh-monitor.service"
            timer_file = systemd_dir / "doh-monitor.timer"

            # Write files only if they don't exist
            if not service_file.exists():
                service_file.write_text(service_content)
            if not timer_file.exists():
                timer_file.write_text(timer_content)

            # Reload systemd and enable/start timer
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=False,
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "--user", "enable", "doh-monitor.timer"],
                check=False,
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "--user", "start", "doh-monitor.timer"],
                check=False,
                capture_output=True,
            )

            return True

        except Exception:
            return False
