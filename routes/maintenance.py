from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from routes.auth import login_required, role_required
from models.maintenance import (
    get_all_maintenance, get_maintenance_by_id, create_maintenance_task,
    update_maintenance_task, update_maintenance_status, delete_maintenance_task,
    get_maintenance_summary
)
from models.asset import get_all_assets
from models.user import get_maintenance_staff

maintenance_bp = Blueprint('maintenance', __name__)

@maintenance_bp.route('/maintenance')
@login_required
def maintenance_page():
    """
    Endpoint: /maintenance (GET)
    
    Purpose:
        Renders the Campus Work Order & Maintenance Management dashboard.
        Enables facilities management and field crew to monitor tasks across lifecycle stages:
        Assigned, In Progress, Completed, or Cancelled.
        
    Query Parameters:
        status (str, optional): Filter by task status.
        priority (str, optional): Filter by urgency ('Low', 'Medium', 'High', 'Urgent').
        search (str, optional): Keyword search matching problem description, work order code, or asset tag.
        
    Context Variables Passed to Template:
        tasks (list): Filtered maintenance work orders.
        assets (list): All registered assets (for the "Create Task" asset selector dropdown).
        staff (list): Eligible maintenance technicians for work assignment.
        summary (dict): KPI summary tallies (total, in_progress, completed, urgent).
        
    Returns:
        HTML template render ('maintenance.html').
    """
    # Step 1: Read optional query filters from request URL
    status = request.args.get('status')
    priority = request.args.get('priority')
    search = request.args.get('search')
    
    # Step 2: Fetch filtered maintenance work orders
    tasks = get_all_maintenance(status=status, priority=priority, search=search)
    
    # Step 3: Fetch supporting data for modal dialogs and filter badges
    assets = get_all_assets()
    staff = get_maintenance_staff()
    summary = get_maintenance_summary()
    
    # Step 4: Render view with all active work order context
    return render_template(
        'maintenance.html',
        tasks=tasks,
        assets=assets,
        staff=staff,
        summary=summary,
        current_status=status,
        current_priority=priority,
        search=search
    )

@maintenance_bp.route('/api/maintenance', methods=['GET'])
@login_required
def api_get_maintenance():
    """
    Endpoint: /api/maintenance (GET)
    
    Purpose:
        REST API endpoint to retrieve maintenance work orders with optional filtering.
        
    Query Parameters:
        status (str, optional): Status filter.
        priority (str, optional): Priority filter.
        search (str, optional): Text search query.
        staff_id (int, optional): Filter by assigned technician.
        
    Returns:
        JSON Response: Array of maintenance task objects with joined asset and staff names.
    """
    # Step 1: Extract filter parameters from URL query string
    status = request.args.get('status')
    priority = request.args.get('priority')
    search = request.args.get('search')
    staff_id = request.args.get('staff_id')
    
    # Step 2: Query database and return JSON array
    return jsonify(get_all_maintenance(status=status, priority=priority, staff_id=staff_id, search=search))

@maintenance_bp.route('/api/maintenance/<int:task_id>', methods=['GET'])
@login_required
def api_get_single_maintenance(task_id):
    """
    Endpoint: /api/maintenance/<int:task_id> (GET)
    
    Purpose:
        REST API endpoint fetching detailed information for a single work order ticket.
        
    Parameters:
        task_id (int): Primary key ID of the maintenance record.
        
    Returns:
        JSON Response: Maintenance task record or 404 error if not found.
    """
    # Step 1: Look up task by ID
    task = get_maintenance_by_id(task_id)
    if not task:
        return jsonify({'error': 'Maintenance task not found'}), 404
        
    # Step 2: Return serialized task dictionary
    return jsonify(task)

