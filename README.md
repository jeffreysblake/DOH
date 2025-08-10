# DOH - Directory Oh-no, Handle this! 🎯

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A smart auto-commit monitoring system for git repositories. DOH intelligently tracks changes in your directories and automatically commits when thresholds are exceeded, with support for both systemd and cron-based monitoring.

## ✨ Features

- 🎯 **Smart monitoring**: Automatically tracks git repository changes
- 🤖 **Auto-commit daemon**: Background monitoring with systemd or cron
- 📊 **Configurable thresholds**: Set custom line-change limits per directory  
- 🚫 **Exclusion system**: Exclude directories and their children from monitoring
- 📈 **Detailed statistics**: View comprehensive git stats with progress indicators
- 🎨 **Beautiful CLI**: Colorful, intuitive command-line interface
- ⚡ **Fast & reliable**: Pure Python implementation with proper error handling
- 💾 **Configuration backup**: Automatic backup system prevents data loss
- 🐳 **Docker-like naming**: Friendly names for monitored directories
- � **Git profile support**: Use custom git configurations for commits
- 🔄 **Force commit**: Instantly commit changes with `-f` flag

## 🚀 Quick Start

### Installation Options

DOH can be installed in multiple ways to suit different needs:

#### 1. Quick Install from PyPI (Recommended for end users)
```bash
# One-line install (when published to PyPI)
curl -sSL https://raw.githubusercontent.com/youruser/doh/main/pip-install | bash

# Or manually:
pip3 install --user doh-monitor
```

#### 2. Install from Source (Recommended for development)
```bash
# Clone and install for current user only (no sudo required)
git clone <repository-url>
cd doh

# Validate package before installation (optional)
./validate

# Install from source (editable mode)
./install --source

# The script will:
# - Install doh to ~/.local/bin (user-level, editable)
# - Set up systemd user daemon (runs every 10 minutes)
# - Provide instructions for adding ~/.local/bin to PATH
```

#### 3. Development Setup
```bash
# Clone and set up for development
git clone <repository-url>
cd doh
./scripts/dev-setup
source venv/bin/activate
```

#### 4. Alternative Installation Methods
```bash
# Force pip installation (even from source directory)
./install --pip

# Direct pip install (if published)
pip3 install --user doh-monitor
```

#### Uninstallation
```bash
# Using uninstall script (handles both source and pip installations)
./uninstall

# Manual removal
pip3 uninstall doh-monitor
systemctl --user stop doh-monitor.timer
systemctl --user disable doh-monitor.timer
```

#### Manual PATH Setup (if needed)
```bash
# If ~/.local/bin is not in your PATH, add this to your shell profile:
# For bash users:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# For zsh users:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Daemon Setup (Automatic)

The installation script automatically sets up a user-level systemd daemon that runs every 10 minutes. No additional setup is required!

### Basic Usage

```bash
# Add current directory to monitoring (default threshold: 50 lines)
doh

# Add current directory with custom options
doh --threshold 25 --name "MyProject"

# Add specific directory to monitoring  
doh add --threshold 25 --name "MyProject" /path/to/project

# Force commit any changes before adding
doh -f --threshold 25 --name "MyProject"

# Show status of all monitored directories  
doh status

# List all monitored directories
doh list

# Show configuration
doh config
```

### Daemon Management

```bash
# Check daemon status
systemctl --user status doh-monitor.timer

# View daemon logs
journalctl --user -u doh-monitor -f

# Stop the daemon
systemctl --user stop doh-monitor.timer

# Start the daemon
systemctl --user start doh-monitor.timer

# Run daemon once manually (perfect for cron)
doh daemon --once

# Run daemon continuously with verbose output
doh daemon --verbose

# Check local daemon logs
cat ~/.doh/logs/daemon_$(date +%Y-%m-%d).log
```

### Exclusion Management

```bash
# Exclude current directory from monitoring
doh ex add

# Exclude specific directory  
doh ex add /path/to/directory

# List all exclusions
doh ex list

# Remove exclusion (alias: ex rm)
doh ex remove /path/to/directory
```

### Configuration

```bash
# Set git profile for commits (includes gpgsigning=false if in your profile)
doh configure --git-profile ~/.gitconfig-personal

