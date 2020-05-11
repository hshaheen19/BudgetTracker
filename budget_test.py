import json
import os
import pytest
import tempfile
import time
from datetime import datetime
from jsonschema import validate
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, StatementError
import app
from app import db, User, Budget, Expense



@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

@pytest.fixture
def client():
    db_fd, db_fname = tempfile.mkstemp()
    app.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_fname
    app.app.config["TESTING"] = True
    
    with app.app.app_context():
        db.create_all()
        _populate_db()
        
    yield app.app.test_client()
    
    os.close(db_fd)
    os.unlink(db_fname)

def _populate_db():
    for i in range(1, 4):
        u = User(
            user_name="User-{}".format(i),
            user_email="user@{}".format(i),
            password="abc"
        )
        for x in range(1,3):
            b = Budget(
                budget_name="Oulu-{}{}".format(i,x),
                budget_description="my budget",
                budget_amount=100,
                currency_type= "euro",
                start_date= datetime.now(),
                end_date=datetime.now(),
                user = u
            )
            for z in range(1,3):
                e = Expense(
                    expense_name="Food-{}{}".format(x,z),
                    expense_description="my food",
                    expense_amount=10,
                    expense_date= datetime.now(),
                    budget = b
                )
                db.session.add(e)

            db.session.add(u)

        db.session.add(b)

    db.session.commit()

def _get_budget_json(number=4):
    """
    Creates a valid budget JSON object to be used for PUT and POST tests.
    """
    return {"budget_name": "Oulu-{}".format(number), "budget_description": "my budget", "budget_amount": 150, "currency_type": "euro", "start_date": "2018-05-03", "end_date": "2018-05-08" }

def _get_expense_json(number=4):
    """
    Creates a valid expense JSON object to be used for PUT and POST tests.
    """
    return {"expense_name": "Food-{}".format(number), "expense_description": "my food", "expense_amount": 10, "expense_date": "2018-05-03" }


def _check_namespace(client, response):
    """
    Checks that the "budtrack" namespace is found from the response body, and
    that its "name" attribute is a URL that can be accessed.
    """
    ns_href = response["@namespaces"]["budtrack"]["name"]
    resp = client.get(ns_href)
    assert resp.status_code == 200
    
def _check_control_get_method(ctrl, client, obj):
    """
    Checks a GET type control from a JSON object be it root document or an item
    in a collection. Also checks that the URL of the control can be accessed.
    """
    
    href = obj["@controls"][ctrl]["href"]
    resp = client.get(href)
    assert resp.status_code == 200
    
    
def _check_control_post_method(ctrl, client, obj , schema_):
    """
    Checks a POST type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid budget against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 201.
    """
    
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "post"
    assert encoding == "json"
    body = schema_
    validate(body, schema)
    resp = client.post(href, json=body)
    assert resp.status_code == 201

def _check_control_delete_method(ctrl, client, obj):
    """
    Checks a DELETE type control from a JSON object be it root document or an
    item in a collection. Checks the contrl's method in addition to its "href".
    Also checks that using the control results in the correct status code of 204.
    """
    
    href = obj["@controls"][ctrl]["href"]
    method = obj["@controls"][ctrl]["method"].lower()
    assert method == "delete"
    resp = client.delete(href)
    assert resp.status_code == 204
    
def _check_control_put_method(ctrl, client, obj, schema_, iden):
    """
    Checks a PUT type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid sensor against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 204.
    """
    
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "put"
    assert encoding == "json"
    body = schema_
    body[iden] = obj[iden]
    validate(body, schema)
    resp = client.put(href, json=body)
    assert resp.status_code == 204


