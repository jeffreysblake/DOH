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
    echo "       doh ex <command> [path]"
    echo ""
    echo "Options:"
    echo "  threshold          Lines threshold (default: 50)"
    echo "  --name, -n NAME    Set a name for this directory"
    echo "  --status, -s       Show status of current directory"
    echo "  --remove, -r       Remove current directory from monitoring"
    echo "  --force-commit, -f Force commit if changes exist"
    echo "  --list, -l         List all monitored directories"
    echo "  --help, -h         Show this help"
    echo ""
    echo "Exclusion commands:"
    echo "  ex list            List excluded directories"
    echo "  ex add [path]      Add directory to exclusions (default: pwd)"
    echo "  ex rm [path]       Remove directory from exclusions (default: pwd)"
    echo ""
    echo "Examples:"
    echo "  doh                # Add current dir or show status if already monitored"
    echo "  doh 25 -n myproj   # Add with threshold and name"
    echo "  doh --status       # Check current directory status"
    echo "  doh ex add         # Exclude current directory from monitoring"
}

# Initialize config directory and file
init_config() {
    mkdir -p "$DOH_CONFIG_DIR/logs"
    
    if [[ ! -f "$DOH_CONFIG_FILE" ]]; then
        cat > "$DOH_CONFIG_FILE" << 'EOF'
{
  "version": "1.0",
  "directories": {},
  "exclusions": {},
  "global_settings": {
    "log_retention_days": 30,
    "default_threshold": 50,
    "check_interval_minutes": 10,
    "git_profile": ""
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
    local name="$3"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Check if directory or any parent directory is excluded
    if is_excluded "$dir_path"; then
        local excluded_path=$(find_excluded_parent "$dir_path")
        if [[ "$excluded_path" == "$dir_path" ]]; then
            echo -e "${RED}Directory is excluded from monitoring${NC}"
            echo "Use 'doh ex rm' to remove from exclusions first"
        else
            echo -e "${RED}Cannot monitor directory - parent directory is excluded${NC}"
            echo "Parent directory '$excluded_path' is in the exclusions list"
            echo "Options:"
            echo "  1. Move current directory outside of '$excluded_path'"
            echo "  2. Remove '$excluded_path' from exclusions: doh ex rm '$excluded_path'"
        fi
        return 1
    fi
    
    # Create a temporary file with updated config
    local temp_file=$(mktemp)
    
    # Generate name if not provided
    if [[ -z "$name" ]]; then
        name=$(basename "$dir_path")
    fi
    
    # Build config entry
    local config_entry="\"name\": \"$name\", \"threshold\": $threshold, \"added\": \"$timestamp\", \"last_checked\": \"$timestamp\""
    
    # If directory already exists in config, update it; otherwise add it
    if grep -q "\"$dir_path\":" "$DOH_CONFIG_FILE"; then
        # Update existing entry
        sed "s|\"$dir_path\": *{[^}]*}|\"$dir_path\": {$config_entry}|" \
            "$DOH_CONFIG_FILE" > "$temp_file"
    else
        # Add new entry - handle both empty and non-empty directories section
        if grep -q '"directories": *{}' "$DOH_CONFIG_FILE"; then
            # Empty directories section - replace {} with {entry}
            sed "s|\"directories\": *{}|\"directories\": {\\n    \"$dir_path\": {$config_entry}\\n  }|" \
                "$DOH_CONFIG_FILE" > "$temp_file"
        else
            # Non-empty directories section - add entry before closing brace
            sed "/\"directories\": *{/,/}/ {
                /}/ {
                    i\\    \"$dir_path\": {$config_entry},
                }
            }" "$DOH_CONFIG_FILE" > "$temp_file"
        fi
    fi
    
    mv "$temp_file" "$DOH_CONFIG_FILE"
}

# Remove directory from config
remove_from_config() {
    local dir_path="$1"
    local temp_file=$(mktemp)
    
    grep -v "\"$dir_path\":" "$DOH_CONFIG_FILE" > "$temp_file"
    
    # Fix trailing commas (simple approach)
    sed 's/,\s*}/}/g' "$temp_file" > "$DOH_CONFIG_FILE"
    rm -f "$temp_file"
}

# Check if directory or any parent directory is excluded
is_excluded() {
    local dir_path="$1"
    
    if [[ ! -f "$DOH_CONFIG_FILE" ]]; then
        return 1
    fi
    
    # Check if the directory itself is excluded
    if sed -n '/\"exclusions\": *{/,/}/p' "$DOH_CONFIG_FILE" | grep -q "\"$dir_path\":"; then
        return 0
    fi
    
    # Check if any parent directory is excluded
    local current_path="$dir_path"
    while [[ "$current_path" != "/" && "$current_path" != "." ]]; do
        current_path=$(dirname "$current_path")
        if sed -n '/\"exclusions\": *{/,/}/p' "$DOH_CONFIG_FILE" | grep -q "\"$current_path\":"; then
            return 0
        fi
    done
    
    return 1
}

