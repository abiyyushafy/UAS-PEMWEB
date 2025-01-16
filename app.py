import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Ganti dengan secret key yang aman

# MySQL Connection Configuration
db_config = {
    'host': "vlnon.h.filess.io",
    'database': "tokoku_weatherat",
    'user': "tokoku_weatherat",
    'password': "a076f5b8f8d9ccba80512b53010a3fe3499575c1",
    'port': "3305"
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Test database connection at startup
try:
    test_connection = get_db_connection()
    if test_connection and test_connection.is_connected():
        db_Info = test_connection.get_server_info()
        print("Connected to MariaDB Server version ", db_Info)
        cursor = test_connection.cursor()
        cursor.execute("select database();")
        record = cursor.fetchone()
        print("You're connected to database: ", record)
        cursor.close()
        test_connection.close()
except Error as e:
    print("Error while connecting to MariaDB", e)

# Define admin_required decorator
def admin_required(f):
    """Decorator to restrict access to admin users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()

        if not user or user['permission'] != 50:  # Ensure only admins (permission 50) can access
            flash('Access Denied. Admin privileges required.', 'error')
            return redirect(url_for('login'))
            
        return f(*args, **kwargs)
    return decorated_function
    
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.md5(request.form['password'].encode()).hexdigest()

        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection error', 'error')
                return render_template('login.html')
                
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', 
                          (username, password))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session['user_id'] = user['id']
                flash('Login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid username or password!', 'error')

        except Error as e:
            print(f"Database error: {e}")
            flash('Database error occurred', 'error')

    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return redirect(url_for('login'))
            
        cursor = conn.cursor(dictionary=True)

        # Fetch user data
        cursor.execute('SELECT username FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()

        # Fetch existing products and promos
        cursor.execute('SELECT * FROM products')
        products = cursor.fetchall()

        cursor.execute('SELECT * FROM promos')
        promos = cursor.fetchall()

        if request.method == 'POST':
            action = request.form['action']

            if action == 'add_product':
                name = request.form['product_name']
                price = request.form['product_price'].replace('Rp', '').replace(',', '').replace('.', '')[:-3]
                cursor.execute('INSERT INTO products (name, price) VALUES (%s, %s)', (name, price))
                conn.commit()
                flash('Product added successfully!', 'success')

            elif action == 'add_promo':
                name = request.form['promo_name']
                discount = request.form['promo_discount']
                cursor.execute('INSERT INTO promos (name, discount) VALUES (%s, %s)', (name, discount))
                conn.commit()
                flash('Promo added successfully!', 'success')

            elif action == 'delete_product':
                product_id = request.form['product_id']
                cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
                conn.commit()
                flash('Product deleted successfully!', 'success')

            elif action == 'delete_promo':
                promo_id = request.form['promo_id']
                cursor.execute('DELETE FROM promos WHERE id = %s', (promo_id,))
                conn.commit()
                flash('Promo deleted successfully!', 'success')

        cursor.close()
        conn.close()
        return render_template('admin_dashboard.html', user=user, products=products, promos=promos)
        
    except Error as e:
        print(f"Database error: {e}")
        flash('Database error occurred', 'error')
        return redirect(url_for('login'))

@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def user_list():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return redirect(url_for('login'))
            
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT username FROM users WHERE id = %s', (session['user_id'],))
        current_user = cursor.fetchone()
        
        if request.method == 'POST':
            action = request.form['action']
            if action == 'add_user':
                username = request.form['username']
                password = hashlib.md5(request.form['password'].encode()).hexdigest()
                permission = int(request.form['permission'])
                cursor.execute('INSERT INTO users (username, password, permission) VALUES (%s, %s, %s)', 
                              (username, password, permission))
                conn.commit()
                flash('User added successfully!', 'success')
            elif action == 'update_user':
                user_id = request.form['user_id']
                username = request.form['username']
                permission = int(request.form['permission'])
                cursor.execute('UPDATE users SET username = %s, permission = %s WHERE id = %s', 
                              (username, permission, user_id))
                conn.commit()
                flash('User updated successfully!', 'success')

        cursor.execute('SELECT id, username, permission FROM users')
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('user_list.html', users=users, user=current_user)
        
    except Error as e:
        print(f"Database error: {e}")
        flash('Database error occurred', 'error')
        return redirect(url_for('login'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return redirect(url_for('user_list'))
            
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('User deleted successfully!', 'success')
        
    except Error as e:
        print(f"Database error: {e}")
        flash('Database error occurred', 'error')
        
    return redirect(url_for('user_list'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
