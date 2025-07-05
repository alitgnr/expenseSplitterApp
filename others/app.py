from flask import Flask, request, render_template, redirect, url_for,session,jsonify, flash

from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
import re
import os
from dotenv import load_dotenv
from datetime import datetime
import validators
from passlib.hash import pbkdf2_sha256
import uuid
import time
import json

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

from flask_cors import cross_origin
from flask_cors import CORS
from time import sleep
from pymongo.errors import ServerSelectionTimeoutError
import requests



load_dotenv()


app = Flask(__name__)

CORS(app,supports_credentials=True)
app.secret_key = os.getenv('SECRET_KEY')
app.debug = False

 

class ExpenseSplitter:
    def __init__(self):
        self.transactions = []
        self.balances = {}

    def add_transaction(self, transaction):
        self.transactions.append(transaction)
        self.process_transaction(transaction)

    def process_transaction(self, transaction):
        if transaction['type'] == 'expenses':
            self.process_expense(transaction)
        elif transaction['type'] == 'money_given':
            self.process_money_given(transaction)
        elif transaction['type'] == 'income':
            self.process_income(transaction)

    def process_expense(self, transaction):
        amount = transaction['amount']
        num_people = len(self.balances)
        split_amount = amount / num_people
        for person in self.balances:
            if person != transaction['person_paid']:
                self.balances[person] -= split_amount
                self.balances[transaction['person_paid']] += split_amount

    def process_money_given(self, transaction):
        self.balances[transaction['person_gave']] += transaction['amount']
        self.balances[transaction['to_whom']] -= transaction['amount']

    def process_income(self, transaction):
        amount = transaction['amount']
        num_people = len(self.balances)
        split_amount = amount / num_people
        for person in self.balances:
            if person != transaction['person']:
                self.balances[person] += split_amount
                self.balances[transaction['person']] -= split_amount

    def add_person(self, person):
        if person not in self.balances:
            self.balances[person] = 0.0

    def get_balances(self):
        return self.balances






@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']['_id']
    
    if request.method == 'POST':
        
        updated_data = {
            'username': request.form['username'],
            'phone': request.form['phone'],
            'public': request.form.get('public', False) == 'on'
        }


        try:

            #db.users.update_one({'_id': (user_id)}, {'$set': updated_data})
            # connect to port 5003 database
            # update the user data
            url = 'http://database:5003/update_user'
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json={'user_id': user_id, 'updated_data': updated_data}, headers=headers)
            if response.status_code == 200:
                session['user'].update(updated_data)
                return redirect(url_for('info', message="Your profile has been updated successfully. Please log in again...", redirect_url=url_for('signout')))

            


            
        except Exception as e:
            print(e)  # For debugging

        return redirect(url_for('dashboard'))

    else:
    # The URL to your service, assuming 'database' is the correct hostname
        url = 'http://database:5003/find_user_by_id'
        headers = {'Content-Type': 'application/json'}
        # Ensure the key here matches what the Flask app is expecting ('user_id')
        data_item = {'user_id': str(user_id)}  # Assuming user_id is an ObjectId

        # Using POST as the method now
        response = requests.post(url, json=data_item, headers=headers)

        # Implement handling the response
        
        user = response.json().get('user')  # Parse the user info from the response


        url = 'http://database:5003/list_items'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=data_item, headers=headers)
        items = response.json().get('items')

        if items:
            for item in items:
                item["_id"] = str(item["_id"])
        else:
            items = []
    
        return render_template('dashboard.html', user=user, items=items, viewer_id=user_id)
 
            
           # return redirect(url_for('login'))



@app.route('/auth')
def auth():
  return render_template('auth.html')


@app.route('/info')
def info():
    message = request.args.get('message')
    redirect_url = request.args.get('redirect_url')

    return render_template('info.html', message=message, redirect_url=redirect_url)


