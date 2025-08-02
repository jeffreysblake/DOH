#!/bin/bash

# Debug script to reproduce JSON corruption issue

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOH_SCRIPT="$SCRIPT_DIR/doh"

# Create isolated test environment
TEST_BASE_DIR="/tmp/doh-json-debug-$(date +%s)"
mkdir -p "$TEST_BASE_DIR"
export HOME="$TEST_BASE_DIR"

echo "Test environment: $TEST_BASE_DIR"

# Initialize test repos
for i in {1..3}; do
    mkdir -p "$TEST_BASE_DIR/repo$i"
    cd "$TEST_BASE_DIR/repo$i"
    git init >/dev/null 2>&1
    git config user.name "Test User"
    git config user.email "test@example.com"
    echo "# Repo $i" > README.md
    git add README.md >/dev/null 2>&1
    git commit -m "Initial commit" >/dev/null 2>&1
done

echo "Created test repositories"

# Rapid operations that might corrupt JSON
cd "$TEST_BASE_DIR/repo1"
echo "=== Adding repo1 ==="
$DOH_SCRIPT 25 -n "repo1"
echo "JSON after adding repo1:"
python3 -m json.tool "$TEST_BASE_DIR/.doh/config.json" || echo "INVALID JSON!"

cd "$TEST_BASE_DIR/repo2" 
echo "=== Adding repo2 ==="
$DOH_SCRIPT 35 -n "repo2"
echo "JSON after adding repo2:"
python3 -m json.tool "$TEST_BASE_DIR/.doh/config.json" || echo "INVALID JSON!"

echo "=== Adding to exclusions ==="
mkdir -p "$TEST_BASE_DIR/excluded"
cd "$TEST_BASE_DIR/excluded"
$DOH_SCRIPT ex add
echo "JSON after exclusion:"
python3 -m json.tool "$TEST_BASE_DIR/.doh/config.json" || echo "INVALID JSON!"

echo "=== Removing from exclusions ==="
$DOH_SCRIPT ex rm
echo "JSON after exclusion removal:"
python3 -m json.tool "$TEST_BASE_DIR/.doh/config.json" || echo "INVALID JSON!"

cd "$TEST_BASE_DIR/repo3"
echo "=== Adding repo3 ==="
$DOH_SCRIPT 45 -n "repo3"
echo "JSON after adding repo3:"
python3 -m json.tool "$TEST_BASE_DIR/.doh/config.json" || echo "INVALID JSON!"

echo "=== Removing repo1 ==="
cd "$TEST_BASE_DIR/repo1"
$DOH_SCRIPT --remove
echo "JSON after removing repo1:"
python3 -m json.tool "$TEST_BASE_DIR/.doh/config.json" || echo "INVALID JSON!"

echo "=== Final JSON content ==="
cat "$TEST_BASE_DIR/.doh/config.json"

# Cleanup
cd /
rm -rf "$TEST_BASE_DIR"
