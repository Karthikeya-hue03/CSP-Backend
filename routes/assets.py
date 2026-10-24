from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from routes.auth import login_required, role_required
from models.asset import (
    get_all_assets, get_asset_by_id, get_streetlights, get_roads,
    get_water_pipelines, get_drainage, create_streetlight, create_road,
    create_water_pipeline, create_drainage, update_streetlight, update_road,
    update_water_pipeline, update_drainage, delete_asset
)
from ml.predict import predict_for_asset
from database import query_db

assets_bp = Blueprint('assets', __name__)

# =============================================================================
# Web Page Views (HTML Template Renders)
# =============================================================================

@assets_bp.route('/map')
@login_required
def campus_map():
    """
    Endpoint: /map (GET)
    
    Purpose:
        Renders the Leaflet.js interactive GIS campus infrastructure map.
        The frontend map fetches geospatial asset pins and telemetry markers
        via asynchronous AJAX calls to /api/assets.
        
    Returns:
        HTML template render ('map.html').
    """
    return render_template('map.html')

@assets_bp.route('/streetlights')
@login_required
def streetlights_page():
    """
    Endpoint: /streetlights (GET)
    
    Purpose:
        Displays the dedicated Streetlight Infrastructure management view.
        Lists all campus lighting poles with wattage, lumen output, power state,
        light health status, and operational schedules. Supports query string search.
        
    Query Parameters:
        search (str, optional): Text filter matching asset name, pole number, or tag.
        
    Returns:
        HTML template render ('streetlights.html') with streetlight records.
    """
    # Step 1: Extract optional search query from URL parameters
    search = request.args.get('search')
    
    # Step 2: Fetch joined assets and streetlights subtable data
    items = get_streetlights(search=search)
    
    # Step 3: Render template with matching streetlight records
    return render_template('streetlights.html', streetlights=items, search=search)

@assets_bp.route('/roads')
@login_required
def roads_page():
    """
    Endpoint: /roads (GET)
    
    Purpose:
        Displays the Road Network Condition Monitoring view.
        Presents surface pavement types (Asphalt, Concrete, Pavers), pothole counts,
        crack severity classifications, length in km, and traffic priority status.
        
    Query Parameters:
        search (str, optional): Text filter matching road name, tag, or location.
        
    Returns:
        HTML template render ('roads.html') with road network records.
    """
    # Step 1: Extract search query filter if supplied
    search = request.args.get('search')
    
    # Step 2: Query database for joined road infrastructure data
    items = get_roads(search=search)
    
    # Step 3: Render road monitoring interface
    return render_template('roads.html', roads=items, search=search)

@assets_bp.route('/pipelines')
@login_required
def pipelines_page():
    """
    Endpoint: /pipelines (GET)
    Redirects to Streetlight Infrastructure Monitoring as pipelines have been deprecated.
    """
    flash('Water Pipelines monitoring has been removed to focus on Streetlights and Road networks.', 'info')
    return redirect(url_for('assets.streetlights_page'))

@assets_bp.route('/drainage')
@login_required
def drainage_page():
    """
    Endpoint: /drainage (GET)
    Redirects to Road Infrastructure Monitoring as drainage has been deprecated.
    """
    flash('Drainage monitoring has been removed to focus on Streetlights and Road networks.', 'info')
    return redirect(url_for('assets.roads_page'))

# =============================================================================
# REST API Endpoints (Data & CRUD Operations)
# =============================================================================

@assets_bp.route('/api/assets', methods=['GET'])
@login_required
def api_get_assets():
    """
    Endpoint: /api/assets (GET)
    
    Purpose:
        REST API providing all registered infrastructure assets enriched with:
        - Precise geographic coordinates (latitude, longitude) for map rendering.
        - Real-time Scikit-learn AI predictive failure risk and maintenance windows.
        
    Query Parameters:
        type (str, optional): Filter by category ('streetlight', 'road', 'water_pipeline', 'drainage').
        condition (str, optional): Filter by condition ('Good', 'Moderate', 'Poor', 'Critical').
        search (str, optional): Text search query.
        
    Returns:
        JSON Response: Array of enriched asset objects.
    """
    # Step 1: Extract filter criteria from request URL
    asset_type = request.args.get('type')
    condition = request.args.get('condition')
    search = request.args.get('search')
    
    # Step 2: Query matching base asset records from the database
    assets = get_all_assets(asset_type=asset_type, condition=condition, search=search)
    
    # Step 3: Enrich each asset record with on-the-fly Machine Learning predictions
    results = []
    for a in assets:
        pred = predict_for_asset(a)
        a_dict = dict(a)
        a_dict['ai_risk'] = pred['risk_level']
        a_dict['ai_window'] = pred['recommended_window']
        results.append(a_dict)
        
    # Step 4: Return enriched JSON array to the client
    return jsonify(results)

