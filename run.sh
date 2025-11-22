#!/bin/bash

# S&P500 Analysis - Quick Start Script

echo "================================================"
echo "S&P500 Analysis - Starting Application"
echo "================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "⚠️  Dependencies not installed. Installing now..."
    pip install -r requirements.txt
    echo ""
fi

# Start backend in background
echo "🚀 Starting backend on http://localhost:8000"
cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend is running
if curl -s http://localhost:8000 > /dev/null; then
    echo "✅ Backend is running (PID: $BACKEND_PID)"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo "🌐 Starting frontend on http://localhost:3000"
cd frontend
python3 -m http.server 3000 &
FRONTEND_PID=$!
cd ..

echo ""
echo "================================================"
echo "✅ Application started successfully!"
echo "================================================"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "📤 Upload:    http://localhost:3000/upload.html"
echo "📖 API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Trap Ctrl+C and cleanup
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Servers stopped.'; exit 0" INT

# Wait for user to stop
wait
