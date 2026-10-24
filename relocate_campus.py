"""
=============================================================================
Campus Infrastructure Monitoring & Predictive Maintenance System
Geospatial Campus Relocation & Pin Shifting Utility
=============================================================================
This script updates the campus center coordinates in .env and config,
and shifts all infrastructure assets (streetlights, roads, water pipelines, drainage)
in the database so that their relative layout is preserved at the new location.
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from config import Config, BASE_DIR
from database import get_db_connection, query_db, execute_db

def update_env_coordinates(new_lat, new_lng, zoom=17, campus_name=None):
    """
    Updates or inserts CAMPUS_CENTER_LAT, CAMPUS_CENTER_LNG, CAMPUS_ZOOM,
    and optionally CAMPUS_NAME in the local .env file.
    """
    env_path = BASE_DIR / '.env'
    if not env_path.exists():
        content = ""
    else:
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()

    def set_kv(text, key, val):
        pattern = rf'^{key}=.*$'
        replacement = f'{key}={val}'
        if re.search(pattern, text, flags=re.MULTILINE):
            return re.sub(pattern, replacement, text, flags=re.MULTILINE)
        else:
            return text.rstrip() + f"\n{replacement}\n"

    content = set_kv(content, 'CAMPUS_CENTER_LAT', f"{float(new_lat):.6f}")
    content = set_kv(content, 'CAMPUS_CENTER_LNG', f"{float(new_lng):.6f}")
    content = set_kv(content, 'CAMPUS_ZOOM', str(int(zoom)))
    if campus_name:
        content = set_kv(content, 'CAMPUS_NAME', f'"{campus_name}"')

    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)

def relocate_campus(new_lat, new_lng, zoom=17, campus_name=None):
    """
    Calculates coordinate offset from the current centroid of all assets
    and shifts every asset's latitude and longitude in the active database.
    """
    new_lat = float(new_lat)
    new_lng = float(new_lng)
    
    # 1. Fetch current center / average coordinates of assets
    assets = query_db("SELECT id, latitude, longitude FROM assets WHERE latitude IS NOT NULL AND longitude IS NOT NULL;")
    if not assets:
        print("[WARNING] No assets found with coordinates to relocate.")
        update_env_coordinates(new_lat, new_lng, zoom, campus_name)
        return

    avg_lat = sum(a['latitude'] for a in assets) / len(assets)
    avg_lng = sum(a['longitude'] for a in assets) / len(assets)

    delta_lat = new_lat - avg_lat
    delta_lng = new_lng - avg_lng

    print(f"[*] Moving campus from ({avg_lat:.6f}, {avg_lng:.6f}) -> ({new_lat:.6f}, {new_lng:.6f})")
    print(f"[*] Offset: delta_lat = {delta_lat:+.6f}, delta_lng = {delta_lng:+.6f}")

    # 2. Update each asset in the database
    count = 0
    for a in assets:
        updated_lat = round(a['latitude'] + delta_lat, 6)
        updated_lng = round(a['longitude'] + delta_lng, 6)
        execute_db(
            "UPDATE assets SET latitude = %s, longitude = %s WHERE id = %s;",
            (updated_lat, updated_lng, a['id'])
        )
        count += 1

    # 3. Update .env configuration
    update_env_coordinates(new_lat, new_lng, zoom, campus_name)
    print(f"[OK] Successfully relocated {count} infrastructure assets to new campus coordinates.")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python relocate_campus.py <latitude> <longitude> [zoom] [campus_name]")
        print("Example: python relocate_campus.py 12.9915 80.2337 17 'IIT Madras'")
        sys.exit(1)

    lat = float(sys.argv[1])
    lng = float(sys.argv[2])
    z = int(sys.argv[3]) if len(sys.argv) > 3 else 17
    name = sys.argv[4] if len(sys.argv) > 4 else None

    relocate_campus(lat, lng, z, name)
