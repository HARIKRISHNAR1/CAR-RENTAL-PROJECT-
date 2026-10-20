import mysql.connector
import os
import sys 
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, g, cli

# --- Configuration ---
app = Flask(__name__)
# IMPORTANT: Set a secret key for session management (required for flash messages)
app.secret_key = 'super_secret_car_key_12345'

# !!! MANDATORY: REPLACE THESE WITH ACTUAL MySQL CREDENTIALS !!!
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root' # e.g., 'root' <-- CHECK THIS!
MYSQL_PASSWORD = 'Hari@996W1234' # e.g., 'mysecretpassword' <-- CHECK THIS!
MYSQL_DATABASE = 'car_rental_db'
# Make sure your MySQL server is running before attempting to connect.

# --- Jinja2 Template Filter Registration FIX ---
# This function registers Python's strftime (string format time) as a filter 
# callable directly in the HTML templates, fixing the Internal Server Error (500).
@app.template_filter()
def strftime(value, format_string='%Y-%m-%d'):
    """Format a date object to a string using strftime."""
    if value is None:
        return ""
    # Python date/datetime objects have a strftime method
    return value.strftime(format_string)

# --- Database Helper Functions ---

def connect_db():
    """Establishes a connection to the MySQL database."""
    print("Attempting to connect to MySQL database...")
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            connection_timeout=5 
        )
        print("SUCCESS: MySQL connection established.")
        return conn
    except mysql.connector.Error as err:
        # CRITICAL DEBUGGING LINE: Prints the actual error to the terminal
        print(f"FATAL ERROR: MySQL connection failed. Error details: {err}", file=sys.stderr)
        flash(f"Database connection failed: {err.msg}. Check your credentials and run 'flask init-mysql-db'", "danger")
        return None
    except Exception as e:
        print(f"AN UNEXPECTED ERROR OCCURRED DURING CONNECTION: {e}", file=sys.stderr)
        flash("An unexpected error occurred during database connection.", "danger")
        return None

def get_db():
    """Gets the database connection for the current request context."""
    if 'db' not in g:
        g.db = connect_db()
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

def init_db():
    """Initializes the MySQL database schema, dropping and recreating ALL tables to ensure foreign keys work."""
    print("--- Starting Database Initialization ---")
    conn = None
    cursor = None
    try:
        # Temporarily connect without specifying the database to create it first
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        cursor = conn.cursor()
        
        # 1. Create the database if it doesn't exist
        print(f"Creating database {MYSQL_DATABASE} if it doesn't exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE}")
        conn.database = MYSQL_DATABASE # Switch to the new database
        
        # CRITICAL FIX: Drop ALL tables in dependency order
        print("Dropping ALL dependent tables (payment, rental, car, customer, staff) for a clean start...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;") 
        cursor.execute("DROP TABLE IF EXISTS payment")
        cursor.execute("DROP TABLE IF EXISTS rental")
        cursor.execute("DROP TABLE IF EXISTS car") 
        cursor.execute("DROP TABLE IF EXISTS customer")
        cursor.execute("DROP TABLE IF EXISTS staff") 
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;") 

        # 2. Create tables (5 tables required)
        print("Creating table 'staff'...")
        cursor.execute('''
            CREATE TABLE staff (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                first_name VARCHAR(255) NOT NULL,
                last_name VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'Agent'
            ) ENGINE=InnoDB
        ''')

        print("Creating table 'customer'...")
        cursor.execute('''
            CREATE TABLE customer (
                id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(255) NOT NULL,
                last_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(255) UNIQUE NOT NULL
            ) ENGINE=InnoDB
        ''')
        
        print("Creating table 'car'...")
        cursor.execute('''
            CREATE TABLE car (
                id INT AUTO_INCREMENT PRIMARY KEY,
                reg_number VARCHAR(50) UNIQUE NOT NULL,
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(100) NOT NULL,
                year INT NOT NULL,
                rate DECIMAL(10, 2) NOT NULL,
                status CHAR(1) NOT NULL DEFAULT 'A'
            ) ENGINE=InnoDB
        ''')

        print("Creating table 'rental'...")
        cursor.execute('''
            CREATE TABLE rental (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                car_id INT NOT NULL,
                rent_date DATE NOT NULL,
                expected_return_date DATE NOT NULL,
                actual_return_date DATE,
                FOREIGN KEY (customer_id) REFERENCES customer(id) ON DELETE CASCADE,
                FOREIGN KEY (car_id) REFERENCES car(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
        ''')

        print("Creating table 'payment'...")
        cursor.execute('''
            CREATE TABLE payment (
                id INT AUTO_INCREMENT PRIMARY KEY,
                rental_id INT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                payment_date DATE NOT NULL,
                FOREIGN KEY (rental_id) REFERENCES rental(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
        ''')

        # Insert initial staff data
        cursor.execute("INSERT INTO staff (username, email, first_name, last_name, role) VALUES ('admin', 'admin@example.com', 'System', 'Admin', 'Administrator')")
        
        conn.commit()
        print("SUCCESS: MySQL schema initialization complete. All 5 tables fixed and ready.")

    except mysql.connector.Error as err:
        print(f"FATAL ERROR: Failed to initialize MySQL schema. Error details: {err}", file=sys.stderr)
        print("Please ensure your MySQL server is running and the user/password are correct.", file=sys.stderr)
        
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    print("--- Database Initialization Finished ---")


