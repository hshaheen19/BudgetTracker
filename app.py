import json
from flask_restful import Resource, Api
from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy import event
from jsonschema import validate, ValidationError
from datetime import datetime



app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tracker.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
api = Api(app)

MASON = "application/vnd.mason+json"
LINK_RELATIONS_URL = "/budtrack/link-relations/"
USER_PROFILE = "/profiles/user/"
BUDGET_PROFILE = "/profiles/budget/"
EXPENSE_PROFILE = "/profiles/expense/" 
ERROR_PROFILE = "/profiles/error/"

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


'''
MODELS
'''
#Creating Schema of tables

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20), nullable=False, unique=True)
    user_email = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(40), nullable=False)

    budgets = db.relationship("Budget", back_populates="user", passive_deletes=True)

    def __repr__(self):
        return "{} <{}>".format(self.user_name, self.id)

class Budget(db.Model):
    #Each user can have one budget with same name
    __table_args__ = (db.UniqueConstraint("budget_name", "user_id", name="_user_budget_uc"), )

    id = db.Column(db.Integer, primary_key=True)
    budget_name = db.Column(db.String(20), nullable=False)
    budget_description = db.Column(db.String(40), nullable=True)
    budget_amount = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    currency_type = db.Column(db.String(20), nullable=True)
    #Relationship with user table
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    user = db.relationship("User", back_populates="budgets")
    #Relationship with expense table
    expenses = db.relationship("Expense", back_populates="budget", passive_deletes=True)

    def __repr__(self):
        return "{} <{}> in {}".format(self.budget_name, self.id, self.user.user_name)


class Expense(db.Model):
     #Each budget can have one expense with same name
    __table_args__ = (db.UniqueConstraint("expense_name", "budget_id", name="_budget_expense_uc"), )

    id = db.Column(db.Integer, primary_key=True)
    expense_name = db.Column(db.String(20), nullable=False)
    expense_description = db.Column(db.String(40), nullable=True)
    expense_amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.DateTime, nullable=False)
    #Relationship with Budget table
    budget_id = db.Column(db.Integer, db.ForeignKey("budget.id", ondelete="CASCADE"))
    budget = db.relationship("Budget", back_populates="expenses")

    def __repr__(self):
        return "{} <{}> in {}".format(self.expense_name, self.id, self.budget.budget_name)


'''
RESOURCE IMPLEMENTATION
'''

'''
User collection 
It has two methods 
GET: Give us the list of all the users
POST: Allow us to add a new user to database
'''
class UserCollection(Resource):

    def get(self):
        #Get all the users and add them in items list
        #also add controls for every user
        body = UserBuilder(items=[])
        for user in User.query.all():
            item = UserBuilder(
                user_name=user.user_name,
                user_email=user.user_email,
                password=user.password
            )
            item.add_control("self", api.url_for(UserCollection)+user.user_name+'/')
            item.add_control("profile", USER_PROFILE)
            body["items"].append(item)
        
        body.add_namespace("budtrack", LINK_RELATIONS_URL)
        body.add_control("self", api.url_for(UserCollection))
        body.add_control_add_user()

        resp = Response(json.dumps(body), status=200, mimetype=MASON)
        resp.headers['Location'] = api.url_for(UserCollection)
        return resp

    def post(self):
        #Check valid json
        if not request.json:
            return create_error_response(415, "Unsupported media type",
                "Requests must be JSON"
                )
        #Validate againsta the schema
        try:
            validate(request.json, UserBuilder.user_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))
        
        #Make a new object and add it in Database
        #IF error generate error otherwise a success message
        user = User(
            user_name=request.json["user_name"],
            user_email=request.json["user_email"],
            password=request.json["password"]
        )

        try:
            db.session.add(user)
            db.session.commit() 
        except IntegrityError:
            return create_error_response(409, "Already exists", 
                "User with username '{}' already exists.".format(request.json["user_name"])
            )
        
        return Response(status=201, headers={
            "Location": api.url_for(UserCollection) + request.json["user_name"]+'/'})


'''
User item 
It has three methods 
GET: Give us the user with the user_name provided in arguments
PUT: Allow us to edit the user
DELETE: Allow us to delete the user
'''

