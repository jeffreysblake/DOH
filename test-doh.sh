#!/bin/bash

# test-doh.sh - Comprehensive test suite for doh system
# Run this script to validate all doh functionality

# Don't exit on errors - we want to capture and report them

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
TEST_BASE_DIR="/tmp/doh-test-$(date +%s)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOH_SCRIPT="$SCRIPT_DIR/doh"
ORIGINAL_DOH_CONFIG="$HOME/.doh"
TEST_DOH_CONFIG="$TEST_BASE_DIR/.doh"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Utility functions
log_test() {
    echo -e "${BLUE}[TEST $((++TESTS_RUN))] $1${NC}"
}

pass_test() {
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    ((TESTS_FAILED++))
}

cleanup() {
    echo -e "\n${YELLOW}Cleaning up test environment...${NC}"
    cd /
    rm -rf "$TEST_BASE_DIR" 2>/dev/null || true
    
    # Restore original config if it was backed up
    if [[ -d "$ORIGINAL_DOH_CONFIG.backup" ]]; then
        rm -rf "$ORIGINAL_DOH_CONFIG" 2>/dev/null || true
        mv "$ORIGINAL_DOH_CONFIG.backup" "$ORIGINAL_DOH_CONFIG"
    fi
}

# Setup test environment
setup_test_env() {
    echo -e "${BLUE}Setting up test environment...${NC}"
    
    # Create test directory
    mkdir -p "$TEST_BASE_DIR"
    cd "$TEST_BASE_DIR"
    
    # Backup existing doh config if it exists
    if [[ -d "$ORIGINAL_DOH_CONFIG" ]]; then
        mv "$ORIGINAL_DOH_CONFIG" "$ORIGINAL_DOH_CONFIG.backup"
    fi
    
    # Set HOME to test directory for doh config
    export HOME="$TEST_BASE_DIR"
    
    echo "Test environment ready at: $TEST_BASE_DIR"
}

# Test helper to run doh command
run_doh() {
    "$DOH_SCRIPT" "$@" 2>&1 || true
}

# Test helper to check if string exists in config
config_contains() {
    grep -q "$1" "$TEST_DOH_CONFIG/config.json" 2>/dev/null
}

# Test helper to get config value
get_test_config_value() {
    local key="$1"
    grep -o "\"$key\": *[^,}]*" "$TEST_DOH_CONFIG/config.json" | sed "s/\"$key\": *\([^,}]*\)/\1/" | tr -d '"'
}

# Initialize git repo for testing
init_test_repo() {
    local dir="$1"
    mkdir -p "$dir"
    cd "$dir"
    git init >/dev/null 2>&1
    git config user.name "Test User" >/dev/null 2>&1
    git config user.email "test@example.com" >/dev/null 2>&1
    echo "# Test repo" > README.md
    git add README.md >/dev/null 2>&1
    git commit -m "Initial commit" >/dev/null 2>&1
}

# Test 1: Basic initialization
test_initialization() {
    log_test "Basic initialization"
    
    # Create a dummy git repo to trigger config creation
    local init_dir="$TEST_BASE_DIR/init_test"
    init_test_repo "$init_dir"
    cd "$init_dir"
    run_doh --status >/dev/null 2>&1 || true
    
    if [[ -f "$TEST_DOH_CONFIG/config.json" ]]; then
        pass_test
    else
        fail_test "Config file not created"
    fi
}

# Test 2: Global git profile configuration
test_git_profile_config() {
    log_test "Global git profile configuration"
    
    # Check if git_profile field exists in global_settings
    if config_contains '"git_profile": ""'; then
        pass_test
    else
        fail_test "git_profile field not found in global_settings"
    fi
}

# Test 3: Adding directory to monitoring
test_add_directory() {
    log_test "Adding directory to monitoring"
    
    local test_dir="$TEST_BASE_DIR/project1"
    init_test_repo "$test_dir"
    cd "$test_dir"
    
    run_doh 30 -n "TestProject"
    
    if config_contains '"TestProject"' && config_contains '"threshold": 30'; then
        pass_test
    else
        fail_test "Directory not added correctly"
    fi
}

# Test 4: Smart behavior - show status for already monitored directory
test_smart_status() {
    log_test "Smart behavior for already monitored directory"
    
    local test_dir="$TEST_BASE_DIR/project1"
    cd "$test_dir"
    
    # Try to add again - should show status instead
    local output=$(run_doh 2>&1)
    
    if echo "$output" | grep -q "already monitored"; then
        pass_test
    else
        fail_test "Should show status for already monitored directory"
    fi
}

# Test 5: Exclusion system
test_exclusions() {
    log_test "Exclusion system"
    
    local exclude_dir="$TEST_BASE_DIR/excluded"
    mkdir -p "$exclude_dir"
    cd "$exclude_dir"
    
    # Add to exclusions
    run_doh ex add
    
    if config_contains '"exclusions"' && config_contains "$exclude_dir"; then
        pass_test
    else
        fail_test "Directory not added to exclusions"
    fi
}

