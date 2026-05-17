from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()

class FinancialRecord(db.Model):
    __tablename__ = 'financial_record'

    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False, default=date.today)
    category = db.Column(db.String(50), nullable=False) # Asset, Liability, Cashflow
    account_name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, nullable=False, default=0.0)

    def __repr__(self):
        return f"<FinancialRecord {self.category} - {self.account_name} - {self.balance}>"
