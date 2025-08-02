#!/bin/bash
# cron-setup.sh - Set up DOH daemon to run via cron

echo "🕐 Setting up DOH daemon for cron"
echo

# Check if doh is installed
if ! command -v doh &> /dev/null; then
    echo "❌ DOH is not installed in PATH"
    echo "Please run 'sudo ./install.sh' first to install DOH system-wide"
    exit 1
fi

echo "✅ DOH found in PATH"

# Test daemon once
echo "🧪 Testing daemon (single run)..."
if doh daemon --once --verbose; then
    echo "✅ Daemon test successful"
else
    echo "❌ Daemon test failed"
    echo "Please check your DOH configuration and try again"
    exit 1
fi

echo
echo "📝 To add DOH daemon to your crontab:"
echo
echo "1. Run: crontab -e"
echo "2. Add this line (runs every 10 minutes):"
echo "   */10 * * * * /usr/local/bin/doh daemon --once >/dev/null 2>&1"
echo
echo "Or for more frequent monitoring (every 5 minutes):"
echo "   */5 * * * * /usr/local/bin/doh daemon --once >/dev/null 2>&1"
echo
echo "Or with logging to a file:"
echo "   */10 * * * * /usr/local/bin/doh daemon --once >> /tmp/doh-cron.log 2>&1"
echo
echo "📊 To check daemon logs:"
echo "   cat ~/.doh/logs/daemon_\$(date +%Y-%m-%d).log"
echo
echo "🔍 To check what directories are being monitored:"
echo "   doh list"
echo
echo "💡 Remember: Add directories to monitoring with 'doh add [directory]'"
