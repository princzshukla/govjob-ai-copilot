#!/usr/bin/env bash
set -e

echo "======================================"
echo "   GovJob AI Copilot Project Setup    "
echo "======================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- 1. Backend Setup ---
echo ""
echo "[1/4] Setting up Python virtual environment..."
cd "$ROOT_DIR/backend"

if [ ! -d "venv" ]; then
  python -m venv venv
  echo "Virtual environment created at backend/venv."
fi

# Detect OS executable path for venv
if [ -f "venv/Scripts/python.exe" ]; then
  VENV_PYTHON="venv/Scripts/python.exe"
else
  VENV_PYTHON="venv/bin/python"
fi

echo "[2/4] Installing backend dependencies..."
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
  echo "Creating default backend .env file..."
  cat << 'EOF' > .env
PORT=8000
ENVIRONMENT=development
DISABLE_SQLALCHEMY_CEXT=1
EOF
fi

# --- 2. Frontend Setup ---
echo ""
echo "[3/4] Setting up Frontend..."
cd "$ROOT_DIR/frontend"

if [ ! -f ".env" ]; then
  echo "Creating default frontend .env file..."
  cat << 'EOF' > .env
VITE_API_BASE_URL=http://localhost:8000/api/v1
EOF
fi

echo "[4/4] Installing frontend dependencies..."
if command -v bun &> /dev/null; then
  echo "Bun detected. Installing packages with Bun..."
  bun install
elif command -v npm &> /dev/null; then
  echo "Npm detected. Installing packages with npm..."
  npm install
else
  echo "Warning: Neither Bun nor npm found. Please install Bun or Node.js."
fi

echo ""
echo "======================================"
echo "         Setup Complete!              "
echo "======================================"
echo "To run the project:"
echo ""
echo "Terminal 1 (Backend):"
echo "  cd backend"
echo "  source venv/Scripts/activate  (or venv/bin/activate on Linux/Mac)"
echo "  python -m alembic upgrade head"
echo "  python -m uvicorn app.main:app --reload --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1"
echo "  (Behind a reverse proxy, set --forwarded-allow-ips to the proxy address.)"
echo ""
echo "Terminal 2 (Frontend):"
echo "  cd frontend"
echo "  bun dev  (or npm run dev)"
echo "======================================"