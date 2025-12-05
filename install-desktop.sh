#!/bin/bash
# Install Thermal Printer desktop entry

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_FILE="$SCRIPT_DIR/thermal-printer.desktop"
INSTALL_DIR="$HOME/.local/share/applications"

if [ ! -f "$DESKTOP_FILE" ]; then
    echo "Error: Desktop file not found at $DESKTOP_FILE"
    exit 1
fi

# Create install directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Update the Exec path to use the actual project location
sed "s|\$HOME/code/personal/print|$SCRIPT_DIR|g" "$DESKTOP_FILE" > "$INSTALL_DIR/thermal-printer.desktop"

# Make sure run.sh is executable
chmod +x "$SCRIPT_DIR/run.sh"

echo "Desktop entry installed to $INSTALL_DIR/thermal-printer.desktop"
echo "You may need to log out and back in, or run: update-desktop-database ~/.local/share/applications"