class UserItem(Resource):
    
    def get(self, user):
        #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )
        
        body = UserBuilder(
            user_name=db_user.user_name,
            user_email=db_user.user_email,
            password=db_user.password
        )

        #Add the hyper media controls
        body.add_namespace("budtrack", LINK_RELATIONS_URL)
        body.add_control("self", api.url_for(UserItem, user=user))
        body.add_control("profile", USER_PROFILE)
        body.add_collection_all_users()
        body.add_control_edit_user(user)
        body.add_control_delete_user(user)
        body.add_control("budtrack:budget-by",
            api.url_for(BudgetCollection, user=user)
        )

        return Response(json.dumps(body), 200, mimetype=MASON)
    
    def put(self, user):
        #check if valid json
        if not request.json:
            return create_error_response(415, "Unsupported media type",
                "Requests must be JSON"
                )
        #get the user from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the user_name {}".format(user)
            )
        #validate schema from request body
        try:
            validate(request.json, UserBuilder.user_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))
        
        #change the db object and if no error commit other wise send an error
        db_user.user_name = request.json["user_name"]
        db_user.user_email = request.json["user_email"]
        db_user.password = request.json["password"]

        try:
            db.session.commit()
        except IntegrityError:
            return create_error_response(409, "Already exists", 
                "User with handle '{}' already exists.".format(request.json["user_name"])
            )

        return Response(status=204, mimetype=MASON)
    
    def delete(self, user):
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the user_name {}".format(user)
            )
        
        User.query.filter_by(user_name=user).delete()
        db.session.commit()

        return Response(status=204, mimetype=MASON)


'''
Budget collection 
It has two methods 
GET: Give us the list of all the user budgets
POST: Allow us to add a new budget to database
'''
class BudgetCollection(Resource):

    def get(self, user):
        #Get all the budgets for this user and add them in items list
        #also add controls for every budget

        #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )
        #Get user budgtes
        db_budgets = Budget.query.filter_by(user=db_user)
        body = BudgetBuilder(items=[])
        for budget in db_budgets:
            item = BudgetBuilder(
                budget_name=budget.budget_name,
                budget_amount=budget.budget_amount,
                budget_description =budget.budget_description,
                currency_type=budget.currency_type,
                start_date=str(budget.start_date),
                end_date=str(budget.end_date)
            )
            item.add_control("self", api.url_for(BudgetItem, user=user, budget=budget.budget_name))
            item.add_control("profile", BUDGET_PROFILE)
            body["items"].append(item)
        
        body.add_namespace("budtrack", LINK_RELATIONS_URL)
        body.add_control("self", api.url_for(BudgetCollection, user=user))
        body.add_control_add_budget(user)

        resp = Response(json.dumps(body), status=200, mimetype=MASON)
        resp.headers['Location'] = api.url_for(BudgetCollection, user=user)
        return resp

    def post(self, user):

        #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )

        #Check valid json
        if not request.json:
            return create_error_response(415, "Unsupported media type",
                "Requests must be JSON"
                )
        #Validate againsta the schema
        try:
            validate(request.json, BudgetBuilder.budget_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))
        
        #Make a new object and add it in Database
        #IF error generate error otherwise a success message
        budget = Budget(
            budget_name=request.json["budget_name"],
            budget_amount=request.json["budget_amount"],
            budget_description=request.json["budget_description"],
            currency_type=request.json["currency_type"],
            start_date=ConverToDatetime(request.json["start_date"]),
            end_date=ConverToDatetime(request.json["end_date"]),
            user=db_user
        )

        try:
            db.session.add(budget)
            db.session.commit() 
        except IntegrityError:
            return create_error_response(409, "Already exists", 
                "Budget with name '{}' already exists.".format(request.json["budget_name"])
            )

        return Response(status=201, headers={
            "Location": api.url_for(BudgetCollection, user=user) + request.json["budget_name"]+'/'})


'''
Budget item 
It has three methods 
GET: Give us the budget of the user with the budget_name provided in arguments
PUT: Allow us to edit the budget
DELETE: Allow us to delete the budget
POST: Allow us to add an expense to the budget
'''

