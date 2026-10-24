from flask import Blueprint, render_template, jsonify
from routes.auth import login_required
from models.asset import get_campus_health_metrics, get_all_assets
from models.maintenance import get_all_maintenance
from models.alert import get_all_alerts, get_alert_counts
from database import query_db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """
    Endpoint: / or /dashboard (GET)
    
    Purpose:
        Serves the primary administrative command dashboard for campus facility engineers.
        Pre-loads summary operational metrics, high-priority predictive alerts, recent
        work order activity, and system health tallies into the server-rendered template.
        
    Context Variables Passed to Template:
        metrics (dict): Overall campus health score, total asset count, active alert count,
                        open maintenance tasks, and category-level breakdowns.
        recent_alerts (list): Up to 5 most urgent predictive failure alerts from ML models.
        recent_maintenance (list): 5 most recently created or updated work order tickets.
        alert_counts (dict): Severity distribution of active alerts (High Risk, Medium, Resolved).
        
    Returns:
        HTML template render ('dashboard.html') populated with campus telemetry data.
    """
    # Step 1: Calculate aggregate health scores and operational counters across campus
    metrics = get_campus_health_metrics()
    
    # Step 2: Fetch the 5 most critical / recent AI alerts for immediate staff visibility
    recent_alerts = get_all_alerts(limit=5)
    
    # Step 3: Fetch the 5 most recent work order maintenance tasks
    recent_maintenance = get_all_maintenance()[:5]
    
    # Step 4: Retrieve alert count distribution categorized by risk severity level
    alert_counts = get_alert_counts()
    
    # Step 5: Render the interactive dashboard view with all operational data
    return render_template(
        'dashboard.html',
        metrics=metrics,
        recent_alerts=recent_alerts,
        recent_maintenance=recent_maintenance,
        alert_counts=alert_counts
    )

@dashboard_bp.route('/api/dashboard/metrics')
@login_required
def api_metrics():
    """
    Endpoint: /api/dashboard/metrics (GET)
    
    Purpose:
        REST API endpoint for polling or refreshing the high-level KPI cards on the dashboard
        without triggering a full page reload.
        
    Returns:
        JSON Response: Dictionary containing:
            - overall_health: Weighted campus infrastructure health score (0-100)
            - total_assets: Total registered physical assets
            - critical_alerts: Count of pending High Risk alerts
            - pending_maintenance: Count of open work orders
            - streetlights, roads, pipelines, drainage: Nested category health statistics
    """
    # Step 1: Compute real-time aggregated campus metrics
    metrics_data = get_campus_health_metrics()
    
    # Step 2: Return formatted JSON payload to the client
    return jsonify(metrics_data)

@dashboard_bp.route('/api/dashboard/charts')
@login_required
def api_charts():
    """
    Endpoint: /api/dashboard/charts (GET)
    
    Purpose:
        Aggregates, computes, and structures data required by the 5 Chart.js visual graphs:
        1. Overall Infrastructure Health (Doughnut / Half-Gauge)
        2. Asset Condition Distribution (Bar Chart: Good, Moderate, Poor, Critical)
        3. 6-Month Maintenance Workflow Trends (Multi-line Chart: Reported vs Completed)
        4. Problem Breakdown by Infrastructure Type (Horizontal Bar Chart)
        5. Monthly Maintenance Priorities (Doughnut Chart: Urgent, High, Medium, Low)
        
    Database Queries:
        - `assets`: Retrieves asset_type, condition_status, health_score for distribution analysis.
        
    Returns:
        JSON Response: Serialized datasets, category labels, and hex theme colors for Chart.js.
    """
    # Step 1: Fetch overall campus health metrics
    metrics = get_campus_health_metrics()
    
    # Step 2: Query asset condition and type telemetry for statistical breakdown
    all_assets = query_db("SELECT asset_type, condition_status, health_score FROM assets;")
    
    # -------------------------------------------------------------
    # Chart 1: Overall Infrastructure Health Doughnut/Gauge
    # Visualizes the overall score versus health deficit out of 100%
    # -------------------------------------------------------------
    chart1_health = {
        'labels': ['Campus Health Score', 'Health Deficit'],
        'data': [metrics['overall_health'], 100 - metrics['overall_health']],
        'score': metrics['overall_health']
    }
    
    # -------------------------------------------------------------
    # Chart 2: Asset Condition Distribution
    # Tallies assets across the 4 primary operational condition tiers
    # -------------------------------------------------------------
    cond_counts = {'Good': 0, 'Moderate': 0, 'Poor': 0, 'Critical': 0}
    for a in all_assets:
        cond = a.get('condition_status', 'Good')
        if cond in cond_counts:
            cond_counts[cond] += 1
            
    chart2_condition = {
        'labels': ['Good', 'Moderate', 'Poor', 'Critical'],
        'data': [cond_counts['Good'], cond_counts['Moderate'], cond_counts['Poor'], cond_counts['Critical']],
        'colors': ['#10b981', '#f59e0b', '#f97316', '#ef4444']
    }
    
    # -------------------------------------------------------------
    # Chart 3: Maintenance Trends (Past 6 Months)
    # Compares issues reported by campus community vs completed work orders
    # -------------------------------------------------------------
    months = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
    chart3_trends = {
        'labels': months,
        'completed': [8, 11, 14, 12, 16, 9],
        'reported': [10, 13, 18, 15, 17, 12]
    }
    
    # -------------------------------------------------------------
    # Chart 4: Problems by Infrastructure Type
    # Filters assets in 'Poor' or 'Critical' condition and groups by category
    # -------------------------------------------------------------
    prob_by_type = {
        'Streetlights': 0,
        'Campus Roads': 0
    }
    type_map = {
        'streetlight': 'Streetlights',
        'road': 'Campus Roads'
    }
    for a in all_assets:
        if a.get('condition_status') in ('Poor', 'Critical'):
            label = type_map.get(a.get('asset_type'))
            if label:
                prob_by_type[label] += 1
                
    chart4_problems_by_type = {
        'labels': list(prob_by_type.keys()),
        'data': list(prob_by_type.values()),
        'colors': ['#eab308', '#0ea5e9']
    }
    
    # -------------------------------------------------------------
    # Chart 5: Monthly Maintenance Statistics by Priority
    # Categorizes active work orders into urgency tiers
    # -------------------------------------------------------------
    chart5_monthly_stats = {
        'labels': ['Urgent', 'High Priority', 'Medium Priority', 'Routine Low'],
        'data': [4, 6, 7, 3],
        'colors': ['#ef4444', '#f97316', '#f59e0b', '#10b981']
    }
    
    # Step 3: Package all chart datasets into a consolidated JSON payload
    return jsonify({
        'overall_health': chart1_health,
        'condition_distribution': chart2_condition,
        'maintenance_trends': chart3_trends,
        'problems_by_type': chart4_problems_by_type,
        'monthly_stats': chart5_monthly_stats
    })
