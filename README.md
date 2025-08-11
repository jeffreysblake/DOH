# DOH - Directory Oh-no, Handle this! 🎯

**Automatic git commits for the chronically forgetful.** DOH monitors your repositories and creates commits when changes pile up, so you can focus on coding without constantly remembering to commit.

## Why Choose DOH?

🎯 **Automatic Safety Net** - Helps prevent losing work to crashes, power outages, or forgotten commits  
🤖 **Set and Forget** - Background monitoring every 10 minutes with zero maintenance  
📊 **Smart Thresholds** - Configure how many lines of changes trigger auto-commits  
🚫 **Flexible Control** - Exclude directories you don't want monitored  
⚡ **Zero Friction** - Works silently in the background, no interruptions

Perfect for ADHD developers and anyone who gets lost in flow state!

## Quick Start

### 1. Install DOH
```bash
pip install doh-monitor
```

### 2. Start monitoring a project
```bash
cd /path/to/your/project
doh
```

That's it! DOH now monitors this directory with sensible defaults (50-line threshold) and will auto-commit when you accumulate changes.

### 3. Check your monitoring status

```bash
# Check local status for current directory
doh status

# Check status for all monitored directories
doh status --global
```

## Use Cases

### � Rapid Prototyping
```bash
# Track experimental changes as you iterate
doh --threshold 30 --name "ML Experiment"
```

### 🏗️ Architecture Changes
```bash
# Monitor during large refactors across multiple projects
cd ~/work/api-server && doh --threshold 100
cd ~/work/frontend && doh --threshold 50
```

### 🚫 Skip Generated Files
```bash
```

## Use Cases

### 🛡️ Protect Work in Progress
```bash
# Monitor your current project with a 30-line safety net
doh --threshold 30 --name "My Important Project"
```

### 📁 Monitor Multiple Projects
```bash
# Set different thresholds for different projects
cd ~/work/api-server && doh --threshold 100
cd ~/personal/website && doh --threshold 25
```

### 🚫 Exclude Build Directories
```bash
# Don't monitor temporary/build directories
doh ex add /path/to/build
doh ex add /path/to/node_modules
```
```

## How It Works

DOH runs in the background and:

1. **Monitors** your git repositories every 10 minutes
2. **Counts** lines changed (staged + unstaged + untracked files)
3. **Commits** automatically when changes exceed your threshold
4. **Continues** monitoring silently

Auto-commits include helpful messages like: `"Auto-commit: 67 lines changed in MyProject"`

## Essential Commands

| Command | What it does |
|---------|-------------|
| `doh` | Start monitoring current directory |
| `doh status` | Show local status for current directory |
| `doh status --global` | Show monitoring status for all projects |
| `doh list` | List all monitored directories |
| `doh rm` | Stop monitoring current directory |
| `doh run` | Check all monitored directories now |
| `doh squash "message"` | Merge temp branch commits |
| `doh cleanup` | Clean up old temporary branches |
| `doh ex add <path>` | Exclude a directory from monitoring |

## Configuration

### Set Your Preferences
```bash
# Change default threshold  
doh config --set --threshold 75

# Use a custom git profile for auto-commits
doh config --set --git-profile ~/.gitconfig-work

# Enable automatic git init for new projects
doh config --set --auto-init-git

# Configure temporary branch settings
doh config --set --temp-branches --temp-branch-prefix "my-commits"
```

### View Current Settings

```bash
doh config
```

## Advanced Usage

### Force Commit Before Monitoring

```bash
doh add --force --threshold 50  # Commits any existing changes first
```

### Temporary Branch Strategy

DOH now uses temporary branches for auto-commits to keep your main branch clean:

```bash
# Check temp branches for current directory
doh status

# Squash temp commits into main branch
doh squash "Implemented user authentication"

# Clean up old temp branches
doh cleanup
```

### Manual Processing

```bash
# Process all monitored directories now (don't wait for timer)
doh run

# Process with verbose output
doh run --verbose
```

## Installation Details

### Standard Installation

```bash
pip install doh-monitor
```

### Development Installation

If you want to contribute or modify DOH:

```bash
git clone <repository-url>
cd doh
pip install -e .  # Install in development mode
```

### Running Tests

DOH has comprehensive test coverage:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/doh --cov-report=term-missing

# Run specific test modules
pytest tests/test_cli.py -v
```

Current test coverage: **70%** across all modules.

### PATH Setup (if needed)

If `doh` command isn't found after installation:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Troubleshooting

**Command not found?**

```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Want to see what DOH is doing?**

```bash
# Check status of all monitored directories
doh status --global

# Run monitoring manually to see output
doh run --verbose
```

**Need to clean up test directories?**

```bash
# Remove directories that no longer exist
doh list  # See what's being monitored
doh rm /path/to/deleted/directory
```

## Uninstall

```bash
pip uninstall doh-monitor

# Optional: Remove configuration and daemon
rm -rf ~/.doh
systemctl --user stop doh-monitor.timer
systemctl --user disable doh-monitor.timer
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

DOH is provided "as is" without warranty of any kind. While DOH aims to help preserve your work through automatic commits, it is not a replacement for proper backup strategies and good development practices. Users are responsible for their own code safety and should maintain regular backups.

---

**DOH - Because `git commit` shouldn't be an afterthought! 🎯**
