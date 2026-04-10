import os
import json
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Import the automation engine
import engine

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'singularity-pro-secure-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- DATABASE MODEL ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AUTH ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name, email, password = request.form.get('name'), request.form.get('email'), request.form.get('password')
        try:
            with open('input.json', 'r') as f:
                allowed = json.load(f)
        except FileNotFoundError:
            flash("System Error: Authorization file missing.", "error")
            return redirect(url_for('signup'))

        if not any(m['email'].lower() == email.lower() for m in allowed):
            flash("Your email is not authorized for access.", "error")
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for('signup'))

        new_user = User(name=name, email=email, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful!", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- DASHBOARD & ENGINE CONNECTORS ---
login_manager.login_view = 'login'
@app.route('/')
@login_required
def index():
    return render_template("index.html", user_name=current_user.name)

# Map Engine Functions to Flask Routes
app.add_url_rule('/status', view_func=engine.get_status)
app.add_url_rule('/send', view_func=engine.start_campaign, methods=['POST'])
app.add_url_rule('/pause', view_func=engine.pause_campaign, methods=['POST'])
app.add_url_rule('/resume', view_func=engine.resume_campaign, methods=['POST'])
app.add_url_rule('/abort', view_func=engine.abort_campaign, methods=['POST'])
app.add_url_rule('/upload_excel', view_func=engine.upload_excel, methods=['POST'])
app.add_url_rule('/upload_csv', view_func=engine.upload_csv, methods=['POST'])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000, use_reloader=False) # use_reloader=False prevents double Selenium triggers