# Test 6: Parent directory exclusion blocking
test_parent_exclusion() {
    log_test "Parent directory exclusion blocking"
    
    local parent_dir="$TEST_BASE_DIR/parent"
    local child_dir="$parent_dir/child"
    
    # Add parent to exclusions
    mkdir -p "$parent_dir"
    cd "$parent_dir"
    run_doh ex add
    
    # Try to monitor child
    init_test_repo "$child_dir"
    cd "$child_dir"
    
    local output=$(run_doh 2>&1)
    
    if echo "$output" | grep -q "parent directory is excluded"; then
        pass_test
    else
        fail_test "Should block monitoring when parent is excluded"
    fi
}

# Test 7: Directory naming system
test_naming_system() {
    log_test "Directory naming system"
    
    local test_dir="$TEST_BASE_DIR/project2"
    init_test_repo "$test_dir"
    cd "$test_dir"
    
    run_doh 25 -n "MyAwesomeProject"
    
    if config_contains '"MyAwesomeProject"'; then
        pass_test
    else
        fail_test "Named directory not configured correctly"
    fi
}

# Test 8: Status display with progress
test_status_display() {
    log_test "Status display with progress indicators"
    
    local test_dir="$TEST_BASE_DIR/project2"
    cd "$test_dir"
    
    # Add some changes
    echo "Some changes" >> test.txt
    git add test.txt
    
    local output=$(run_doh --status 2>&1)
    
    if echo "$output" | grep -q "Status:" && echo "$output" | grep -q "Progress:"; then
        pass_test
    else
        fail_test "Status display not working correctly"
    fi
}

# Test 9: Force commit functionality
test_force_commit() {
    log_test "Force commit functionality"
    
    local test_dir="$TEST_BASE_DIR/project2"
    cd "$test_dir"
    
    # Add some changes if not already present
    echo "More changes" >> test.txt
    
    local output=$(run_doh --force-commit 2>&1)
    
    if echo "$output" | grep -q "committed successfully"; then
        pass_test
    else
        fail_test "Force commit not working"
    fi
}

# Test 10: List monitored directories
test_list_directories() {
    log_test "List monitored directories"
    
    local output=$(run_doh --list 2>&1)
    
    if echo "$output" | grep -q "TestProject" && echo "$output" | grep -q "MyAwesomeProject"; then
        pass_test
    else
        fail_test "List command not showing monitored directories"
    fi
}

# Test 11: Remove directory from monitoring
test_remove_directory() {
    log_test "Remove directory from monitoring"
    
    local test_dir="$TEST_BASE_DIR/project1"
    cd "$test_dir"
    
    run_doh --remove
    
    if ! config_contains "$test_dir"; then
        pass_test
    else
        fail_test "Directory not removed from monitoring"
    fi
}

# Test 12: Remove from exclusions
test_remove_exclusion() {
    log_test "Remove from exclusions"
    
    local exclude_dir="$TEST_BASE_DIR/excluded"
    cd "$exclude_dir"
    
    run_doh ex rm
    
    # Check exclusions section doesn't contain this directory
    local exclusions_section=$(sed -n '/\"exclusions\": *{/,/}/p' "$TEST_DOH_CONFIG/config.json")
    
    if ! echo "$exclusions_section" | grep -q "$exclude_dir"; then
        pass_test
    else
        fail_test "Directory not removed from exclusions"
    fi
}

# Test 13: Config file integrity
test_config_integrity() {
    log_test "Config file JSON integrity"
    
    # Validate JSON syntax
    if python3 -m json.tool "$TEST_DOH_CONFIG/config.json" >/dev/null 2>&1; then
        pass_test
    else
        fail_test "Config file is not valid JSON"
    fi
}

# Test 14: Global git profile field persistence
test_git_profile_persistence() {
    log_test "Global git profile field persistence"
    
    # Add a test directory to ensure config updates work
    local test_dir="$TEST_BASE_DIR/profile_test"
    init_test_repo "$test_dir"
    cd "$test_dir"
    run_doh 50
    
    # Check git_profile field still exists and is empty
    local git_profile=$(get_test_config_value "git_profile")
    
    if [[ "$git_profile" == "" ]]; then
        pass_test
    else
        fail_test "git_profile field not preserved correctly: '$git_profile'"
    fi
}

# Main test execution
main() {
    echo -e "${BLUE}=== DOH System Test Suite ===${NC}"
    echo "Testing doh script: $DOH_SCRIPT"
    echo ""
    
    # Setup
    setup_test_env
    
    # Trap cleanup on exit
    trap cleanup EXIT
    
    # Run all tests
    test_initialization
    test_git_profile_config
    test_add_directory
    test_smart_status
    test_exclusions
    test_parent_exclusion
    test_naming_system
    test_status_display
    test_force_commit
    test_list_directories
    test_remove_directory
    test_remove_exclusion
    test_config_integrity
    test_git_profile_persistence
    
    # Results
    echo ""
    echo -e "${BLUE}=== Test Results ===${NC}"
    echo "Tests run: $TESTS_RUN"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 All tests passed! DOH system is working correctly.${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ $TESTS_FAILED test(s) failed. Please review the failures above.${NC}"
        exit 1
    fi
}

# Check dependencies
if ! command -v git >/dev/null 2>&1; then
    echo -e "${RED}Error: git is required for testing${NC}"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: python3 not found, JSON validation test will be skipped${NC}"
fi

# Run the tests
main "$@"
