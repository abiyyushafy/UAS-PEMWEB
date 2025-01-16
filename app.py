import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Ganti dengan secret key yang aman

# MySQL Connection Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Replace with your password if necessary
    'database': 'tokoku'
}

def get_db_connection():
    """Connect to the database and return the connection."""
    return mysql.connector.connect(**db_config)

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

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', 
                       (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password!', 'error')

    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    conn = get_db_connection()
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

    conn.close()
    return render_template('admin_dashboard.html', user=user, products=products, promos=promos)

@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def user_list():
    conn = get_db_connection()
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
    conn.close()
    return render_template('user_list.html', users=users, user=current_user)  # Add user=current_user here

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('user_list'))

@app.route('/admin/users/update', methods=['POST'])
@admin_required
def update_user():
    user_id = request.form['user_id']
    username = request.form['username']
    permission = int(request.form['permission'])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET username = %s, permission = %s WHERE id = %s', 
                   (username, permission, user_id))
    conn.commit()
    conn.close()
    flash('User updated successfully!', 'success')
    return redirect(url_for('user_list'))



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
