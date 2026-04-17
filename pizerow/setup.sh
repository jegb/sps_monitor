#!/bin/bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
LOG_FILE="$SCRIPT_DIR/setup.log"
CONFIG_FILE="$SCRIPT_DIR/config.py"
CONFIG_TEMPLATE="$SCRIPT_DIR/config.py.example"
DATA_DIR="$SCRIPT_DIR/data"

log() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

section() {
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}============================================================${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}$1${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}============================================================${NC}" | tee -a "$LOG_FILE"
}

check_prerequisites() {
    section "CHECKING PREREQUISITES"

    if ! command -v python3 >/dev/null 2>&1; then
        error "python3 is not installed"
    fi

    success "Python found: $(python3 --version)"

    if grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        success "Running on Raspberry Pi"
    else
        warn "This does not look like a Raspberry Pi"
    fi

    if [ -e /dev/i2c-1 ]; then
        success "I2C bus /dev/i2c-1 is available"
    else
        warn "I2C bus /dev/i2c-1 is not available"
        warn "Enable it with: sudo raspi-config (Interface Options -> I2C)"
    fi
}

install_system_packages() {
    section "INSTALLING SYSTEM PACKAGES"

    log "Updating apt package lists"
    sudo apt-get update >>"$LOG_FILE" 2>&1

    local packages=(
        python3
        python3-pip
        python3-venv
        i2c-tools
        git
        mosquitto-clients
    )

    log "Installing: ${packages[*]}"
    sudo apt-get install -y "${packages[@]}" >>"$LOG_FILE" 2>&1
    success "System packages installed"
}

create_venv() {
    section "CREATING VIRTUAL ENVIRONMENT"

    if [ ! -d "$VENV_DIR" ]; then
        log "Creating venv at $VENV_DIR"
        python3 -m venv "$VENV_DIR" >>"$LOG_FILE" 2>&1
    else
        success "Using existing venv at $VENV_DIR"
    fi

    log "Upgrading pip tooling"
    "$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel >>"$LOG_FILE" 2>&1

    log "Installing Python dependencies"
    "$VENV_DIR/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt" >>"$LOG_FILE" 2>&1
    success "Python dependencies installed"
}

prepare_local_files() {
    section "PREPARING LOCAL FILES"

    mkdir -p "$DATA_DIR/history" "$DATA_DIR/queue"
    success "Ensured local data directories under $DATA_DIR"

    if [ ! -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_TEMPLATE" "$CONFIG_FILE"
        warn "Created $CONFIG_FILE from template"
        warn "Edit MQTT_HOST and any sensor settings before running the node"
    else
        success "Keeping existing config at $CONFIG_FILE"
    fi
}

run_tests() {
    section "RUNNING LOCAL TESTS"

    (
        cd "$REPO_ROOT"
        "$VENV_DIR/bin/python" -m unittest discover -s pizerow/tests -q
    ) >>"$LOG_FILE" 2>&1

    success "Host-side tests passed"
}

print_next_steps() {
    section "NEXT STEPS"

    echo "1. Edit: $CONFIG_FILE" | tee -a "$LOG_FILE"
    echo "2. Verify sensors: i2cdetect -y 1" | tee -a "$LOG_FILE"
    echo "3. Run the node:" | tee -a "$LOG_FILE"
    echo "   cd $REPO_ROOT" | tee -a "$LOG_FILE"
    echo "   $VENV_DIR/bin/python -m pizerow.main" | tee -a "$LOG_FILE"
    echo "4. Optional boot service:" | tee -a "$LOG_FILE"
    echo "   sudo $SCRIPT_DIR/install_service.sh" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "Setup log: $LOG_FILE" | tee -a "$LOG_FILE"
}

main() {
    : >"$LOG_FILE"
    check_prerequisites
    install_system_packages
    create_venv
    prepare_local_files
    run_tests
    print_next_steps
}

main "$@"
