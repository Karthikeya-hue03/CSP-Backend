from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from routes.auth import login_required, role_required
from models.asset import get_all_assets, get_asset_by_id
from models.alert import get_all_alerts, get_alert_by_id, create_alert, update_alert_status, get_alert_counts
from models.maintenance import create_maintenance_task, generate_maintenance_code
from ml.predict import predict_maintenance_risk, predict_for_asset
from datetime import date, timedelta

predictions_bp = Blueprint('predictions', __name__)

@predictions_bp.route('/predictions')
@login_required
def predictions_page():
    """
    Endpoint: /predictions (GET)
    
    Purpose:
        Serves the AI-Powered Predictive Maintenance & Anomaly Detection Center.
        Performs batch inference on all campus assets using the trained Scikit-learn
        Random Forest model and presents:
        - Interactive ML simulation sandbox (simulate what-if telemetry).
        - Real-time asset health predictions with days-to-failure estimations.
        - High-priority automated alert queue with one-click work order conversion.
        
    Context Variables Passed to Template:
        asset_predictions (list): Combined asset records and their ML risk inference outputs.
        alerts (list): Active predictive failure notifications.
        alert_counts (dict): Categorical counts of alerts by risk tier.
        
    Returns:
        HTML template render ('predictions.html').
    """
    # Step 1: Load all campus assets and existing alerts
    assets = get_all_assets()
    alerts = get_all_alerts()
    alert_counts = get_alert_counts()
    
    # Step 2: Run batch machine learning inference across every campus asset
    asset_predictions = []
    for a in assets:
        pred = predict_for_asset(a)
        asset_predictions.append({
            'asset': a,
            'prediction': pred
        })
        
    # Step 3: Render predictive maintenance interface with live ML outputs
    return render_template(
        'predictions.html',
        asset_predictions=asset_predictions,
        alerts=alerts,
        alert_counts=alert_counts
    )

@predictions_bp.route('/api/predict', methods=['POST'])
@login_required
def api_predict():
    """
    Endpoint: /api/predict (POST)
    
    Purpose:
        Real-time Scikit-learn Random Forest model inference endpoint.
        Supports two invocation modes:
        1. By Asset ID: Fetches saved telemetry from DB and scores the asset.
        2. Arbitrary Telemetry: Accepts synthetic/simulated parameters for interactive sandbox testing.
        
    Request Payload (JSON or Form Data):
        asset_id (int, optional): If supplied, loads telemetry from DB.
        age_years (float, optional): Asset operational age.
        previous_failures (int, optional): Historical breakdown count.
        health_score (int, optional): Engineer assessed health score (0-100).
        inspection_frequency (int, optional): Inspections conducted per year.
        complaint_count (int, optional): Registered community complaints.
        previous_maintenance_count (int, optional): Previous work orders count.
        condition (str, optional): 'Good', 'Moderate', 'Poor', or 'Critical'.
        days_since_last_maintenance (int, optional): Days elapsed since last repair.
        
    Returns:
        JSON Response:
            - risk_level: 'Low Risk', 'Medium Risk', or 'High Risk'
            - predicted_failure_days: Estimated days remaining before operational failure
            - recommended_window: Recommended maintenance timeframe
            - recommended_action: Prescriptive guidance for field engineers
            - high_risk_probability, medium_risk_probability, low_risk_probability: Probabilities in %
            - badge_color: Bootstrap color token for UI rendering
    """
    # Step 1: Parse request data from JSON or form payload
    data = request.get_json() if request.is_json else request.form.to_dict()
    
    # Step 2: Mode 1 - If asset_id is provided, load its features directly from the database
    if 'asset_id' in data and data['asset_id']:
        asset = get_asset_by_id(int(data['asset_id']))
        if not asset:
            return jsonify({'error': 'Asset not found'}), 404
        result = predict_for_asset(asset)
        result['asset'] = dict(asset)
        return jsonify(result)
        
    # Step 3: Mode 2 - Parse manual or sandbox telemetry parameters
    try:
        age_years = float(data.get('age_years', 2.0))
        previous_failures = int(data.get('previous_failures', 0))
        health_score = int(data.get('health_score', 80))
        inspection_frequency = int(data.get('inspection_frequency', 4))
        complaint_count = int(data.get('complaint_count', 0))
        previous_maintenance_count = int(data.get('previous_maintenance_count', 1))
        condition = data.get('condition', 'Good')
        days_since_last_maintenance = int(data.get('days_since_last_maintenance', 30))
        
        # Step 4: Execute inference pipeline via predict_maintenance_risk
        result = predict_maintenance_risk(
            age_years=age_years,
            previous_failures=previous_failures,
            health_score=health_score,
            inspection_frequency=inspection_frequency,
            complaint_count=complaint_count,
            previous_maintenance_count=previous_maintenance_count,
            condition=condition,
            days_since_last_maintenance=days_since_last_maintenance
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f"Prediction failed: {str(e)}"}), 400

