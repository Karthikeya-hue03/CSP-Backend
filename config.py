"""
=============================================================================
Campus Infrastructure Monitoring & Predictive Maintenance System
System Configuration & Environment Specification
=============================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory: Absolute root path of the project workspace (parent of this backend/ folder)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local environment overrides from .env file if present
load_dotenv(BASE_DIR / '.env')

class Config:
    """
    Central application configuration class defining server security keys,
    database connection settings, GIS campus center coordinates, and AI model paths.
    """
    # Cryptographic secret key used by Flask to sign session cookies and flash messages
    SECRET_KEY = os.getenv('SECRET_KEY', 'campus-infra-ai-super-secret-key-2026')
    
    # -------------------------------------------------------------------------
    # MySQL Database Server Configuration
    # -------------------------------------------------------------------------
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'campus_maintenance')
    
    # -------------------------------------------------------------------------
    # Zero-Config SQLite Fallback Database
    # Automatically utilized if MySQL service is offline or unreachable
    # -------------------------------------------------------------------------
    SQLITE_DB_PATH = BASE_DIR / 'campus_maintenance.db'
    
    # -------------------------------------------------------------------------
    # Scikit-learn AI Predictive Model Serialized Artifact
    # -------------------------------------------------------------------------
    ML_MODEL_PATH = Path(__file__).resolve().parent / 'ml' / 'model.joblib'
    
    # -------------------------------------------------------------------------
    # Campus Interactive GIS Map Defaults (Latitude, Longitude, Initial Zoom)
    # -------------------------------------------------------------------------
    CAMPUS_NAME = os.getenv('CAMPUS_NAME', 'Seshadri Rao Gudlavalleru Engineering College (SRGEC)')
    CAMPUS_CENTER_LAT = float(os.getenv('CAMPUS_CENTER_LAT', 16.350975))
    CAMPUS_CENTER_LNG = float(os.getenv('CAMPUS_CENTER_LNG', 81.042576))
    CAMPUS_ZOOM = int(os.getenv('CAMPUS_ZOOM', 17))
    
    # -------------------------------------------------------------------------
    # User Session Lifetime (in seconds): 86400 seconds = 24 hours
    # -------------------------------------------------------------------------
    PERMANENT_SESSION_LIFETIME = 86400
