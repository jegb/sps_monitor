#!/bin/bash

################################################################################
#                   SPS30 AIR QUALITY MONITOR - SETUP SCRIPT                   #
#                                                                              #
# Automated installation, testing, and deployment                             #
# Downloads repo → Installs deps → Validates hardware → Starts services       #
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/setup.log"
VENV_DIR="$SCRIPT_DIR/venv"

################################################################################
# Logging Functions
################################################################################

log() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

section() {
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}$1${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
}

################################################################################
# System Checks
################################################################################

check_prerequisites() {
    section "CHECKING PREREQUISITES"

    # Check if running on Raspberry Pi
    if ! grep -q "Raspberry" /proc/device-tree/model 2>/dev/null; then
        warn "Not running on Raspberry Pi (detected: $(cat /proc/device-tree/model 2>/dev/null || echo 'unknown'))"
        warn "This script is optimized for Raspberry Pi. Some features may not work."
    else
        success "Running on Raspberry Pi"
    fi

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed. Install with: sudo apt-get install python3 python3-pip"
    fi
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    success "Python 3 found: $PYTHON_VERSION"

    # Check git
    if ! command -v git &> /dev/null; then
        warn "Git not installed. Install with: sudo apt-get install git"
    else
        success "Git found"
    fi

    # Check I2C
    if [ ! -e /dev/i2c-1 ]; then
        warn "I2C not detected. Enable with: sudo raspi-config (Interfacing Options → I2C)"
        warn "Continuing anyway - you can enable I2C and re-run tests."
    else
        success "I2C detected"
    fi
}

################################################################################
# Dependency Installation
################################################################################

install_system_dependencies() {
    section "INSTALLING SYSTEM DEPENDENCIES"

    log "Updating package lists..."
    sudo apt-get update 2>&1 | tee -a "$LOG_FILE" > /dev/null

    PACKAGES=(
        "python3-dev"
        "python3-pip"
        "libssl-dev"
        "libffi-dev"
        "i2c-tools"
        "libi2c-dev"
        "build-essential"
        "git"
        "libgpiod3"
    )

    for pkg in "${PACKAGES[@]}"; do
        if dpkg -l | grep -q "^ii  $pkg"; then
            success "$pkg already installed"
        else
            log "Installing $pkg..."
            sudo apt-get install -y "$pkg" 2>&1 | tee -a "$LOG_FILE" > /dev/null
            success "$pkg installed"
        fi
    done
}

create_venv() {
    section "CREATING PYTHON VIRTUAL ENVIRONMENT"

    if [ -d "$VENV_DIR" ]; then
        warn "Virtual environment already exists at $VENV_DIR"
        log "Using existing virtual environment"
        return
    fi

    log "Creating virtual environment at $VENV_DIR..."
    if python3 -m venv "$VENV_DIR" 2>&1 | tee -a "$LOG_FILE"; then
        success "Virtual environment created"
    else
        error "Failed to create virtual environment"
    fi
}

install_python_dependencies() {
    section "INSTALLING PYTHON DEPENDENCIES"

    VENV_PIP="$VENV_DIR/bin/pip"

    log "Upgrading pip in venv..."
    "$VENV_PIP" install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG_FILE" > /dev/null

    PYTHON_PACKAGES=(
        "paho-mqtt"
        "adafruit-blinka"
        "adafruit-circuitpython-busio"
        "adafruit-circuitpython-sht31d"
        "adafruit-circuitpython-dht"
        "RPi.GPIO"
        "flask"
        "smbus2"
    )

    for pkg in "${PYTHON_PACKAGES[@]}"; do
        if "$VENV_PIP" show "$pkg" &>/dev/null; then
            success "$pkg already installed"
        else
            log "Installing Python package: $pkg..."
            "$VENV_PIP" install "$pkg" 2>&1 | tee -a "$LOG_FILE" > /dev/null
            success "Installed: $pkg"
        fi
    done
}

build_sps30_driver() {
    section "BUILDING SPS30 DRIVER"

    log "Running SPS30 library compilation script..."
    if "$SCRIPT_DIR/compile_sps30.sh" 2>&1 | tee -a "$LOG_FILE"; then
        success "SPS30 driver built successfully"
    else
        error "SPS30 driver build failed. Run './compile_sps30.sh' manually to debug."
    fi
}

