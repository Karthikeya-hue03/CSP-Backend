import os
import logging
from pathlib import Path
from flask import Flask, render_template, session, redirect, url_for
from config import Config
from database import get_db_type, query_db
from models.alert import get_alert_counts
import init_db

# Configure system logging for tracking application events and database interactions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('campus_infra')

def create_app():
    """
    Application Factory Function.
    
    How it works:
    1. Instantiates the core Flask web application instance.
    2. Loads configuration parameters (secret keys, database credentials, campus coordinates) from Config.
    3. Checks the state of the active database engine; if using SQLite and the database file is missing
       or empty, automatically populates all tables and demo campus infrastructure assets.
    4. Registers all modular feature Blueprints (auth, dashboard, assets, maintenance, predictions, surveys, reports, settings).
    5. Injects global session and navigation variables via context processor so every Jinja template has access to them.
    6. Registers custom template filters and HTTP error handlers (404 and 500).
    
    Returns:
        Flask: The fully configured Flask application instance ready to serve requests.
    """
    # Resolve the project root (one level above this backend/ folder)
    _ROOT = Path(__file__).resolve().parent.parent

    # Tell Flask where HTML templates and static assets live (inside frontend/)
    app = Flask(
        __name__,
        template_folder=str(_ROOT / 'frontend' / 'templates'),
        static_folder=str(_ROOT / 'frontend' / 'static'),
        static_url_path='/static'
    )
    app.config.from_object(Config)
    
    # Auto-initialize SQLite database if database is empty/missing
    try:
        if get_db_type() == 'sqlite':
            if not Config.SQLITE_DB_PATH.exists() or os.path.getsize(Config.SQLITE_DB_PATH) == 0:
                logger.info("Initializing database with demo campus records...")
                init_db.init_sqlite_database()
    except Exception as e:
        logger.warning(f"Database pre-check notice: {e}")
        
    # Register Blueprints for modular route organization
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.assets import assets_bp
    from routes.maintenance import maintenance_bp
    from routes.predictions import predictions_bp
    from routes.surveys import surveys_bp
    from routes.reports import reports_bp
    from routes.settings import settings_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(surveys_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    
    # Global context processor for navigation badges and user session info
    @app.context_processor
    def inject_global_context():
        """
        Global Context Processor.
        
        How it works:
        - Automatically executes before rendering any Jinja2 template.
        - Checks Flask session for authenticated user details (name, email, role, department).
        - Queries the database for active unresolved predictive alerts to show live notification badges in the topbar.
        - Provides the active database engine type ('mysql' or 'sqlite') to render the database badge.
        
        Returns:
            dict: Context variables injected into the global template scope.
        """
        alert_info = {'Critical': 0, 'Warning': 0, 'Maintenance': 0, 'total': 0}
        if 'user_id' in session:
            try:
                alert_info = get_alert_counts()
            except Exception:
                pass
        return {
            'app_title': 'Smart Campus Infrastructure Health & Predictive Maintenance',
            'current_user': {
                'id': session.get('user_id'),
                'name': session.get('user_name', 'Guest'),
                'email': session.get('user_email'),
                'role': session.get('user_role', 'Viewer'),
                'department': session.get('user_department')
            },
            'active_db': get_db_type(),
            'global_alert_counts': alert_info
        }
        
    # Custom Jinja template filters
    @app.template_filter('badge_class')
    def badge_class_filter(val):
        """
        Jinja2 Template Filter for Status Badges.
        
        How it works:
        - Normalizes input status/condition string to lowercase.
        - Maps operational states (e.g. 'Good', 'Working', 'Completed', 'Low Risk') to CSS class 'badge-success'.
        - Maps intermediate warning states (e.g. 'Moderate', 'Flickering', 'Medium Risk') to 'badge-warning'.
        - Maps elevated wear states (e.g. 'Poor', 'Leak Detected', 'Low Flow', 'Blocked') to 'badge-orange'.
        - Maps emergency states (e.g. 'Critical', 'Faulty', 'High Risk', 'Overflow') to 'badge-danger'.
        
        Args:
            val (str): The raw status or condition string from database.
            
        Returns:
            str: Appropriate CSS badge class name for UI styling.
        """
        v = str(val).lower()
        if v in ('good', 'normal', 'working', 'completed', 'low risk', 'resolved', 'yes', 'on'):
            return 'badge-success'
        elif v in ('moderate', 'flickering', 'assigned', 'medium risk', 'warning', 'minor'):
            return 'badge-warning'
        elif v in ('poor', 'in progress', 'leak detected', 'low flow', 'urgent', 'blocked'):
            return 'badge-orange'
        elif v in ('critical', 'faulty', 'power off', 'high risk', 'severe', 'overflow'):
            return 'badge-danger'
        return 'badge-secondary'

    # HTTP Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        """
        HTTP 404 Error Handler.
        
        How it works:
        - Catches invalid or non-existent URLs.
        - Renders a clean user-friendly error view using base layout instead of a raw server crash page.
        
        Args:
            e (Exception): The Werkzeug NotFound HTTP exception.
            
        Returns:
            tuple: Rendered HTML template and HTTP status code 404.
        """
        return render_template('base.html', error_title="404 - Page Not Found", error_message="The requested resource could not be found."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        """
        HTTP 500 Error Handler.
        
        How it works:
        - Catches unhandled server-side application errors.
        - Logs the incident and displays a friendly error page.
        
        Args:
            e (Exception): The unhandled exception.
            
        Returns:
            tuple: Rendered HTML template and HTTP status code 500.
        """
        return render_template('base.html', error_title="500 - Server Error", error_message="An internal server error occurred."), 500

    return app

# Instantiate the application for WSGI servers and direct execution
app = create_app()

if __name__ == '__main__':
    # Print startup banner displaying environment configuration and listening URL
    print("\n" + "="*70)
    print("  AI-Powered Campus Infrastructure Health Monitoring & Maintenance")
    print(f"  Database Engine: {get_db_type().upper()}")
    print("  Server running at: http://127.0.0.1:5000")
    print("="*70 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
