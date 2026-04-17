#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UNIT_PATH="/etc/systemd/system/pizerow.service"
RUN_USER="${SUDO_USER:-${USER}}"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run with sudo: sudo ./pizerow/install_service.sh"
    exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Missing virtualenv interpreter at $PYTHON_BIN"
    echo "Run ./pizerow/setup.sh first."
    exit 1
fi

cat >"$UNIT_PATH" <<EOF
[Unit]
Description=Pi Zero SPS30/SHT3x MQTT Publisher
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$REPO_ROOT
Environment=PYTHONPATH=$REPO_ROOT
ExecStart=$PYTHON_BIN -m pizerow.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now pizerow

echo "Installed $UNIT_PATH"
systemctl status pizerow --no-pager
