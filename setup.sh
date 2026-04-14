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

install_python_dependencies() {
    section "INSTALLING PYTHON DEPENDENCIES"

    log "Upgrading pip..."
    python3 -m pip install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG_FILE" > /dev/null

    PYTHON_PACKAGES=(
        "paho-mqtt"
        "adafruit-circuitpython-busio"
        "adafruit-circuitpython-sht31d"
        "adafruit-circuitpython-dht"
        "RPi.GPIO"
        "flask"
    )

    for pkg in "${PYTHON_PACKAGES[@]}"; do
        log "Installing Python package: $pkg..."
        python3 -m pip install "$pkg" 2>&1 | tee -a "$LOG_FILE" > /dev/null
        success "Installed: $pkg"
    done
}

build_sps30_driver() {
    section "BUILDING SPS30 DRIVER"

    if [ ! -f "$SCRIPT_DIR/c_sps30_i2c/libsps30.so" ]; then
        log "Building SPS30 driver..."
        cd "$SCRIPT_DIR/c_sps30_i2c"

        if [ -f "RPI_DRIVER_BUILD.md" ]; then
            # Extract and run build commands from documentation
            log "Extracting build commands from documentation..."
            # This is a simplified version - actual build varies by instructions
            if [ -f "Makefile" ]; then
                make clean
                make
                success "SPS30 driver built"
            else
                warn "SPS30 driver build instructions not found. See c_sps30_i2c/RPI_DRIVER_BUILD.md"
            fi
        else
            warn "SPS30 driver build documentation not found. Skipping driver build."
            warn "You may need to build manually: cd c_sps30_i2c && bash RPI_DRIVER_BUILD.md"
        fi

        cd "$SCRIPT_DIR"
    else
        success "SPS30 driver already built"
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

    # I2C Bus Scan
    log "Scanning I2C bus..."
    if python3 "$SCRIPT_DIR/test_sensors_unit.py" --scan 2>&1 | tee -a "$LOG_FILE"; then
        success "I2C bus scan completed"
    else
        warn "I2C bus scan failed. Check your connections."
    fi

    # Store results
    SENSOR_RESULTS_FILE="/tmp/sensor_test_results.txt"
    > "$SENSOR_RESULTS_FILE"

    # Test each sensor
    for sensor in sht3x sps30 dht11; do
        log "Testing $sensor..."
        if timeout 30 python3 "$SCRIPT_DIR/test_sensors_unit.py" --$sensor -n 1 2>&1 | tee -a "$LOG_FILE" > /tmp/${sensor}_test.txt; then
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

    log "Starting sensor_reader.py in background..."

    # Create a simple systemd user service or screen session
    if command -v systemctl &> /dev/null; then
        log "Creating systemd user service..."

        SERVICE_FILE="$HOME/.config/systemd/user/sps30-reader.service"
        mkdir -p "$(dirname "$SERVICE_FILE")"

        cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=SPS30 Sensor Data Reader
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {SCRIPT_DIR}/sensor_reader.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

        # Replace placeholder
        sed -i "s|{SCRIPT_DIR}|$SCRIPT_DIR|g" "$SERVICE_FILE"

        systemctl --user daemon-reload
        systemctl --user enable sps30-reader.service
        systemctl --user start sps30-reader.service

        if systemctl --user is-active sps30-reader.service &>/dev/null; then
            success "Sensor reader started as systemd service"
            success "View logs: journalctl --user -u sps30-reader.service -f"
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

    sleep 2
}

start_web_server() {
    section "STARTING WEB DASHBOARD"

    log "Starting Flask web server..."

    # Create systemd user service for web server
    if command -v systemctl &> /dev/null; then
        SERVICE_FILE="$HOME/.config/systemd/user/sps30-webserver.service"
        mkdir -p "$(dirname "$SERVICE_FILE")"

        cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=SPS30 Web Dashboard
After=network.target sps30-reader.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 {SCRIPT_DIR}/web_server.py --port 5000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

        sed -i "s|{SCRIPT_DIR}|$SCRIPT_DIR|g" "$SERVICE_FILE"

        systemctl --user daemon-reload
        systemctl --user enable sps30-webserver.service
        systemctl --user start sps30-webserver.service

        if systemctl --user is-active sps30-webserver.service &>/dev/null; then
            success "Web server started as systemd service"
            success "View logs: journalctl --user -u sps30-webserver.service -f"
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

    sleep 2
}

################################################################################
# Status & Summary
################################################################################

show_status() {
    section "SYSTEM STATUS"

    # Get Raspberry Pi IP
    PI_IP=$(hostname -I | awk '{print $1}')

    if [ -z "$PI_IP" ]; then
        PI_IP="<IP_ADDRESS>"
    fi

    echo ""
    echo -e "${GREEN}✓ Setup Complete!${NC}"
    echo ""
    echo "📊 Web Dashboard:"
    echo "   http://$PI_IP:5000"
    echo ""
    echo "📋 Data Collection:"
    echo "   $(systemctl --user is-active sps30-reader.service 2>/dev/null && echo '✓ Active' || echo '⚠ Check logs')"
    echo ""
    echo "📝 Useful Commands:"
    echo "   View sensor logs:    journalctl --user -u sps30-reader.service -f"
    echo "   View webserver logs: journalctl --user -u sps30-webserver.service -f"
    echo "   Stop services:       systemctl --user stop sps30-reader.service sps30-webserver.service"
    echo "   Restart services:    systemctl --user restart sps30-reader.service sps30-webserver.service"
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
    install_system_dependencies
    install_python_dependencies
    build_sps30_driver
    run_hardware_tests
    init_database
    start_sensor_reader
    start_web_server
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
        install_system_dependencies
        install_python_dependencies
        build_sps30_driver
        init_database
        start_sensor_reader
        start_web_server
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