@assets_bp.route('/api/assets/<int:asset_id>', methods=['GET'])
@login_required
def api_get_asset_detail(asset_id):
    """
    Endpoint: /api/assets/<int:asset_id> (GET)
    
    Purpose:
        Fetches the complete telemetry and specification profile for an individual asset,
        joining its primary record, category-specific subtable, and Scikit-learn AI inference.
        
    Parameters:
        asset_id (int): Primary key ID of the target asset.
        
    Returns:
        JSON Response: Dictionary containing:
            - asset: General attributes (tag, name, condition, age, health_score, coordinates)
            - details: Specialized subtable attributes (wattage, pothole count, pressure, etc.)
            - ai_prediction: Full ML inference results with probabilities and recommended action
    """
    # Step 1: Fetch primary asset row
    asset = get_asset_by_id(asset_id)
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404
        
    # Step 2: Query category-specific subtable based on asset type
    a_type = asset['asset_type']
    specific = None
    if a_type == 'streetlight':
        specific = query_db("SELECT * FROM streetlights WHERE asset_id = %s;", (asset_id,), one=True)
    elif a_type == 'road':
        specific = query_db("SELECT * FROM roads WHERE asset_id = %s;", (asset_id,), one=True)
    elif a_type == 'water_pipeline':
        specific = query_db("SELECT * FROM water_pipelines WHERE asset_id = %s;", (asset_id,), one=True)
    elif a_type == 'drainage':
        specific = query_db("SELECT * FROM drainage WHERE asset_id = %s;", (asset_id,), one=True)
        
    # Step 3: Execute Scikit-learn Random Forest model inference on this asset's telemetry
    ai_prediction = predict_for_asset(asset)
    
    # Step 4: Return consolidated asset detail package
    return jsonify({
        'asset': dict(asset),
        'details': dict(specific) if specific else {},
        'ai_prediction': ai_prediction
    })

@assets_bp.route('/api/streetlights', methods=['GET'])
@login_required
def api_get_streetlights():
    """
    Endpoint: /api/streetlights (GET)
    
    Purpose:
        REST API returning streetlight records joined with pole and luminaire telemetry.
        
    Query Parameters:
        search (str, optional): Keyword search filter.
        
    Returns:
        JSON Response: Array of streetlight objects.
    """
    search = request.args.get('search')
    return jsonify(get_streetlights(search=search))

@assets_bp.route('/api/roads', methods=['GET'])
@login_required
def api_get_roads():
    """
    Endpoint: /api/roads (GET)
    
    Purpose:
        REST API returning road records joined with surface condition telemetry.
        
    Query Parameters:
        search (str, optional): Keyword search filter.
        
    Returns:
        JSON Response: Array of road network objects.
    """
    search = request.args.get('search')
    return jsonify(get_roads(search=search))

@assets_bp.route('/api/pipelines', methods=['GET'])
@login_required
def api_get_pipelines():
    """
    Endpoint: /api/pipelines (GET)
    
    Purpose:
        REST API returning water distribution pipeline records and sensor telemetry.
        
    Query Parameters:
        search (str, optional): Keyword search filter.
        
    Returns:
        JSON Response: Array of water pipeline objects.
    """
    search = request.args.get('search')
    return jsonify(get_water_pipelines(search=search))

@assets_bp.route('/api/drainage', methods=['GET'])
@login_required
def api_get_drainage():
    """
    Endpoint: /api/drainage (GET)
    
    Purpose:
        REST API returning drainage channels and stormwater blockage telemetry.
        
    Query Parameters:
        search (str, optional): Keyword search filter.
        
    Returns:
        JSON Response: Array of drainage channel objects.
    """
    search = request.args.get('search')
    return jsonify(get_drainage(search=search))

@assets_bp.route('/api/streetlights/next-tag', methods=['GET'])
@login_required
def api_next_streetlight_tag():
    """
    Endpoint: /api/streetlights/next-tag (GET)
    Returns the next available sequential streetlight asset tag and pole number for map placement.
    """
    from models.asset import get_next_streetlight_tag
    tag, pole = get_next_streetlight_tag()
    return jsonify({'next_tag': tag, 'next_pole': pole})

