#!/bin/bash

echo "================================================"
echo "Social Media Monitor - Setup Script"
echo "================================================"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
playwright install chromium

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    
    # Generate encryption key
    echo "Generating encryption key..."
    encryption_key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # Update .env with encryption key (macOS compatible)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$encryption_key/" .env
    else
        sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$encryption_key/" .env
    fi
    
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
echo "2. Run: source .venv/bin/activate"
echo "3. Add accounts: python3 -c \"import asyncio; from main import add_account; asyncio.run(add_account('linkedin', 'your_email', 'your_email', 'your_password'))\""
echo "4. Test scraper: python3 main.py"
echo ""