@app.route('/user')
def user_detail():
    
    user_id = request.args.get('uid', None)
    viewer_id = None
    if (session.get('logged_in') == True):
        viewer_id = session['user']['_id']
        if (session['user']['_id'] == user_id):
            return redirect(url_for('dashboard'))
        
    
    if user_id:
        
            #user = db.users.find_one({'_id': (user_id)})
            url = 'http://database:5003/find_user_by_id'
            headers = {'Content-Type': 'application/json'}
            data_item = {'user_id': user_id}  # Assuming user_id is an ObjectId
            response = requests.post(url, json=data_item, headers=headers)
            user = response.json().get('user')

            if (user == None):
                return render_template('user.html', user=None,items=None, message="User not found")
            
            try:
                    if (session['user']['_id']):
                        if (user['_id'] == session['user']['_id']):
                            user_id = session['user']['_id']
                            
                            query_filter = {
                                'uid': user_id, 
                                'hide_item': {'$ne': True}  
                            }


                            #items = list(items_collection.find(query_filter).sort('_id', -1))
                            url = 'http://database:5003/list_items'
                            headers = {'Content-Type': 'application/json'}
                            response = requests.post(url, json={'user_id': user_id}, headers=headers)
                            items = response.json().get('items')


                         
                            if items:
                                for item in items:
                                    item["_id"] = str(item["_id"])
                            else:
                                items = []

                            return render_template('user.html', user=user, items=items, viewer_id=viewer_id)
            except:
                pass
        
            if (user['public'] or (( ( user['public'] == False) and (session.get('logged_in')) ))):
            
                user.pop('password', None)
                
                user['_id'] = str(user['_id'])
                
                user_id = user['_id']
                query_filter = {
                                'uid': user_id,  
                                'hide_item': {'$ne': True} 
                            }

                #items = list(items_collection.find(query_filter).sort('_id', -1))
                url = 'http://database:5003/list_items'
                headers = {'Content-Type': 'application/json'}
                response = requests.post(url, json={'user_id': user_id}, headers=headers)
                items = response.json().get('items')

                if  (session.get('logged_in')):
                    if items:
                        for item in items:
                            item["_id"] = str(item["_id"])
                    else:
                        items = []
                    
                else:
                    if items:
                        for item in items:
                            item["_id"] = str(item["_id"])

                    else:
                        items = []
                    
                
                return render_template('user.html', user=user,items=items, viewer_id=viewer_id)
            elif ( ( user['public'] == False) and (not session.get('logged_in')) ):
               
                return render_template('user.html', user=None,items=None, message="User is private")
            
                  
            else:
                
                return render_template('user.html', user=None,items=None, message="User not found")

    else:
        
        return render_template('user.html', user=None,items=None, message="User ID not provided")





@app.route('/')
def home():

    if 'user' not in session:
        return render_template('auth.html')
    else:
        return redirect(url_for('dashboard'))




def sanitize_input(data):


    sanitized_data = {}
    for field, value in data.items():
        if (field == 'image'):
                
            if not validators.url(value):
                value = 'https://www.svgrepo.com/show/508699/landscape-placeholder.svg'
            elif not value.startswith('https'):
                value = 'https://www.svgrepo.com/show/508699/landscape-placeholder.svg'
            else:
                pass
            sanitized_data[field] = value
            continue
        elif (field == 'storage_specifications' ):
            for storage in value:
               
                sanitized_1 = re.sub(r'[^a-zA-Z0-9 _.(),-/]', '', storage[0])
                sanitized_1 = sanitized_1.replace(' ', '_')
                sanitized_2 = re.sub(r'[^a-zA-Z0-9 _.(),-/]', '',storage[1])
                str_ = f"storage_({sanitized_1})"
                sanitized_data[str_] = sanitized_2
            continue
        elif (field == 'camera_specifications' ):
            for camera in value:
                sanitized_1 = re.sub(r'[^a-zA-Z0-9 _.(),-/]', '', camera[0])
                sanitized_1 = sanitized_1.replace(' ', '_')
                sanitized_2 = re.sub(r'[^a-zA-Z0-9 _.(),-/]', '', camera[1])
                str_ = f"camera_specification_({sanitized_1})"
                sanitized_data[str_] = sanitized_2
            continue
        elif (field == 'lessons'):
            sanitized_list = ""
            value = value.split()
            for lesson in value:
                
                lesson = re.sub(r'[^a-zA-Z0-9 _.(),-/]', '', lesson)
                
                sanitized_list += lesson + ' '
            sanitized_data['Lessons'] = sanitized_list
            continue

            


        else:   
            sanitized_value = re.sub(r'[^a-zA-Z0-9 _.,/]', '', value)
            field = field.replace(' ', '_').lower()
            sanitized_data[field] = sanitized_value
                

    return sanitized_data