################################################################################
# Hardware Testing
################################################################################

run_hardware_tests() {
    section "RUNNING HARDWARE VALIDATION TESTS"

    if [ ! -f "$SCRIPT_DIR/test_sensors_unit.py" ]; then
        error "test_sensors_unit.py not found!"
    fi

    VENV_PYTHON="$VENV_DIR/bin/python3"

    # I2C Bus Scan
    log "Scanning I2C bus..."
    if "$VENV_PYTHON" "$SCRIPT_DIR/test_sensors_unit.py" --scan 2>&1 | tee -a "$LOG_FILE"; then
        success "I2C bus scan completed"
    else
        warn "I2C bus scan failed. Check your connections."
    fi

    # Store results
    SENSOR_RESULTS_FILE="/tmp/sensor_test_results.txt"
    > "$SENSOR_RESULTS_FILE"

    # Test each sensor
    SENSORS_TO_TEST="sht3x sps30 dht11"

    # Check if PPD42 is enabled in config
    if grep -q "PPD42_ENABLED = True" "$SCRIPT_DIR/config.py"; then
        SENSORS_TO_TEST="$SENSORS_TO_TEST ppd42"
    fi

    for sensor in $SENSORS_TO_TEST; do
        log "Testing $sensor..."
        if [ "$sensor" = "ppd42" ]; then
            # PPD42 needs longer sample duration
            timeout_duration=40
        else
            timeout_duration=30
        fi

        if timeout $timeout_duration "$VENV_PYTHON" "$SCRIPT_DIR/test_sensors_unit.py" --$sensor -n 1 2>&1 | tee -a "$LOG_FILE" > /tmp/${sensor}_test.txt; then
            if grep -q "PASSED" /tmp/${sensor}_test.txt; then
                success "$sensor test PASSED"
                echo "$sensor=PASS" >> "$SENSOR_RESULTS_FILE"
            else
                warn "$sensor test did not pass"
                echo "$sensor=FAIL" >> "$SENSOR_RESULTS_FILE"
            fi
        else
            warn "$sensor test timed out or errored"
            echo "$sensor=FAIL" >> "$SENSOR_RESULTS_FILE"
        fi
    done

    # Summary
    PASS_COUNT=$(grep -c "=PASS" "$SENSOR_RESULTS_FILE" 2>/dev/null || echo 0)
    echo ""
    log "Test Summary: $PASS_COUNT sensor(s) connected and responding"

    if [ "$PASS_COUNT" -eq 0 ]; then
        error "No sensors detected! Please check your hardware connections."
    else
        success "At least one sensor validated. Proceeding with setup."
    fi
}

################################################################################
# Database Initialization
################################################################################

init_database() {
    section "INITIALIZING DATABASE"

    if [ -f "$SCRIPT_DIR/sps30_data.db" ]; then
        warn "Database already exists at $SCRIPT_DIR/sps30_data.db"
        read -p "Overwrite existing database? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Keeping existing database"
            return
        fi
    fi

    log "Initializing database..."
    if python3 "$SCRIPT_DIR/init_sps30_db.py" 2>&1 | tee -a "$LOG_FILE"; then
        success "Database initialized"
    else
        error "Failed to initialize database"
    fi
}

################################################################################
# Service Management
################################################################################

start_sensor_reader() {
    section "STARTING SENSOR DATA COLLECTION"

    log "Installing sensor reader as system-level service..."

    if command -v systemctl &> /dev/null; then
        # Copy service file to system location (uses repo file with correct naming)
        log "Copying sps30_reader.service to /etc/systemd/system/..."
        sudo cp "$SCRIPT_DIR/sps30_reader.service" /etc/systemd/system/

        sudo systemctl daemon-reload
        sudo systemctl enable sps30_reader.service
        sudo systemctl start sps30_reader.service

        sleep 2

        if sudo systemctl is-active sps30_reader.service &>/dev/null; then
            success "Sensor reader started as system service"
            success "View logs: sudo journalctl -u sps30_reader.service -f"
        else
            error "Failed to start sensor reader service"
        fi

    else
        # Fallback: Start in background
        log "Starting sensor_reader.py in background (no systemd available)..."
        nohup python3 "$SCRIPT_DIR/sensor_reader.py" > "$SCRIPT_DIR/sensor_reader.log" 2>&1 &
        READER_PID=$!
        success "Sensor reader started with PID $READER_PID"
        log "Logs at: $SCRIPT_DIR/sensor_reader.log"
    fi
}

