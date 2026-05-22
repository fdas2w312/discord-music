#!/bin/bash
# Discord Lyrics Scroller — Installation script

set -e

echo "=== Discord Lyrics Scroller Installer ==="

PROJECT_DIR="/opt/discord-lyrics-scroller"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create project directory
echo "📁 Installing to $PROJECT_DIR..."
sudo mkdir -p "$PROJECT_DIR"
sudo cp -r "$SCRIPT_DIR"/* "$PROJECT_DIR/"

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env from example if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit $PROJECT_DIR/.env and add your Discord token!"
    echo "   nano $PROJECT_DIR/.env"
    echo ""
fi

# Install systemd service
echo "🔧 Installing systemd service..."
sudo cp discord-lyrics.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable discord-lyrics.service

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env:  nano $PROJECT_DIR/.env"
echo "  2. Start service:  sudo systemctl start discord-lyrics"
echo "  3. Open web panel: http://localhost:8080"
echo ""
