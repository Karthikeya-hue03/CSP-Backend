from flask import Blueprint, render_template, request, flash, redirect, url_for
from routes.auth import login_required, role_required
from models.user import get_all_users
from database import get_db_type, check_mysql_connection
from config import Config
import init_db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def settings_page():
    """
    Endpoint: /settings (GET)
    
    Purpose:
        Serves the System Settings, Diagnostic Status & Access Management console.
        Allows administrators to:
        - View registered user accounts, assigned roles, and login emails.
        - Check database connectivity status (active MySQL server vs zero-config SQLite engine).
        - Inspect server configuration parameters and ML threshold constants.
        
    Context Variables Passed to Template:
        users (list): All registered campus system user accounts.
        db_mode (str): Active database dialect ('mysql' or 'sqlite').
        mysql_live (bool): Connectivity ping result to external MySQL instance.
        config (class): Configuration class attributes.
        
    Returns:
        HTML template render ('settings.html').
    """
    # Step 1: Query user accounts across campus departments
    users = get_all_users()
    
    # Step 2: Determine active database engine and test live connection
    db_mode = get_db_type()
    mysql_live = check_mysql_connection()
    
    # Step 3: Render settings console with diagnostic health variables
    return render_template(
        'settings.html',
        users=users,
        db_mode=db_mode,
        mysql_live=mysql_live,
        config=Config
    )

@settings_bp.route('/settings/reseed', methods=['POST'])
@role_required('Admin')
def reseed_database():
    """
    Endpoint: /settings/reseed (POST)
    
    Purpose:
        Administrative reset and demonstration utility.
        Triggers `init_db.main()` to rebuild database tables and populate fresh,
        realistic demonstration assets, work orders, AI alerts, and survey records.
        
    Authorization:
        Restricted to 'Admin' users only.
        
    Returns:
        HTTP 302 redirect back to /settings with a success or error flash message.
    """
    # Step 1: Execute complete database re-seeding routine
    try:
        init_db.main()
        flash('Database successfully re-seeded with fresh demonstration records!', 'success')
    except Exception as e:
        flash(f'Error re-seeding database: {e}', 'danger')
        
    # Step 2: Redirect user back to the settings management page
    return redirect(url_for('settings.settings_page'))

@settings_bp.route('/settings/relocate', methods=['POST'])
@role_required('Admin')
def update_map_location():
    """
    Endpoint: /settings/relocate (POST)
    
    Purpose:
        Updates the GIS campus center coordinates and shifts all 58 infrastructure
        asset pins in the database to the specified latitude and longitude.
        
    Authorization:
        Restricted to 'Admin' role.
        
    Form Fields:
        latitude (float): New campus latitude.
        longitude (float): New campus longitude.
        zoom (int): Map zoom level (default 17).
        campus_name (str, optional): Custom college or campus identifier.
        
    Returns:
        HTTP 302 redirect back to /settings.
    """
    from relocate_campus import relocate_campus
    try:
        lat = float(request.form.get('latitude', 17.385044))
        lng = float(request.form.get('longitude', 78.486671))
        zoom = int(request.form.get('zoom', 17))
        name = request.form.get('campus_name')
        
        # Execute pin relocation and .env update
        relocate_campus(lat, lng, zoom, name)
        
        # Update runtime in-memory Config attributes
        Config.CAMPUS_CENTER_LAT = lat
        Config.CAMPUS_CENTER_LNG = lng
        Config.CAMPUS_ZOOM = zoom
        
        flash(f'Campus map location successfully updated to ({lat:.4f}, {lng:.4f})! All 58 asset pins have been shifted to the new location.', 'success')
    except Exception as e:
        flash(f'Error updating campus location: {e}', 'danger')
        
    return redirect(url_for('settings.settings_page'))