class BudgetItem(Resource):
    
    def get(self, user, budget):
        #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )
        
        #Filter the budget with user and budget name
        db_budget = Budget.query.filter_by(user=db_user,budget_name=budget).first()
        if db_budget is None:
            return create_error_response(404, "Not found", 
                "No Budget was found with the name {}".format(budget)
            )
        
        body = BudgetBuilder(
                budget_name=db_budget.budget_name,
                budget_amount=db_budget.budget_amount,
                budget_description =db_budget.budget_description,
                currency_type=db_budget.currency_type,
                start_date=str(db_budget.start_date),
                end_date=str(db_budget.end_date),
                items=[]
        )

        #Get all the expenses assosiated with this budget
        db_expenses = Expense.query.filter_by(budget=db_budget).all()
        if db_expenses:
            for expense in db_expenses:
                item = ExpenseBuilder(
                    expense_name=expense.expense_name,
                    expense_description=expense.expense_description,
                    expense_amount=expense.expense_amount,
                    expense_date=str(expense.expense_date),
                )
                item.add_control("self", api.url_for(ExpenseItem, user=user, budget=budget, expense=expense.expense_name))
                item.add_control("profile", EXPENSE_PROFILE)
                body["items"].append(item)

        #Add the hyper media controls
        body.add_namespace("budtrack", LINK_RELATIONS_URL)
        body.add_control("self", api.url_for(BudgetItem, user=user, budget=budget))
        body.add_control("profile", BUDGET_PROFILE)
        body.add_control("author",api.url_for(UserItem, user=user))
        body.add_control("user-all",api.url_for(UserCollection))
        body.add_control_edit_budget(user,budget)
        body.add_control_delete_budget(user,budget)
        body.add_control("budtrack:budget-by",
            api.url_for(BudgetCollection, user=user)
        )
        body.add_control_add_budget_expense(user,budget)

        return Response(json.dumps(body), 200, mimetype=MASON)
    
    #This post method will add the expense in this budget
    def post(self, user, budget):
        #Check valid json
        if not request.json:
            return create_error_response(415, "Unsupported media type",
                "Requests must be JSON"
                )

        #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )
        
        #Filter the budget with user and budget name
        db_budget = Budget.query.filter_by(user=db_user, budget_name=budget).first()
        if db_budget is None:
            return create_error_response(404, "Not found", 
                "No Budget was found with the name {}".format(budget)
            )

        #Validate againsta the expense schema
        try:
            validate(request.json, ExpenseBuilder.expense_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))
        
        #Make a new object and add it in Database
        #IF error generate error otherwise a success message
        expense = Expense(
            expense_name=request.json["expense_name"],
            expense_description=request.json["expense_description"],
            expense_amount=request.json["expense_amount"],
            expense_date=ConverToDatetime(request.json["expense_date"]),
            budget=db_budget
        )

        try:
            db.session.add(expense)
            db.session.commit() 
        except IntegrityError:
            return create_error_response(409, "Already exists", 
                "Expense with name '{}' already exists.".format(request.json["expense_name"])
            )

        return Response(status=201, headers={
            "Location": api.url_for(BudgetItem, user=user, budget=budget) + request.json["expense_name"]+'/'})

    
    def put(self, user, budget):
        #check if valid json
        if not request.json:
            return create_error_response(415, "Unsupported media type",
                "Requests must be JSON"
                )
        
        #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )
        
        #Filter the budget with user and budget name
        db_budget = Budget.query.filter_by(user=db_user, budget_name=budget).first()
        if db_budget is None:
            return create_error_response(404, "Not found", 
                "No Budget was found with the name {}".format(budget)
            )

        #validate schema from request body
        try:
            validate(request.json, BudgetBuilder.budget_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))
        
        #change the db object and if no error commit other wise send an error

        db_budget.budget_name= request.json["budget_name"]
        db_budget.budget_amount= request.json["budget_amount"]
        db_budget.budget_description= request.json["budget_description"]
        db_budget.currency_type= request.json["currency_type"]
        db_budget.start_date= ConverToDatetime(request.json["start_date"])
        db_budget.end_date= ConverToDatetime(request.json["end_date"])

        try:
            db.session.commit()
        except IntegrityError:
            return create_error_response(409, "Already exists", 
                "Budget with name '{}' already exists.".format(request.json["budget_name"])
            )

        return Response(status=204, mimetype=MASON)
    
    def delete(self, user, budget):

         #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )
        
        #Filter the budget with user and budget name
        db_budget = Budget.query.filter_by(user=db_user, budget_name=budget).first()
        if db_budget is None:
            return create_error_response(404, "Not found", 
                "No Budget was found with the name {}".format(budget)
            )
        
        Budget.query.filter_by(user=db_user, budget_name=budget).delete()
        db.session.commit()

        return Response(status=204, mimetype=MASON)

