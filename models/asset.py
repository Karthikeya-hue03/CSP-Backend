import re
from datetime import date, timedelta
from config import Config
from database import query_db, execute_db

def _safe_float(val, default=0.0):
    """Safely converts string or numerical value to float, handling empty strings and invalid formats."""
    if val is None or val == '':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def _safe_int(val, default=0):
    """Safely converts string or numerical value to integer, handling empty strings and decimals."""
    if val is None or val == '':
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default

def get_next_streetlight_tag():
    """Calculates the next available sequential streetlight asset tag and pole number."""
    rows = query_db("SELECT asset_tag FROM assets WHERE asset_type = 'streetlight';")
    nums = []
    for r in rows:
        match = re.search(r'(\d+)', r['asset_tag'])
        if match:
            nums.append(int(match.group(1)))
    next_num = (max(nums) + 1) if nums else 1
    return f"SL-{next_num:03d}", f"POL-{next_num:02d}"

def get_next_road_tag():
    """Calculates the next available sequential road asset tag."""
    rows = query_db("SELECT asset_tag FROM assets WHERE asset_type = 'road';")
    nums = []
    for r in rows:
        match = re.search(r'(\d+)', r['asset_tag'])
        if match:
            nums.append(int(match.group(1)))
    next_num = (max(nums) + 1) if nums else 1
    return f"RD-{next_num:03d}"

def get_all_assets(asset_type=None, condition=None, search=None):
    """
    Retrieves all master infrastructure assets with dynamic multi-criteria filtering.
    
    How it works:
    1. Builds a dynamic SQL SELECT query starting with base condition `WHERE 1=1`.
    2. Conditionally appends criteria for `asset_type` (streetlight, road).
    3. Conditionally appends criteria for `condition_status` (Good, Moderate, Poor, Critical).
    4. Conditionally adds LIKE search pattern across name, asset_tag, and location.
    5. Executes via safe parameterized binding and returns matched asset dictionaries.
    
    Args:
        asset_type (str, optional): Filter by asset type or 'all'.
        condition (str, optional): Filter by operational condition or 'all'.
        search (str, optional): Text keyword for searching names or locations.
        
    Returns:
        list[dict]: Filtered list of asset records.
    """
    query = "SELECT * FROM assets WHERE 1=1"
    params = []
    
    if asset_type and asset_type.lower() != 'all':
        query += " AND asset_type = %s"
        params.append(asset_type)
    else:
        # Focus on active monitored infrastructure
        query += " AND asset_type IN ('streetlight', 'road')"
        
    if condition and condition.lower() != 'all':
        query += " AND condition_status = %s"
        params.append(condition)
        
    if search:
        query += " AND (name LIKE %s OR asset_tag LIKE %s OR location LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])
        
    query += " ORDER BY id ASC;"
    return query_db(query, tuple(params))

def get_asset_by_id(asset_id):
    """
    Retrieves a single asset record by primary key ID.
    
    How it works:
    - Runs a parameterized query against `assets` table for `id = %s`.
    
    Args:
        asset_id (int): Primary key ID of the asset.
        
    Returns:
        dict | None: The asset dictionary or None if not found.
    """
    return query_db("SELECT * FROM assets WHERE id = %s;", (asset_id,), one=True)

def get_asset_by_tag(asset_tag):
    """
    Retrieves a single asset record by its unique campus asset tag (e.g. 'SL-001').
    
    How it works:
    - Filters the `assets` table on `asset_tag = %s`.
    
    Args:
        asset_tag (str): Unique identifier string.
        
    Returns:
        dict | None: The asset dictionary or None if not found.
    """
    return query_db("SELECT * FROM assets WHERE asset_tag = %s;", (asset_tag,), one=True)

# -------------------------------------------------------------
# Category-Specific Queries with Sub-table Joins
# -------------------------------------------------------------