# Find which excluded directory (self or parent) is blocking this path
find_excluded_parent() {
    local dir_path="$1"
    
    if [[ ! -f "$DOH_CONFIG_FILE" ]]; then
        return 1
    fi
    
    # Check if the directory itself is excluded
    if sed -n '/\"exclusions\": *{/,/}/p' "$DOH_CONFIG_FILE" | grep -q "\"$dir_path\":"; then
        echo "$dir_path"
        return 0
    fi
    
    # Check if any parent directory is excluded
    local current_path="$dir_path"
    while [[ "$current_path" != "/" && "$current_path" != "." ]]; do
        current_path=$(dirname "$current_path")
        if sed -n '/\"exclusions\": *{/,/}/p' "$DOH_CONFIG_FILE" | grep -q "\"$current_path\":"; then
            echo "$current_path"
            return 0
        fi
    done
    
    return 1
}

# Check if directory is monitored
is_monitored() {
    local dir_path="$1"
    
    if [[ ! -f "$DOH_CONFIG_FILE" ]]; then
        return 1
    fi
    
    # Simple check if directory exists in config
    grep -q "\"$dir_path\":" "$DOH_CONFIG_FILE"
}

# Add directory to exclusions
add_exclusion() {
    local dir_path="$1"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local temp_file=$(mktemp)
    
    # Remove from monitoring if it exists
    if is_monitored "$dir_path"; then
        remove_from_config "$dir_path"
    fi
    
    # Add to exclusions
    if grep -q "\"$dir_path\":" "$DOH_CONFIG_FILE"; then
        # Update existing entry in exclusions
        sed "s|\"$dir_path\": *{[^}]*}|\"$dir_path\": {\"excluded\": \"$timestamp\"}|" \
            "$DOH_CONFIG_FILE" > "$temp_file"
    else
        # Add new exclusion entry
        sed "/\"exclusions\": *{/a\\    \"$dir_path\": {\"excluded\": \"$timestamp\"}," \
            "$DOH_CONFIG_FILE" > "$temp_file"
    fi
    
    mv "$temp_file" "$DOH_CONFIG_FILE"
}

# Remove directory from exclusions
remove_exclusion() {
    local dir_path="$1"
    local temp_file=$(mktemp)
    
    # Simple: just remove the line with this directory path
    grep -v "\"$dir_path\":" "$DOH_CONFIG_FILE" > "$temp_file"
    mv "$temp_file" "$DOH_CONFIG_FILE"
}

