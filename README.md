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
doh status
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
| `doh status` | Show monitoring status for all projects |
| `doh list` | List all monitored directories |
| `doh remove` | Stop monitoring current directory |
| `doh ex add <path>` | Exclude a directory from monitoring |

## Configuration

### Set Your Preferences
```bash
# Change default threshold
doh configure --threshold 75

# Use a custom git profile for auto-commits
doh configure --git-profile ~/.gitconfig-work

# Enable automatic git init for new projects
doh configure --auto-init-git
```

### View Current Settings
```bash
doh config
```

## Advanced Usage

### Force Commit Before Monitoring
```bash
doh -f --threshold 50  # Commits any existing changes first
```

### Control the Background Daemon
```bash
# Check if daemon is running
systemctl --user status doh-monitor.timer

# Stop monitoring temporarily
systemctl --user stop doh-monitor.timer

# Restart monitoring
systemctl --user start doh-monitor.timer
```

### View Activity Logs
```bash
# See what DOH is doing
journalctl --user -u doh-monitor -f
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
./install
```

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

**Daemon not running?**
```bash
systemctl --user status doh-monitor.timer
# or test manually:
doh daemon --once
```

**Want to see activity?**
```bash
journalctl --user -u doh-monitor -f
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