def get_fields_for_item_type_add(item_type):
    return [ 'event_name','home_currency', 'person2' ]


@app.route('/admin')
def admin():
    url = 'http://database:5003/is_admin'
    headers = {'Content-Type': 'application/json'}
    user_id = session['user']['_id']
    item_data = {'user_id': user_id}
    response = requests.post(url, json=item_data, headers=headers)

    if response.status_code != 200:
        return redirect(url_for('login'))
    
    user_is_admin = True

    if not session.get('logged_in') or not user_is_admin:
        flash('You must be an admin to access this page.', 'danger')
        return redirect(url_for('login'))
    
    url = 'http://database:5003/get_all_users'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers)
    users = response.json()
    return render_template('admin.html', users=users)





def get_user_name(user_id):
    #user = db.users.find_one({'_id': user_id})
    url = 'http://database:5003/find_user_by_id'
    headers = {'Content-Type': 'application/json'}
    data_item = {'user_id': user_id}  # Assuming user_id is an ObjectId
    response = requests.post(url, json=data_item, headers=headers)
    user = response.json().get('user')
   
    if user:
        return user['username']
    return "Unknown User"




@app.route('/health')
def health():
    return "HEALTHY", 200



@app.route('/item')
def item_detail():
    
    item_id = request.args.get('id', None)
  

    
    
    if item_id:
        try:
            
            object_id = ObjectId(item_id)
        except:
            
            return "Invalid item ID format.", 400
        
        
        #item = items_collection.find_one({"_id": object_id})
        url = 'http://database:5003/find_item_by_id'
        headers = {'Content-Type': 'application/json'}
        data_item = {'item_id': item_id}  # Assuming user_id is an ObjectId
        response = requests.post(url, json=data_item, headers=headers)
        item = response.json().get('item')
        currency = item.get('home_currency', '')
        persons = []
        persons.append(get_user_name(item['uid']))
            # the length of the item attribute
        length = len(item)
        splitter = ExpenseSplitter()
        splitter.add_person(persons[0])
        for i in range(length):
            person = item.get(f'person{i}', '')
            if person:
                persons.append(person)
                splitter.add_person(person)
        
       # expenses = list(expense_collection.find({'egid': item_id}))
        url = 'http://database:5003/list_expenses'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json={'item_id': item_id}, headers=headers)
        expenses = response.json().get('items')
        if not expenses:
            expenses = []
        for expense in expenses:
            expense['_id'] = str(expense['_id'])
            if expense['type'] == 'expenses':
                if (expense['amount'] == ""):
                    expense['amount'] = 0
                splitter.add_transaction({
                    'type': 'expenses',
                    'person_paid': expense['person_paid'],
                    'amount': float(expense['amount'])
                })
            elif expense['type'] == 'money_given':
                if (expense['amount'] == ""):
                    expense['amount'] = 0
                splitter.add_transaction({
                    'type': 'money_given',
                    'person_gave': expense['person_gave'],
                    'to_whom': expense['to_whom'],
                    'amount': float(expense['amount'])
                })
            elif expense['type'] == 'income':
                if (expense['amount'] == ""):
                    expense['amount'] = 0
                splitter.add_transaction({
                    'type': 'income',
                    'person': expense['person'],
                    'amount': float(expense['amount'])
                })
            else:
                pass
        balance = splitter.get_balances()
        balance_list = []
        for person, amount in balance.items():
            balance_list.append({'person': person, 'amount': int(amount), 'owe': amount < 0})
        if item:
            
            try:
                owner = get_user_name(item['uid'])
                owner_uid = item['uid']
            except:
                owner = "Unknown User"
                owner_uid = ""
            item['_id'] = str(item['_id'])
            viewer_id = session.get('user', {}).get('_id', None)
           
          
            view_dict = dict()
            
            for key in item:
                if (key == '_id'):
                    view_dict[key] = item[key]
                else:
                    view_dict[key.replace('_',' ')] = item[key]
            
            
  
               
            return render_template('item_detail.html', item=view_dict, owner=owner,owner_uid=owner_uid,
                                   viewer_id=viewer_id,  items=expenses, currency=currency, balances=balance_list, item_id=item_id)
        else:
          
            return "Item not found.", 404
    else:
       
        return "Item ID not provided.", 400


