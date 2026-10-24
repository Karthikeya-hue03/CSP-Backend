from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.user import verify_user_credentials, get_user_by_email

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """
    Route Decorator: Requires an authenticated user session.
    
    Purpose:
        Protects web endpoints and API routes from unauthorized access by verifying
        that an active 'user_id' exists in Flask's cryptographically signed session cookie.
        
    Parameters:
        f (function): The view function or API handler being decorated.
        
    Returns:
        function: Decorated wrapper function that either executes the original handler
                  or redirects unauthenticated users to the login screen with a 'next' redirect.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Step 1: Check if the user ID key exists in the current session
        if 'user_id' not in session:
            # Step 2: Inform user and redirect to login, preserving intended destination
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
            
        # Step 3: Session is valid, proceed with the original route function
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Route Decorator Factory: Enforces Role-Based Access Control (RBAC).
    
    Purpose:
        Restricts access to sensitive actions (e.g., adding assets, deleting work orders,
        re-seeding database) based on the user's role stored in their session.
        Supports dual response formats: JSON 403 for AJAX/API calls, or UI flash + redirect
        for browser page navigation.
        
    Parameters:
        *allowed_roles (str): Variable argument list of authorized role names (e.g. 'Admin', 'Maintenance Staff').
        
    Returns:
        function: Decorator function configured with the specified role whitelist.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Step 1: Ensure user is logged in before checking role permissions
            if 'user_id' not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for('auth.login'))
                
            # Step 2: Retrieve active role from user session
            user_role = session.get('user_role')
            
            # Step 3: Check whether current role is permitted for this endpoint
            if user_role not in allowed_roles:
                # Step 3a: Return structured JSON error for REST API / AJAX requests
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Unauthorized: Access restricted for your role'}), 403
                    
                # Step 3b: Redirect browser navigation to dashboard with an alert
                flash("Access denied: Your account role does not have permission for that action.", "danger")
                return redirect(url_for('dashboard.index'))
                
            # Step 4: Role matches permissions, execute target view function
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Endpoint: /login (GET, POST)
    
    Purpose:
        Handles user authentication for campus facility engineers, maintenance crew,
        and administrators.
        - GET: Displays the login screen with credential form.
        - POST: Validates email/password against stored SHA-256 salted hashes in the database.
        
    Request Parameters (POST Form):
        email (str): Registered staff email address.
        password (str): Plaintext password submitted via form.
        
    Session Attributes Set:
        user_id (int): Primary key ID of the user.
        user_name (str): Full display name.
        user_email (str): Email address.
        user_role (str): Security role ('Admin', 'Maintenance Staff', 'Management').
        user_department (str): Assigned campus department.
        
    Returns:
        HTML template render ('login.html') or HTTP 302 redirect to dashboard/next URL.
    """
    # Step 1: If user already has an active session, skip login and redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
        
    # Step 2: Process submitted login form on POST
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        # Step 2a: Validate that required fields are non-empty
        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template('login.html', email=email)
            
        # Step 2b: Verify credentials against the database user table
        user = verify_user_credentials(email, password)
        if user:
            # Step 2c: Wipe any prior session data to prevent session fixation attacks
            session.clear()
            
            # Step 2d: Store essential user identity in secure encrypted session cookie
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            session['user_department'] = user.get('department', 'Campus Estate Office')
            session.permanent = True  # Enable configured session lifetime
            
            flash(f"Welcome back, {user['name']}! Logged in as {user['role']}.", "success")
            
            # Step 2e: Redirect to original destination if 'next' parameter was supplied
            next_url = request.args.get('next') or url_for('dashboard.index')
            return redirect(next_url)
        else:
            # Step 2f: Authentication failed; present user-friendly error
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('login.html', email=email)
            
    # Step 3: GET request renders the clean login page
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """
    Endpoint: /logout (GET)
    
    Purpose:
        Terminates the user's active session, purges all stored session variables,
        and safely returns them to the login screen.
        
    Returns:
        HTTP 302 redirect to the login page ('auth.login').
    """
    # Step 1: Clear all cached keys (user_id, role, etc.) from Flask session
    session.clear()
    
    # Step 2: Notify user and redirect to login view
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('auth.login'))
