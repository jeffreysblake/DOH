# DOH - Directory Oh-no, Handle this! 🎯

**Automatic git commits for rapid development.** DOH monitors your repositories and creates commits as changes accumulate, so you can focus on building without managing commit state.

## Why Choose DOH?

🎯 **Continuous Snapshots** - Automatic commits during rapid iteration and refactoring  
🤖 **Zero Overhead** - Background monitoring every 10 minutes with no interruptions  
📊 **Configurable Triggers** - Set line-change thresholds that match your workflow  
🚫 **Smart Exclusions** - Skip build directories and files you don't want tracked  
⚡ **Seamless Integration** - Works silently while you code

Perfect for LLM-assisted development, prototyping, and high-churn workflows!

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
# Exclude build output and dependencies
doh ex add /path/to/dist
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

| Command | Purpose |
|---------|---------|
| `doh` | Start monitoring current directory |
| `doh status` | Show monitoring status |
| `doh remove` | Stop monitoring current directory |
| `doh ex add <path>` | Exclude directory from monitoring |

## Configuration

```bash
# Adjust threshold for your workflow
doh configure --threshold 75

# Use custom git profile for auto-commits
doh configure --git-profile ~/.gitconfig-work

# View current settings
doh config
```

## Advanced Usage

Need more control? DOH has you covered:

```bash
# Force commit existing changes before monitoring
doh -f --threshold 50

# Control the background daemon
systemctl --user status doh-monitor.timer
systemctl --user stop doh-monitor.timer

# View activity logs
journalctl --user -u doh-monitor -f
```

## Installation & Troubleshooting

**Standard Installation:**
```bash
pip install doh-monitor
```

**Command not found?** Add to PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Check daemon status:**
```bash
systemctl --user status doh-monitor.timer
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

DOH is provided "as is" without warranty. While it helps preserve work through automatic commits, it's not a replacement for proper backup strategies. Users are responsible for their own code safety and should maintain regular backups.

---

**DOH - Because `git commit` shouldn't interrupt your flow! 🎯**