@maintenance_bp.route('/api/maintenance', methods=['POST'])
@role_required('Admin', 'Maintenance Staff')
def api_create_maintenance():
    """
    Endpoint: /api/maintenance (POST)
    
    Purpose:
        Creates a new work order maintenance task for campus infrastructure repair.
        Generates an automatic tracking code (e.g., 'WO-2026-ABCD') if not explicitly supplied.
        
    Authorization:
        Restricted to 'Admin' and 'Maintenance Staff'.
        
    Request Payload (JSON or Form Data):
        asset_id (int): Target infrastructure asset ID.
        problem (str): Detailed description of reported defect or preventative maintenance need.
        priority (str): Urgency ('Low', 'Medium', 'High', 'Urgent').
        assigned_staff_id (int, optional): User ID of technician assigned to the job.
        due_date (str): Expected completion deadline (YYYY-MM-DD).
        status (str, optional): Initial status (defaults to 'Assigned').
        notes (str, optional): Additional instructions or context.
        
    Returns:
        JSON Response with new task ID (201) or HTTP 302 redirect for browser forms.
    """
    # Step 1: Extract submitted payload from JSON or form
    data = request.get_json() if request.is_json else request.form.to_dict()
    
    # Step 2: Validate mandatory fields
    if not data.get('asset_id') or not data.get('problem'):
        return jsonify({'error': 'asset_id and problem are required'}), 400
        
    # Step 3: Insert new maintenance task into database
    try:
        task_id = create_maintenance_task(data)
        
        # Step 4: Return JSON response for AJAX or flash redirect for web interface
        if request.is_json:
            return jsonify({'success': True, 'id': task_id, 'message': 'Maintenance task created successfully'}), 201
            
        flash('Maintenance task created successfully!', 'success')
        return redirect(url_for('maintenance.maintenance_page'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error creating task: {e}', 'danger')
        return redirect(url_for('maintenance.maintenance_page'))

@maintenance_bp.route('/api/maintenance/<int:task_id>', methods=['PUT', 'POST'])
@role_required('Admin', 'Maintenance Staff')
def api_update_maintenance(task_id):
    """
    Endpoint: /api/maintenance/<int:task_id> (PUT, POST)
    
    Purpose:
        Updates work order details such as problem description, assigned technician,
        priority tier, due date, or field inspection notes.
        
    Authorization:
        Restricted to 'Admin' and 'Maintenance Staff'.
        
    Parameters:
        task_id (int): Primary key ID of the maintenance task.
        
    Returns:
        JSON Response indicating success or HTTP 302 redirect for browser forms.
    """
    # Step 1: Extract payload
    data = request.get_json() if request.is_json else request.form.to_dict()
    
    # Step 2: Verify task exists
    task = get_maintenance_by_id(task_id)
    if not task:
        return jsonify({'error': 'Maintenance task not found'}), 404
        
    # Step 3: Apply updates to the database
    try:
        update_maintenance_task(task_id, data)
        if request.is_json:
            return jsonify({'success': True, 'message': 'Maintenance task updated successfully'})
            
        flash('Maintenance task updated successfully!', 'success')
        return redirect(url_for('maintenance.maintenance_page'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error updating task: {e}', 'danger')
        return redirect(url_for('maintenance.maintenance_page'))

@maintenance_bp.route('/api/maintenance/<int:task_id>/status', methods=['POST'])
@role_required('Admin', 'Maintenance Staff')
def api_update_status(task_id):
    """
    Endpoint: /api/maintenance/<int:task_id>/status (POST)
    
    Purpose:
        Fast-track status update for technicians in the field (e.g., mark as 'In Progress'
        when beginning repair, or 'Completed' upon resolution).
        
    Authorization:
        Restricted to 'Admin' and 'Maintenance Staff'.
        
    Parameters:
        task_id (int): Primary key ID of the maintenance record.
        
    Request Payload:
        status (str): New lifecycle status ('Assigned', 'In Progress', 'Completed', 'Cancelled').
        notes (str, optional): Technician's completion remarks or diagnostic notes.
        
    Returns:
        JSON Response indicating success or HTTP 302 redirect for browser forms.
    """
    # Step 1: Extract status update payload
    data = request.get_json() if request.is_json else request.form.to_dict()
    new_status = data.get('status')
    notes = data.get('notes')
    
    # Step 2: Validate presence of new status
    if not new_status:
        return jsonify({'error': 'New status is required'}), 400
        
    # Step 3: Update database status and append notes
    try:
        update_maintenance_status(task_id, new_status, notes=notes)
        if request.is_json:
            return jsonify({'success': True, 'message': f'Status updated to {new_status}'})
            
        flash(f'Maintenance task updated to {new_status}!', 'success')
        return redirect(url_for('maintenance.maintenance_page'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error updating status: {e}', 'danger')
        return redirect(url_for('maintenance.maintenance_page'))

@maintenance_bp.route('/api/maintenance/<int:task_id>', methods=['DELETE'])
@role_required('Admin')
def api_delete_maintenance(task_id):
    """
    Endpoint: /api/maintenance/<int:task_id> (DELETE)
    
    Purpose:
        Permanently removes a maintenance work order from the system.
        
    Authorization:
        Restricted to 'Admin' users only.
        
    Parameters:
        task_id (int): Primary key ID of the work order to delete.
        
    Returns:
        JSON Response indicating deletion confirmation.
    """
    # Step 1: Delete task from database
    try:
        delete_maintenance_task(task_id)
        return jsonify({'success': True, 'message': 'Maintenance task deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
