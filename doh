#!/bin/bash

# doh - "Directory Oh-no, Handle this!" 
# Quick command to add current directory to auto-commit monitoring
# Usage: doh [threshold] [--status] [--remove] [--force-commit]

DOH_CONFIG_DIR="$HOME/.doh"
DOH_CONFIG_FILE="$DOH_CONFIG_DIR/config.json"
DOH_DAEMON_SCRIPT="$(dirname "$0")/doh-daemon"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default threshold
DEFAULT_THRESHOLD=50

print_usage() {
    echo "doh - Directory auto-commit handler"
    echo ""
    echo "Usage: doh [threshold] [options]"
    echo ""
    echo "Options:"
    echo "  threshold          Lines threshold (default: 50)"
    echo "  --status, -s       Show status of current directory"
    echo "  --remove, -r       Remove current directory from monitoring"
    echo "  --force-commit, -f Force commit if changes exist"
    echo "  --list, -l         List all monitored directories"
    echo "  --help, -h         Show this help"
    echo ""
    echo "Examples:"
    echo "  doh                # Add current dir with 50-line threshold"
    echo "  doh 25             # Add current dir with 25-line threshold"
    echo "  doh --status       # Check current directory status"
    echo "  doh --force-commit # Force commit current changes"
}

# Initialize config directory and file
init_config() {
    mkdir -p "$DOH_CONFIG_DIR/logs"
    
    if [[ ! -f "$DOH_CONFIG_FILE" ]]; then
        cat > "$DOH_CONFIG_FILE" << 'EOF'
{
  "version": "1.0",
  "directories": {},
  "global_settings": {
    "log_retention_days": 30,
    "default_threshold": 50,
    "check_interval_minutes": 10
  }
}
EOF
    fi
}

# Read JSON config (simple bash JSON parser for our specific format)
get_config_value() {
    local key="$1"
    local dir_path="$2"
    
    if [[ -n "$dir_path" ]]; then
        # Get directory-specific setting
        grep -o "\"$(printf '%s' "$dir_path" | sed 's/[[\.*^$()+?{|]/\\&/g')\": *{[^}]*\"$key\": *[^,}]*" "$DOH_CONFIG_FILE" | \
        sed -n "s/.*\"$key\": *\([^,}]*\).*/\1/p" | tr -d '"'
    else
        # Get global setting
        grep -o "\"$key\": *[^,}]*" "$DOH_CONFIG_FILE" | \
        sed "s/\"$key\": *\([^,}]*\)/\1/" | tr -d '"'
    fi
}

# Update JSON config
update_config() {
    local dir_path="$1"
    local threshold="$2"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Create a temporary file with updated config
    local temp_file=$(mktemp)
    
    # If directory already exists in config, update it; otherwise add it
    if grep -q "\"$dir_path\":" "$DOH_CONFIG_FILE"; then
        # Update existing entry
        sed "s|\"$dir_path\": *{[^}]*}|\"$dir_path\": {\"threshold\": $threshold, \"added\": \"$timestamp\", \"last_checked\": \"$timestamp\"}|" \
            "$DOH_CONFIG_FILE" > "$temp_file"
    else
        # Add new entry (insert before the closing brace of directories)
        sed "/\"directories\": *{/a\\    \"$dir_path\": {\"threshold\": $threshold, \"added\": \"$timestamp\", \"last_checked\": \"$timestamp\"}," \
            "$DOH_CONFIG_FILE" > "$temp_file"
    fi
    
    mv "$temp_file" "$DOH_CONFIG_FILE"
}

# Remove directory from config
remove_from_config() {
    local dir_path="$1"
    local temp_file=$(mktemp)
    
    grep -v "\"$dir_path\":" "$DOH_CONFIG_FILE" > "$temp_file"
    mv "$temp_file" "$DOH_CONFIG_FILE"
}

# Get git stats for current directory
get_git_stats() {
    local dir="$1"
    
    if ! git -C "$dir" rev-parse --git-dir >/dev/null 2>&1; then
        echo "not_git"
        return 1
    fi
    
    # Check for changes
    if git -C "$dir" diff --quiet HEAD 2>/dev/null; then
        echo "0:0:0:0:0"
        return 0
    fi
    
    # Get detailed stats
    local stats=$(git -C "$dir" diff --numstat HEAD 2>/dev/null)
    local added=0 deleted=0 files_changed=0
    
    while IFS=$'\t' read -r add del file; do
        if [[ "$add" != "-" ]]; then
            added=$((added + add))
        fi
        if [[ "$del" != "-" ]]; then
            deleted=$((deleted + del))
        fi
        files_changed=$((files_changed + 1))
    done <<< "$stats"
    
    # Get untracked files
    local untracked=$(git -C "$dir" ls-files --others --exclude-standard 2>/dev/null | wc -l)
    
    local total_changes=$((added + deleted))
    echo "$total_changes:$added:$deleted:$files_changed:$untracked"
}

