from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import extract, func
import os

app = Flask(__name__)
app.secret_key = 'secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

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

# --- AUTH ROUTES ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        user = User(username=username, password=password)
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
        user = User.query.filter_by(username=username, password=password).first()
        if user:
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
    if 'user_id' not in session:
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
    if 'user_id' not in session:
        return redirect(url_for('login'))

    amount = float(request.form['amount'])
    description = request.form['description']
    date_str = request.form.get('date')
    if date_str:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        date = datetime.utcnow().date()

    income = Income(user_id=session['user_id'], amount=amount, description=description, date=date)
    db.session.add(income)
    db.session.commit()
    flash('Income added.', 'success')
    return redirect(url_for('income_history'))

@app.route('/income/history')
def income_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    incomes = Income.query.filter_by(user_id=session['user_id']).order_by(Income.date.desc()).all()
    return render_template('income_history.html', incomes=incomes)

@app.route('/income/edit/<int:id>', methods=['GET', 'POST'])
def edit_income(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    income = Income.query.get_or_404(id)
    if income.user_id != session['user_id']:
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    income = Income.query.get_or_404(id)
    if income.user_id != session['user_id']:
        flash("Unauthorized access!", 'danger')
        return redirect(url_for('income_history'))
    db.session.delete(income)
    db.session.commit()
    flash('Income deleted.', 'success')
    return redirect(url_for('income_history'))

# --- EXPENSE CRUD ---

@app.route('/expense', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    amount = float(request.form['amount'])
    description = request.form['description']
    date_str = request.form.get('date')
    if date_str:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        date = datetime.utcnow().date()

    expense = Expense(user_id=session['user_id'], amount=amount, description=description, date=date)
    db.session.add(expense)
    db.session.commit()
    flash('Expense added.', 'success')
    return redirect(url_for('expense_history'))

@app.route('/expense/history')
def expense_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expenses = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc()).all()
    return render_template('expense_history.html', expenses=expenses)

@app.route('/expense/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.get_or_404(id)
    if expense.user_id != session['user_id']:
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.get_or_404(id)
    if expense.user_id != session['user_id']:
        flash("Unauthorized access!", 'danger')
        return redirect(url_for('expense_history'))
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted.', 'success')
    return redirect(url_for('expense_history'))

# --- GOAL ---

@app.route('/goal', methods=['GET', 'POST'])
def set_goal():
    if 'user_id' not in session:
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
    if 'user_id' not in session:
        return jsonify({})

    user_id = session['user_id']

    # Get last 12 months (month-year strings)
    today = datetime.today()
    months = []
    for i in range(11, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year - ((today.month - i - 1) // 12)
        months.append(f"{y}-{m:02d}")

    # Query total income per month
    income_data = (
        db.session.query(
            func.strftime("%Y-%m", Income.date),
            func.coalesce(func.sum(Income.amount), 0)
        )
        .filter(Income.user_id == user_id)
        .filter(func.strftime("%Y-%m", Income.date).in_(months))
        .group_by(func.strftime("%Y-%m", Income.date))
        .all()
    )
    income_dict = {month: 0 for month in months}
    for month, total in income_data:
        income_dict[month] = total

    # Query total expense per month
    expense_data = (
        db.session.query(
            func.strftime("%Y-%m", Expense.date),
            func.coalesce(func.sum(Expense.amount), 0)
        )
        .filter(Expense.user_id == user_id)
        .filter(func.strftime("%Y-%m", Expense.date).in_(months))
        .group_by(func.strftime("%Y-%m", Expense.date))
        .all()
    )
    expense_dict = {month: 0 for month in months}
    for month, total in expense_data:
        expense_dict[month] = total

    return jsonify({
        'months': months,
        'income': [income_dict[m] for m in months],
        'expenses': [expense_dict[m] for m in months]
    })

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