'''
Expense item 
It has three methods 
GET: Give us the expense of budget with the expense_name provided in arguments
PUT: Allow us to edit the expense
DELETE: Allow us to delete the expense
'''

class ExpenseItem(Resource):
    
    def get(self, user, budget, expense):
        #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )
        
        #Filter the budget with user and budget name
        db_budget = Budget.query.filter_by(user=db_user, budget_name=budget).first()
        if db_budget is None:
            return create_error_response(404, "Not found", 
                "No Budget was found with the name {}".format(budget)
            )
        
        #Filter the expense budget and expense name
        db_expense = Expense.query.filter_by(budget=db_budget, expense_name=expense).first()
        if db_expense is None:
            return create_error_response(404, "Not found", 
                "No Expense was found with the name {}".format(expense)
            )
        
        body = ExpenseBuilder(
            expense_name=db_expense.expense_name,
            expense_description=db_expense.expense_description,
            expense_amount=db_expense.expense_amount,
            expense_date=str(db_expense.expense_date),
        )
        
        #Add the hyper media controls
        body.add_namespace("budtrack", LINK_RELATIONS_URL)
        body.add_control("self", api.url_for(ExpenseItem, user=user, budget=budget, expense=expense))
        body.add_control("profile", EXPENSE_PROFILE)
        body.add_control("author",api.url_for(UserItem, user=user))
        body.add_control("up",api.url_for(BudgetItem, user=user, budget=budget))
        body.add_control_edit_expense(user,budget,expense)
        body.add_control_delete_expense(user,budget,expense)
        body.add_control("budtrack:budget-by",
            api.url_for(BudgetCollection, user=user)
        )

        return Response(json.dumps(body), 200, mimetype=MASON)
    
    def put(self, user, budget, expense):
        #check if valid json
        if not request.json:
            return create_error_response(415, "Unsupported media type",
                "Requests must be JSON"
                )
        
        #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )
        
        #Filter the budget with user and budget name
        db_budget = Budget.query.filter_by(user=db_user, budget_name=budget).first()
        if db_budget is None:
            return create_error_response(404, "Not found", 
                "No Budget was found with the name {}".format(budget)
            )
        
        #Filter the expense budget and expense name
        db_expense = Expense.query.filter_by(budget=db_budget, expense_name=expense).first()
        if db_expense is None:
            return create_error_response(404, "Not found", 
                "No Expense was found with the name {}".format(expense)
            )

        #validate schema from request body
        try:
            validate(request.json, ExpenseBuilder.expense_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))
        
        #change the db object and if no error commit other wise send an error

        db_expense.expense_name=request.json["expense_name"]
        db_expense.expense_description=request.json["expense_description"]
        db_expense.expense_amount=request.json["expense_amount"]
        db_expense.expense_date=ConverToDatetime(request.json["expense_date"])

        try:
            db.session.commit()
        except IntegrityError:
            return create_error_response(409, "Already exists", 
                "Expense with name '{}' already exists.".format(request.json["expense_name"])
            )

        return Response(status=204, mimetype=MASON)
    
    def delete(self, user, budget, expense):

         #Filter the user with the user_name from database
        db_user = User.query.filter_by(user_name=user).first()
        if db_user is None:
            return create_error_response(404, "Not found", 
                "No user was found with the username {}".format(user)
            )
        
        #Filter the budget with user and budget name
        db_budget = Budget.query.filter_by(user=db_user, budget_name=budget).first()
        if db_budget is None:
            return create_error_response(404, "Not found", 
                "No Budget was found with the name {}".format(budget)
            )
        
        #Filter the expense budget and expense name
        db_expense = Expense.query.filter_by(budget=db_budget, expense_name=expense).first()
        if db_expense is None:
            return create_error_response(404, "Not found", 
                "No Expense was found with the name {}".format(expense)
            )
        
        Expense.query.filter_by(budget=db_budget, expense_name=expense).delete()
        db.session.commit()

        return Response(status=204, mimetype=MASON)