@assets_bp.route('/api/assets', methods=['POST'])
@role_required('Admin')
def api_create_asset():
    """
    Endpoint: /api/assets (POST)
    
    Purpose:
        Registers a new campus infrastructure asset. Dispatches the insert operation
        to the appropriate model function according to `asset_type` to populate both
        the parent `assets` table and the respective subtable atomically.
        
    Authorization:
        Restricted to 'Admin' users via @role_required.
        
    Request Payload (JSON or Form Data):
        asset_type (str): 'streetlight' or 'road'.
        asset_tag (str, optional): Unique identifier code (auto-generated if omitted).
        name (str, optional): Human-readable name.
        location (str, optional): Physical campus location / landmark.
        latitude (float), longitude (float): GPS coordinates.
        health_score (int): Initial health rating (0-100).
        condition_status (str): 'Good', 'Moderate', 'Poor', or 'Critical'.
        ... plus category-specific fields (wattage, length_km, etc.)
        
    Returns:
        JSON Response with created asset ID & enriched data (201) or HTTP 302 redirect for HTML forms.
    """
    # Step 1: Parse payload from either JSON body or HTML multipart form
    data = request.get_json() if request.is_json else request.form.to_dict()
    asset_type = data.get('asset_type') or 'streetlight'
    data['asset_type'] = asset_type
    
    # Step 2: Route to specialized category creator based on asset_type
    try:
        if asset_type == 'streetlight':
            asset_id = create_streetlight(data)
        elif asset_type == 'road':
            asset_id = create_road(data)
        elif asset_type == 'water_pipeline':
            asset_id = create_water_pipeline(data)
        elif asset_type == 'drainage':
            asset_id = create_drainage(data)
        else:
            return jsonify({'error': f'Unsupported asset type: {asset_type}'}), 400
            
        # Step 3: Fetch newly created asset to enrich response for instant map rendering
        new_asset = get_asset_by_id(asset_id)
        
        if request.is_json:
            pred = predict_for_asset(new_asset)
            asset_dict = dict(new_asset)
            asset_dict['ai_risk'] = pred['risk_level']
            asset_dict['ai_window'] = pred['recommended_window']
            return jsonify({
                'success': True,
                'id': asset_id,
                'asset': asset_dict,
                'message': f"Asset {asset_dict['asset_tag']} created successfully!"
            }), 201
            
        flash(f"Infrastructure asset {new_asset['asset_tag']} created successfully!", 'success')
        return redirect(request.referrer or url_for('dashboard.index'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error creating asset: {e}', 'danger')
        return redirect(request.referrer or url_for('dashboard.index'))

@assets_bp.route('/api/assets/<int:asset_id>', methods=['PUT', 'POST'])
@role_required('Admin', 'Maintenance Staff')
def api_update_asset(asset_id):
    """
    Endpoint: /api/assets/<int:asset_id> (PUT, POST)
    
    Purpose:
        Updates an existing infrastructure asset's status, telemetry, health score,
        and category-specific attributes.
        
    Authorization:
        Restricted to 'Admin' and 'Maintenance Staff'.
        
    Parameters:
        asset_id (int): Primary key ID of the asset to update.
        
    Request Payload (JSON or Form Data):
        Fields to update (name, condition_status, health_score, category telemetry, etc.)
        
    Returns:
        JSON Response indicating success or HTTP 302 redirect for browser forms.
    """
    # Step 1: Parse request data from JSON or form payload
    data = request.get_json() if request.is_json else request.form.to_dict()
    
    # Step 2: Verify asset exists
    asset = get_asset_by_id(asset_id)
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404
        
    a_type = asset['asset_type']
    
    # Step 3: Dispatch update to appropriate subtable handler
    try:
        if a_type == 'streetlight':
            update_streetlight(asset_id, data)
        elif a_type == 'road':
            update_road(asset_id, data)
        elif a_type == 'water_pipeline':
            update_water_pipeline(asset_id, data)
        elif a_type == 'drainage':
            update_drainage(asset_id, data)
            
        # Step 4: Return structured JSON or flash notice
        if request.is_json:
            return jsonify({'success': True, 'message': 'Asset updated successfully'})
            
        flash('Asset updated successfully!', 'success')
        return redirect(request.referrer or url_for('dashboard.index'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error updating asset: {e}', 'danger')
        return redirect(request.referrer or url_for('dashboard.index'))

@assets_bp.route('/api/assets/<int:asset_id>', methods=['DELETE'])
@role_required('Admin')
def api_delete_asset(asset_id):
    """
    Endpoint: /api/assets/<int:asset_id> (DELETE)
    
    Purpose:
        Permanently deletes an infrastructure asset and cascades deletion to
        associated subtables, maintenance work orders, and predictive alerts.
        
    Authorization:
        Restricted strictly to 'Admin' role.
        
    Parameters:
        asset_id (int): Primary key ID of the asset to delete.
        
    Returns:
        JSON Response indicating deletion confirmation.
    """
    # Step 1: Check existence of the asset
    asset = get_asset_by_id(asset_id)
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404
        
    # Step 2: Execute cascading deletion via asset model
    try:
        delete_asset(asset_id)
        return jsonify({'success': True, 'message': f"Asset {asset['asset_tag']} deleted successfully"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
