from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tracker.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

#Creating Schema of tables

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20), nullable=True)
    user_email = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.TIMESTAMP, nullable=False)

    bugdets = db.relationship("Budget", back_populates="user")

class Budget(db.Model):
    budget_id = db.Column(db.Integer, primary_key=True)
    budget_name = db.Column(db.String(20), nullable=False)
    budget_description = db.Column(db.String(40), nullable=True)
    budget_amount = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    currency_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.TIMESTAMP, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))

    user = db.relationship("User", back_populates="budget")

class Expense(db.Model):
    expense_id = db.Column(db.Integer, primary_key=True)
    expense_name = db.Column(db.String(20), nullable=False)
    expense_description = db.Column(db.String(40), nullable=True)
    expense_amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.TIMESTAMP, nullable=False)

    budget_id = db.Column(db.Integer, db.ForeignKey("budget.budget_id"))

    budget = db.relationship("Budget", back_populates="expense")

    category_id = db.Column(db.Integer, db.ForeignKey("category.category_id"))

    category = db.relationship("Category", back_populates="expense")

class Category(db.Model):
    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(20), nullable=False)
    icon_id = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.TIMESTAMP, nullable=False)
    modified_at = db.Column(db.TIMESTAMP, nullable=False)

    category = db.relationship("Expense", back_populates="category")



#will create the DB
db.create_all()