# Set default threshold
doh configure --threshold 75

# Enable/disable automatic git init for non-git directories
doh configure --auto-init-git          # Enable (default)
doh configure --no-auto-init-git       # Disable

# Show current configuration
doh config
```

## 📖 Command Reference

### Main Commands

| Command | Description | Examples |
|---------|-------------|----------|
| `doh` | Add current directory to monitoring | `doh --threshold 30 --name "API"`<br>`doh -f` (force commit first) |
| `doh add` | Add directory to monitoring | `doh add --threshold 30 --name "API"`<br>`doh add /path/to/project` |
| `doh status` | Show monitoring status | `doh status` |
| `doh list` | List monitored directories | `doh list` |
| `doh remove` | Remove from monitoring | `doh remove` |
| `doh daemon` | Run monitoring daemon | `doh daemon --once`<br>`doh daemon --verbose` |
| `doh commit` | Force commit directory | `doh commit` |
| `doh config` | Show configuration | `doh config` |
| `doh configure` | Update configuration | `doh configure --git-profile ~/.gitconfig-work` |

### Exclusion Commands

| Command | Description | Examples |
|---------|-------------|----------|
| `doh ex add` | Add exclusion | `doh ex add`<br>`doh ex add /path/to/dir` |
| `doh ex list` | List exclusions | `doh ex list` |
| `doh ex remove` | Remove exclusion | `doh ex remove /path/to/dir` |

### Global Options

| Option | Description | Example |
|--------|-------------|---------|
| `-f, --force` | Force commit before command | `doh -f` |
| `-t, --threshold` | Set threshold for current directory | `doh -t 30` |
| `-n, --name` | Set name for current directory | `doh -n "MyProject"` |
| `--verbose` | Verbose output | `doh --verbose daemon` |
| `--help` | Show help | `doh --help` |

## 🏗️ Architecture

DOH follows a modern Python package structure:

```
doh/
├── src/doh/              # Main package source
│   ├── __init__.py       # Package initialization
│   ├── cli.py           # Click-based CLI interface
│   ├── core.py          # Core monitoring logic
│   ├── config.py        # Configuration management
│   ├── git_stats.py     # Git statistics engine
│   └── colors.py        # Terminal colors and formatting
├── tests/               # Test suite
│   ├── __init__.py      # Test package
│   └── test_doh.py      # Main test file
├── scripts/             # Setup and daemon scripts
│   ├── dev-setup        # Development environment setup
│   ├── systemd-setup    # Systemd daemon setup (DEPRECATED - use ./install)
│   ├── cron-setup       # Cron daemon setup
│   ├── doh-daemon@.service  # Systemd service template
│   └── doh-daemon@.timer    # Systemd timer (10 minute intervals)
├── install              # Smart installation script (source/pip auto-detection)
├── uninstall            # Uninstallation script
├── validate             # Package validation script
├── pip-install          # Quick PyPI installation script
├── build-release        # PyPI package builder and publisher
├── pyproject.toml       # Modern Python packaging
└── README.md           # This file
```

## 🔧 Configuration

DOH stores configuration in `~/.doh/config.json`:

```json
{
  "global_settings": {
    "default_threshold": 50,
    "git_profile": "~/.gitconfig-personal"
  },
  "monitored_directories": {
    "/path/to/project": {
      "name": "MyProject",
      "threshold": 25,
      "last_commit": "2024-01-15T10:30:00"
    }
  },
  "exclusions": [
    "/path/to/excluded/dir"
  ]
}
```

### Git Profile Integration

Configure a custom git profile for auto-commits:

```bash
# Set global git profile for all DOH commits
doh configure --git-profile ~/.gitconfig-personal

# Example ~/.gitconfig-personal
[user]
    name = "Your Name"
    email = "your.email@example.com"
[commit]
    gpgsign = false
[core]
    editor = "code --wait"
```

The git profile is automatically applied when DOH creates commits. This is perfect for:
- Using different email/name for personal vs work commits
- Disabling GPG signing for auto-commits (`gpgsign = false`)
- Setting specific git configurations for DOH operations

### Automatic Git Initialization

DOH can automatically initialize git repositories:

```bash
# Enable automatic git init (default)
doh configure --auto-init-git