def create_error_response(status_code, title, message=None):
    resource_url = request.path
    body = MasonBuilder(resource_url=resource_url)
    body.add_error(title, message)
    body.add_control("profile", href=ERROR_PROFILE)
    return Response(json.dumps(body), status_code, mimetype=MASON)

@app.route("/api/", methods=["GET"])
def entry_point():
    body = UserBuilder()
    body.add_namespace("budtrack", LINK_RELATIONS_URL)
    body.add_control_all_users()
    return Response(json.dumps(body), 200, mimetype=MASON)

@app.route("/storage/link-relations/")
def redirect_to_apiary_link_rels():
    return "", 200

@app.route("/profiles/<resource>/")
def send_profile_html(resource):
    return "", 200

def ConverToDatetime(dateStr):
    return datetime.strptime(dateStr, '%Y-%m-%d')

class MasonBuilder(dict):
    """
    A convenience class for managing dictionaries that represent Mason
    objects. It provides nice shorthands for inserting some of the more
    elements into the object but mostly is just a parent for the much more
    useful subclass defined next. This class is generic in the sense that it
    does not contain any application specific implementation details.
    """

    def add_error(self, title, details):
        """
        Adds an error element to the object. Should only be used for the root
        object, and only in error scenarios.

        Note: Mason allows more than one string in the @messages property (it's
        in fact an array). However we are being lazy and supporting just one
        message.

        : param str title: Short title for the error
        : param str details: Longer human-readable description
        """

        self["@error"] = {
            "@message": title,
            "@messages": [details],
        }

    def add_namespace(self, ns, uri):
        """
        Adds a namespace element to the object. A namespace defines where our
        link relations are coming from. The URI can be an address where
        developers can find information about our link relations.

        : param str ns: the namespace prefix
        : param str uri: the identifier URI of the namespace
        """

        if "@namespaces" not in self:
            self["@namespaces"] = {}

        self["@namespaces"][ns] = {
            "name": uri
        }

    def add_control(self, ctrl_name, href, **kwargs):
        """
        Adds a control property to an object. Also adds the @controls property
        if it doesn't exist on the object yet. Technically only certain
        properties are allowed for kwargs but again we're being lazy and don't
        perform any checking.

        The allowed properties can be found from here
        https://github.com/JornWildt/Mason/blob/master/Documentation/Mason-draft-2.md

        : param str ctrl_name: name of the control (including namespace if any)
        : param str href: target URI for the control
        """

        if "@controls" not in self:
            self["@controls"] = {}

        self["@controls"][ctrl_name] = kwargs
        self["@controls"][ctrl_name]["href"] = href

class UserBuilder(MasonBuilder):
    
    @staticmethod
    def user_schema():
        schema = {
            "type": "object",
            "required": ["user_name", "user_email", "password"]
            }
        props = schema["properties"] = {}
        props["user_name"] = {
            "description": "User unique name",
            "type": "string"
        }
        props["user_email"] = {
            "description": "User email",
            "type": "string"
        }
        props["password"] = {
            "description": "User password",
            "type": "string"
        }
        return schema

    def add_control_all_users(self):
        self.add_control(
            "budtrack:users-all",
            href=api.url_for(UserCollection),
            method="GET",
            title="List of all users"
        )
    
    def add_collection_all_users(self):
        self.add_control(
            "collection",
            href=api.url_for(UserCollection),
            method="GET",
            title="List of all users"
        )

    def add_control_delete_user(self, user_name):
        self.add_control(
            "budtrack:delete",
            href=api.url_for(UserCollection) + user_name+'/',
            method="DELETE",
            title="Delete this User"
        )
    
    def add_control_add_user(self):
        self.add_control(
            "budtrack:add-user",
            href=api.url_for(UserCollection),
            method="POST",
            encoding="json",
            title="Add this user",
            schema=self.user_schema()
        )

    def add_control_edit_user(self, user_name):
        self.add_control(
            "edit",
            href=api.url_for(UserCollection)+ user_name+'/',
            method="PUT",
            encoding="json",
            title="Edit this user",
            schema=self.user_schema()
        )

