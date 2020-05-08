from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import Engine
from sqlalchemy import event

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tracker.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

#Creating Schema of tables

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20), nullable=True)
    user_email = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.TIMESTAMP, nullable=False)

    budgets = db.relationship("Budget", back_populates="user", passive_deletes=True)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_name = db.Column(db.String(20), nullable=False,  unique=True)
    budget_description = db.Column(db.String(40), nullable=True)
    budget_amount = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    currency_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.TIMESTAMP, nullable=False)
    #Relationship with user table
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    user = db.relationship("User", back_populates="budgets", passive_deletes=True)
    #Relationship with expense table
    expenses = db.relationship("Expense", back_populates="budget", passive_deletes=True)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_name = db.Column(db.String(20), nullable=False)
    expense_description = db.Column(db.String(40), nullable=True)
    expense_amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.TIMESTAMP, nullable=False)
    #Relationship with Budget table
    budget_id = db.Column(db.Integer, db.ForeignKey("budget.id", ondelete="CASCADE"))
    budget = db.relationship("Budget", back_populates="expenses", passive_deletes=True)


#Excluding the expenses from the project
'''
category_id = db.Column(db.Integer, db.ForeignKey("category.category_id"))
category = db.relationship("Category", back_populates="expense")
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(20), nullable=False)
    icon_id = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.TIMESTAMP, nullable=False)
    modified_at = db.Column(db.TIMESTAMP, nullable=False)

    category = db.relationship("Expense", back_populates="category")
'''






