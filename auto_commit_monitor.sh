#!/bin/bash

# Auto-commit monitor script
# Monitors git changes and auto-commits when threshold is exceeded
# Usage: ./auto_commit_monitor.sh [directory] [threshold] [check_interval]

# Default values
DEFAULT_DIRECTORY="$(pwd)"
DEFAULT_THRESHOLD=50  # lines changed
DEFAULT_INTERVAL=300  # 5 minutes in seconds

# Parse arguments
MONITOR_DIR="${1:-$DEFAULT_DIRECTORY}"
THRESHOLD="${2:-$DEFAULT_THRESHOLD}"
CHECK_INTERVAL="${3:-$DEFAULT_INTERVAL}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file
LOG_DIR="$(dirname "$0")/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/auto_commit_$(date +%Y%m%d).log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

print_usage() {
    echo "Usage: $0 [directory] [threshold] [check_interval_seconds]"
    echo ""
    echo "Arguments:"
    echo "  directory           Directory to monitor (default: current directory)"
    echo "  threshold          Lines changed threshold for auto-commit (default: 50)"
    echo "  check_interval     Check interval in seconds (default: 300)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Monitor current dir, 50 lines, 5min interval"
    echo "  $0 /path/to/project 100 600          # Monitor project, 100 lines, 10min interval"
    echo "  $0 . 25 180                          # Monitor current dir, 25 lines, 3min interval"
}

check_git_repo() {
    if ! git -C "$MONITOR_DIR" rev-parse --git-dir >/dev/null 2>&1; then
        echo -e "${RED}Error: $MONITOR_DIR is not a git repository${NC}"
        exit 1
    fi
}

get_git_stats() {
    local dir="$1"
    
    # Check if there are any changes
    if ! git -C "$dir" diff --quiet HEAD 2>/dev/null; then
        # Get detailed stats
        local stats=$(git -C "$dir" diff --numstat HEAD 2>/dev/null)
        local added=0
        local deleted=0
        local files_changed=0
        
        while IFS=$'\t' read -r add del file; do
            if [[ "$add" != "-" ]]; then
                added=$((added + add))
            fi
            if [[ "$del" != "-" ]]; then
                deleted=$((deleted + del))
            fi
            files_changed=$((files_changed + 1))
        done <<< "$stats"
        
        local total_changes=$((added + deleted))
        
        echo "$total_changes:$added:$deleted:$files_changed"
    else
        echo "0:0:0:0"
    fi
}

create_commit_message() {
    local total_changes="$1"
    local added="$2"
    local deleted="$3"
    local files_changed="$4"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "Auto-commit: Snapshot taken at $timestamp

Changes detected:
- Lines added: $added
- Lines deleted: $deleted
- Total changes: $total_changes
- Files modified: $files_changed

Threshold exceeded ($total_changes > $THRESHOLD lines)"
}

perform_auto_commit() {
    local dir="$1"
    local total_changes="$2"
    local added="$3"
    local deleted="$4"
    local files_changed="$5"
    
    log_message "${GREEN}Threshold exceeded! Performing auto-commit...${NC}"
    
    # Stage all changes
    if git -C "$dir" add . 2>/dev/null; then
        local commit_msg=$(create_commit_message "$total_changes" "$added" "$deleted" "$files_changed")
        
        # Commit changes
        if git -C "$dir" commit -m "$commit_msg" 2>/dev/null; then
            log_message "${GREEN}✓ Auto-commit successful${NC}"
            log_message "  Changes: +$added/-$deleted lines across $files_changed files"
            return 0
        else
            log_message "${RED}✗ Failed to commit changes${NC}"
            return 1
        fi
    else
        log_message "${RED}✗ Failed to stage changes${NC}"
        return 1
    fi
}

monitor_loop() {
    log_message "${BLUE}Starting auto-commit monitor${NC}"
    log_message "Directory: $MONITOR_DIR"
    log_message "Threshold: $THRESHOLD lines"
    log_message "Check interval: $CHECK_INTERVAL seconds"
    log_message "Press Ctrl+C to stop monitoring"
    echo ""
    
    while true; do
        # Get current git stats
        local stats=$(get_git_stats "$MONITOR_DIR")
        IFS=':' read -r total_changes added deleted files_changed <<< "$stats"
        
        if [[ "$total_changes" -gt 0 ]]; then
            if [[ "$total_changes" -ge "$THRESHOLD" ]]; then
                log_message "${YELLOW}Threshold exceeded: $total_changes changes (threshold: $THRESHOLD)${NC}"
                perform_auto_commit "$MONITOR_DIR" "$total_changes" "$added" "$deleted" "$files_changed"
            else
                log_message "Changes detected: $total_changes lines (+$added/-$deleted) in $files_changed files (below threshold)"
            fi
        else
            log_message "No changes detected"
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

cleanup_on_exit() {
    log_message "${YELLOW}Auto-commit monitor stopped${NC}"
    exit 0
}

# Main execution
main() {
    # Handle help flag
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        print_usage
        exit 0
    fi
    
    # Validate directory
    if [[ ! -d "$MONITOR_DIR" ]]; then
        echo -e "${RED}Error: Directory $MONITOR_DIR does not exist${NC}"
        exit 1
    fi
    
    # Check if it's a git repository
    check_git_repo
    
    # Validate threshold
    if ! [[ "$THRESHOLD" =~ ^[0-9]+$ ]] || [[ "$THRESHOLD" -lt 1 ]]; then
        echo -e "${RED}Error: Threshold must be a positive integer${NC}"
        exit 1
    fi
    
    # Validate check interval
    if ! [[ "$CHECK_INTERVAL" =~ ^[0-9]+$ ]] || [[ "$CHECK_INTERVAL" -lt 1 ]]; then
        echo -e "${RED}Error: Check interval must be a positive integer${NC}"
        exit 1
    fi
    
    # Set up signal handling
    trap cleanup_on_exit INT TERM
    
    # Start monitoring
    monitor_loop
}

# Run main function
main "$@"
