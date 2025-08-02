#!/bin/bash
# systemd-setup.sh - Set up DOH daemon as a systemd service

set -e

USER_NAME="${SUDO_USER:-$USER}"
SERVICE_NAME="doh-daemon@${USER_NAME}.service"
SERVICE_FILE="/etc/systemd/system/doh-daemon@.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}${BOLD}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

main() {
    echo -e "${BOLD}DOH Systemd Service Setup${NC}"
    echo "Setting up DOH daemon as a systemd service for user: $USER_NAME"
    echo
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root or with sudo"
    fi
    
    # Check if doh is installed
    if ! command -v doh &> /dev/null; then
        print_error "DOH is not installed. Please run 'sudo ./install.sh' first"
    fi
    
    # Check if systemd is available
    if ! command -v systemctl &> /dev/null; then
        print_error "systemd is not available on this system. Use cron-setup.sh instead"
    fi
    
    print_step "Installing systemd service file"
    
    # Copy service file
    if [[ ! -f "doh-daemon@.service" ]]; then
        print_error "Service file 'doh-daemon@.service' not found in current directory"
    fi
    
    cp "doh-daemon@.service" "$SERVICE_FILE"
    print_success "Service file installed to $SERVICE_FILE"
    
    print_step "Configuring systemd service"
    
    # Reload systemd
    systemctl daemon-reload
    print_success "Systemd configuration reloaded"
    
    # Test the service configuration
    if systemctl cat "$SERVICE_NAME" &> /dev/null; then
        print_success "Service configuration valid"
    else
        print_error "Service configuration invalid"
    fi
    
    print_step "Testing service (dry run)"
    
    # Test daemon once as the user
    if sudo -u "$USER_NAME" doh daemon --once --verbose; then
        print_success "Daemon test successful"
    else
        print_warning "Daemon test had issues - check configuration"
    fi
    
    echo
    echo -e "${GREEN}${BOLD}Systemd service setup complete!${NC}"
    echo
    echo "To manage the DOH daemon service:"
    echo
    echo -e "${BLUE}Start the service:${NC}"
    echo "  sudo systemctl start $SERVICE_NAME"
    echo
    echo -e "${BLUE}Enable auto-start on boot:${NC}"
    echo "  sudo systemctl enable $SERVICE_NAME"
    echo
    echo -e "${BLUE}Check service status:${NC}"
    echo "  sudo systemctl status $SERVICE_NAME"
    echo
    echo -e "${BLUE}View logs:${NC}"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo -e "${BLUE}Stop the service:${NC}"
    echo "  sudo systemctl stop $SERVICE_NAME"
    echo
    echo -e "${BLUE}Disable auto-start:${NC}"
    echo "  sudo systemctl disable $SERVICE_NAME"
    echo
    echo -e "${YELLOW}Note: The service runs as user '$USER_NAME' and monitors directories in their ~/.doh/ config${NC}"
    echo
    echo "To add directories to monitoring:"
    echo "  sudo -u $USER_NAME doh add [directory]"
    echo
    echo "To check what's being monitored:"
    echo "  sudo -u $USER_NAME doh list"
}

main "$@"
