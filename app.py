import os
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from models import db, FinancialRecord
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///networth.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def dashboard():
    # Calculate current metrics
    # Get the latest entry date for each account
    subquery = db.session.query(
        FinancialRecord.account_name,
        func.max(FinancialRecord.entry_date).label('max_date')
    ).group_by(FinancialRecord.account_name).subquery()

    latest_records = db.session.query(FinancialRecord).join(
        subquery,
        db.and_(
            FinancialRecord.account_name == subquery.c.account_name,
            FinancialRecord.entry_date == subquery.c.max_date
        )
    ).all()

    total_assets = sum(r.balance for r in latest_records if r.category == 'Asset')
    total_liabilities = sum(r.balance for r in latest_records if r.category == 'Liability')
    current_net_worth = total_assets - total_liabilities

    # Get data for previous quarter to calculate QoQ Growth
    # For simplicity, we find the distinct dates and get the second most recent
    distinct_dates = db.session.query(FinancialRecord.entry_date).distinct().order_by(FinancialRecord.entry_date.desc()).all()
    qoq_growth = 0.0
    if len(distinct_dates) >= 2:
        prev_date = distinct_dates[1][0]
        prev_records = db.session.query(FinancialRecord).filter(FinancialRecord.entry_date <= prev_date).all()
        
        # Calculate net worth at prev_date
        prev_subquery = db.session.query(
            FinancialRecord.account_name,
            func.max(FinancialRecord.entry_date).label('max_date')
        ).filter(FinancialRecord.entry_date <= prev_date).group_by(FinancialRecord.account_name).subquery()

        prev_latest_records = db.session.query(FinancialRecord).join(
            prev_subquery,
            db.and_(
                FinancialRecord.account_name == prev_subquery.c.account_name,
                FinancialRecord.entry_date == prev_subquery.c.max_date
            )
        ).all()

        prev_assets = sum(r.balance for r in prev_latest_records if r.category == 'Asset')
        prev_liabilities = sum(r.balance for r in prev_latest_records if r.category == 'Liability')
        prev_net_worth = prev_assets - prev_liabilities

        if prev_net_worth != 0:
            qoq_growth = ((current_net_worth - prev_net_worth) / abs(prev_net_worth)) * 100

    # Get chart data (Net worth over time per distinct date)
    chart_labels = []
    chart_data = []
    
    # Sort distinct dates ascending
    dates_asc = sorted([d[0] for d in distinct_dates])
    for dt in dates_asc:
        dt_subquery = db.session.query(
            FinancialRecord.account_name,
            func.max(FinancialRecord.entry_date).label('max_date')
        ).filter(FinancialRecord.entry_date <= dt).group_by(FinancialRecord.account_name).subquery()
        
        dt_records = db.session.query(FinancialRecord).join(
            dt_subquery,
            db.and_(
                FinancialRecord.account_name == dt_subquery.c.account_name,
                FinancialRecord.entry_date == dt_subquery.c.max_date
            )
        ).all()
        
        dt_assets = sum(r.balance for r in dt_records if r.category == 'Asset')
        dt_liabilities = sum(r.balance for r in dt_records if r.category == 'Liability')
        dt_net_worth = dt_assets - dt_liabilities
        
        chart_labels.append(dt.strftime('%Y-%m-%d'))
        chart_data.append(dt_net_worth)

    from collections import defaultdict
    # Compute Data Completeness
    all_records = db.session.query(FinancialRecord.entry_date, FinancialRecord.account_name).all()
    total_accounts = set(r.account_name for r in all_records)
    quarter_data = defaultdict(set)
    for r in all_records:
        quarter = f"Q{(r.entry_date.month - 1) // 3 + 1} {r.entry_date.year}"
        quarter_data[quarter].add(r.account_name)
    
    completeness_stats = []
    sorted_quarters = sorted(quarter_data.items(), key=lambda x: (int(x[0].split()[1]), x[0].split()[0]), reverse=True)
    
    for q, accounts in sorted_quarters[:4]:
        percentage = len(accounts) / len(total_accounts) if total_accounts else 0
        if percentage >= 0.875:
            quartile = 100
        elif percentage >= 0.625:
            quartile = 75
        elif percentage >= 0.375:
            quartile = 50
        elif percentage >= 0.125:
            quartile = 25
        else:
            quartile = 0
            
        completeness_stats.append({
            'quarter': q,
            'percentage': int(percentage * 100),
            'quartile': quartile,
            'count': len(accounts),
            'total': len(total_accounts)
        })

    return render_template('dashboard.html', 
                           current_net_worth=current_net_worth,
                           total_assets=total_assets,
                           total_liabilities=total_liabilities,
                           qoq_growth=qoq_growth,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           completeness_stats=completeness_stats)

