#!/bin/bash

# Git Auto-Commit Cron Setup Helper
# This script helps set up cron jobs for the git auto-commit monitor

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_AUTOCOMMIT_SCRIPT="$SCRIPT_DIR/git_auto_commit.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_usage() {
    echo "Git Auto-Commit Cron Setup Helper"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  setup     Set up cron job for a repository"
    echo "  list      List existing auto-commit cron jobs"
    echo "  remove    Remove cron job for a repository"
    echo "  test      Test the script on a repository"
    echo ""
    echo "Setup Options:"
    echo "  -d, --directory DIR    Repository directory (default: current)"
    echo "  -t, --threshold NUM    Lines threshold (default: 50)"
    echo "  -i, --interval STR     Cron interval (default: '*/10 * * * *' = every 10 minutes)"
    echo ""
    echo "Examples:"
    echo "  $0 setup -d /path/to/repo -t 100 -i '*/5 * * * *'"
    echo "  $0 test -d /path/to/repo"
    echo "  $0 list"
    echo "  $0 remove -d /path/to/repo"
}

setup_cron() {
    local repo_dir="$1"
    local threshold="$2"
    local interval="$3"
    
    # Validate repository
    if [[ ! -d "$repo_dir" ]]; then
        echo -e "${RED}Error: Directory $repo_dir does not exist${NC}"
        return 1
    fi
    
    if ! git -C "$repo_dir" rev-parse --git-dir >/dev/null 2>&1; then
        echo -e "${RED}Error: $repo_dir is not a git repository${NC}"
        return 1
    fi
    
    # Create cron job entry
    local abs_repo_dir=$(realpath "$repo_dir")
    local cron_comment="# Auto-commit monitor for $abs_repo_dir"
    local cron_job="$interval cd $abs_repo_dir && $GIT_AUTOCOMMIT_SCRIPT -t $threshold $abs_repo_dir"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "$abs_repo_dir.*git_auto_commit.py"; then
        echo -e "${YELLOW}Cron job already exists for $abs_repo_dir${NC}"
        echo "Remove it first with: $0 remove -d $repo_dir"
        return 1
    fi
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$cron_comment"; echo "$cron_job") | crontab -
    
    echo -e "${GREEN}✓ Cron job added successfully${NC}"
    echo "Repository: $abs_repo_dir"
    echo "Threshold: $threshold lines"
    echo "Interval: $interval"
    echo ""
    echo "The script will now run automatically and check for changes."
    echo "Logs will be written to: $SCRIPT_DIR/logs/"
}

list_cron_jobs() {
    echo -e "${BLUE}Current auto-commit cron jobs:${NC}"
    echo ""
    
    local jobs=$(crontab -l 2>/dev/null | grep -A1 "Auto-commit monitor for" || true)
    
    if [[ -z "$jobs" ]]; then
        echo "No auto-commit cron jobs found."
        return 0
    fi
    
    echo "$jobs" | while IFS= read -r line; do
        if [[ "$line" == \#* ]]; then
            echo -e "${YELLOW}$line${NC}"
        else
            echo "$line"
            echo ""
        fi
    done
}

remove_cron() {
    local repo_dir="$1"
    local abs_repo_dir=$(realpath "$repo_dir" 2>/dev/null || echo "$repo_dir")
    
    # Remove cron job
    local temp_cron=$(mktemp)
    crontab -l 2>/dev/null | grep -v "$abs_repo_dir.*git_auto_commit.py" | grep -v "Auto-commit monitor for $abs_repo_dir" > "$temp_cron"
    crontab "$temp_cron"
    rm "$temp_cron"
    
    echo -e "${GREEN}✓ Cron job removed for $abs_repo_dir${NC}"
}

test_script() {
    local repo_dir="$1"
    local threshold="$2"
    
    echo -e "${BLUE}Testing auto-commit script...${NC}"
    echo "Repository: $repo_dir"
    echo "Threshold: $threshold"
    echo ""
    
    python3 "$GIT_AUTOCOMMIT_SCRIPT" -t "$threshold" -v "$repo_dir"
}

# Parse command line arguments
COMMAND=""
REPO_DIR="$(pwd)"
THRESHOLD=50
INTERVAL="*/10 * * * *"  # Every 10 minutes

while [[ $# -gt 0 ]]; do
    case $1 in
        setup|list|remove|test)
            COMMAND="$1"
            shift
            ;;
        -d|--directory)
            REPO_DIR="$2"
            shift 2
            ;;
        -t|--threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Execute command
case "$COMMAND" in
    setup)
        setup_cron "$REPO_DIR" "$THRESHOLD" "$INTERVAL"
        ;;
    list)
        list_cron_jobs
        ;;
    remove)
        remove_cron "$REPO_DIR"
        ;;
    test)
        test_script "$REPO_DIR" "$THRESHOLD"
        ;;
    *)
        echo -e "${RED}No command specified${NC}"
        print_usage
        exit 1
        ;;
esac
