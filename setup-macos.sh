#!/bin/bash

echo "================================================"
echo "Social Media Monitor - macOS Setup Script"
echo "================================================"
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  This script is for macOS. Use setup.sh for Linux."
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Check if using Python 3.13
if [[ $python_version == 3.13* ]]; then
    echo "⚠️  Python 3.13 detected - some packages may need compilation"
    echo "   Installing Xcode Command Line Tools if needed..."
    xcode-select --install 2>/dev/null || echo "✓ Xcode tools already installed"
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip and setuptools
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install requirements
echo ""
echo "Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt

# Check if playwright install succeeded
if ! command -v playwright &> /dev/null; then
    echo ""
    echo "Installing Playwright browsers..."
    python -m playwright install chromium
else
    echo ""
    echo "Installing Playwright browsers..."
    playwright install chromium
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    
    # Generate encryption key
    echo "Generating encryption key..."
    encryption_key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # Update .env with encryption key (macOS sed syntax)
    sed -i '' "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$encryption_key/" .env
    
    echo "✓ Encryption key generated and saved to .env"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p logs data browser_profiles

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Activate venv: source .venv/bin/activate"
echo "3. Add account: python3 cli.py add-account linkedin your_email your_email your_password"
echo "4. Test scraper: python3 cli.py scrape linkedin your_email your_password --no-headless"
echo ""
echo "Note: First run should be with --no-headless to handle 2FA/CAPTCHA"
echo ""