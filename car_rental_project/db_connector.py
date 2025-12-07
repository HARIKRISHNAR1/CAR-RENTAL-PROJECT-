import mysql.connector
from mysql.connector import Error

# --- CONFIGURATION ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root", # <--- CHANGE THIS
    "password": "Hari@996W1234", # <--- CHANGE THIS
    "database": "car_rental_db" 
}
# ---------------------

def create_db_connection():
    """Establishes a connection to the MySQL database."""
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        print("Please check your MySQL server is running and credentials are correct.")
        return None

def execute_query(connection, query, data=None, fetch=False):
    """Executes a single SQL query (INSERT, UPDATE, DELETE, or SELECT)."""
    cursor = None
    try:
        cursor = connection.cursor(buffered=True) 
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)
            
        if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
            connection.commit()
            return cursor.rowcount
            
        if fetch:
            return cursor.fetchall()
            
    except Error as e:
        print(f"Database Error: {e}")
        print(f"Query was: {query}")
        return None
    finally:
        if cursor:
            cursor.close()