import io
import csv
from flask import Blueprint, render_template, request, Response, jsonify
from routes.auth import login_required
from models.asset import get_all_assets, get_campus_health_metrics
from models.maintenance import get_all_maintenance
from models.alert import get_all_alerts
from models.survey import get_survey_responses
from ml.predict import predict_for_asset

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def reports_page():
    """
    Endpoint: /reports (GET)
    
    Purpose:
        Renders the Campus Infrastructure Analytical Reports & Export Center.
        Provides multi-dimensional operational reports with real-time filtering:
        - Infrastructure Health & Asset Catalog
        - Work Order History & Completion Statistics
        - AI Predictive Alerts & Anomaly Records
        - Campus Community Feedback & Survey Audits
        
    Query Parameters:
        type (str, optional): Active report tab ('health', 'maintenance', 'alerts', 'surveys').
        asset_type (str, optional): Category filter ('all', 'streetlight', 'road', etc.).
        status (str, optional): Condition status filter.
        risk (str, optional): AI risk level filter ('all', 'High Risk', 'Medium Risk', 'Low Risk').
        
    Context Variables Passed to Template:
        report_type (str): Currently selected tab identifier.
        assets (list): Infrastructure assets enriched with live AI inference.
        maintenance (list): Maintenance work order logs.
        alerts (list): Predictive anomaly alerts.
        surveys (list): Community survey submissions.
        metrics (dict): Campus-wide summary health metrics.
        
    Returns:
        HTML template render ('reports.html').
    """
    # Step 1: Read report filtering parameters from URL query string
    report_type = request.args.get('type', 'health')
    asset_type = request.args.get('asset_type', 'all')
    status = request.args.get('status', 'all')
    risk_level = request.args.get('risk', 'all')
    
    # Step 2: Query base asset records according to applied category and status filters
    assets = get_all_assets(asset_type=asset_type, condition=status)
    
    # Step 3: Enrich asset rows with Scikit-learn AI predictions and apply risk filtering
    enriched_assets = []
    for a in assets:
        pred = predict_for_asset(a)
        # Apply risk level filter if specified
        if risk_level != 'all' and pred['risk_level'] != risk_level:
            continue
        item = dict(a)
        item['ai_risk'] = pred['risk_level']
        item['ai_window'] = pred['recommended_window']
        item['failure_prob'] = pred['high_risk_probability']
        enriched_assets.append(item)
        
    # Step 4: Retrieve datasets for all potential report views
    maintenance = get_all_maintenance()
    alerts = get_all_alerts()
    surveys = get_survey_responses(limit=30)
    metrics = get_campus_health_metrics()
    
    # Step 5: Render report dashboard with filtered data collections
    return render_template(
        'reports.html',
        report_type=report_type,
        asset_type=asset_type,
        status=status,
        risk_level=risk_level,
        assets=enriched_assets,
        maintenance=maintenance,
        alerts=alerts,
        surveys=surveys,
        metrics=metrics
    )

@reports_bp.route('/api/reports/export')
@login_required
def export_csv():
    """
    Endpoint: /api/reports/export (GET)
    
    Purpose:
        Generates and streams downloadable RFC 4180-compliant CSV spreadsheets
        for administrative record-keeping and external audits.
        
    Query Parameters:
        type (str): Type of report to export ('health', 'maintenance', 'alerts', 'surveys').
        
    Returns:
        Flask Response: In-memory streaming CSV file attachment with appropriate MIME type
                        and filename header.
    """
    # Step 1: Read requested export report type
    report_type = request.args.get('type', 'health')
    
    # Step 2: Initialize in-memory string buffer and CSV writer
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Step 3: Branch by report type to construct specific column headers and record rows
    if report_type == 'maintenance':
        writer.writerow(['Maintenance Code', 'Asset Tag', 'Asset Type', 'Location', 'Problem', 'Priority', 'Assigned Staff', 'Created Date', 'Due Date', 'Status'])
        records = get_all_maintenance()
        for r in records:
            writer.writerow([
                r['maintenance_code'], r['asset_tag'], r['asset_type'], r['location'],
                r['problem'], r['priority'], r['staff_name'] or 'Unassigned',
                r['created_date'], r['due_date'], r['status']
            ])
        filename = "campus_maintenance_report.csv"
        
    elif report_type == 'alerts':
        writer.writerow(['Alert ID', 'Asset Tag', 'Asset Type', 'Alert Type', 'Risk Level', 'Problem', 'Recommended Action', 'Status', 'Date'])
        alerts = get_all_alerts()
        for a in alerts:
            writer.writerow([
                a['id'], a['asset_tag'], a['asset_type'], a['alert_type'],
                a['risk_level'], a['problem'], a['recommended_action'], a['status'], a['created_at']
            ])
        filename = "campus_predictive_alerts_report.csv"
        
    elif report_type == 'surveys':
        writer.writerow(['Response ID', 'Respondent', 'Role', 'Streetlights Working', 'Roads Condition', 'Water Supply Regular', 'Drainage Blocked', 'Satisfaction (1-5)', 'AI Monitoring Useful', 'Date'])
        surveys = get_survey_responses(limit=200)
        for s in surveys:
            writer.writerow([
                s['id'], s['respondent_name'], s['respondent_role'], s['streetlights_working'],
                s['roads_potholes'], s['water_supply_regular'], s['drainage_blocked'],
                s['maintenance_satisfaction'], s['ai_monitoring_useful'], s['created_at']
            ])
        filename = "campus_surveys_report.csv"
        
    else:  # 'health' / default asset catalog
        writer.writerow(['Asset Tag', 'Name', 'Type', 'Location', 'Health Score', 'Condition', 'Age (Yrs)', 'Previous Failures', 'Complaints', 'AI Risk Level', 'Predicted Maintenance Window'])
        assets = get_all_assets()
        for a in assets:
            pred = predict_for_asset(a)
            writer.writerow([
                a['asset_tag'], a['name'], a['asset_type'], a['location'],
                a['health_score'], a['condition_status'], a['age_years'],
                a['previous_failures'], a['complaint_count'], pred['risk_level'],
                pred['recommended_window']
            ])
        filename = "campus_infrastructure_health_report.csv"
        
    # Step 4: Rewind string buffer pointer to the beginning of the file
    output.seek(0)
    
    # Step 5: Deliver HTTP attachment download response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