# Context Processor: Inject variables available in all templates
@app.context_processor
def inject_global_vars():
    """Provides common variables like the current year to all templates."""
    return dict(current_year=date.today().year)

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html', title='Dashboard')

# --- STAFF MANAGEMENT (CRUD) ---
@app.route('/staff')
def staff_list():
    db = get_db()
    if db is None: return render_template('index.html', title='Dashboard')
    cursor = None
    staff = []
    try:
        cursor = db.cursor(dictionary=True) 
        cursor.execute('SELECT id, username, first_name, last_name, email, role FROM staff ORDER BY last_name')
        staff = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Error loading staff data: {e}", 'danger')
    finally:
        if cursor: cursor.close()
            
    return render_template('staff_list.html', title='Staff Management', staff=staff)

@app.route('/staff/add', methods=['GET', 'POST'])
def add_staff():
    if request.method == 'POST':
        db = get_db()
        if db is None: 
            flash('Database connection failed.', 'danger')
            return redirect(url_for('staff_list'))
        
        cursor = None
        try:
            cursor = db.cursor()
            sql = 'INSERT INTO staff (username, email, first_name, last_name, role) VALUES (%s, %s, %s, %s, %s)'
            data = (request.form['username'], request.form['email'], request.form['first_name'], request.form['last_name'], request.form['role'])
            cursor.execute(sql, data)
            db.commit()
            flash('Staff member added successfully!', 'success')
            return redirect(url_for('staff_list'))
            
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Error: A staff member with this username or email already exists.', 'danger')
            else:
                flash(f'An SQL error occurred: {err}', 'danger')
        finally:
            if cursor: cursor.close()
    
    return render_template('staff_form.html', title='Add New Staff Member', staff={})

@app.route('/staff/edit/<int:staff_id>', methods=['GET', 'POST'])
def edit_staff(staff_id):
    db = get_db()
    if db is None: return redirect(url_for('staff_list'))
    
    staff = None
    cursor = None
    
    try:
        cursor = db.cursor(dictionary=True) 
        cursor.execute('SELECT id, username, email, first_name, last_name, role FROM staff WHERE id = %s', (staff_id,))
        staff = cursor.fetchone()
    except mysql.connector.Error as e:
        flash(f"Error retrieving staff data: {e}", 'danger')
    finally:
        if cursor: cursor.close()

    if staff is None:
        flash('Staff member not found.', 'danger')
        return redirect(url_for('staff_list'))

    if request.method == 'POST':
        cursor = None
        try:
            cursor = db.cursor()
            sql = 'UPDATE staff SET username = %s, email = %s, first_name = %s, last_name = %s, role = %s WHERE id = %s'
            data = (request.form['username'], request.form['email'], request.form['first_name'], request.form['last_name'], request.form['role'], staff_id)
            cursor.execute(sql, data)
            db.commit()
            flash('Staff member updated successfully!', 'success')
            return redirect(url_for('staff_list'))
            
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Error: A staff member with this username or email already exists.', 'danger')
            else:
                flash(f'An SQL error occurred: {err}', 'danger')
        finally:
            if cursor: cursor.close()

    return render_template('staff_form.html', title='Edit Staff Member', staff=staff)

# not functionaning as it is not required
@app.route('/staff/delete/<int:staff_id>', methods=['POST'])
def delete_staff(staff_id):
    db = get_db()
    if db is None: return redirect(url_for('staff_list'))
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute('DELETE FROM staff WHERE id = %s', (staff_id,))
        db.commit()
        flash('Staff member deleted successfully.', 'success')
    except mysql.connector.Error as e:
        flash(f'An error occurred during deletion: {e}', 'danger')
    finally:
        if cursor: cursor.close()
    return redirect(url_for('staff_list'))

