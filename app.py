# app.py

import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kunci-rahasia-yang-sangat-sulit-ditebak'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/moneypad_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    transaksi = db.relationship('Transaksi', backref='pemilik', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipe = db.Column(db.String(50), nullable=False) 
    deskripsi = db.Column(db.String(200), nullable=False)
    jumlah = db.Column(db.Float, nullable=False)
    kategori = db.Column(db.String(100), nullable=False)
    tanggal = db.Column(db.Date, nullable=False, default=datetime.date.today)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Routes 
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'danger')
            return render_template('register.html')
        
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            return render_template('register.html')
    return render_template('register.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check if email and password are provided
        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        if user:
            # Debug: print hash info (remove in production)
            print(f"Stored hash: {user.password_hash}")
            print(f"Hash length: {len(user.password_hash)}")
            
            if user.check_password(password):
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Incorrect password. Please try again.', 'danger')
        else:
            flash('Email not found. Please register first.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    transaksi = Transaksi.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', transaksi=transaksi)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        tipe = request.form['tipe']
        deskripsi = request.form['deskripsi']
        jumlah = float(request.form['jumlah'])
        kategori = request.form['kategori']
        tanggal = datetime.datetime.strptime(request.form['tanggal'], '%Y-%m-%d').date()
        
        transaksi_baru = Transaksi(tipe=tipe, deskripsi=deskripsi, jumlah=jumlah, kategori=kategori, tanggal=tanggal, user_id=current_user.id)
        db.session.add(transaksi_baru)
        db.session.commit()
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('form_transaksi.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    transaksi = Transaksi.query.get_or_404(id)
    if transaksi.user_id != current_user.id:
        flash('You do not have permission to edit this transaction.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        transaksi.tipe = request.form['tipe']
        transaksi.deskripsi = request.form['deskripsi']
        transaksi.jumlah = float(request.form['jumlah'])
        transaksi.kategori = request.form['kategori']
        transaksi.tanggal = datetime.datetime.strptime(request.form['tanggal'], '%Y-%m-%d').date()
        
        db.session.commit()
        flash('Transaction updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('form_transaksi.html', transaksi=transaksi)

@app.route('/delete/<int:id>')
@login_required
def delete_transaction(id):
    transaksi = Transaksi.query.get_or_404(id)
    if transaksi.user_id != current_user.id:
        flash('You do not have permission to delete this transaction.', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(transaksi)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

# Route untuk reset database (hanya untuk development)
@app.route('/reset_db')
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        flash('Database reset successfully! Please register again.', 'success')
        return redirect(url_for('register'))
    except Exception as e:
        flash(f'Error resetting database: {str(e)}', 'danger')
        return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)