def get_streetlights(search=None):
    """
    Retrieves streetlight assets joined with the streetlights specification subtable.
    
    How it works:
    1. Performs an INNER JOIN between `assets` and `streetlights` on `a.id = s.asset_id`.
    2. Combines physical metadata (pole_number, wattage, power_status, light_status, lumens)
       with geospatial and telemetry metrics (health_score, previous_failures, location).
    3. Supports optional keyword search across pole number, asset tag, and campus location.
    
    Args:
        search (str, optional): Search keyword.
        
    Returns:
        list[dict]: Joined streetlight asset records.
    """
    query = """
        SELECT a.id, a.asset_tag, a.name, a.location, a.latitude, a.longitude,
               a.health_score, a.condition_status, a.age_years, a.previous_failures,
               a.complaint_count, a.last_inspection, a.next_maintenance,
               s.pole_number, s.wattage, s.power_status, s.light_status, s.lumens
        FROM assets a
        JOIN streetlights s ON a.id = s.asset_id
        WHERE a.asset_type = 'streetlight'
    """
    params = []
    if search:
        query += " AND (a.name LIKE %s OR a.asset_tag LIKE %s OR a.location LIKE %s OR s.pole_number LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
    query += " ORDER BY a.id ASC;"
    return query_db(query, tuple(params))

def get_roads(search=None):
    """
    Retrieves road segments joined with the roads specification subtable.
    
    How it works:
    1. Performs an INNER JOIN between `assets` and `roads` on `a.id = r.asset_id`.
    2. Includes road telemetry: length in km, surface type, pothole counts, crack severity, and priority.
    3. Supports optional search by road name or location.
    
    Args:
        search (str, optional): Search keyword.
        
    Returns:
        list[dict]: Joined road segment records.
    """
    query = """
        SELECT a.id, a.asset_tag, a.name, a.location, a.latitude, a.longitude,
               a.health_score, a.condition_status, a.age_years, a.previous_failures,
               a.complaint_count, a.last_inspection, a.next_maintenance,
               r.road_name, r.length_km, r.surface_type, r.pothole_count,
               r.crack_severity, r.road_condition, r.priority
        FROM assets a
        JOIN roads r ON a.id = r.asset_id
        WHERE a.asset_type = 'road'
    """
    params = []
    if search:
        query += " AND (a.name LIKE %s OR a.asset_tag LIKE %s OR a.location LIKE %s OR r.road_name LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
    query += " ORDER BY a.id ASC;"
    return query_db(query, tuple(params))

def get_water_pipelines(search=None):
    """
    Retrieves water pipelines joined with the water_pipelines subtable.
    
    How it works:
    1. Performs an INNER JOIN between `assets` and `water_pipelines` on `a.id = p.asset_id`.
    2. Fetches pipeline-specific operational parameters: pipe material, leak status, flow rate, and pressure PSI.
    3. Supports optional search filter by pipeline code or zone.
    
    Args:
        search (str, optional): Search keyword.
        
    Returns:
        list[dict]: Joined water pipeline telemetry records.
    """
    query = """
        SELECT a.id, a.asset_tag, a.name, a.location, a.latitude, a.longitude,
               a.health_score, a.condition_status, a.age_years, a.previous_failures,
               a.complaint_count, a.last_inspection, a.next_maintenance,
               p.pipeline_code, p.length_km, p.pipe_material, p.leak_status,
               p.water_flow_rate, p.pressure_psi
        FROM assets a
        JOIN water_pipelines p ON a.id = p.asset_id
        WHERE a.asset_type = 'water_pipeline'
    """
    params = []
    if search:
        query += " AND (a.name LIKE %s OR a.asset_tag LIKE %s OR a.location LIKE %s OR p.pipeline_code LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
    query += " ORDER BY a.id ASC;"
    return query_db(query, tuple(params))

def get_drainage(search=None):
    """
    Retrieves drainage systems joined with the drainage subtable.
    
    How it works:
    1. Performs an INNER JOIN between `assets` and `drainage` on `a.id = d.asset_id`.
    2. Fetches drainage-specific parameters: drain type, flow status, blockage level, and water stagnation risk.
    3. Supports optional search filter by drain code or campus quadrant.
    
    Args:
        search (str, optional): Search keyword.
        
    Returns:
        list[dict]: Joined drainage system records.
    """
    query = """
        SELECT a.id, a.asset_tag, a.name, a.location, a.latitude, a.longitude,
               a.health_score, a.condition_status, a.age_years, a.previous_failures,
               a.complaint_count, a.last_inspection, a.next_maintenance,
               d.drain_code, d.drain_type, d.flow_status, d.blockage_level,
               d.stagnation_risk
        FROM assets a
        JOIN drainage d ON a.id = d.asset_id
        WHERE a.asset_type = 'drainage'
    """
    params = []
    if search:
        query += " AND (a.name LIKE %s OR a.asset_tag LIKE %s OR a.location LIKE %s OR d.drain_code LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
    query += " ORDER BY a.id ASC;"
    return query_db(query, tuple(params))