'''
TEST FOR BUDGET COLLECTION RESOURCE
'''
BUDGET_COLLECTION_URL = "/api/users/User-1/budgets"
def test_BudgetCollection_get(client):
        resp = client.get(BUDGET_COLLECTION_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_post_method("budtrack:add-budget", client, body, _get_budget_json())
        assert len(body["items"]) == 2
        for item in body["items"]:
            _check_control_get_method("self", client, item)
            _check_control_get_method("profile", client, item)

def test_BudgetCollection_post(client):
        valid = _get_budget_json()
        
        # test with wrong content type
        resp = client.post(BUDGET_COLLECTION_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
        # test with valid and see that it exists afterward
        resp = client.post(BUDGET_COLLECTION_URL, json=valid)
        assert resp.status_code == 201

        # send same data again for 409
        resp = client.post(BUDGET_COLLECTION_URL, json=valid)
        assert resp.status_code == 409
        
        # remove password field for 400
        valid.pop("start_date")
        resp = client.post(BUDGET_COLLECTION_URL, json=valid)
        assert resp.status_code == 400

        

'''
TEST FOR BUDGET ITEM RESOURCE
'''
BUDGET_ITEM_URL = "/api/users/User-1/budgets/Oulu-11"
INVALID_URL = "/api/users/User-1/budgets/Oulu-51"
    
def test_BudgetItem_get(client):
        resp = client.get(BUDGET_ITEM_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_get_method("profile", client, body)
        _check_control_put_method("edit", client, body, _get_budget_json(),"budget_name")
        _check_control_post_method("budtrack:add-expense", client, body, _get_expense_json())
        _check_control_delete_method("budtrack:delete", client, body)
        resp = client.get(INVALID_URL)
        assert resp.status_code == 404

def test_BudgetItem_post(client):
        valid = _get_expense_json()
        
        # test with wrong content type
        resp = client.post(BUDGET_ITEM_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
        # test with valid and see that it exists afterward
        resp = client.post(BUDGET_ITEM_URL, json=valid)
        assert resp.status_code == 201

        # send same data again for 409
        resp = client.post(BUDGET_ITEM_URL, json=valid)
        assert resp.status_code == 409
        
        # remove password field for 400
        valid.pop("expense_date")
        resp = client.post(BUDGET_ITEM_URL, json=valid)
        assert resp.status_code == 400


def test_UserItem_put(client):
        valid = _get_budget_json()
        
        # test with wrong content type
        resp = client.put(BUDGET_ITEM_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
        resp = client.put(INVALID_URL, json=valid)
        assert resp.status_code == 404
        
        # test with another budget's name
        valid["budget_name"] = "Oulu-12"
        resp = client.put(BUDGET_ITEM_URL, json=valid)
        assert resp.status_code == 409
        
        # test with valid (only change password)
        valid["budget_name"] = "Oulu-11"
        valid["budget_amount"] = 77
        resp = client.put(BUDGET_ITEM_URL, json=valid)
        assert resp.status_code == 204
        
        # remove field for 400
        valid.pop("budget_amount")
        resp = client.put(BUDGET_ITEM_URL, json=valid)
        assert resp.status_code == 400
        
def test_BudgetItem_delete(client):
        resp = client.delete(BUDGET_ITEM_URL)
        assert resp.status_code == 204
        resp = client.delete(BUDGET_ITEM_URL)
        assert resp.status_code == 404
        resp = client.delete(INVALID_URL)
        assert resp.status_code == 404  
        
        
'''
TEST FOR EXPENSE ITEM RESOURCE
'''
EXPENSE_ITEM_URL = "/api/users/User-1/budgets/Oulu-11/Food-11"
EXPENSE_INVALID_URL = "/api/users/User-1/budgets/Oulu-11/Food-51"
    
def test_ExpensetItem_get(client):
        resp = client.get(EXPENSE_ITEM_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_get_method("profile", client, body)
        _check_control_put_method("edit", client, body, _get_expense_json(),"expense_name")
        _check_control_delete_method("budtrack:delete", client, body)
        resp = client.get(EXPENSE_INVALID_URL)
        assert resp.status_code == 404


def test_UserItem_put(client):
        valid = _get_expense_json()
        
        # test with wrong content type
        resp = client.put(EXPENSE_ITEM_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
        resp = client.put(EXPENSE_INVALID_URL, json=valid)
        assert resp.status_code == 404
        
        # test with another expense's name
        valid["expense_name"] = "Food-12"
        resp = client.put(EXPENSE_ITEM_URL, json=valid)
        assert resp.status_code == 409
        
        # test with valid (only change amount)
        valid["expense_name"] = "Food-11"
        valid["expense_amount"] = 77
        resp = client.put(EXPENSE_ITEM_URL, json=valid)
        assert resp.status_code == 204
        
        # remove field for 400
        valid.pop("expense_amount")
        resp = client.put(EXPENSE_ITEM_URL, json=valid)
        assert resp.status_code == 400
        
def test_BudgetItem_delete(client):
        resp = client.delete(EXPENSE_ITEM_URL)
        assert resp.status_code == 204
        resp = client.delete(EXPENSE_ITEM_URL)
        assert resp.status_code == 404
        resp = client.delete(EXPENSE_INVALID_URL)
        assert resp.status_code == 404  
    

    

        
            
    