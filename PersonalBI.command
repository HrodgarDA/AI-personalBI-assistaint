#!/bin/bash

# Naviga nella directory dove risiede questo script
cd "$(dirname "$0")"

echo "------------------------------------------"
echo "🚀 RESTARTING PERSONAL BI ASSISTANT..."
echo "------------------------------------------"

# 1. Chiude i processi streamlit attivi per questo progetto
echo "🧹 Cleaning up existing processes..."
pkill -f "streamlit run app/webapp.py"

# 2. Breve attesa per assicurarsi che le porte siano libere
sleep 1

# 3. Lancio della nuova istanza tramite l'ambiente virtuale locale
echo "📈 Launching new instance..."
echo "The browser should open automatically in a few seconds."
./.venv/bin/python -m streamlit run app/webapp.py
