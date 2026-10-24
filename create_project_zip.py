"""
=============================================================================
Project Archival & Submission Packaging Script
Packages the complete AI-Powered Campus Infrastructure System into a clean ZIP.
=============================================================================
"""

import os
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ZIP_NAME = "AI_Campus_Infrastructure_Monitoring_SRGEC.zip"
ZIP_PATH = BASE_DIR / ZIP_NAME

# Folders and files to exclude
EXCLUDE_DIRS = {
    '__pycache__',
    '.git',
    '.vscode',
    '.idea',
    'venv',
    '.env_venv',
    'node_modules'
}

EXCLUDE_EXTENSIONS = {
    '.pyc',
    '.pyo',
    '.pyd',
    '.log',
    '.tmp'
}

EXCLUDE_FILES = {
    ZIP_NAME,
    'create_project_zip.py'
}

def create_zip():
    print(f"[*] Packaging project files into: {ZIP_NAME}...")
    
    file_count = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
            
            for file in files:
                if file in EXCLUDE_FILES:
                    continue
                    
                ext = os.path.splitext(file)[1].lower()
                if ext in EXCLUDE_EXTENSIONS:
                    continue

                abs_file_path = Path(root) / file
                rel_path = abs_file_path.relative_to(BASE_DIR)

                # Store inside a root folder inside the ZIP for clean extraction
                archive_name = Path("AI_Campus_Infrastructure_SRGEC") / rel_path

                zf.write(abs_file_path, arcname=str(archive_name))
                file_count += 1
                total_uncompressed_bytes += abs_file_path.stat().st_size

    compressed_size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    uncompressed_size_mb = total_uncompressed_bytes / (1024 * 1024)
    
    print(f"[OK] Archive successfully generated!")
    print(f"     Path: {ZIP_PATH}")
    print(f"     Files packaged: {file_count}")
    print(f"     Uncompressed size: {uncompressed_size_mb:.2f} MB")
    print(f"     Compressed ZIP size: {compressed_size_mb:.2f} MB")

if __name__ == '__main__':
    create_zip()
