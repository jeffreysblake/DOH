#!/bin/bash
# setup.sh - Set up DOH development environment

echo "🚀 Setting up DOH development environment..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x doh.py
chmod +x test_doh.py

# Create symlink for easy access (optional)
echo "🔗 Creating convenience symlink..."
if [ ! -L doh ]; then
    ln -s doh.py doh
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To use DOH:"
echo "  source .venv/bin/activate  # Activate virtual environment"
echo "  ./doh.py --help           # Show help"
echo "  ./doh.py                  # Add current directory to monitoring"
echo ""
echo "To run tests:"
echo "  python -m pytest test_doh.py -v"
echo ""
echo "To deactivate virtual environment:"
echo "  deactivate"
