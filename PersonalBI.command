#!/bin/bash

# Navigate to the directory where this script resides
cd "$(dirname "$0")"

echo "------------------------------------------"
echo "🚀 RESTARTING PERSONAL BI ASSISTANT..."
echo "------------------------------------------"

# 1. Terminate active streamlit processes for this project
echo "🧹 Cleaning up existing processes..."
pkill -f "streamlit run frontend/webapp.py"

# 2. Brief pause to ensure ports are released
sleep 1

# 3. Launch the new instance using the local virtual environment
echo "📈 Launching new instance..."
echo "The browser should open automatically in a few seconds."
./.venv/bin/python -m streamlit run frontend/webapp.py
