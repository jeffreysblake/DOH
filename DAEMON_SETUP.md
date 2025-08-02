# DOH Daemon Setup Guide

DOH offers two ways to run the monitoring daemon: **systemd** (recommended for modern Linux) and **cron** (universal compatibility).

## 🚀 Quick Setup

1. **Install DOH system-wide:**
   ```bash
   sudo ./install.sh
   ```

2. **Choose your daemon method:**

### Option A: Systemd Service (Recommended)
**Advantages:** Automatic restart, better logging, resource limits, start/stop control
**Requirements:** systemd-based Linux (Ubuntu 16+, CentOS 7+, Fedora, etc.)

```bash
sudo ./systemd-setup.sh
sudo systemctl enable doh-daemon@$USER.service
sudo systemctl start doh-daemon@$USER.service
```

### Option B: Cron Job (Universal)
**Advantages:** Works on all *nix systems, simple, lightweight
**Requirements:** Any system with cron

```bash
./cron-setup.sh
# Follow the instructions to add to crontab
```

## 🔧 Systemd Management

```bash
# Start the service
sudo systemctl start doh-daemon@$USER.service

# Enable auto-start on boot
sudo systemctl enable doh-daemon@$USER.service

# Check status
sudo systemctl status doh-daemon@$USER.service

# View logs
sudo journalctl -u doh-daemon@$USER.service -f

# Stop the service
sudo systemctl stop doh-daemon@$USER.service

# Restart the service
sudo systemctl restart doh-daemon@$USER.service
```

## 📅 Cron Management

```bash
# Edit crontab
crontab -e

# Add one of these lines:
# Every 10 minutes (recommended)
*/10 * * * * /usr/local/bin/doh daemon --once >/dev/null 2>&1

# Every 5 minutes (more frequent)
*/5 * * * * /usr/local/bin/doh daemon --once >/dev/null 2>&1

# With logging
*/10 * * * * /usr/local/bin/doh daemon --once >> /tmp/doh-cron.log 2>&1

# Check cron logs
tail -f /var/log/cron    # CentOS/RHEL
tail -f /var/log/syslog  # Ubuntu/Debian
```

## 📊 Monitoring and Logs

### Systemd Logs
```bash
# Follow logs in real-time
sudo journalctl -u doh-daemon@$USER.service -f

# View recent logs
sudo journalctl -u doh-daemon@$USER.service --since "1 hour ago"

# View logs with timestamps
sudo journalctl -u doh-daemon@$USER.service --since today
```

### DOH Internal Logs
```bash
# View daemon logs (both systemd and cron write here)
cat ~/.doh/logs/daemon_$(date +%Y-%m-%d).log

# Follow daemon logs
tail -f ~/.doh/logs/daemon_$(date +%Y-%m-%d).log
```

## 🛠 Configuration

```bash
# Add directories to monitoring
doh add /path/to/project --threshold 100 --name "My Project"

# Check what's being monitored
doh list

# Check status
doh status

# Test daemon manually
doh daemon --once --verbose
```

## 🚨 Troubleshooting

### Systemd Issues
```bash
# Check service status
sudo systemctl status doh-daemon@$USER.service

# Check if doh is in PATH
which doh

# Restart the service
sudo systemctl restart doh-daemon@$USER.service

# Check logs for errors
sudo journalctl -u doh-daemon@$USER.service --no-pager
```

### Cron Issues
```bash
# Test daemon manually
/usr/local/bin/doh daemon --once --verbose

# Check cron is running
sudo systemctl status cron     # Ubuntu/Debian
sudo systemctl status crond    # CentOS/RHEL

# Check crontab
crontab -l
```

### General Issues
```bash
# Check configuration
doh config

# Verify git repositories
doh list

# Check permissions
ls -la ~/.doh/
```

## 🔄 Switching Between Methods

### From Cron to Systemd
```bash
# Remove cron job
crontab -e  # Delete the doh line

# Setup systemd
sudo ./systemd-setup.sh
sudo systemctl enable doh-daemon@$USER.service
sudo systemctl start doh-daemon@$USER.service
```

### From Systemd to Cron
```bash
# Stop and disable systemd service
sudo systemctl stop doh-daemon@$USER.service
sudo systemctl disable doh-daemon@$USER.service

# Setup cron
./cron-setup.sh
# Follow instructions to add to crontab
```

## 💡 Tips

- **Start with systemd** if your system supports it - it's more robust
- **Use cron** for shared hosting or older systems
- **Check logs regularly** to ensure everything is working
- **Test with `--verbose`** flag first to see what's happening
- **Both methods can co-exist** but don't run both simultaneously
