from app import app, db
from models import FinancialRecord
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

def init_db():
    with app.app_context():
        # Drop all tables and recreate them for a fresh start
        db.drop_all()
        db.create_all()

        print("Database initialized.")

        # Dummy data parameters
        start_date = date.today() - relativedelta(months=24) # 2 years ago
        quarters = 8
        
        # Initial balances
        balances = {
            "Konto Comdirect": {"balance": 15000.0, "category": "Asset", "growth": 500.0},
            "N26": {"balance": 2000.0, "category": "Asset", "growth": 100.0},
            "TradeRep": {"balance": 50000.0, "category": "Asset", "growth": 2500.0},
            "Kleve, Huiskampstr. 141": {"balance": 250000.0, "category": "Asset", "growth": 1000.0},
            "Mortgage": {"balance": 200000.0, "category": "Liability", "growth": -1500.0}, # Pays down 1500 per quarter
            "Personal Loan": {"balance": 10000.0, "category": "Liability", "growth": -500.0} # Pays down 500 per quarter
        }

        # Generate data for 8 quarters
        for i in range(quarters):
            current_date = start_date + relativedelta(months=i*3)
            
            for account, data in balances.items():
                record = FinancialRecord(
                    entry_date=current_date,
                    category=data["category"],
                    account_name=account,
                    balance=data["balance"]
                )
                db.session.add(record)
                
                # Update balance for next quarter
                balances[account]["balance"] += data["growth"]
                
                # Make sure liabilities don't go below 0
                if data["category"] == "Liability" and balances[account]["balance"] < 0:
                    balances[account]["balance"] = 0.0

        db.session.commit()
        print("Dummy data inserted.")

if __name__ == '__main__':
    init_db()
