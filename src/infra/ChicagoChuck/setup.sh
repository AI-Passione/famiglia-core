#!/bin/bash
# setup.sh
# Configures Ollama to bind to 0.0.0.0 natively and pulls appropriate models.

set -e

OS="$(uname -s)"
echo "=== Ollama Setup ($OS) ==="

# 1. Configure the Background Service
if [ "$OS" = "Linux" ]; then
    if ! command -v ollama &> /dev/null; then
        echo "Ollama is not installed. Please install: curl -fsSL https://ollama.com/install.sh | sh"
        exit 1
    fi
    echo "Configuring rootless user-level systemd service..."
    SERVICE_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SERVICE_DIR"
    
    cat > "$SERVICE_DIR/ollama.service" <<EOF
[Unit]
Description=Ollama Service (User Level)

[Service]
ExecStart=$(command -v ollama || echo /usr/local/bin/ollama) serve
Environment="OLLAMA_HOST=0.0.0.0"
Restart=always

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user stop ollama.service 2>/dev/null || true
    systemctl --user enable --now ollama.service
    echo "Service bound to 0.0.0.0 (User level)."

elif [ "$OS" = "Darwin" ]; then
    if ! command -v ollama &> /dev/null && [ ! -f "/usr/local/bin/ollama" ]; then
        echo "Ollama not found. Please install from https://ollama.com/download/mac"
        exit 1
    fi
    echo "Configuring LaunchAgent..."
    PLIST_NAME="com.ollama.server.plist"
    TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"
    mkdir -p "$HOME/Library/LaunchAgents"
    cp "./$PLIST_NAME" "$TARGET_PLIST"
    launchctl unload "$TARGET_PLIST" 2>/dev/null || true
    launchctl load "$TARGET_PLIST"
    echo "Service bound to 0.0.0.0."

else
    echo "Unsupported OS: $OS"
    exit 1
fi

echo ""
echo "=== Ollama Model Auto-Manager ==="

# 2. Detect Total RAM (in GB)
if [ "$OS" = "Linux" ]; then
    TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1024 / 1024))
elif [ "$OS" = "Darwin" ]; then
    TOTAL_RAM_BYTES=$(sysctl hw.memsize | awk '{print $2}')
    TOTAL_RAM_GB=$((TOTAL_RAM_BYTES / 1024 / 1024 / 1024))
fi

echo "Detected RAM: ${TOTAL_RAM_GB}GB"

# 3. Determine Model Set based on RAM
if [ "$TOTAL_RAM_GB" -ge 12 ]; then
    echo "Selecting Large Model Set (RAM >= 12GB)..."
    # Fedora 16GB priority targets
    MODELS=("gemma3:4b" "qwen3.5:9b" "qwen2.5-coder:14b" "gemma2:9b")
else
    echo "Selecting Small Model Set (RAM < 12GB)..."
    # Macbook Air 8GB fallback targets
    MODELS=("gemma3:4b" "qwen2.5-coder:7b" "gemma2:2b")
fi

# 4. Pull Models
for MODEL in "${MODELS[@]}"; do
    echo "----------------------------------------"
    if ollama list | grep -q "$MODEL"; then
        echo "Model $MODEL is already downloaded locally. Skipping pull."
    else
        echo "Pulling model: $MODEL (Stream silenced to prevent Github Action Log spam)"
        # We redirect output to prevent the endless logging loop in Actions
        # and enforce a timeout in case of layer pull freeze.
        timeout 900 ollama pull "$MODEL" > /dev/null 2>&1 || {
            echo "Warning: Pull failed or timed out for $MODEL."
        }
    fi
done

echo "----------------------------------------"
echo "=== Setup Complete! ==="

# 5. Detect and Print Local IP
if [ "$OS" = "Linux" ]; then
    # Gets the primary IP address on Linux
    SERVER_IP=$(hostname -I | awk '{print $1}')
elif [ "$OS" = "Darwin" ]; then
    # Gets the IP for the active WiFi/Ethernet interface on macOS
    SERVER_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1)
fi

echo "Your Ollama Server IP is: $SERVER_IP"
echo "Use this IP address to connect from La Passione!"
echo "----------------------------------------"

echo "Current models available:"
ollama list
