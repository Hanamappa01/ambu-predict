#!/bin/bash
# AmbuPredict — Quick Start Script
# Run this from the AmbuPredict_Project/ folder
 
echo "=================================="
echo "  AmbuPredict API — Starting..."
echo "=================================="
echo ""
 
# Always run from the directory this script lives in (project root)
cd "$(dirname "$0")"
 
echo "Working directory: $(pwd)"
echo ""
echo "Installing dependencies..."
pip install -r ambu_api/requirements.txt -q
 
echo ""
echo "Starting FastAPI server on port 8000..."
echo "Open ambu_frontend.html in your browser."
echo "API docs: http://localhost:8000/docs"
echo ""
 
# Run from project root so Python can resolve 'ambu_api' as a package
uvicorn ambu_api.main:app --reload --port 8000
 