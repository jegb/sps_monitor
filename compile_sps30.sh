#!/bin/bash
# Compile SPS30 I2C library for the current architecture

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/c_sps30_i2c"
SOURCE_DIR="$HOME/.cache/embedded-sps"

echo "=========================================="
echo "SPS30 Library Compiler"
echo "=========================================="

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Check if library already exists
if [ -f "$LIB_DIR/libsps30.so" ]; then
    echo "Existing library found:"
    file "$LIB_DIR/libsps30.so"

    # Verify it's the correct architecture
    if file "$LIB_DIR/libsps30.so" | grep -q "$ARCH"; then
        echo "✓ Library is already compiled for $ARCH"
        read -p "Recompile anyway? (y/n): " recompile
        if [ "$recompile" != "y" ]; then
            echo "Skipping compilation."
            exit 0
        fi
    else
        echo "⚠️  Library is for wrong architecture, recompiling..."
    fi
fi

# Clone source if needed
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Cloning Sensirion embedded-sps repository..."
    git clone https://github.com/Sensirion/embedded-sps.git "$SOURCE_DIR"
fi

# Initialize submodules
echo "Initializing submodules..."
cd "$SOURCE_DIR"
git submodule update --init --recursive

# Compile
echo "Compiling SPS30 library for $ARCH..."
cd "$SOURCE_DIR/sps30-i2c"

gcc -fPIC -shared -o libsps30.so \
    sps30.c \
    ../embedded-common/sensirion_common.c \
    ../embedded-common/hw_i2c/sensirion_hw_i2c_implementation.c \
    ../sps-common/sps_git_version.c \
    -I. -I../embedded-common/hw_i2c -I../embedded-common -I../sps-common

# Verify compilation
if [ ! -f libsps30.so ]; then
    echo "✗ Compilation failed!"
    exit 1
fi

echo ""
echo "Compiled library info:"
file libsps30.so

# Copy to project
echo ""
echo "Installing library to $LIB_DIR..."
cp libsps30.so "$LIB_DIR/"

echo ""
echo "✓ SPS30 library compiled successfully!"
echo "Location: $LIB_DIR/libsps30.so"
