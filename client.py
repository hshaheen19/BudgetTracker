import json
import requests
import sys

API_URL = "http://127.0.0.1:5000"

def prompt_client_options():
    print("--------------------------")
    print("1. Get All Users")
    print("2. Create a User")
    print("3. Edit User Information")
    print("4. Delete User")
    print("5. Get User Budgets")
    print("6. Create User Budget")
    print("--------------------------")
    choice = int(input("Choose functionality by typing a number: "))
    return choice


def get_users():
    with requests.Session() as s:
        s.headers.update({"Accept": "application/vnd.mason+json, */*"})
        resp = s.get(API_URL + "/api/users")
        if resp.status_code != 200:
            print("Unable to access API.")
        else:
            body = resp.json()
            if len(body["items"]) == 0:
                print("No user is present")
            else:
                for usr in body["items"]:
                    print ("Name: " + usr["user_name"])
                    print ("Email: " + usr["user_email"])
                    print("-----------")

def create_user():
    with requests.Session() as s:
        s.headers.update({"Accept": "application/vnd.mason+json, */*"})
        resp = s.get(API_URL + "/api/users")
        if resp.status_code != 200:
            print("Unable to access API.")
        else:
            body = resp.json()
            ctrl = body["@controls"]["budtrack:add-user"]
            schema = ctrl["schema"]
            data = {}
            for field in schema["required"]:
                data[field] = convert_value(input(schema["properties"][field]["description"]+": "),schema["properties"][field]["type"]) 
            
            submit_data(s,ctrl,data)
            

def edit_user_info():
    usr_nm= prompt_usersearch_option()
    with requests.Session() as s:
        s.headers.update({"Accept": "application/vnd.mason+json, */*"})
        resp = s.get(API_URL + "/api/users/" + usr_nm)
        if resp.status_code != 200:
            print("No user found!")
        else:
            body = resp.json()
            ctrl = body["@controls"]["edit"]
            schema = ctrl["schema"]
            data = {}
            for field in schema["required"]:
                data[field] = convert_value(input(schema["properties"][field]["description"]+": "),schema["properties"][field]["type"]) 
            
            submit_data(s,ctrl,data)

def delete_user():
    usr_nm= prompt_usersearch_option()
    with requests.Session() as s:
        s.headers.update({"Accept": "application/vnd.mason+json, */*"})
        resp = s.get(API_URL + "/api/users/" + usr_nm)
        if resp.status_code != 200:
            print("No user found!")
        else:
            body = resp.json()
            ctrl = body["@controls"]["budtrack:delete"]
            data = {}
            submit_data(s,ctrl,data)


def get_user_budgets():
    usr_nm= prompt_usersearch_option()
    with requests.Session() as s:
        s.headers.update({"Accept": "application/vnd.mason+json, */*"})
        resp = s.get(API_URL + "/api/users/" + usr_nm + "/budgets")
        if resp.status_code != 200:
            print("No user found!")
        else:
            body = resp.json()
            if len(body["items"]) == 0:
                print("No budget is present")
            else:
                for bud in body["items"]:
                    print ("Name: " + bud["budget_name"])
                    print ("Description: " + bud["budget_description"])
                    print ("Currency: " + bud["currency_type"])
                    print ("Amount: " + str(bud["budget_amount"]))
                    print ("Start date: " + bud["start_date"])
                    print ("End date: " + bud["end_date"])
                    print("-----------")

def create_user_budget():
    usr_nm= prompt_usersearch_option()
    with requests.Session() as s:
        s.headers.update({"Accept": "application/vnd.mason+json, */*"})
        resp = s.get(API_URL + "/api/users/" + usr_nm+ "/budgets")
        if resp.status_code != 200:
            print("No user found!")
        else:
            print("NOTE: Enter date in format yyyy-mm-dd")
            body = resp.json()
            ctrl = body["@controls"]["budtrack:add-budget"]
            schema = ctrl["schema"]
            data = {}
            for field in schema["required"]:
                data[field] = convert_value(input(schema["properties"][field]["description"]+": "),schema["properties"][field]["type"]) 
            
            submit_data(s,ctrl,data)

def prompt_usersearch_option():
    return input("Enter the user name: ")

def submit_data(s, ctrl, data):
    resp = s.request(
        ctrl["method"],
        API_URL + ctrl["href"],
        data=json.dumps(data),
        headers = {"Content-type": "application/json"}
    )
    return resp

def convert_value(value, ptype):
    if ptype == "integer":
        value = int(value)
    elif ptype == "number":
        value = float(value)
    return value

# map the inputs to the function blocks
options = {1 : get_users,
           2 : create_user,
           3 : edit_user_info,
           4 : delete_user,
           5 : get_user_budgets,
           6 : create_user_budget,
}


if __name__ == "__main__":
    try:
        root_path = sys.argv[1]
    except IndexError:
        root_path = "."

    #Step 1 prompt users with options
    opr = prompt_client_options()
    #Step 2 call the desired function
    options[opr]()