from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func, extract, case
import os

app = Flask(__name__, instance_relative_config=True)
app.secret_key = 'your-secret-key'  # Use a secure secret key in production

# Update the path to your database file here
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/saadathasanakhtarusmani/Documents/BudgetManagerApp/data/budget.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# --- APP CONFIGURATION ---

app = Flask(__name__, instance_relative_config=True)
app.secret_key = 'your-secret-key'  # Use a secure secret key in production

# Update the path to your database file here
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/saadathasanakhtarusmani/Documents/BudgetManagerApp/data/budget.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE MODELS ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float)
    description = db.Column(db.String(255))
    date = db.Column(db.Date, default=datetime.utcnow)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float)
    description = db.Column(db.String(255))
    date = db.Column(db.Date, default=datetime.utcnow)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.String(7))
    amount = db.Column(db.Float)

with app.app_context():
    db.create_all()

# --- AUTH ROUTES ---

@app.route('/')
def index():
    return redirect(url_for('dashboard') if session.get('user_id') else url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

# --- DASHBOARD ---

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session['user_id']
    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expense.query.filter_by(user_id=user_id).all()
    total_income = sum(i.amount for i in incomes)
    total_expenses = sum(e.amount for e in expenses)
    balance = total_income - total_expenses

    current_month = datetime.today().strftime('%Y-%m')
    goal = Goal.query.filter_by(user_id=user_id, month=current_month).first()
    goal_amount = goal.amount if goal else None

    return render_template('dashboard.html',
                           income=total_income,
                           expenses=total_expenses,
                           balance=balance,
                           goal_amount=goal_amount)

# --- INCOME CRUD ---

@app.route('/income', methods=['POST'])
def add_income():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    amount = float(request.form['amount'])
    description = request.form['description']
    date_str = request.form.get('date')
    date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()

    income = Income(user_id=session['user_id'], amount=amount, description=description, date=date)
    db.session.add(income)
    db.session.commit()
    flash('Income added.', 'success')
    return redirect(url_for('income_history'))

@app.route('/income/history')
def income_history():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    incomes = Income.query.filter_by(user_id=session['user_id']).order_by(Income.date.desc()).all()
    return render_template('income_history.html', incomes=incomes)

@app.route('/income/edit/<int:id>', methods=['GET', 'POST'])
def edit_income(id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    income = db.session.get(Income, id)
    if not income or income.user_id != session['user_id']:
        flash("Unauthorized access!", 'danger')
        return redirect(url_for('income_history'))

    if request.method == 'POST':
        income.amount = float(request.form['amount'])
        income.description = request.form['description']
        date_str = request.form.get('date')
        if date_str:
            income.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        db.session.commit()
        flash('Income updated.', 'success')
        return redirect(url_for('income_history'))
    return render_template('edit_income.html', income=income)

@app.route('/income/delete/<int:id>', methods=['POST'])
def delete_income(id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    income = db.session.get(Income, id)
    if not income or income.user_id != session['user_id']:
        flash("Unauthorized access!", 'danger')
        return redirect(url_for('income_history'))
    db.session.delete(income)
    db.session.commit()
    flash('Income deleted.', 'success')
    return redirect(url_for('income_history'))

# --- EXPENSE CRUD ---

@app.route('/expense', methods=['POST'])
def add_expense():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    amount = float(request.form['amount'])
    description = request.form['description']
    date_str = request.form.get('date')
    date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()

    expense = Expense(user_id=session['user_id'], amount=amount, description=description, date=date)
    db.session.add(expense)
    db.session.commit()
    flash('Expense added.', 'success')
    return redirect(url_for('expense_history'))

@app.route('/expense/history')
def expense_history():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    expenses = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc()).all()
    return render_template('expense_history.html', expenses=expenses)

@app.route('/expense/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    expense = db.session.get(Expense, id)
    if not expense or expense.user_id != session['user_id']:
        flash("Unauthorized access!", 'danger')
        return redirect(url_for('expense_history'))

    if request.method == 'POST':
        expense.amount = float(request.form['amount'])
        expense.description = request.form['description']
        date_str = request.form.get('date')
        if date_str:
            expense.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        db.session.commit()
        flash('Expense updated.', 'success')
        return redirect(url_for('expense_history'))
    return render_template('edit_expense.html', expense=expense)

@app.route('/expense/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    expense = db.session.get(Expense, id)
    if not expense or expense.user_id != session['user_id']:
        flash("Unauthorized access!", 'danger')
        return redirect(url_for('expense_history'))
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted.', 'success')
    return redirect(url_for('expense_history'))

# --- GOAL ---

@app.route('/goal', methods=['GET', 'POST'])
def set_goal():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session['user_id']
    current_month = datetime.today().strftime('%Y-%m')
    goal = Goal.query.filter_by(user_id=user_id, month=current_month).first()
    if request.method == 'POST':
        amount = float(request.form['amount'])
        if goal:
            goal.amount = amount
        else:
            goal = Goal(user_id=user_id, month=current_month, amount=amount)
            db.session.add(goal)
        db.session.commit()
        flash('Goal set/updated.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('goal.html', goal=goal)

# --- CHART DATA API ---

@app.route('/chart-data')
def chart_data():
    if not session.get('user_id'):
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']

    # Determine the correct expression for month based on the database dialect
    if 'sqlite' in db.engine.url.drivername:
        month_expr = func.strftime('%Y-%m', Income.date)
    else:
        month_expr = func.to_char(Income.date, 'YYYY-MM')  # For PostgreSQL or others

    # Aggregate income and expense by month
    income_data = db.session.query(
        month_expr.label('month'),
        func.sum(Income.amount).label('total_income')
    ).filter(Income.user_id == user_id).group_by(month_expr).all()

    expense_data = db.session.query(
        month_expr.label('month'),
        func.sum(Expense.amount).label('total_expense')
    ).filter(Expense.user_id == user_id).group_by(month_expr).all()

    # Merge income and expense data by month
    income_dict = {item.month: item.total_income for item in income_data}
    expense_dict = {item.month: item.total_expense for item in expense_data}
    months = sorted(set(income_dict.keys()).union(expense_dict.keys()))

    chart_data = {
        "labels": months,
        "income": [income_dict.get(month, 0) for month in months],
        "expenses": [expense_dict.get(month, 0) for month in months]
    }

    return jsonify(chart_data)


# --- RUN APP ---

if __name__ == '__main__':
    app.run(debug=True)