# Disable if you prefer manual initialization
doh configure --no-auto-init-git
```

When enabled, DOH will run `git init` automatically when you try to monitor a non-git directory.

## 🤖 Daemon Setup

### User-level Systemd (Recommended and Automatic)

The installation script automatically sets up a user-level systemd daemon:

```bash
# Check daemon status
systemctl --user status doh-monitor.timer

# View daemon logs
journalctl --user -u doh-monitor -f

# Stop the daemon
systemctl --user stop doh-monitor.timer

# Start the daemon
systemctl --user start doh-monitor.timer

# Run daemon once manually (perfect for testing)
doh daemon --once

# Run daemon continuously with verbose output
doh daemon --verbose

# Check local daemon logs
cat ~/.doh/logs/daemon_$(date +%Y-%m-%d).log
```

**Note**: The systemd service runs every **10 minutes** to check all monitored directories. This prevents log spam while ensuring timely auto-commits.

### Cron (Universal)

```bash
# Set up cron job (runs every 5 minutes)
./scripts/cron-setup

# Manual cron entry
*/5 * * * * /usr/local/bin/doh daemon --once
```

## 📊 Monitoring Logic

DOH intelligently monitors directories using these rules:

1. **Git Repository Detection**: Only monitors directories that are git repositories
2. **Change Threshold**: Automatically commits when line changes exceed threshold
3. **Exclusion Respect**: Skips any excluded directories and their children
4. **Profile Application**: Uses configured git profile for all auto-commits
5. **Safe Operations**: Only commits when working directory is clean (no uncommitted changes)

### Status Indicators

- 🟢 **CLEAN**: No changes detected
- 🟡 **BELOW**: Changes detected but under threshold  
- 🔴 **OVER**: Changes exceed threshold (ready for auto-commit)
- ⚠️ **DIRTY**: Uncommitted changes present (auto-commit skipped)
- ❌ **NOT_GIT**: Directory is not a git repository
```

## 🔍 Troubleshooting

### Common Issues

**Command not found after installation:**
```bash
# Reload shell or log out/in
source ~/.bashrc
# Or check PATH
echo $PATH | grep /usr/local/bin
```

**Daemon not running:**
```bash
# Check systemd status
sudo systemctl status doh-daemon

# Check cron
crontab -l | grep doh

# Manual daemon test
doh daemon --once --verbose
```

**Git profile not working:**
```bash
# Verify profile file exists
ls -la ~/.gitconfig-personal

# Test configuration
doh configure --git-profile ~/.gitconfig-personal
doh config
```

### Logs

DOH maintains comprehensive logs:
- Daemon logs: `~/.doh/logs/daemon_YYYY-MM-DD.log`
- Error logs: Standard output with `--verbose`
- Configuration backups: `~/.doh/config.json.backup`

## 🤝 Contributing

### Development Workflow

1. **Fork and clone the repository**
```bash
git clone https://github.com/yourusername/doh.git
cd doh
```

2. **Set up development environment**
```bash
./scripts/dev-setup
source venv/bin/activate
```

3. **Install in editable mode**
```bash
./install --source
```

4. **Make changes and test**
```bash
# Validate package structure
./validate

# Run tests (if available)
python -m pytest tests/

# Test CLI functionality
doh --help
```

5. **Build and test package**
```bash
# Build package locally
./build-release --build

# Test on TestPyPI (maintainers only)
./build-release --test
```

### Publishing to PyPI

For maintainers with PyPI access:

```bash
# Build and publish to TestPyPI first
./build-release --test

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ doh-monitor

# If everything works, publish to production PyPI
./build-release --prod
```

### Installation Methods Summary

| Method | Use Case | Command |
|--------|----------|---------|
| **PyPI Install** | End users, production use | `pip3 install --user doh-monitor` |
| **Quick PyPI** | One-line install | `curl -sSL .../pip-install \| bash` |
| **Source Install** | Development, customization | `./install --source` |
| **Dev Setup** | Contributing, testing | `./scripts/dev-setup` |

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**DOH - Keeping your commits clean and your repos healthy! 🎯**