@app.route('/add', methods=['GET', 'POST'])
def add_record():
    if request.method == 'POST':
        try:
            entry_date = datetime.strptime(request.form['entry_date'], '%Y-%m-%d').date()
            category = request.form['category']
            account_name = request.form['account_name']
            balance = float(request.form['balance'])

            new_record = FinancialRecord(
                entry_date=entry_date,
                category=category,
                account_name=account_name,
                balance=balance
            )
            db.session.add(new_record)
            db.session.commit()
            
            # Since it's mobile first, we might want to redirect to dashboard immediately
            return redirect(url_for('dashboard'))
        except ValueError:
            pass # Handle error gracefully in real app
            
    return render_template('add_record.html')

@app.route('/history')
def history():
    account = request.args.get('account')
    query = FinancialRecord.query
    if account:
        query = query.filter(FinancialRecord.account_name == account)
    records = query.order_by(FinancialRecord.entry_date.desc()).all()
    return render_template('history.html', records=records, account_filter=account)

@app.route('/edit/<int:record_id>', methods=['GET', 'POST'])
def edit_record(record_id):
    record = FinancialRecord.query.get_or_404(record_id)
    if request.method == 'POST':
        try:
            record.entry_date = datetime.strptime(request.form['entry_date'], '%Y-%m-%d').date()
            record.category = request.form['category']
            record.account_name = request.form['account_name']
            record.balance = float(request.form['balance'])
            db.session.commit()
            return redirect(url_for('history'))
        except ValueError:
            pass
    return render_template('edit_record.html', record=record)

@app.route('/delete/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    record = FinancialRecord.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
    return redirect(url_for('history'))

@app.route('/breakdown/<category>')
def breakdown(category):
    if category not in ['Asset', 'Liability']:
        return redirect(url_for('dashboard'))
    
    subquery = db.session.query(
        FinancialRecord.account_name,
        func.max(FinancialRecord.entry_date).label('max_date')
    ).filter(FinancialRecord.category == category).group_by(FinancialRecord.account_name).subquery()

    latest_records = db.session.query(FinancialRecord).join(
        subquery,
        db.and_(
            FinancialRecord.account_name == subquery.c.account_name,
            FinancialRecord.entry_date == subquery.c.max_date
        )
    ).order_by(FinancialRecord.balance.desc()).all()
    
    total = sum(r.balance for r in latest_records)

    return render_template('breakdown.html', category=category, records=latest_records, total=total)

@app.route('/completeness/<quarter>')
def completeness_detail(quarter):
    all_records = db.session.query(FinancialRecord.entry_date, FinancialRecord.account_name, FinancialRecord.category).all()
    
    account_category_map = {}
    total_accounts = set()
    quarter_accounts = set()
    
    for r in all_records:
        account_category_map[r.account_name] = r.category
        total_accounts.add(r.account_name)
        q_str = f"Q{(r.entry_date.month - 1) // 3 + 1} {r.entry_date.year}"
        if q_str == quarter:
            quarter_accounts.add(r.account_name)
            
    missing_accounts = total_accounts - quarter_accounts
    
    missing_assets = [acc for acc in missing_accounts if account_category_map.get(acc) == 'Asset']
    missing_liabilities = [acc for acc in missing_accounts if account_category_map.get(acc) == 'Liability']
    
    updated_assets = [acc for acc in quarter_accounts if account_category_map.get(acc) == 'Asset']
    updated_liabilities = [acc for acc in quarter_accounts if account_category_map.get(acc) == 'Liability']
    
    return render_template('completeness.html', 
                           quarter=quarter,
                           missing_assets=sorted(missing_assets),
                           missing_liabilities=sorted(missing_liabilities),
                           updated_assets=sorted(updated_assets),
                           updated_liabilities=sorted(updated_liabilities))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