start_web_server() {
    section "STARTING WEB DASHBOARD"

    log "Installing web server as system-level service..."

    if command -v systemctl &> /dev/null; then
        # Copy service file to system location (uses repo file with correct naming)
        log "Copying sps30_webserver.service to /etc/systemd/system/..."
        sudo cp "$SCRIPT_DIR/sps30_webserver.service" /etc/systemd/system/

        sudo systemctl daemon-reload
        sudo systemctl enable sps30_webserver.service
        sudo systemctl start sps30_webserver.service

        sleep 2

        if sudo systemctl is-active sps30_webserver.service &>/dev/null; then
            success "Web server started as system service"
            success "View logs: sudo journalctl -u sps30_webserver.service -f"
        else
            error "Failed to start web server"
        fi

    else
        log "Starting web_server.py in background..."
        nohup python3 "$SCRIPT_DIR/web_server.py" --port 5000 > "$SCRIPT_DIR/web_server.log" 2>&1 &
        WEB_PID=$!
        success "Web server started with PID $WEB_PID"
        log "Logs at: $SCRIPT_DIR/web_server.log"
    fi
}

################################################################################
# System Configuration
################################################################################

configure_hostname() {
    section "CONFIGURING HOSTNAME"

    HOSTNAME="sps-station"
    CURRENT_HOSTNAME=$(hostname)
    HOSTNAME_CHANGED=false

    if [ "$CURRENT_HOSTNAME" = "$HOSTNAME" ]; then
        success "Hostname already set to $HOSTNAME"
    else
        log "Setting hostname to $HOSTNAME..."

        # Check if we need sudo
        if [ "$EUID" -ne 0 ]; then
            log "Requesting sudo access to set hostname..."
            sudo hostnamectl set-hostname "$HOSTNAME" 2>&1 | tee -a "$LOG_FILE" > /dev/null
        else
            hostnamectl set-hostname "$HOSTNAME" 2>&1 | tee -a "$LOG_FILE" > /dev/null
        fi
        success "Hostname set to $HOSTNAME"
        HOSTNAME_CHANGED=true
    fi

    # Update /etc/hosts to resolve hostname locally (fixes sudo warnings)
    log "Updating /etc/hosts..."
    if ! grep -q "127.0.1.1.*$HOSTNAME" /etc/hosts; then
        if [ "$EUID" -ne 0 ]; then
            echo "127.0.1.1 $HOSTNAME" | sudo tee -a /etc/hosts > /dev/null 2>&1
        else
            echo "127.0.1.1 $HOSTNAME" >> /etc/hosts
        fi
        success "Added $HOSTNAME to /etc/hosts"
    else
        success "/etc/hosts already configured"
    fi

    # Verify avahi-daemon is installed for mDNS
    if ! command -v avahi-daemon &> /dev/null; then
        warn "avahi-daemon not installed. Installing for mDNS support..."
        sudo apt-get install -y avahi-daemon 2>&1 | tee -a "$LOG_FILE" > /dev/null
        sudo systemctl enable avahi-daemon
        sudo systemctl start avahi-daemon
    fi

    success "Access dashboard at: http://$HOSTNAME.local:5000"
    if [ "$HOSTNAME_CHANGED" = true ]; then
        warn "Note: Reboot may be required for hostname change to take full effect"
    fi
}

setup_maintenance_cron() {
    section "SETTING UP DATABASE MAINTENANCE"

    CRON_SCHEDULE="0 2 * * *"  # 2 AM daily
    CRON_CMD="cd $SCRIPT_DIR && $SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/db_maintenance.py"
    CRON_JOB="$CRON_SCHEDULE $CRON_CMD"
    CRON_ID="# SPS30 Database Maintenance"

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "db_maintenance.py"; then
        success "Database maintenance cron job already configured"
        return
    fi

    # Add cron job
    log "Adding daily database maintenance to crontab..."
    (crontab -l 2>/dev/null || echo "") | {
        cat
        echo "$CRON_ID"
        echo "$CRON_JOB"
    } | crontab -

    if crontab -l 2>/dev/null | grep -q "db_maintenance.py"; then
        success "Database maintenance cron job installed"
        log "Schedule: Daily at 2:00 AM"
        log "Retention: 90 days (3 months)"
        log "View cron log: grep CRON /var/log/syslog"
    else
        warn "Failed to install cron job. Install manually:"
        log "  crontab -e"
        log "  Then add: $CRON_JOB"
    fi
}

