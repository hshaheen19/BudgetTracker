import os
import pytest
import tempfile
import datetime
import app
from app import User, Budget, Expense
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

@pytest.fixture
def db_handle():
    db_fd, db_fname = tempfile.mkstemp()
    app.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_fname
    app.app.config["TESTING"] = True
    
    with app.app.app_context():
        app.db.create_all()
        
    yield app.db
    
    app.db.session.remove()
    os.close(db_fd)
    os.unlink(db_fname)

def _get_user():
    return User(
        user_name="User 1",
        user_email="user1@",
        password="abc",
        created_at=datetime.datetime.now()
    )

def _get_budget():
    return Budget(
        budget_name="Budget 1",
        budget_amount=10,
        start_date=datetime.datetime.now(),
        end_date=datetime.datetime.now(),
        currency_type="euro",
        created_at=datetime.datetime.now()
    )

def _get_expense():
    return Expense(
        expense_name="Expense 1",
        expense_amount=1,
        expense_date=datetime.datetime.now(),
        created_at=datetime.datetime.now()
    )

def test_create_instances(db_handle):
    
    """
    Tests that we can create one instance of each model and save them to the
    database using valid values for all columns. After creation, test that 
    everything can be found from database, and that all relationships have been
    saved correctly.
    """

    # Create everything
    user = _get_user()
    budget = _get_budget()
    expense = _get_expense()

    budget.user = user
    expense.budget = budget

    db_handle.session.add(user)
    db_handle.session.add(budget)
    db_handle.session.add(expense)
    db_handle.session.commit()
    
    # Check that everything exists
    assert User.query.count() == 1
    assert Budget.query.count() == 1
    assert Expense.query.count() == 1

    db_user = User.query.first()
    db_bugdet = Budget.query.first()
    db_expense = Expense.query.first()
    
    # Check all relationships (both sides)
    assert db_bugdet.user == db_user
    assert db_expense.budget == db_bugdet
    
    assert db_bugdet in db_user.budgets
    assert db_expense in db_bugdet.expenses


def test_user_ondelete(db_handle):
    """
    Tests that expense and bugdet is cascaded when the 
    user is deleted.
    """
    # Create everything
    user = _get_user()
    budget = _get_budget()
    expense = _get_expense()

    budget.user = user
    expense.budget = budget

    db_handle.session.add(user)
    db_handle.session.add(budget)
    db_handle.session.add(expense)
    db_handle.session.commit()

    # Check that everything exists
    assert User.query.count() == 1
    assert Budget.query.count() == 1
    assert Expense.query.count() == 1

    #Delete the user
    db_handle.session.delete(user)
    db_handle.session.commit()

    #Check that budget and expense are cascaded
    assert Budget.query.count() == 0
    assert Expense.query.count() == 0


def test_expense_onupdate_budget(db_handle):
    """
    Tests that expense is change in a budget and 
    add another expense and check changes in a 
    budget
    """
    #Creating budget and expense
    budget = _get_budget()
    expense = _get_expense()
    expense.budget = budget
    #Add it in the DB
    db_handle.session.add(expense)
    db_handle.session.commit()

    # Check that everything exists
    assert Budget.query.count() == 1
    assert Expense.query.count() == 1

    #Retreive both from DB
    db_bugdet = Budget.query.first()
    db_expense = Expense.query.first()

    #Change the expense 
    db_expense.expense_amount = 2
    #Get new expense and add it to the budget
    new_expense = _get_expense()
    #Can not add expense with same name
    new_expense.expense_name = "new expense"
    
    new_expense.budget = db_bugdet

    #Add it in the DB
    db_handle.session.add(new_expense)
    db_handle.session.commit()

    # Check that everything exists
    assert Budget.query.count() == 1
    assert Expense.query.count() == 2


def test_user_budget_unique(db_handle):
    """
    Tests that two budgets with same user
    can not exist for same user 
    """
    user = _get_user()
    budget_1 = _get_budget()
    budget_2 = _get_budget()
    budget_1.user = user
    budget_2.user = user
    db_handle.session.add(budget_1)
    db_handle.session.add(budget_2)    
    with pytest.raises(IntegrityError):
        db_handle.session.commit()