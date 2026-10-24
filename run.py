"""
run.py — Project Root Launcher
================================
Run this file from the project root to start the application:
    python run.py

How it works:
1. Adds the backend/ folder to Python's import search path so that
   all Flask imports (config, database, routes, models, ml) resolve correctly.
2. Imports the pre-built Flask app instance from backend/app.py.
3. Prints a startup banner with the active database type and server URL.
4. Starts the Flask development server on http://0.0.0.0:5000.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Make backend/ importable: all Python files (config, database, routes, etc.)
# live inside backend/ so we add it to the Python module search path.
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, BACKEND_DIR)

# ---------------------------------------------------------------------------
# Import the Flask application factory output and DB-type helper from backend.
# ---------------------------------------------------------------------------
from app import app                       # noqa: E402  (import after sys.path edit)
from database import get_db_type          # noqa: E402

if __name__ == '__main__':
    # Print startup banner displaying environment configuration and listening URL
    print("\n" + "=" * 70)
    print("  AI-Powered Campus Infrastructure Health Monitoring & Maintenance")
    print(f"  Database Engine : {get_db_type().upper()}")
    print("  Server running at: http://127.0.0.1:5000")
    print("=" * 70 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