enable_service_autostart() {
    section "ENABLING AUTO-START ON BOOT"

    log "System-level services are configured to auto-start on boot via systemd"
    success "sps30_reader.service enabled for multi-user.target"
    success "sps30_webserver.service enabled for multi-user.target"
    log "Services will start automatically after next reboot, no login required"
}

################################################################################
# Status & Summary
################################################################################

show_status() {
    section "SYSTEM STATUS"

    # Get Raspberry Pi IP and hostname
    PI_IP=$(hostname -I | awk '{print $1}')
    PI_HOSTNAME=$(hostname)

    if [ -z "$PI_IP" ]; then
        PI_IP="<IP_ADDRESS>"
    fi

    echo ""
    echo -e "${GREEN}✓ Setup Complete!${NC}"
    echo ""
    echo "📊 Web Dashboard:"
    echo "   http://$PI_HOSTNAME.local:5000  (recommended)"
    echo "   http://$PI_IP:5000"
    echo ""
    echo "📋 Data Collection:"
    echo "   $(sudo systemctl is-active sps30_reader.service 2>/dev/null && echo '✓ Active' || echo '⚠ Check logs')"
    echo ""
    echo "📝 Useful Commands:"
    echo "   View sensor logs:    sudo journalctl -u sps30_reader.service -f"
    echo "   View webserver logs: sudo journalctl -u sps30_webserver.service -f"
    echo "   Stop services:       sudo systemctl stop sps30_reader.service sps30_webserver.service"
    echo "   Restart services:    sudo systemctl restart sps30_reader.service sps30_webserver.service"
    echo "   Run tests:           python3 $SCRIPT_DIR/test_sensors_unit.py --all"
    echo ""
    echo "📚 Documentation:"
    echo "   Testing Guide:      cat $SCRIPT_DIR/TESTING.md"
    echo "   Quick Reference:    cat $SCRIPT_DIR/TEST_QUICK_REFERENCE.md"
    echo "   Configuration:      nano $SCRIPT_DIR/config.py"
    echo ""
}

################################################################################
# Main Flow
################################################################################

main() {
    echo ""
    echo -e "${BLUE}"
    cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║   SPS30 Air Quality Monitor - Automated Setup              ║
║   GitHub: https://github.com/your-username/sps_monitor    ║
╚════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    log "Setup started at $(date)"
    log "Working directory: $SCRIPT_DIR"

    # Run setup phases
    check_prerequisites
    configure_hostname
    install_system_dependencies
    create_venv
    install_python_dependencies
    build_sps30_driver
    run_hardware_tests
    init_database
    start_sensor_reader
    start_web_server
    setup_maintenance_cron
    enable_service_autostart
    show_status

    success "Setup completed successfully!"
    log "Setup finished at $(date)"
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTION]

Automated setup script for SPS30 Air Quality Monitor

Options:
  (no args)        Run full setup (install, test, deploy)
  --help           Show this help message
  --test-only      Run tests only (no installation/deployment)
  --skip-tests     Install and deploy, skip hardware tests
  --status         Show current system status

Examples:
  $0                    # Full setup
  $0 --test-only        # Validate hardware only
  $0 --skip-tests       # Install & deploy (skip tests)

EOF
}

# Parse arguments
case "${1:-}" in
    --help)
        usage
        exit 0
        ;;
    --test-only)
        section "HARDWARE TESTING ONLY"
        run_hardware_tests
        exit 0
        ;;
    --skip-tests)
        log "Skipping hardware tests..."
        check_prerequisites
        configure_hostname
        install_system_dependencies
        create_venv
        install_python_dependencies
        build_sps30_driver
        init_database
        start_sensor_reader
        start_web_server
        setup_maintenance_cron
        enable_service_autostart
        show_status
        exit 0
        ;;
    --status)
        show_status
        exit 0
        ;;
    "")
        main
        ;;
    *)
        echo "Unknown option: $1"
        usage
        exit 1
        ;;
esac
