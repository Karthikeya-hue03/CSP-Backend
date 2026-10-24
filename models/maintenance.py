from datetime import datetime, date
from database import query_db, execute_db

def get_all_maintenance(status=None, priority=None, staff_id=None, search=None):
    """
    Retrieves maintenance work orders with associated asset telemetry and technician details.
    
    How it works:
    1. Performs a JOIN between `maintenance` and `assets` on `m.asset_id = a.id`.
    2. Performs a LEFT JOIN with `users` on `m.assigned_staff_id = u.id` to include technician details.
    3. Dynamically applies filters:
       - `status` (Pending, Assigned, In Progress, Completed).
       - `priority` (Urgent, High, Medium, Low).
       - `staff_id` (Filtered to assigned technician).
       - `search` (Search keyword matching maintenance code, problem description, or asset tag).
    4. Orders results by priority urgency (Urgent first) and created date descending.
    
    Args:
        status (str, optional): Filter by task status.
        priority (str, optional): Filter by priority level.
        staff_id (int, optional): Filter by assigned staff ID.
        search (str, optional): Keyword search string.
        
    Returns:
        list[dict]: List of maintenance work order dictionaries.
    """
    query = """
        SELECT m.id, m.maintenance_code, m.asset_id, m.problem, m.priority,
               m.assigned_staff_id, m.created_date, m.due_date, m.status, m.notes,
               m.created_at,
               a.asset_tag, a.name AS asset_name, a.asset_type, a.location, a.health_score,
               u.name AS staff_name, u.email AS staff_email
        FROM maintenance m
        JOIN assets a ON m.asset_id = a.id
        LEFT JOIN users u ON m.assigned_staff_id = u.id
        WHERE 1=1
    """
    params = []
    
    if status and status.lower() != 'all':
        query += " AND m.status = %s"
        params.append(status)
        
    if priority and priority.lower() != 'all':
        query += " AND m.priority = %s"
        params.append(priority)
        
    if staff_id:
        query += " AND m.assigned_staff_id = %s"
        params.append(staff_id)
        
    if search:
        query += " AND (m.maintenance_code LIKE %s OR m.problem LIKE %s OR a.asset_tag LIKE %s OR a.name LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
        
    query += " ORDER BY CASE m.priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, m.created_date DESC;"
    return query_db(query, tuple(params))

def get_maintenance_by_id(task_id):
    """
    Retrieves a single maintenance task by ID with full asset and assigned staff details.
    
    How it works:
    - Joins `maintenance` with `assets` and `users` filtering on `m.id = %s`.
    
    Args:
        task_id (int): Primary key ID of the work order.
        
    Returns:
        dict | None: The work order dictionary or None if not found.
    """
    query = """
        SELECT m.id, m.maintenance_code, m.asset_id, m.problem, m.priority,
               m.assigned_staff_id, m.created_date, m.due_date, m.status, m.notes,
               a.asset_tag, a.name AS asset_name, a.asset_type, a.location, a.health_score,
               u.name AS staff_name, u.email AS staff_email
        FROM maintenance m
        JOIN assets a ON m.asset_id = a.id
        LEFT JOIN users u ON m.assigned_staff_id = u.id
        WHERE m.id = %s;
    """
    return query_db(query, (task_id,), one=True)

def generate_maintenance_code():
    """
    Generates a standardized human-readable maintenance code: MNT-YYYY-XXX.
    
    How it works:
    1. Extracts the current calendar year (e.g. 2026).
    2. Counts existing maintenance records created in that year.
    3. Increments the count and formats with zero-padding (e.g. 'MNT-2026-021').
    
    Returns:
        str: Formatted unique work order tracking code.
    """
    year = datetime.now().year
    row = query_db("SELECT COUNT(*) AS cnt FROM maintenance WHERE maintenance_code LIKE %s;", (f"MNT-{year}-%",), one=True)
    count = (row['cnt'] if row else 0) + 1
    return f"MNT-{year}-{count:03d}"

def create_maintenance_task(data):
    """
    Creates a new maintenance work order.
    
    How it works:
    1. Auto-generates a tracking code if not explicitly provided.
    2. Defaults `created_date` to today's date.
    3. Inserts problem description, priority level, assigned technician ID, due date, status, and engineering notes.
    4. Returns the newly created work order primary key ID.
    
    Args:
        data (dict): Work order fields from form or API request.
        
    Returns:
        int: The primary key ID of the created maintenance record.
    """
    code = data.get('maintenance_code') or generate_maintenance_code()
    created_date = data.get('created_date') or date.today().strftime('%Y-%m-%d')
    
    task_id = execute_db(
        """INSERT INTO maintenance (maintenance_code, asset_id, problem, priority,
                                    assigned_staff_id, created_date, due_date, status, notes)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
        (
            code, int(data['asset_id']), data['problem'], data.get('priority', 'Medium'),
            data.get('assigned_staff_id') or None, created_date,
            data.get('due_date'), data.get('status', 'Pending'), data.get('notes', '')
        ),
        return_id=True
    )
    return task_id

def update_maintenance_task(task_id, data):
    """
    Updates the fields of an existing maintenance work order.
    
    How it works:
    - Modifies problem description, priority, technician assignment, due date, status, and notes.
    
    Args:
        task_id (int): ID of the task to update.
        data (dict): Updated dictionary of values.
        
    Returns:
        int: Number of rows affected.
    """
    return execute_db(
        """UPDATE maintenance
           SET problem = %s, priority = %s, assigned_staff_id = %s,
               due_date = %s, status = %s, notes = %s
           WHERE id = %s;""",
        (
            data['problem'], data.get('priority', 'Medium'),
            data.get('assigned_staff_id') or None, data.get('due_date'),
            data.get('status', 'Pending'), data.get('notes', ''),
            task_id
        )
    )

def update_maintenance_status(task_id, new_status, notes=None):
    """
    Transitions the operational workflow status of a work order.
    
    How it works:
    - Supports transitions: Pending -> Assigned -> In Progress -> Completed.
    - Conditionally appends resolution notes or technician completion remarks.
    
    Args:
        task_id (int): Work order ID.
        new_status (str): Target status.
        notes (str, optional): Completion notes or progress remarks.
        
    Returns:
        int: Number of rows affected.
    """
    if notes:
        return execute_db(
            "UPDATE maintenance SET status = %s, notes = %s WHERE id = %s;",
            (new_status, notes, task_id)
        )
    return execute_db(
        "UPDATE maintenance SET status = %s WHERE id = %s;",
        (new_status, task_id)
    )

def delete_maintenance_task(task_id):
    """
    Deletes a maintenance record by primary key ID.
    
    Args:
        task_id (int): Work order ID to remove.
        
    Returns:
        int: Number of rows affected.
    """
    return execute_db("DELETE FROM maintenance WHERE id = %s;", (task_id,))

def get_maintenance_summary():
    """
    Aggregates work order counts grouped by operational status.
    
    How it works:
    - Runs a `GROUP BY status` query on the `maintenance` table.
    - Pre-populates a dictionary ensuring zero counts for Pending, Assigned, In Progress, and Completed.
    - Used by the maintenance dashboard KPI cards.
    
    Returns:
        dict: Counts by status: {'Pending': X, 'Assigned': Y, 'In Progress': Z, 'Completed': W}.
    """
    counts = query_db("""
        SELECT status, COUNT(*) AS count
        FROM maintenance
        GROUP BY status;
    """)
    res = {'Pending': 0, 'Assigned': 0, 'In Progress': 0, 'Completed': 0}
    for row in counts:
        if row['status'] in res:
            res[row['status']] = row['count']
    return res