# Show status of current directory
show_status() {
    local current_dir=$(pwd)
    local stats=$(get_git_stats "$current_dir")
    
    if [[ "$stats" == "not_git" ]]; then
        echo -e "${RED}Not a git repository${NC}"
        return 1
    fi
    
    IFS=':' read -r total added deleted files untracked <<< "$stats"
    local threshold=$(get_config_value "threshold" "$current_dir")
    threshold=${threshold:-$DEFAULT_THRESHOLD}
    
    echo -e "${BLUE}Directory Status: $current_dir${NC}"
    echo "Changes: $total lines (+$added/-$deleted) in $files files"
    echo "Untracked files: $untracked"
    echo "Threshold: $threshold lines"
    
    if [[ "$total" -gt 0 ]]; then
        if [[ "$total" -ge "$threshold" ]]; then
            echo -e "${YELLOW}⚠️  Threshold exceeded - ready for auto-commit${NC}"
        else
            echo -e "${GREEN}✓ Changes below threshold${NC}"
        fi
    else
        echo -e "${GREEN}✓ No changes${NC}"
    fi
    
    # Check if directory is monitored
    if grep -q "\"$current_dir\":" "$DOH_CONFIG_FILE" 2>/dev/null; then
        echo -e "${GREEN}📍 Directory is being monitored${NC}"
    else
        echo -e "${YELLOW}📍 Directory not monitored (run 'doh' to add)${NC}"
    fi
}

# Force commit current changes
force_commit() {
    local current_dir=$(pwd)
    local stats=$(get_git_stats "$current_dir")
    
    if [[ "$stats" == "not_git" ]]; then
        echo -e "${RED}Not a git repository${NC}"
        return 1
    fi
    
    IFS=':' read -r total added deleted files untracked <<< "$stats"
    
    if [[ "$total" -eq 0 ]]; then
        echo -e "${YELLOW}No changes to commit${NC}"
        return 0
    fi
    
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local threshold=$(get_config_value "threshold" "$current_dir")
    threshold=${threshold:-$DEFAULT_THRESHOLD}
    
    local commit_msg="Manual doh commit: Snapshot at $timestamp

Changes detected:
- Lines added: $added
- Lines deleted: $deleted  
- Total changes: $total
- Files modified: $files
- Untracked files: $untracked

Manually triggered (threshold: $threshold lines)"
    
    echo -e "${BLUE}Committing changes...${NC}"
    
    if git -C "$current_dir" add . && git -C "$current_dir" commit -m "$commit_msg"; then
        echo -e "${GREEN}✓ Changes committed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to commit changes${NC}"
        return 1
    fi
}

# List all monitored directories
list_directories() {
    echo -e "${BLUE}Monitored directories:${NC}"
    
    if [[ ! -f "$DOH_CONFIG_FILE" ]]; then
        echo "No directories being monitored"
        return 0
    fi
    
    # Extract directory entries from JSON
    grep -o '"[^"]*": {[^}]*}' "$DOH_CONFIG_FILE" | while read -r line; do
        local dir_path=$(echo "$line" | sed 's/"\([^"]*\)": {.*/\1/')
        local threshold=$(echo "$line" | grep -o '"threshold": [0-9]*' | sed 's/"threshold": //')
        
        if [[ -d "$dir_path" ]]; then
            echo -e "  ${GREEN}✓${NC} $dir_path (threshold: $threshold)"
        else
            echo -e "  ${RED}✗${NC} $dir_path (threshold: $threshold) - Directory not found"
        fi
    done
}

# Main execution
main() {
    local current_dir=$(pwd)
    local threshold="$DEFAULT_THRESHOLD"
    local action="add"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_usage
                exit 0
                ;;
            -s|--status)
                action="status"
                shift
                ;;
            -r|--remove)
                action="remove"
                shift
                ;;
            -f|--force-commit)
                action="commit"
                shift
                ;;
            -l|--list)
                action="list"
                shift
                ;;
            [0-9]*)
                threshold="$1"
                shift
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                print_usage
                exit 1
                ;;
        esac
    done
    
    # Initialize config
    init_config
    
    # Execute action
    case "$action" in
        "add")
            if [[ ! -d "$current_dir/.git" ]]; then
                echo -e "${RED}Current directory is not a git repository${NC}"
                exit 1
            fi
            
            update_config "$current_dir" "$threshold"
            echo -e "${GREEN}✓ Added $current_dir to monitoring (threshold: $threshold lines)${NC}"
            echo "Run 'doh --status' to check current status"
            echo "The doh-daemon will monitor this directory automatically"
            ;;
        "status")
            show_status
            ;;
        "remove")
            remove_from_config "$current_dir"
            echo -e "${GREEN}✓ Removed $current_dir from monitoring${NC}"
            ;;
        "commit")
            force_commit
            ;;
        "list")
            list_directories
            ;;
    esac
}

main "$@"
