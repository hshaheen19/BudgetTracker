# PWP SPRING 2020
# Budget Tracker
# Group information
* Hassan Shaheen 2600602

__Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint and instructions on how to setup and run the client__

# Instructions

## Dependencies
To run this project you need to have following packages installed in your python virtual enviroment

* Flask <pre><code>pip install Flask</code></pre>
* Sqlite3 <pre><code>pip install pysqlite3</code></pre>
* SqlAlchemy <pre><code>pip install flask-sqlalchemy</code></pre>
* Pytest <pre><code>pip install pytest</code></pre>
* Pytest-cov <pre><code>pip install pytest-cov</code></pre>
* Flask-restful <pre><code>pip install flask-restful</code></pre>
* JsonSchema <pre><code>pip install jsonschema</code></pre>
* Requests <pre><code>pip install requests</code></pre>

## Resources and Models
The resouces and model details are mentioned in repositry wiki. The project structure is straight forward there is one file named **app.py** which contains all models and resources. Code is commedted so that reader can easily get an idea how things work.
To run everything first you need to install all the dependencies mentioned above after doing it, it's quite simple to run the project.
In the main folder of repo open a terminal and type
<pre><code>run flask</code></pre>
It will start a server that is running on **localhost:5000** , i have already provided a database file named **tracker.db** but if you want a clean start, you can delete the file and open the python terminal. Following commands will create a fresh database.
<pre><code>from app import db, User, Budget, Expense</code></pre>
<pre><code>db.create_all()</code></pre>
To Access the resources the entry point is **/api/** as i am using hypermedia it will give you link-relation that you can follow for other resoruces. All details are mentioned in wiki.

## Test Cases
There are total three files, All the test cases are described and commented for easier understanding
* test_db.py
* user_test.py
* budget_test.py

The first one contains test for the database models, other two deals with the resouces. To run the test cases you have different options 
<pre><code>pytest</code></pre>
Running above command in your repo directory will run all the test cases and will show if there is any errors
<pre><code>pip --verbose</code></pre>
This will show the names of all the passes test cases
<pre><code>pip --cov=./</code></pre>
Will generate a coverage report about test cases. Right now running this will generate **94%** coverage.



