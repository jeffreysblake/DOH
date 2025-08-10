# DOH Development Notes

This file contains detailed technical information, development workflows, and implementation details that were moved from the main README to keep it user-focused.

## Architecture Details

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
├── install              # Development installation script (source only)
├── uninstall            # Comprehensive uninstallation script
├── validate             # Package validation script
├── build                # Simple PyPI builder
├── pyproject.toml       # Modern Python packaging
└── README.md           # Main documentation
```

## Development Workflow

### Setting Up Development Environment

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
./install
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
./build
```

### Publishing to PyPI

For maintainers with PyPI access:

```bash
# Build package
./build

# Upload to TestPyPI first
python3 -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ doh-monitor

# If everything works, publish to production PyPI
python3 -m twine upload dist/*
```

## Installation Methods (Complete Reference)

| Method | Use Case | Command |
|--------|----------|---------|
| **PyPI Install** | End users, production use | `pip3 install --user doh-monitor` |
| **Source Install** | Development, customization | `./install` |
| **Dev Setup** | Contributing, testing | `./scripts/dev-setup` |

## Configuration File Structure

DOH stores configuration in `~/.doh/config.json`:

```json
{
  "global_settings": {
    "default_threshold": 50,
    "git_profile": "~/.gitconfig-personal",
    "auto_init_git": true
  },
  "directories": {
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

## Monitoring Logic Details

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

## Advanced Configuration

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

## Troubleshooting

### Common Issues

**Command not found after installation:**
```bash
# Reload shell or log out/in
source ~/.bashrc
# Or check PATH
echo $PATH | grep ~/.local/bin
```

**Daemon not running:**
```bash
# Check systemd status
systemctl --user status doh-monitor.timer

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

## Daemon Setup Details

### User-level Systemd (Automatic)

DOH automatically sets up a user-level systemd daemon on first run:

```bash
# Check daemon status
systemctl --user status doh-monitor.timer

# View daemon logs
journalctl --user -u doh-monitor -f

# Stop the daemon
systemctl --user stop doh-monitor.timer

# Start the daemon
systemctl --user start doh-monitor.timer
```

**Note**: The systemd service runs every **10 minutes** to check all monitored directories.

### Cron (Alternative)

```bash
# Set up cron job (runs every 5 minutes)
./scripts/cron-setup

# Manual cron entry
*/5 * * * * ~/.local/bin/doh daemon --once
```

## Complete Command Reference

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

## First-Run Setup Details

DOH automatically handles setup on first use:
- ✅ Creates `~/.doh/` configuration directory
- ✅ Sets up systemd user daemon (if available)
- ✅ Starts 10-minute monitoring timer
- ✅ No manual configuration needed!

The setup happens in the `config.py` module when the CLI is first invoked.
