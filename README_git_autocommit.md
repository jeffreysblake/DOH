# Git Auto-Commit Monitor

A lightweight, resource-efficient system for automatically committing git changes when a threshold of modified lines is exceeded. Uses cron for scheduling to minimize resource usage.

## Features

- **Threshold-based commits**: Only commits when changes exceed a specified line count
- **Detailed commit messages**: Includes timestamp and change statistics
- **Resource efficient**: Runs via cron, not continuously
- **Configurable**: Customizable thresholds and check intervals
- **Logging**: Comprehensive logging with daily log rotation
- **Multiple repository support**: Can monitor multiple repos with different settings

## Files

- `git_auto_commit.py` - Main monitoring script
- `setup_git_autocommit_cron.sh` - Helper for managing cron jobs
- `logs/` - Directory for log files (created automatically)

## Quick Start

### 1. Test the script manually
```bash
# Test on current directory with 50-line threshold
./git_auto_commit.py

# Test on specific repo with custom threshold
./git_auto_commit.py -t 100 /path/to/your/repo
```

### 2. Set up automatic monitoring with cron
```bash
# Set up monitoring for current repo (checks every 10 minutes)
./setup_git_autocommit_cron.sh setup

# Set up with custom settings
./setup_git_autocommit_cron.sh setup -d /path/to/repo -t 100 -i "*/5 * * * *"
```

### 3. Manage cron jobs
```bash
# List all auto-commit cron jobs
./setup_git_autocommit_cron.sh list

# Remove monitoring for a repo
./setup_git_autocommit_cron.sh remove -d /path/to/repo
```

## Usage Examples

### Manual Usage
```bash
# Basic usage (current directory, 50-line threshold)
./git_auto_commit.py

# Custom threshold
./git_auto_commit.py -t 25 /home/user/my-project

# Verbose output
./git_auto_commit.py -v -t 75 /path/to/repo
```

### Cron Setup Examples
```bash
# Monitor current repo, check every 10 minutes, 50-line threshold
./setup_git_autocommit_cron.sh setup

# Monitor specific repo, check every 5 minutes, 100-line threshold
./setup_git_autocommit_cron.sh setup -d /home/user/project -t 100 -i "*/5 * * * *"

# Monitor documentation repo, check hourly, 25-line threshold
./setup_git_autocommit_cron.sh setup -d /home/user/docs -t 25 -i "0 * * * *"
```

### Cron Interval Examples
- `*/5 * * * *` - Every 5 minutes
- `*/10 * * * *` - Every 10 minutes (default)
- `*/15 * * * *` - Every 15 minutes
- `0 * * * *` - Every hour
- `0 */2 * * *` - Every 2 hours
- `0 9-17 * * 1-5` - Every hour during business hours (9-5, Mon-Fri)

## Commit Message Format

When the threshold is exceeded, commits are created with detailed messages:

```
Auto-commit: Snapshot at 2025-08-02 14:30:15

Changes detected:
- Lines added: 67
- Lines deleted: 23
- Total changes: 90
- Files modified: 5

Threshold exceeded (90 > 50 lines)
```

## Configuration

### Command Line Options

**git_auto_commit.py:**
- `-t, --threshold NUM` - Lines threshold (default: 50)
- `-c, --config FILE` - Config file path
- `-v, --verbose` - Verbose output

**setup_git_autocommit_cron.sh:**
- `-d, --directory DIR` - Repository directory
- `-t, --threshold NUM` - Lines threshold
- `-i, --interval STR` - Cron interval

### Configuration File

Create `.auto_commit_config.json` in your repository for persistent settings:

```json
{
  "threshold": 75,
  "exclude_patterns": [
    "*.log",
    "node_modules/*",
    ".git/*"
  ],
  "last_commit_time": "2025-08-02T14:30:15"
}
```

## Logging

Logs are written to `logs/auto_commit_YYYYMMDD.log` with entries like:

```
2025-08-02 14:30:15,123 - INFO - Changes detected: 45 lines (+32/-13) in 3 files, 0 untracked (below threshold)
2025-08-02 14:35:15,456 - INFO - Threshold exceeded: 67 changes (threshold: 50)
2025-08-02 14:35:16,789 - INFO - ✓ Auto-commit successful: +45/-22 lines across 4 files
```

## Resource Usage

This system is designed to be lightweight:

- **Memory**: ~10-20MB per execution (Python + git commands)
- **CPU**: Minimal - only runs for 1-2 seconds per check
- **Disk**: Log files rotate daily, git operations are standard
- **Network**: None (unless you have git hooks that push)

## Modern Ubuntu Alternatives

### systemd Timers (Alternative to cron)

For more modern Ubuntu systems, you could use systemd timers instead of cron:

1. Create a service file:
```bash
sudo tee /etc/systemd/system/git-autocommit@.service << EOF
[Unit]
Description=Git Auto-Commit for %i
After=network.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=%i
ExecStart=/home/decisiv/tooling/scripts/git_auto_commit.py -t 50 %i
EOF
```

2. Create a timer file:
```bash
sudo tee /etc/systemd/system/git-autocommit@.timer << EOF
[Unit]
Description=Run git auto-commit every 10 minutes for %i
Requires=git-autocommit@%i.service

[Timer]
OnCalendar=*:0/10
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

3. Enable and start:
```bash
sudo systemctl enable git-autocommit@$(systemd-escape /path/to/repo).timer
sudo systemctl start git-autocommit@$(systemd-escape /path/to/repo).timer
```

### Git Hooks Alternative

For immediate commits on changes, you could use git hooks:

```bash
# In your repo's .git/hooks/post-commit
#!/bin/bash
/home/decisiv/tooling/scripts/git_auto_commit.py /path/to/repo
```

## Troubleshooting

### Check if cron is running
```bash
sudo systemctl status cron
```

### View cron logs
```bash
grep auto_commit /var/log/syslog
```

### Test script manually
```bash
./setup_git_autocommit_cron.sh test -d /path/to/repo
```

### View current cron jobs
```bash
crontab -l
```

## Security Considerations

- The script only works within git repositories
- Uses standard git commands (no external network access)
- Logs are written to local filesystem only
- Runs with user permissions (not root)

## Recommendations

- **Development repos**: 25-50 line threshold, 5-10 minute intervals
- **Documentation**: 10-25 line threshold, 15-30 minute intervals  
- **Configuration files**: 5-15 line threshold, 5 minute intervals
- **Large projects**: 100+ line threshold, 15-30 minute intervals