@predictions_bp.route('/api/alerts', methods=['GET'])
@login_required
def api_get_alerts():
    """
    Endpoint: /api/alerts (GET)
    
    Purpose:
        REST API endpoint to fetch predictive alerts with optional filtering.
        
    Query Parameters:
        status (str, optional): 'Pending', 'In Progress', 'Resolved'.
        type (str, optional): 'Predictive Failure', 'Threshold Breach', 'Anomaly'.
        risk (str, optional): 'High Risk', 'Medium Risk', 'Low Risk'.
        
    Returns:
        JSON Response: Array of alert objects joined with asset tag and location.
    """
    # Step 1: Read query filters
    status = request.args.get('status')
    alert_type = request.args.get('type')
    risk_level = request.args.get('risk')
    
    # Step 2: Query database and return JSON array
    return jsonify(get_all_alerts(status=status, alert_type=alert_type, risk_level=risk_level))

@predictions_bp.route('/api/alerts/<int:alert_id>/status', methods=['POST'])
@role_required('Admin', 'Maintenance Staff')
def api_update_alert_status(alert_id):
    """
    Endpoint: /api/alerts/<int:alert_id>/status (POST)
    
    Purpose:
        Updates an alert's review status ('Pending', 'In Progress', or 'Resolved').
        
    Authorization:
        Restricted to 'Admin' and 'Maintenance Staff'.
        
    Parameters:
        alert_id (int): Primary key ID of the alert.
        
    Request Payload:
        status (str): New alert status.
        
    Returns:
        JSON Response or HTTP 302 redirect for browser requests.
    """
    # Step 1: Extract new status from request
    data = request.get_json() if request.is_json else request.form.to_dict()
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
        
    # Step 2: Update status in database
    try:
        update_alert_status(alert_id, new_status)
        if request.is_json:
            return jsonify({'success': True, 'message': f'Alert status changed to {new_status}'})
            
        flash(f'Alert status updated to {new_status}!', 'success')
        return redirect(url_for('predictions.predictions_page'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error updating alert: {e}', 'danger')
        return redirect(url_for('predictions.predictions_page'))

@predictions_bp.route('/api/alerts/<int:alert_id>/create-task', methods=['POST'])
@role_required('Admin', 'Maintenance Staff')
def api_convert_alert_to_task(alert_id):
    """
    Endpoint: /api/alerts/<int:alert_id>/create-task (POST)
    
    Purpose:
        One-click preventative maintenance workflow: Converts an AI-generated failure
        prediction alert directly into a formal Work Order task, setting an automated
        due date (+5 days), urgency level (Urgent for High Risk), and switching the alert
        status to 'In Progress'.
        
    Authorization:
        Restricted to 'Admin' and 'Maintenance Staff'.
        
    Parameters:
        alert_id (int): Primary key ID of the predictive alert.
        
    Returns:
        JSON Response with new task ID or HTTP 302 redirect to maintenance management.
    """
    # Step 1: Retrieve alert details
    alert = get_alert_by_id(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
        
    try:
        # Step 2: Calculate automatic due date (5 days ahead for proactive intervention)
        due = (date.today() + timedelta(days=5)).strftime('%Y-%m-%d')
        priority = 'Urgent' if alert['risk_level'] == 'High Risk' else 'High'
        
        # Step 3: Insert new maintenance work order referencing the alert details
        task_id = create_maintenance_task({
            'maintenance_code': generate_maintenance_code(),
            'asset_id': alert['asset_id'],
            'problem': f"[AI Alert] {alert['problem']}",
            'priority': priority,
            'assigned_staff_id': None,
            'due_date': due,
            'status': 'Assigned',
            'notes': f"Recommended Action: {alert['recommended_action']}"
        })
        
        # Step 4: Advance alert status to 'In Progress' to prevent duplicate ticketing
        update_alert_status(alert_id, 'In Progress')
        
        # Step 5: Deliver response based on client request format
        if request.is_json:
            return jsonify({'success': True, 'task_id': task_id, 'message': 'Maintenance task created from AI alert'})
            
        flash('Maintenance task successfully created from AI alert!', 'success')
        return redirect(url_for('maintenance.maintenance_page'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error creating task: {e}', 'danger')
        return redirect(url_for('predictions.predictions_page'))