# -------------------------------------------------------------
# Asset Mutations (CRUD)
# -------------------------------------------------------------

def create_streetlight(data):
    """
    Creates a master asset record and its corresponding streetlight subtable entry.
    
    How it works:
    1. Inserts the common asset telemetry (tag, type, name, coordinates, health) into `assets`.
    2. Obtains the auto-generated `asset_id`.
    3. Inserts streetlight-specific specifications (pole_number, wattage, power_status, lumens)
       into `streetlights` with foreign key linking to `assets.id`.
       
    Args:
        data (dict): Combined form/API data containing asset and streetlight fields.
        
    Returns:
        int: The primary key ID of the created asset.
    """
    asset_tag = (data.get('asset_tag') or '').strip()
    auto_tag, auto_pole = get_next_streetlight_tag()
    if not asset_tag:
        asset_tag = auto_tag

    pole_number = (data.get('pole_number') or auto_pole).strip()
    name = (data.get('name') or f"LED Pole {pole_number}").strip()
    location = (data.get('location') or "Campus Area").strip()
    lat = _safe_float(data.get('latitude'), Config.CAMPUS_CENTER_LAT)
    lng = _safe_float(data.get('longitude'), Config.CAMPUS_CENTER_LNG)
    health_score = _safe_int(data.get('health_score'), 95)
    condition_status = (data.get('condition_status') or 'Good').strip()
    age_years = _safe_int(data.get('age_years'), 1)
    previous_failures = _safe_int(data.get('previous_failures'), 0)
    complaint_count = _safe_int(data.get('complaint_count'), 0)
    last_inspection = data.get('last_inspection') or date.today().strftime('%Y-%m-%d')
    next_maintenance = data.get('next_maintenance') or (date.today() + timedelta(days=90)).strftime('%Y-%m-%d')

    wattage = _safe_int(data.get('wattage'), 70)
    power_status = (data.get('power_status') or 'ON').strip()
    light_status = (data.get('light_status') or 'Working').strip()
    lumens = _safe_int(data.get('lumens'), 6500)

    asset_id = execute_db(
        """INSERT INTO assets (asset_tag, asset_type, name, location, latitude, longitude,
                              health_score, condition_status, age_years, previous_failures,
                              complaint_count, last_inspection, next_maintenance)
           VALUES (%s, 'streetlight', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
        (
            asset_tag, name, location, lat, lng, health_score,
            condition_status, age_years, previous_failures, complaint_count,
            last_inspection, next_maintenance
        ),
        return_id=True
    )
    execute_db(
        """INSERT INTO streetlights (asset_id, pole_number, wattage, power_status, light_status, lumens)
           VALUES (%s, %s, %s, %s, %s, %s);""",
        (
            asset_id, pole_number, wattage, power_status, light_status, lumens
        )
    )
    return asset_id

def create_road(data):
    """
    Creates a master asset record and its corresponding road subtable entry.
    
    How it works:
    1. Inserts common geospatial and health fields into `assets` with asset_type='road'.
    2. Captures generated `asset_id`.
    3. Inserts road-specific attributes (length_km, surface_type, pothole_count, crack_severity, priority)
       into `roads`.
       
    Args:
        data (dict): Combined road creation parameters.
        
    Returns:
        int: The primary key ID of the created road asset.
    """
    asset_tag = (data.get('asset_tag') or '').strip()
    if not asset_tag:
        asset_tag = get_next_road_tag()

    name = (data.get('name') or data.get('road_name') or f"Campus Road {asset_tag}").strip()
    location = (data.get('location') or "Campus Sector").strip()
    lat = _safe_float(data.get('latitude'), Config.CAMPUS_CENTER_LAT)
    lng = _safe_float(data.get('longitude'), Config.CAMPUS_CENTER_LNG)
    health_score = _safe_int(data.get('health_score'), 85)
    condition_status = (data.get('condition_status') or 'Good').strip()
    age_years = _safe_int(data.get('age_years'), 1)
    previous_failures = _safe_int(data.get('previous_failures'), 0)
    complaint_count = _safe_int(data.get('complaint_count'), 0)
    last_inspection = data.get('last_inspection') or date.today().strftime('%Y-%m-%d')
    next_maintenance = data.get('next_maintenance') or (date.today() + timedelta(days=90)).strftime('%Y-%m-%d')

    road_name = (data.get('road_name') or name).strip()
    length_km = _safe_float(data.get('length_km'), 1.0)
    surface_type = (data.get('surface_type') or 'Asphalt').strip()
    pothole_count = _safe_int(data.get('pothole_count'), 0)
    crack_severity = (data.get('crack_severity') or 'None').strip()
    road_condition = (data.get('road_condition') or condition_status).strip()
    priority = (data.get('priority') or 'Medium').strip()

    asset_id = execute_db(
        """INSERT INTO assets (asset_tag, asset_type, name, location, latitude, longitude,
                              health_score, condition_status, age_years, previous_failures,
                              complaint_count, last_inspection, next_maintenance)
           VALUES (%s, 'road', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
        (
            asset_tag, name, location, lat, lng, health_score,
            condition_status, age_years, previous_failures, complaint_count,
            last_inspection, next_maintenance
        ),
        return_id=True
    )
    execute_db(
        """INSERT INTO roads (asset_id, road_name, length_km, surface_type, pothole_count,
                             crack_severity, road_condition, priority)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s);""",
        (
            asset_id, road_name, length_km, surface_type, pothole_count,
            crack_severity, road_condition, priority
        )
    )
    return asset_id

def create_water_pipeline(data):
    """
    Creates a master asset record and its corresponding water_pipelines subtable entry.
    
    How it works:
    1. Inserts master asset telemetry into `assets` with asset_type='water_pipeline'.
    2. Inserts pipeline specifications (pipeline_code, pipe_material, leak_status, pressure)
       into `water_pipelines`.
       
    Args:
        data (dict): Combined water pipeline parameters.
        
    Returns:
        int: The primary key ID of the created water pipeline asset.
    """
    asset_id = execute_db(
        """INSERT INTO assets (asset_tag, asset_type, name, location, latitude, longitude,
                              health_score, condition_status, age_years, previous_failures,
                              complaint_count, last_inspection, next_maintenance)
           VALUES (%s, 'water_pipeline', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
        (
            data['asset_tag'], data['name'], data['location'], float(data.get('latitude', 17.3850)),
            float(data.get('longitude', 78.4866)), int(data.get('health_score', 85)),
            data.get('condition_status', 'Good'), int(data.get('age_years', 1)),
            int(data.get('previous_failures', 0)), int(data.get('complaint_count', 0)),
            data.get('last_inspection'), data.get('next_maintenance')
        ),
        return_id=True
    )
    execute_db(
        """INSERT INTO water_pipelines (asset_id, pipeline_code, length_km, pipe_material,
                                       leak_status, water_flow_rate, pressure_psi)
           VALUES (%s, %s, %s, %s, %s, %s, %s);""",
        (
            asset_id, data.get('pipeline_code', data['asset_tag']), float(data.get('length_km', 0.5)),
            data.get('pipe_material', 'HDPE'), data.get('leak_status', 'Normal'),
            float(data.get('water_flow_rate', 45.0)), float(data.get('pressure_psi', 55.0))
        )
    )
    return asset_id

def create_drainage(data):
    """
    Creates a master asset record and its corresponding drainage subtable entry.
    
    How it works:
    1. Inserts master asset entry into `assets` with asset_type='drainage'.
    2. Inserts drainage specifications (drain_code, drain_type, flow_status, blockage_level, stagnation_risk)
       into `drainage`.
       
    Args:
        data (dict): Combined drainage point parameters.
        
    Returns:
        int: The primary key ID of the created drainage asset.
    """
    asset_id = execute_db(
        """INSERT INTO assets (asset_tag, asset_type, name, location, latitude, longitude,
                              health_score, condition_status, age_years, previous_failures,
                              complaint_count, last_inspection, next_maintenance)
           VALUES (%s, 'drainage', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
        (
            data['asset_tag'], data['name'], data['location'], float(data.get('latitude', 17.3850)),
            float(data.get('longitude', 78.4866)), int(data.get('health_score', 85)),
            data.get('condition_status', 'Good'), int(data.get('age_years', 1)),
            int(data.get('previous_failures', 0)), int(data.get('complaint_count', 0)),
            data.get('last_inspection'), data.get('next_maintenance')
        ),
        return_id=True
    )
    execute_db(
        """INSERT INTO drainage (asset_id, drain_code, drain_type, flow_status, blockage_level, stagnation_risk)
           VALUES (%s, %s, %s, %s, %s, %s);""",
        (
            asset_id, data.get('drain_code', data['asset_tag']), data.get('drain_type', 'Storm Water'),
            data.get('flow_status', 'Normal'), data.get('blockage_level', 'None'),
            data.get('stagnation_risk', 'Low')
        )
    )
    return asset_id

def update_asset_record(asset_id, data):
    """
    Updates the shared base columns in the `assets` table.
    
    How it works:
    - Modifies name, location, latitude, longitude, health score, condition, age, and inspection dates.
    - Preserves existing dates and values if not explicitly provided or if submitted empty.
    
    Args:
        asset_id (int): Primary key ID of the asset.
        data (dict): Updated attribute values.
    """
    existing = get_asset_by_id(asset_id)
    if not existing:
        return

    name = (data.get('name') or existing['name']).strip()
    location = (data.get('location') or existing['location']).strip()
    lat = _safe_float(data.get('latitude'), existing['latitude'])
    lng = _safe_float(data.get('longitude'), existing['longitude'])
    health_score = _safe_int(data.get('health_score'), existing['health_score'])
    condition_status = (data.get('condition_status') or existing['condition_status']).strip()
    age_years = _safe_int(data.get('age_years'), existing['age_years'])
    
    last_inspection = data.get('last_inspection') or existing['last_inspection']
    next_maintenance = data.get('next_maintenance') or existing['next_maintenance']

    execute_db(
        """UPDATE assets 
           SET name = %s, location = %s, latitude = %s, longitude = %s,
               health_score = %s, condition_status = %s, age_years = %s,
               last_inspection = %s, next_maintenance = %s
           WHERE id = %s;""",
        (
            name, location, lat, lng, health_score,
            condition_status, age_years, last_inspection, next_maintenance,
            asset_id
        )
    )

def update_streetlight(asset_id, data):
    """
    Updates both the master asset record and streetlight specifications.
    
    How it works:
    1. Updates common asset fields using `update_asset_record()`.
    2. Updates pole_number, wattage, power_status, light_status, and lumens in `streetlights`.
    
    Args:
        asset_id (int): Primary key ID of the asset.
        data (dict): Updated field dictionary.
    """
    update_asset_record(asset_id, data)
    
    wattage = _safe_int(data.get('wattage'), 70)
    lumens = _safe_int(data.get('lumens'), 6500)
    power_status = (data.get('power_status') or 'ON').strip()
    light_status = (data.get('light_status') or 'Working').strip()
    pole_number = (data.get('pole_number') or '').strip()

    execute_db(
        """UPDATE streetlights
           SET pole_number = COALESCE(NULLIF(%s, ''), pole_number),
               wattage = %s, power_status = %s,
               light_status = %s, lumens = %s
           WHERE asset_id = %s;""",
        (
            pole_number, wattage, power_status, light_status, lumens, asset_id
        )
    )

def update_road(asset_id, data):
    """
    Updates both the master asset record and road specifications.
    
    How it works:
    1. Updates common asset fields using `update_asset_record()`.
    2. Updates road_name, length_km, surface_type, pothole_count, crack_severity, and priority in `roads`.
    
    Args:
        asset_id (int): Primary key ID of the asset.
        data (dict): Updated field dictionary.
    """
    update_asset_record(asset_id, data)
    
    road_name = (data.get('road_name') or data.get('name') or '').strip()
    length_km = _safe_float(data.get('length_km'), 1.0)
    surface_type = (data.get('surface_type') or 'Asphalt').strip()
    pothole_count = _safe_int(data.get('pothole_count'), 0)
    crack_severity = (data.get('crack_severity') or 'None').strip()
    road_condition = (data.get('road_condition') or data.get('condition_status') or 'Good').strip()
    priority = (data.get('priority') or 'Medium').strip()

    execute_db(
        """UPDATE roads
           SET road_name = COALESCE(NULLIF(%s, ''), road_name),
               length_km = %s, surface_type = %s,
               pothole_count = %s, crack_severity = %s,
               road_condition = %s, priority = %s
           WHERE asset_id = %s;""",
        (
            road_name, length_km, surface_type, pothole_count,
            crack_severity, road_condition, priority, asset_id
        )
    )

def update_water_pipeline(asset_id, data):
    """
    Updates both the master asset record and water pipeline specifications.
    
    How it works:
    1. Updates common asset fields using `update_asset_record()`.
    2. Updates pipeline_code, length_km, pipe_material, leak_status, flow_rate, and pressure in `water_pipelines`.
    
    Args:
        asset_id (int): Primary key ID of the asset.
        data (dict): Updated field dictionary.
    """
    update_asset_record(asset_id, data)
    execute_db(
        """UPDATE water_pipelines
           SET pipeline_code = %s, length_km = %s, pipe_material = %s,
               leak_status = %s, water_flow_rate = %s, pressure_psi = %s
           WHERE asset_id = %s;""",
        (
            data.get('pipeline_code', ''), float(data.get('length_km', 0.5)),
            data.get('pipe_material', 'HDPE'), data.get('leak_status', 'Normal'),
            float(data.get('water_flow_rate', 45.0)), float(data.get('pressure_psi', 55.0)),
            asset_id
        )
    )

def update_drainage(asset_id, data):
    """
    Updates both the master asset record and drainage specifications.
    
    How it works:
    1. Updates common asset fields using `update_asset_record()`.
    2. Updates drain_code, drain_type, flow_status, blockage_level, and stagnation_risk in `drainage`.
    
    Args:
        asset_id (int): Primary key ID of the asset.
        data (dict): Updated field dictionary.
    """
    update_asset_record(asset_id, data)
    execute_db(
        """UPDATE drainage
           SET drain_code = %s, drain_type = %s, flow_status = %s,
               blockage_level = %s, stagnation_risk = %s
           WHERE asset_id = %s;""",
        (
            data.get('drain_code', ''), data.get('drain_type', 'Storm Water'),
            data.get('flow_status', 'Normal'), data.get('blockage_level', 'None'),
            data.get('stagnation_risk', 'Low'), asset_id
        )
    )

def delete_asset(asset_id):
    """
    Deletes an asset and automatically cascades deletions to child tables.
    
    How it works:
    - Executes `DELETE FROM assets WHERE id = %s`.
    - Due to ON DELETE CASCADE foreign key constraints, associated entries in
      `streetlights`, `roads`, `water_pipelines`, `drainage`, `maintenance`,
      and `alerts` are cleanly and safely removed without leaving orphan records.
      
    Args:
        asset_id (int): Primary key ID of the asset to delete.
        
    Returns:
        int: Number of rows affected.
    """
    return execute_db("DELETE FROM assets WHERE id = %s;", (asset_id,))

# -------------------------------------------------------------
# Overall Campus Health Metrics Calculation
# -------------------------------------------------------------

def get_campus_health_metrics():
    """
    Calculates aggregated campus infrastructure health scores and KPI statistics.
    
    How it works:
    1. Queries all assets to calculate the campus-wide Average Health Score (0-100).
    2. Computes breakdown counts:
       - Healthy Assets (Score >= 80)
       - Warning Assets (Score between 60 and 79)
       - Critical Assets (Score < 60)
    3. Aggregates category-specific operational metrics:
       - Streetlights: Total count, Working count, Faulty count.
       - Roads: Total length (km), Good surface length (km), Damaged length (km).
       - Water Pipelines: Total length (km), Normal length (km), Leakage length (km).
       - Drainage: Total drainage points, Normal flow, Blocked sumps.
    4. Computes pending work order counts and unresolved AI failure alerts.
    
    Returns:
        dict: Complete metrics dictionary rendered on the main dashboard cards and charts.
    """
    all_assets = query_db("SELECT id, asset_type, health_score, condition_status FROM assets;")
    
    total_assets = len(all_assets)
    if total_assets == 0:
        return {
            'overall_health': 100,
            'total_assets': 0,
            'healthy_assets': 0,
            'warning_assets': 0,
            'critical_assets': 0,
            'pending_maintenance': 0,
            'predicted_failures': 0,
            'streetlights': {'total': 0, 'working': 0, 'faulty': 0},
            'roads': {'total_km': 0.0, 'good_km': 0.0, 'damaged_km': 0.0},
            'pipelines': {'total_km': 0.0, 'normal_km': 0.0, 'leakage_km': 0.0},
            'drainage': {'total': 0, 'normal': 0, 'blocked': 0}
        }
        
    avg_health = round(sum(a['health_score'] for a in all_assets) / total_assets)
    
    healthy_count = sum(1 for a in all_assets if a['health_score'] >= 80)
    warning_count = sum(1 for a in all_assets if 60 <= a['health_score'] < 80)
    critical_count = sum(1 for a in all_assets if a['health_score'] < 60)
    
    # Streetlight stats
    sl_rows = query_db("""
        SELECT a.health_score, s.light_status, s.power_status 
        FROM assets a JOIN streetlights s ON a.id = s.asset_id;
    """)
    sl_total = len(sl_rows)
    sl_working = sum(1 for s in sl_rows if s['light_status'] == 'Working' and s['power_status'] == 'ON')
    sl_faulty = sl_total - sl_working
    
    # Road stats
    rd_rows = query_db("""
        SELECT r.length_km, r.road_condition, r.pothole_count, a.health_score
        FROM assets a JOIN roads r ON a.id = r.asset_id;
    """)
    rd_total_km = round(sum(float(r['length_km'] or 0) for r in rd_rows), 1)
    rd_good_km = round(sum(float(r['length_km'] or 0) for r in rd_rows if r['road_condition'] in ('Good', 'Moderate')), 1)
    rd_damaged_km = round(rd_total_km - rd_good_km, 1)
    rd_potholes = sum(int(r['pothole_count'] or 0) for r in rd_rows)
    
    # Water Pipeline stats (kept for legacy fallback)
    wp_rows = query_db("""
        SELECT p.length_km, p.leak_status, a.health_score
        FROM assets a JOIN water_pipelines p ON a.id = p.asset_id;
    """)
    wp_total_km = round(sum(float(p['length_km'] or 0) for p in wp_rows), 1) if wp_rows else 0.0
    wp_normal_km = round(sum(float(p['length_km'] or 0) for p in wp_rows if p['leak_status'] == 'Normal'), 1) if wp_rows else 0.0
    wp_leakage_km = round(wp_total_km - wp_normal_km, 1)
    
    # Drainage stats (kept for legacy fallback)
    dr_rows = query_db("""
        SELECT d.flow_status, d.blockage_level, a.health_score
        FROM assets a JOIN drainage d ON a.id = d.asset_id;
    """)
    dr_total = len(dr_rows) if dr_rows else 0
    dr_normal = sum(1 for d in dr_rows if d['flow_status'] == 'Normal') if dr_rows else 0
    dr_blocked = dr_total - dr_normal
    
    # Maintenance pending
    pending_maint = query_db(
        "SELECT COUNT(*) as cnt FROM maintenance WHERE status IN ('Pending', 'Assigned', 'In Progress');",
        one=True
    )['cnt']
    
    # Predicted failures (High Risk alerts + critical assets)
    high_risk_alerts = query_db(
        "SELECT COUNT(*) as cnt FROM alerts WHERE status IN ('Pending', 'In Progress') AND risk_level = 'High Risk';",
        one=True
    )['cnt']
    
    return {
        'overall_health': avg_health,
        'total_assets': total_assets,
        'healthy_assets': healthy_count,
        'warning_assets': warning_count,
        'critical_assets': critical_count,
        'pending_maintenance': pending_maint,
        'predicted_failures': high_risk_alerts,
        'streetlights': {
            'total': sl_total,
            'working': sl_working,
            'faulty': sl_faulty,
            'active_pct': round((sl_working / sl_total * 100), 1) if sl_total else 0
        },
        'roads': {
            'total_km': rd_total_km,
            'good_km': rd_good_km,
            'damaged_km': rd_damaged_km,
            'potholes': rd_potholes,
            'good_pct': round((rd_good_km / rd_total_km * 100), 1) if rd_total_km else 0
        },
        'pipelines': {
            'total_km': wp_total_km,
            'normal_km': wp_normal_km,
            'leakage_km': wp_leakage_km
        },
        'drainage': {
            'total': dr_total,
            'normal': dr_normal,
            'blocked': dr_blocked
        }
    }