class BudgetBuilder(MasonBuilder):
   
    @staticmethod
    def budget_schema():
        schema = {
            "type": "object",
            "required": ["budget_name", "budget_amount", "start_date", "end_date"]
            }
        props = schema["properties"] = {}
        props["budget_name"] = {
            "description": "Budget title",
            "type": "string"
        }
        props["budget_description"] = {
            "description": "Budget description",
            "type": "string"
        }
        props["currency_type"] = {
            "description": "Budget currency type",
            "type": "string"
        }
        props["budget_amount"] = {
            "description": "Budget amount",
            "type": "number"
        }
        props["start_date"] = {
            "description": "Budget start date",
            "type": "string",
            "pattern": "^[0-9]{4}-[01][0-9]-[0-3][0-9]$"
        }
        props["end_date"] = {
            "description": "Budget end date",
            "type": "string",
            "pattern": "^[0-9]{4}-[01][0-9]-[0-3][0-9]$"
        }
        return schema

    def add_control_user_budgets(self,user_name):
        self.add_control(
            "budtrack:budget-by",
            href=api.url_for(BudgetCollection, user=user_name),
            method="GET",
            title="List of all budgets of user"
        )
    
    def add_control_add_budget(self,user_name):
        self.add_control(
            "budtrack:add-budget",
            href=api.url_for(BudgetCollection, user=user_name),
            method="POST",
            encoding="json",
            title="Add this budget",
            schema=self.budget_schema()
        )
    

    def add_control_delete_budget(self, user_name, budget_name):
        self.add_control(
            "budtrack:delete",
            href=api.url_for(BudgetItem, user=user_name, budget=budget_name),
            method="DELETE",
            title="Delete this Budget"
        )
    

    def add_control_edit_budget(self, user_name, budget_name):
        self.add_control(
            "edit",
            href=api.url_for(BudgetItem, user=user_name, budget=budget_name),
            method="PUT",
            encoding="json",
            title="Edit this Budget",
            schema=self.budget_schema()
        )
    
    def add_control_add_budget_expense(self, user_name, budget_name):
        self.add_control(
            "budtrack:add-expense",
            href=api.url_for(BudgetItem, user=user_name, budget=budget_name),
            method="POST",
            encoding="json",
            title="Add this expense",
            schema=ExpenseBuilder.expense_schema()
        )

class ExpenseBuilder(MasonBuilder):
   
    @staticmethod
    def expense_schema():
        schema = {
            "type": "object",
            "required": ["expense_name","expense_description", "expense_amount", "expense_date"]
            }
        props = schema["properties"] = {}
        props["expense_name"] = {
            "description": "Expense title",
            "type": "string"
        }
        props["expense_description"] = {
            "description": "Expense description",
            "type": "string"
        }
        props["expense_amount"] = {
            "description": "Expense amount",
            "type": "number"
        }
        props["expense_date"] = {
            "description": "Expense date",
            "type": "string",
            "pattern": "^[0-9]{4}-[01][0-9]-[0-3][0-9]$"
        }

        return schema
    
    def add_control_delete_expense(self, user_name, budget_name, expense):
        self.add_control(
            "budtrack:delete",
            href=api.url_for(ExpenseItem, user=user_name, budget=budget_name, expense=expense),
            method="DELETE",
            title="Delete this expense"
        )
    

    def add_control_edit_expense(self, user_name, budget_name, expense):
        self.add_control(
            "edit",
            href=api.url_for(ExpenseItem, user=user_name, budget=budget_name, expense=expense),
            method="PUT",
            encoding="json",
            title="Edit this Budget",
            schema=self.expense_schema()
        )

api.add_resource(UserCollection, "/api/users/")
api.add_resource(UserItem, "/api/users/<user>/")
api.add_resource(BudgetCollection, "/api/users/<user>/budgets")
api.add_resource(BudgetItem, "/api/users/<user>/budgets/<budget>")
api.add_resource(ExpenseItem, "/api/users/<user>/budgets/<budget>/<expense>")