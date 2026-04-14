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
        echo "✓ Library is already compiled for $ARCH and working"
        echo "✓ No recompilation needed"
        echo ""
        echo "To force recompilation, delete the file first:"
        echo "  rm $LIB_DIR/libsps30.so"
        echo "  ./compile_sps30.sh"
        exit 0
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

# Check if required directories exist
echo ""
echo "Checking for required source directories..."
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

if [ ! -f "$SOURCE_DIR/Makefile" ]; then
    echo "✗ Makefile not found!"
    exit 1
fi

echo "✓ All required directories and Makefile found"

# Compile using repository Makefile
echo "Compiling SPS30 library for $ARCH..."
cd "$SOURCE_DIR"

# Use the repository's Makefile to build
echo "Building with repository Makefile..."
make

# The Makefile should create the library in the release folder
if [ -f "release/libsps30.so" ]; then
    cp release/libsps30.so sps30-i2c/libsps30.so
elif [ -f "sps30-i2c/libsps30.so" ]; then
    echo "Library already in sps30-i2c/"
else
    echo "⚠️  Makefile build didn't create libsps30.so, trying manual compilation..."
    cd sps30-i2c
    gcc -fPIC -shared -o libsps30.so \
        sps30.c \
        ../embedded-common/sensirion_common.c \
        ../embedded-common/hw_i2c/sensirion_hw_i2c_implementation.c \
        -I. -I../embedded-common/hw_i2c -I../embedded-common -I../sps-common
fi

# Find the compiled library
LIB_PATH=""
if [ -f "sps30-i2c/libsps30.so" ]; then
    LIB_PATH="sps30-i2c/libsps30.so"
elif [ -f "release/libsps30.so" ]; then
    LIB_PATH="release/libsps30.so"
fi

# Verify compilation
if [ -z "$LIB_PATH" ] || [ ! -f "$LIB_PATH" ]; then
    echo "✗ Compilation failed! Library not found."
    exit 1
fi

echo ""
echo "Compiled library info:"
file "$LIB_PATH"

# Copy to project
echo ""
echo "Installing library to $LIB_DIR..."
cp "$LIB_PATH" "$LIB_DIR/"

echo ""
echo "✓ SPS30 library compiled successfully!"
echo "Location: $LIB_DIR/libsps30.so"
