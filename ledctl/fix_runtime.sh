#!/bin/bash
# Fix runtime issues for LED control system

echo "=== Fixing Runtime Issues ==="

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file with secret key..."
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    cat > .env << EOF
FLASK_ENV=production
FLASK_SECRET_KEY=$SECRET_KEY
API_AUTH_ENABLED=False
API_KEYS=
CORS_ORIGINS=*
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
RATE_LIMIT_ENABLED=True
EOF
    echo "✓ Created .env file"
fi

# Create device.yml if it doesn't exist
if [ ! -f "config/device.yml" ]; then
    echo "Creating device.yml from default..."
    cp config/device.default.yml config/device.yml
    echo "✓ Created config/device.yml"
fi

# Create uploads directory
mkdir -p uploads
echo "✓ Created uploads directory"

echo
echo "=== Setup Complete ==="
echo "Now you can run:"
echo "  python3 app.py --mock"
echo
echo "Or with hardware (requires sudo):"
echo "  sudo python3 app.py"