# --- CUSTOMER MANAGEMENT (CRUD) ---
@app.route('/customers')
def customer_list():
    db = get_db()
    if db is None: return render_template('index.html', title='Dashboard')
    cursor = None
    customers = []
    try:
        cursor = db.cursor(dictionary=True) 
        cursor.execute('SELECT id, first_name, last_name, phone, email FROM customer ORDER BY last_name')
        customers = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Error loading customer data: {e}", 'danger')
    finally:
        if cursor: cursor.close()
            
    return render_template('customer_management_list.html', title='Customer Management', customers=customers)

@app.route('/customer/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        db = get_db()
        if db is None: return redirect(url_for('customer_list'))
        cursor = None
        try:
            cursor = db.cursor()
            sql = 'INSERT INTO customer (first_name, last_name, phone, email) VALUES (%s, %s, %s, %s)'
            data = (request.form['first_name'], request.form['last_name'], request.form['phone'], request.form['email'])
            cursor.execute(sql, data)
            db.commit()
            flash('Customer added successfully!', 'success')
            return redirect(url_for('customer_list'))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Error: A customer with this email already exists.', 'danger')
            else:
                flash(f'An SQL error occurred: {err}', 'danger')
        finally:
            if cursor: cursor.close()
    
    return render_template('customer_form.html', title='Add New Customer', customer={})

@app.route('/customer/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    db = get_db()
    if db is None: return redirect(url_for('customer_list'))
    customer = None
    cursor = None
    try:
        cursor = db.cursor(dictionary=True) 
        cursor.execute('SELECT * FROM customer WHERE id = %s', (customer_id,))
        customer = cursor.fetchone()
    except mysql.connector.Error as e:
        flash(f"Error retrieving customer data: {e}", 'danger')
    finally:
        if cursor: cursor.close()

    if customer is None:
        flash('Customer not found.', 'danger')
        return redirect(url_for('customer_list'))

    if request.method == 'POST':
        cursor = None
        try:
            cursor = db.cursor()
            sql = 'UPDATE customer SET first_name = %s, last_name = %s, phone = %s, email = %s WHERE id = %s'
            data = (request.form['first_name'], request.form['last_name'], request.form['phone'], request.form['email'], customer_id)
            cursor.execute(sql, data)
            db.commit()
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('customer_list'))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Error: A customer with this email already exists.', 'danger')
            else:
                flash(f'An SQL error occurred: {err}', 'danger')
        finally:
            if cursor: cursor.close()

    return render_template('customer_form.html', title='Edit Customer', customer=customer)

@app.route('/customer/delete/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    db = get_db()
    if db is None: return redirect(url_for('customer_list'))
    cursor = None
    try:
        cursor = db.cursor()
        # Check for active rentals first
        cursor.execute('SELECT COUNT(*) FROM rental WHERE customer_id = %s AND actual_return_date IS NULL', (customer_id,))
        rental_check = cursor.fetchone()[0]
        
        if rental_check > 0:
            flash('Cannot delete customer: they have an active rental.', 'danger')
        else:
            # ON DELETE CASCADE handles dependent rentals/payments in MySQL
            cursor.execute('DELETE FROM customer WHERE id = %s', (customer_id,))
            db.commit()
            flash('Customer deleted successfully.', 'success')
    except mysql.connector.Error as e:
        flash(f'An error occurred during deletion: {e}', 'danger')
    finally:
        if cursor: cursor.close()
    return redirect(url_for('customer_list'))

# --- CAR MANAGEMENT (CRUD) ---

@app.route('/cars')
def car_list():
    db = get_db()
    if db is None: return render_template('index.html', title='Dashboard')
    cursor = None
    cars = []
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT id, reg_number, brand, model, year, rate, status FROM car ORDER BY brand, model')
        cars = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Error loading car data: {e}", 'danger')
    finally:
        if cursor: cursor.close()
            
    return render_template('car_management_list.html', title='Car Inventory', cars=cars)

@app.route('/car/add', methods=['GET', 'POST'])
def add_car():
    if request.method == 'POST':
        db = get_db()
        if db is None: return redirect(url_for('car_list'))
        cursor = None
        try:
            cursor = db.cursor()
            sql = 'INSERT INTO car (reg_number, brand, model, year, rate, status) VALUES (%s, %s, %s, %s, %s, %s)'
            data = (request.form['reg_number'], request.form['brand'], request.form['model'], 
                    int(request.form['year']), float(request.form['rate']), request.form.get('status', 'A'))
            cursor.execute(sql, data)
            db.commit()
            flash('Car added to inventory successfully!', 'success')
            return redirect(url_for('car_list'))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Error: A car with this registration number already exists.', 'danger')
            else:
                flash(f'An SQL error occurred: {err}', 'danger')
        except ValueError:
            flash('Error: Year or Rate must be a valid number.', 'danger')
        finally:
            if cursor: cursor.close()

    return render_template('car_form.html', title='Add New Car', car={})

@app.route('/car/edit/<int:car_id>', methods=['GET', 'POST'])
def edit_car(car_id):
    db = get_db()
    if db is None: return redirect(url_for('car_list'))
    car = None
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM car WHERE id = %s', (car_id,))
        car = cursor.fetchone()
    finally:
        if cursor: cursor.close()

    if car is None:
        flash('Car not found.', 'danger')
        return redirect(url_for('car_list'))

    if request.method == 'POST':
        cursor = None
        try:
            cursor = db.cursor()
            sql = 'UPDATE car SET reg_number = %s, brand = %s, model = %s, year = %s, rate = %s, status = %s WHERE id = %s'
            data = (request.form['reg_number'], request.form['brand'], request.form['model'], 
                    int(request.form['year']), float(request.form['rate']), request.form['status'], car_id)
            cursor.execute(sql, data)
            db.commit()
            flash('Car details updated successfully!', 'success')
            return redirect(url_for('car_list'))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Error: A car with this registration number already exists.', 'danger')
            else:
                flash(f'An SQL error occurred: {err}', 'danger')
        except ValueError:
            flash('Error: Year or Rate must be a valid number.', 'danger')
        finally:
            if cursor: cursor.close()

    return render_template('car_form.html', title='Edit Car', car=car)

@app.route('/car/delete/<int:car_id>', methods=['POST'])
def delete_car(car_id):
    db = get_db()
    if db is None: return redirect(url_for('car_list'))
    cursor = None
    try:
        cursor = db.cursor()
        # Check for active rentals first
        cursor.execute('SELECT COUNT(*) FROM rental WHERE car_id = %s AND actual_return_date IS NULL', (car_id,))
        rental_check = cursor.fetchone()[0]
        
        if rental_check > 0:
            flash('Cannot delete car: it is currently rented.', 'danger')
        else:
            cursor.execute('DELETE FROM car WHERE id = %s', (car_id,))
            db.commit()
            flash('Car deleted successfully.', 'success')
    except mysql.connector.Error as e:
        flash(f'An error occurred during deletion: {e}', 'danger')
    finally:
        if cursor: cursor.close()
    return redirect(url_for('car_list'))

# --- RENTAL MANAGEMENT (Start/Return) ---

@app.route('/rentals')
def rental_list():
    db = get_db()
    if db is None: return render_template('index.html', title='Dashboard')
    cursor = None
    rentals = []
    try:
        cursor = db.cursor(dictionary=True)
        sql_query = '''
            SELECT 
                r.id AS rental_id, 
                c.first_name, c.last_name, 
                cr.brand, cr.model, cr.reg_number,
                r.rent_date, 
                r.expected_return_date, 
                r.actual_return_date
            FROM rental r
            JOIN customer c ON r.customer_id = c.id
            JOIN car cr ON r.car_id = cr.id
            ORDER BY r.rent_date DESC
        '''
        cursor.execute(sql_query)
        rentals = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Error loading rental data. Please run 'flask init-mysql-db'. Details: {e}", 'danger')
    finally:
        if cursor: cursor.close()
            
    return render_template('rental_management_list.html', title='Rental History', rentals=rentals)

@app.route('/rental/add', methods=['GET', 'POST'])
def add_rental():
    db = get_db()
    if db is None: return redirect(url_for('rental_list'))
    
    cursor = None
    customers = []
    available_cars = []
    
    try:
        cursor = db.cursor(dictionary=True) 
        
        if request.method == 'POST':
            customer_id = request.form['customer_id']
            car_id = request.form['car_id']
            rent_date = request.form['rent_date']
            expected_return_date = request.form['expected_return_date']

            # 1. Insert rental record
            sql_rental = 'INSERT INTO rental (customer_id, car_id, rent_date, expected_return_date) VALUES (%s, %s, %s, %s)'
            cursor.execute(sql_rental, (customer_id, car_id, rent_date, expected_return_date))
            
            # 2. Update car status to R (Rented)
            sql_car = 'UPDATE car SET status = %s WHERE id = %s'
            cursor.execute(sql_car, ('R', car_id))
            
            db.commit()
            flash('Rental agreement successfully started.', 'success')
            return redirect(url_for('rental_list'))
        
        # GET logic: Fetch data for the form
        cursor.execute('SELECT id, first_name, last_name, phone FROM customer ORDER BY last_name')
        customers = cursor.fetchall()
        
        cursor.execute('SELECT id, reg_number, brand, model, rate FROM car WHERE status = "A" ORDER BY brand, model')
        available_cars = cursor.fetchall()
        
    except mysql.connector.Error as e:
        flash(f'An SQL error occurred while processing the rental request: {e}', 'danger')
        return redirect(url_for('rental_list'))
    finally:
        if cursor: cursor.close()

    today = date.today().isoformat()
    default_return = (date.today() + timedelta(days=7)).isoformat()

    return render_template('rental_form.html', 
                           title='Start New Rental',
                           customers=customers,
                           available_cars=available_cars,
                           today=today,
                           default_return=default_return)

@app.route('/rental/return/<int:rental_id>', methods=['POST'])
def return_rental(rental_id):
    db = get_db()
    if db is None: return redirect(url_for('rental_list'))
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        sql_fetch = '''
            SELECT 
                r.actual_return_date, r.rent_date, c.rate, c.id AS car_id
            FROM rental r 
            JOIN car c ON r.car_id = c.id 
            WHERE r.id = %s
        '''
        cursor.execute(sql_fetch, (rental_id,))
        rental = cursor.fetchone()

        if rental is None:
            flash('Rental record not found.', 'danger')
            return redirect(url_for('rental_list'))
        
        if rental['actual_return_date'] is not None: 
            flash('This rental has already been returned and processed.', 'warning')
            return redirect(url_for('rental_list'))

        # NOTE: rental['rent_date'] is a Python date object here 
        rent_date = rental['rent_date']
        return_date = date.today()
        # Calculate rental days
        rental_days = max(1, (return_date - rent_date).days)
            
        daily_rate = float(rental['rate'])
        total_amount = daily_rate * rental_days
        car_id = rental['car_id']

        # 1. Update rental record
        sql_update_rental = 'UPDATE rental SET actual_return_date = %s WHERE id = %s'
        cursor.execute(sql_update_rental, (return_date.isoformat(), rental_id))

        # 2. Insert payment record (links to rental)
        sql_insert_payment = 'INSERT INTO payment (rental_id, amount, payment_date) VALUES (%s, %s, %s)'
        cursor.execute(sql_insert_payment, (rental_id, total_amount, return_date.isoformat()))

        # 3. Update car status
        sql_update_car = 'UPDATE car SET status = %s WHERE id = %s'
        cursor.execute(sql_update_car, ('A', car_id))

        db.commit()
        flash(f'Rental #{rental_id} returned. Charge: ${total_amount:.2f} ({rental_days} days).', 'success')
        
    except mysql.connector.Error as e:
        db.rollback() 
        flash(f'An SQL error occurred during rental return. Details: {e}', 'danger')
    finally:
        if cursor: cursor.close()
        
    return redirect(url_for('rental_list'))


# --- PAYMENT MANAGEMENT ---

@app.route('/payments')
def payment_list():
    db = get_db()
    if db is None: return render_template('index.html', title='Dashboard')
    
    cursor = None
    payments = []
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute('''
            SELECT 
                p.id AS payment_id, 
                p.amount, 
                p.payment_date, 
                r.id AS rental_id,
                c.first_name, c.last_name,
                cr.reg_number, cr.brand, cr.model
            FROM payment p
            JOIN rental r ON p.rental_id = r.id
            JOIN customer c ON r.customer_id = c.id
            JOIN car cr ON r.car_id = cr.id
            ORDER BY p.payment_date DESC
        ''')
        payments = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Error loading payment data: {e}", 'danger')
    finally:
        if cursor: cursor.close()
    
    return render_template('payment_list.html', title='Payment History', payments=payments)


# --- Initialization ---
# Custom command for initializing the database via Flask CLI
@app.cli.command('init-mysql-db')
def init_mysql_db_command():
    """Custom command to initialize the MySQL database schema."""
    init_db()

if __name__ == '__main__':
    # When running directly, ensure CLI commands are available
    cli.main(app=app)