# List exclusions
list_exclusions() {
    echo -e "${BLUE}Excluded directories:${NC}"
    
    if [[ ! -f "$DOH_CONFIG_FILE" ]]; then
        echo "No directories are excluded"
        return 0
    fi
    
    # Extract exclusion entries from JSON exclusions section only
    local found_exclusions=false
    sed -n '/\"exclusions\": *{/,/}/p' "$DOH_CONFIG_FILE" | grep -o '"[^"]*": {[^}]*}' | while read -r line; do
        # Skip if this is just the section header or empty
        if [[ "$line" =~ ^\"exclusions\": || -z "$line" ]]; then
            continue
        fi
        
        found_exclusions=true
        local dir_path=$(echo "$line" | sed 's/"\([^"]*\)": {.*/\1/')
        local excluded_date=$(echo "$line" | grep -o '"excluded": "[^"]*"' | sed 's/"excluded": "\([^"]*\)"/\1/')
        
        if [[ -d "$dir_path" ]]; then
            echo -e "  ${YELLOW}✗${NC} $dir_path (excluded: $excluded_date)"
        else
            echo -e "  ${RED}✗${NC} $dir_path (excluded: $excluded_date) - Directory not found"
        fi
    done
    
    # Check if no exclusions were found
    if ! sed -n '/\"exclusions\": *{/,/}/p' "$DOH_CONFIG_FILE" | grep -q '"[^"]*": {[^}]*}' | grep -v '"exclusions":'; then
        echo "No directories are excluded"
    fi
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
    local name=$(get_config_value "name" "$current_dir")
    threshold=${threshold:-$DEFAULT_THRESHOLD}
    
    echo -e "${BLUE}Directory Status: $current_dir${NC}"
    if [[ -n "$name" ]]; then
        echo -e "${BLUE}Name: $name${NC}"
    fi
    echo "Changes: $total lines (+$added/-$deleted) in $files files"
    echo "Untracked files: $untracked"
    echo "Threshold: $threshold lines"
    
    # Status assessment
    if [[ "$total" -gt 0 ]]; then
        if [[ "$total" -ge "$threshold" ]]; then
            echo -e "${YELLOW}⚠️  Status: THRESHOLD EXCEEDED - Auto-commit ready${NC}"
            echo -e "   Would trigger: $total >= $threshold lines"
        else
            echo -e "${GREEN}✓ Status: THRESHOLD NOT MET${NC}"
            echo -e "   Progress: $total/$threshold lines ($(( (total * 100) / threshold ))%)"
        fi
    else
        echo -e "${GREEN}✓ Status: CLEAN - No changes${NC}"
    fi
    
    # Check monitoring status
    if is_excluded "$current_dir"; then
        local excluded_path=$(find_excluded_parent "$current_dir")
        if [[ "$excluded_path" == "$current_dir" ]]; then
            echo -e "${RED}📍 Directory is EXCLUDED from monitoring${NC}"
        else
            echo -e "${RED}📍 Directory is EXCLUDED (parent '$excluded_path' is excluded)${NC}"
        fi
    elif is_monitored "$current_dir"; then
        echo -e "${GREEN}📍 Directory is being MONITORED${NC}"
    else
        echo -e "${YELLOW}📍 Directory NOT monitored (run 'doh' to add)${NC}"
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
    
    # Extract directory paths from the config file
    local found_directories=false
    while IFS= read -r dir_path; do
        [[ -z "$dir_path" ]] && continue
        found_directories=true
        
        local threshold=$(get_config_value "threshold" "$dir_path")
        local name=$(get_config_value "name" "$dir_path")
        local git_profile=$(get_config_value "git_profile" "$dir_path")
        
        if [[ -d "$dir_path" ]]; then
            if [[ -n "$name" ]]; then
                local display_line="  ${GREEN}✓${NC} $name: $dir_path (threshold: $threshold"
            else
                local display_line="  ${GREEN}✓${NC} $dir_path (threshold: $threshold"
            fi
            if [[ -n "$git_profile" ]]; then
                display_line="$display_line, profile: $git_profile"
            fi
            echo -e "$display_line)"
        else
            if [[ -n "$name" ]]; then
                echo -e "  ${RED}✗${NC} $name: $dir_path (threshold: $threshold) - Directory not found"
            else
                echo -e "  ${RED}✗${NC} $dir_path (threshold: $threshold) - Directory not found"
            fi
        fi
    done < <(grep -o '"/[^"]*":' "$DOH_CONFIG_FILE" | tr -d '":')
    
    if [[ "$found_directories" == false ]]; then
        echo "No directories being monitored"
    fi
}

# Main execution
main() {
    local current_dir=$(pwd)
    local threshold="$DEFAULT_THRESHOLD"
    local action="add"
    local name=""
    
    # Handle exclusion commands
    if [[ "$1" == "ex" ]]; then
        shift
        case "$1" in
            "list")
                init_config
                list_exclusions
                exit 0
                ;;
            "add")
                local target_dir="${2:-$current_dir}"
                init_config
                add_exclusion "$target_dir"
                echo -e "${GREEN}✓ Added $target_dir to exclusions${NC}"
                exit 0
                ;;
            "rm"|"remove")
                local target_dir="${2:-$current_dir}"
                init_config
                remove_exclusion "$target_dir"
                echo -e "${GREEN}✓ Removed $target_dir from exclusions${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown exclusion command: $1${NC}"
                echo "Use: doh ex list|add|rm [path]"
                exit 1
                ;;
        esac
    fi
    
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
            -n|--name)
                name="$2"
                shift 2
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
            # Check if already monitored, show status instead of re-adding
            if is_monitored "$current_dir"; then
                echo -e "${YELLOW}Directory already monitored. Showing current status:${NC}"
                echo ""
                show_status
            elif is_excluded "$current_dir"; then
                local excluded_path=$(find_excluded_parent "$current_dir")
                if [[ "$excluded_path" == "$current_dir" ]]; then
                    echo -e "${RED}Directory is excluded from monitoring${NC}"
                    echo "Use 'doh ex rm' to remove from exclusions first"
                else
                    echo -e "${RED}Cannot monitor directory - parent directory is excluded${NC}"
                    echo "Parent directory '$excluded_path' is in the exclusions list"
                    echo "Options:"
                    echo "  1. Move current directory outside of '$excluded_path'"
                    echo "  2. Remove '$excluded_path' from exclusions: doh ex rm '$excluded_path'"
                fi
                exit 1
            elif [[ ! -d "$current_dir/.git" ]]; then
                echo -e "${RED}Current directory is not a git repository${NC}"
                echo "Use 'git init' to initialize a git repository first"
                exit 1
            else
                update_config "$current_dir" "$threshold" "$name"
                local display_name="${name:-$(basename "$current_dir")}"
                echo -e "${GREEN}✓ Added '$display_name' to monitoring${NC}"
                echo "  Path: $current_dir"
                echo "  Threshold: $threshold lines"
                echo ""
                echo "Current status:"
                show_status
            fi
            ;;
        "status")
            show_status
            ;;
        "remove")
            if is_monitored "$current_dir"; then
                remove_from_config "$current_dir"
                echo -e "${GREEN}✓ Removed $current_dir from monitoring${NC}"
            else
                echo -e "${YELLOW}Directory is not currently monitored${NC}"
            fi
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
