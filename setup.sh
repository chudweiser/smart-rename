#!/bin/bash

echo ""
echo "=================================================="
echo "  Smart Rename — Setup"
echo "=================================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "  [error] Python 3 is not installed."
    echo "  Install it with your package manager, e.g.:"
    echo "    sudo pacman -S python    (Arch)"
    echo "    sudo apt install python3 (Ubuntu/Debian)"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_VERSION" -lt 10 ]; then
    echo "  [error] Python 3.10 or higher is required."
    echo "  You have: $(python3 --version)"
    exit 1
fi
echo "  ✓ Python $(python3 --version)"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo ""
    echo "  [error] Ollama is not installed."
    echo "  Install it with:"
    echo "    curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi
echo "  ✓ Ollama found"

# Check llava model
if ! ollama list 2>/dev/null | grep -q "llava"; then
    echo ""
    echo "  llava model not found. Pulling now (~4GB)..."
    ollama pull llava
fi
echo "  ✓ llava model ready"

# Create venv
echo ""
echo "  Creating virtual environment..."
python3 -m venv venv
echo "  ✓ Virtual environment created"

# Install dependencies
echo ""
echo "  Installing dependencies..."
venv/bin/pip install --quiet -r requirements.txt
echo "  ✓ Dependencies installed"

# Create run script
cat > run.sh << 'RUNEOF'
#!/bin/bash
cd "$(dirname "$0")"
if ! curl -s http://localhost:11434 | grep -q "Ollama"; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 2
fi
venv/bin/python watcher.py
RUNEOF
chmod +x run.sh

echo ""
echo "=================================================="
echo "  Setup complete!"
echo ""
echo "  To start Smart Rename, run:"
echo "    bash run.sh"
echo "=================================================="
echo ""
