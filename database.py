import sqlite3
import re
import logging
from config import Config

logger = logging.getLogger(__name__)

# Global variables tracking active database mode: 'mysql' or 'sqlite'
_ACTIVE_DB_TYPE = None
_MYSQL_AVAILABLE = None

def check_mysql_connection():
    """
    Checks if a local or remote MySQL database server is actively reachable.
    
    How it works:
    1. Attempts to establish a low-timeout socket connection to MySQL using host,
       port, user, and password specified in the application configuration.
    2. If the connection succeeds, it flags `_MYSQL_AVAILABLE = True` and closes the probe.
    3. If connection fails (e.g. MySQL service not started in XAMPP or Windows Services),
       it catches the exception, logs a helpful warning, flags `_MYSQL_AVAILABLE = False`,
       and allows the application to gracefully fall back to SQLite without crashing.
       
    Returns:
        bool: True if MySQL server is reachable, False otherwise.
    """
    global _MYSQL_AVAILABLE
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            connection_timeout=3
        )
        if conn.is_connected():
            conn.close()
            _MYSQL_AVAILABLE = True
            return True
    except Exception as e:
        logger.warning(f"MySQL connection check failed ({e}). Falling back to local SQLite engine.")
        _MYSQL_AVAILABLE = False
        return False

def get_db_type():
    """
    Identifies and returns the currently active database engine.
    
    How it works:
    1. Inspects the cached `_ACTIVE_DB_TYPE` variable.
    2. If not previously checked, executes `check_mysql_connection()`.
    3. Sets active type to 'mysql' if reachable; otherwise defaults to 'sqlite'.
    
    Returns:
        str: Either 'mysql' or 'sqlite'.
    """
    global _ACTIVE_DB_TYPE
    if _ACTIVE_DB_TYPE is None:
        if check_mysql_connection():
            _ACTIVE_DB_TYPE = 'mysql'
        else:
            _ACTIVE_DB_TYPE = 'sqlite'
    return _ACTIVE_DB_TYPE

def set_db_type(db_type):
    """
    Manually overrides the active database engine type.
    
    How it works:
    - Allows programmatic switching between 'mysql' and 'sqlite' (e.g. for testing).
    
    Args:
        db_type (str): 'mysql' or 'sqlite'.
    """
    global _ACTIVE_DB_TYPE
    _ACTIVE_DB_TYPE = db_type

def get_db_connection():
    """
    Instantiates and returns a raw connection to the active database engine.
    
    How it works:
    1. Calls `get_db_type()` to determine whether MySQL or SQLite is active.
    2. If 'mysql', creates a native connection using `mysql.connector.connect()`.
    3. If 'sqlite', opens the local SQLite file defined in Config.SQLITE_DB_PATH
       and attaches `sqlite3.Row` factory so results behave like dictionaries.
       
    Returns:
        Connection: A database connection object (MySQLConnection or sqlite3.Connection).
    """
    db_type = get_db_type()
    if db_type == 'mysql':
        import mysql.connector
        return mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
    else:
        # SQLite connection
        conn = sqlite3.connect(Config.SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def _convert_query_for_sqlite(query):
    """
    Syntax adapter converting MySQL queries to SQLite-compatible syntax.
    
    How it works:
    1. Replaces `%s` parameter placeholders used by MySQL with `?` placeholders used by SQLite.
    2. Replaces MySQL's `NOW()` function with SQLite's `CURRENT_TIMESTAMP`.
    3. Guarantees that all application route queries write once in standard SQL
       and run identically on both database engines without SQL injection risk.
       
    Args:
        query (str): The raw SQL query written with `%s` placeholders.
        
    Returns:
        str: Transformed SQL query compatible with Python's sqlite3 driver.
    """
    # Replace %s parameter placeholder with ? for sqlite3
    query = query.replace('%s', '?')
    # Replace NOW() with CURRENT_TIMESTAMP
    query = re.sub(r'\bNOW\(\)', 'CURRENT_TIMESTAMP', query, flags=re.IGNORECASE)
    return query

def query_db(query, params=(), one=False):
    """
    Executes a SELECT query and returns rows as dictionaries.
    
    How it works:
    1. Obtains a connection to the active database engine (MySQL or SQLite).
    2. Executes the query using safe parameterized binding to prevent SQL injection.
    3. If MySQL: Uses a dictionary cursor (`dictionary=True`) so column values are keyed by name.
    4. If SQLite: Adapts placeholders via `_convert_query_for_sqlite()` and converts rows to dicts.
    5. Safely closes the cursor and connection in the `finally` block to prevent connection leaks.
    
    Args:
        query (str): The parameterized SQL SELECT query string.
        params (tuple): Parameters to bind safely into the query.
        one (bool): If True, returns only the first matched dictionary or None.
        
    Returns:
        list[dict] | dict | None: Query results formatted as dictionaries.
    """
    db_type = get_db_type()
    conn = None
    try:
        conn = get_db_connection()
        if db_type == 'mysql':
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            return (rows[0] if rows else None) if one else rows
        else:
            # SQLite
            sqlite_query = _convert_query_for_sqlite(query)
            cursor = conn.cursor()
            cursor.execute(sqlite_query, params)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            cursor.close()
            return (result[0] if result else None) if one else result
    except Exception as e:
        logger.error(f"Error executing query [{query}] with params {params}: {e}")
        raise e
    finally:
        if conn:
            conn.close()

def execute_db(query, params=(), return_id=False):
    """
    Executes an INSERT, UPDATE, or DELETE query and commits the transaction.
    
    How it works:
    1. Obtains a connection to the active database.
    2. Adapts syntax if SQLite is active.
    3. Executes the statement using safe parameterized query binding.
    4. Commits the transaction to persist changes to disk.
    5. Retrieves either the newly created primary key `lastrowid` or the count of affected rows.
    6. Automatically rolls back the transaction if an exception occurs to maintain ACID integrity.
    
    Args:
        query (str): The parameterized INSERT/UPDATE/DELETE statement.
        params (tuple): Parameter values to bind into the statement.
        return_id (bool): If True, returns `cursor.lastrowid` (for new records).
        
    Returns:
        int: Newly inserted record ID if return_id=True, else number of rows affected.
    """
    db_type = get_db_type()
    conn = None
    try:
        conn = get_db_connection()
        if db_type == 'mysql':
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            last_id = cursor.lastrowid
            affected = cursor.rowcount
            cursor.close()
            return last_id if return_id else affected
        else:
            # SQLite
            sqlite_query = _convert_query_for_sqlite(query)
            cursor = conn.cursor()
            cursor.execute(sqlite_query, params)
            conn.commit()
            last_id = cursor.lastrowid
            affected = cursor.rowcount
            cursor.close()
            return last_id if return_id else affected
    except Exception as e:
        logger.error(f"Error executing statement [{query}] with params {params}: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()
