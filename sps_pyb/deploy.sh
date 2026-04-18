#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCAL_FLASH_DIR="$SCRIPT_DIR/flash"
DEFAULT_MPREMOTE="$REPO_ROOT/.venv-tools/bin/mpremote"

MPREMOTE="${MPREMOTE:-$DEFAULT_MPREMOTE}"
DEVICE="${MPREMOTE_DEVICE:-auto}"
UPLOAD_CONFIG=1
CLEAN_STALE=0

usage() {
    cat <<'EOF'
Usage: ./sps_pyb/deploy.sh [--device <id>] [--no-config] [--clean-stale]

Options:
  --device <id>     mpremote device selector (default: auto)
  --no-config       skip uploading sps_pyb/flash/config.py
  --clean-stale     remove a mistaken nested /flash/flash tree after deploy

Environment overrides:
  MPREMOTE          path to mpremote executable
  MPREMOTE_DEVICE   default device selector
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --device)
            DEVICE="${2:-}"
            shift 2
            ;;
        --no-config)
            UPLOAD_CONFIG=0
            shift
            ;;
        --clean-stale)
            CLEAN_STALE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ -z "$DEVICE" ]]; then
    echo "Missing mpremote device selector" >&2
    exit 1
fi

if [[ ! -x "$MPREMOTE" ]]; then
    if command -v mpremote >/dev/null 2>&1; then
        MPREMOTE="$(command -v mpremote)"
    else
        echo "mpremote not found. Expected $DEFAULT_MPREMOTE or mpremote in PATH." >&2
        exit 1
    fi
fi

if [[ ! -d "$LOCAL_FLASH_DIR" ]]; then
    echo "Missing local flash tree at $LOCAL_FLASH_DIR" >&2
    exit 1
fi

mp() {
    "$MPREMOTE" connect "$DEVICE" "$@"
}

remote_mkdir() {
    if ! mp mkdir "$1" >/dev/null 2>&1; then
        :
    fi
}

copy_file() {
    local src="$1"
    local dest="$2"
    echo "copy $src -> $dest"
    mp cp "$src" "$dest"
}

echo "Using mpremote: $MPREMOTE"
echo "Target device: $DEVICE"
echo "Local flash dir: $LOCAL_FLASH_DIR"

echo "Ensuring boot stays on internal flash"
mp exec "open('/flash/SKIPSD','a').close()"

echo "Ensuring remote directories"
remote_mkdir :/flash/lib
remote_mkdir :/flash/lib/app
remote_mkdir :/flash/lib/sensors
remote_mkdir :/flash/lib/umqtt

while IFS= read -r -d '' file; do
    rel="${file#$LOCAL_FLASH_DIR/}"

    case "$rel" in
        __pycache__/*|*/__pycache__/*|*.pyc|config.py.example)
            continue
            ;;
        config.py)
            if [[ "$UPLOAD_CONFIG" -ne 1 ]]; then
                continue
            fi
            ;;
    esac

    copy_file "$file" ":/flash/$rel"
done < <(find "$LOCAL_FLASH_DIR" -type f -print0 | sort -z)

if [[ "$UPLOAD_CONFIG" -eq 1 && ! -f "$LOCAL_FLASH_DIR/config.py" ]]; then
    echo "warning: $LOCAL_FLASH_DIR/config.py not found; board config.py was not updated" >&2
fi

if mp ls :/flash/flash >/dev/null 2>&1; then
    if [[ "$CLEAN_STALE" -eq 1 ]]; then
        echo "Removing stale nested /flash/flash tree"
        mp rm -r :/flash/flash
    else
        echo "warning: stale /flash/flash tree still exists; rerun with --clean-stale to remove it" >&2
    fi
fi

echo "Soft-resetting board"
mp soft-reset

echo "Deployment complete"
echo "Verify with:"
echo "  $MPREMOTE connect $DEVICE ls :/flash"
echo "  $MPREMOTE connect $DEVICE cat :/flash/config.py"
echo "  $MPREMOTE connect $DEVICE exec \"import mock_publish; mock_publish.run_once()\""
