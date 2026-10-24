from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db, execute_db

def get_user_by_email(email):
    """
    Retrieves a user record from the database by email address.
    
    How it works:
    - Normalizes the input email by trimming whitespace and converting to lowercase.
    - Executes a parameterized SQL query against the `users` table.
    - Returns a dictionary representing the user record or None if not found.
    
    Args:
        email (str): The email address to look up.
        
    Returns:
        dict | None: The user's record including hashed password and role.
    """
    return query_db("SELECT * FROM users WHERE LOWER(email) = LOWER(%s);", (email.strip(),), one=True)

def get_user_by_id(user_id):
    """
    Retrieves a user record from the database by primary key ID.
    
    How it works:
    - Queries the `users` table filtering on `id = user_id`.
    - Used by session managers to re-fetch current authenticated user info.
    
    Args:
        user_id (int): Primary key ID of the user.
        
    Returns:
        dict | None: User record dictionary or None if not found.
    """
    return query_db("SELECT * FROM users WHERE id = %s;", (user_id,), one=True)

def verify_user_credentials(email, password):
    """
    Authenticates user login credentials using secure password hashing.
    
    How it works:
    1. Looks up the user account via `get_user_by_email(email)`.
    2. If no record matches the email, immediately returns None.
    3. Uses Werkzeug's `check_password_hash()` to compare the plaintext password
       against the cryptographic scrypt/pbkdf2 hash stored in `password_hash`.
    4. If the hash matches, returns the full user dictionary; otherwise returns None.
    
    Args:
        email (str): Entered email address.
        password (str): Plaintext password entered in the login form.
        
    Returns:
        dict | None: Authenticated user dictionary if valid, otherwise None.
    """
    user = get_user_by_email(email)
    if not user:
        return None
    if check_password_hash(user['password_hash'], password):
        return user
    return None

def create_user(name, email, password, role='Viewer', phone=None, department=None):
    """
    Registers a new campus user with an encrypted password hash.
    
    How it works:
    1. Hashes the plaintext password using `generate_password_hash()`.
    2. Executes a parameterized INSERT query into the `users` table.
    3. Returns the newly generated user ID.
    
    Args:
        name (str): Full name of the user.
        email (str): Valid email address.
        password (str): Plaintext password to be hashed.
        role (str): Account role ('Admin', 'Maintenance Staff', 'Viewer').
        phone (str, optional): Contact phone number.
        department (str, optional): Campus department or estate office branch.
        
    Returns:
        int: The primary key ID of the inserted user.
    """
    pw_hash = generate_password_hash(password)
    return execute_db(
        """INSERT INTO users (name, email, password_hash, role, phone, department) 
           VALUES (%s, %s, %s, %s, %s, %s);""",
        (name, email.strip().lower(), pw_hash, role, phone, department),
        return_id=True
    )

def get_all_users():
    """
    Retrieves all registered user accounts for the admin settings dashboard.
    
    How it works:
    - Selects id, name, email, role, phone, department, and created_at.
    - Explicitly excludes `password_hash` to maintain security best practices.
    
    Returns:
        list[dict]: List of all registered user dictionaries.
    """
    return query_db("SELECT id, name, email, role, phone, department, created_at FROM users ORDER BY id ASC;")

def get_maintenance_staff():
    """
    Fetches qualified staff members available for maintenance work order assignment.
    
    How it works:
    - Filters users with roles 'Maintenance Staff' or 'Admin'.
    - Populates the technician assignment dropdown in the maintenance task creation modal.
    
    Returns:
        list[dict]: List of available field personnel.
    """
    return query_db("SELECT id, name, email, role, phone FROM users WHERE role IN ('Maintenance Staff', 'Admin') ORDER BY name ASC;")
