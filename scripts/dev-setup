#!/bin/bash
# DOH Development Setup Script
# Sets up a local virtual environment for development and testing

set -e

# Configuration
VENV_DIR="venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}${BOLD}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

main() {
    echo -e "${BOLD}DOH Development Setup${NC}"
    echo "Setting up local development environment"
    echo
    
    print_step "Creating virtual environment"
    if [[ ! -d "$VENV_DIR" ]]; then
        python3 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi
    
    print_step "Upgrading pip"
    "$VENV_DIR/bin/pip" install --upgrade pip
    
    print_step "Installing package in development mode"
    "$VENV_DIR/bin/pip" install -e .
    
    print_step "Installing development dependencies"
    "$VENV_DIR/bin/pip" install pytest
    
    print_success "Development environment ready!"
    echo
    echo "To use the development version:"
    echo "  source venv/bin/activate"
    echo "  doh --help"
    echo
    echo "Or run directly:"
    echo "  ./venv/bin/python -m doh.cli --help"
    echo
    echo "To run tests:"
    echo "  ./venv/bin/pytest"
    echo
    echo "To deactivate:"
    echo "  deactivate"
}

main "$@"
