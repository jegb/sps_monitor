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

# List repository structure for debugging
echo "Repository structure:"
ls -la "$SOURCE_DIR/"

# Check if required files exist
echo ""
echo "Checking for required source files..."
if [ ! -d "$SOURCE_DIR/sps30-i2c" ]; then
    echo "✗ sps30-i2c directory not found!"
    exit 1
fi

if [ ! -d "$SOURCE_DIR/sps-common" ]; then
    echo "✗ sps-common directory not found!"
    echo "Directory contents:"
    ls -la "$SOURCE_DIR/"
    exit 1
fi

if [ ! -f "$SOURCE_DIR/sps-common/sps_git_version.c" ]; then
    echo "✗ sps_git_version.c not found in sps-common!"
    echo "sps-common contents:"
    ls -la "$SOURCE_DIR/sps-common/"
    exit 1
fi

echo "✓ All required source files found"

# Compile
echo "Compiling SPS30 library for $ARCH..."
cd "$SOURCE_DIR/sps30-i2c"

# Check if sps_git_version.c needs to be generated
if [ ! -f "../sps-common/sps_git_version.c" ]; then
    echo "sps_git_version.c not found, attempting to generate..."

    # Try using the Makefile to generate it
    if [ -f "../Makefile" ]; then
        cd ..
        make sps-common/sps_git_version.c 2>/dev/null || true
        cd sps30-i2c
    fi

    # If still not found, compile without it
    if [ ! -f "../sps-common/sps_git_version.c" ]; then
        echo "Compiling without sps_git_version.c..."
        gcc -fPIC -shared -o libsps30.so \
            sps30.c \
            ../embedded-common/sensirion_common.c \
            ../embedded-common/hw_i2c/sensirion_hw_i2c_implementation.c \
            -I. -I../embedded-common/hw_i2c -I../embedded-common -I../sps-common
    else
        echo "Using generated sps_git_version.c"
        gcc -fPIC -shared -o libsps30.so \
            sps30.c \
            ../embedded-common/sensirion_common.c \
            ../embedded-common/hw_i2c/sensirion_hw_i2c_implementation.c \
            ../sps-common/sps_git_version.c \
            -I. -I../embedded-common/hw_i2c -I../embedded-common -I../sps-common
    fi
else
    gcc -fPIC -shared -o libsps30.so \
        sps30.c \
        ../embedded-common/sensirion_common.c \
        ../embedded-common/hw_i2c/sensirion_hw_i2c_implementation.c \
        ../sps-common/sps_git_version.c \
        -I. -I../embedded-common/hw_i2c -I../embedded-common -I../sps-common
fi

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
