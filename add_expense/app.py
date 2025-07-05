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
import requests

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

from flask_cors import cross_origin
from flask_cors import CORS



load_dotenv()




app = Flask(__name__)
CORS(app,supports_credentials=True)
app.secret_key = os.getenv('SECRET_KEY')
app.debug = False



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




@app.route('/edit_item', methods=['GET', 'POST'])
def edit_item():
    if 'user' not in session:
        
        print('You must be logged in to edit items.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'GET':
            
        item_id = request.args.get('id')
        #item = items_collection.find_one({'_id': ObjectId(item_id)}),
        url = 'http://database:5003/find_item_by_id'
        headers = {'Content-Type': 'application/json'}
        data_item = {'item_id': item_id}  # Assuming user_id is an ObjectId
        response = requests.post(url, json=data_item, headers=headers)
    
        item = response.json().get('item')

        if item:
            # create person list
            persons = []
            persons.append(get_user_name(item['uid']))
            # the length of the item attribute
            length = len(item)
            for i in range(length):
                person = item.get(f'person{i}', '')
                if person:
                    persons.append(person)
            # also add the owner of the item
            currency = item.get('home_currency', '')
          
            

            return render_template('add_expense.html', persons=persons,currency=currency, item_id=item_id)
        else:
            print('Item not found.', 'warning')
            return redirect(url_for('dashboard'))
    
    elif request.method == 'POST':
        form_type = request.form.get('form_type')
        egid = request.args.get('id')
        
        if form_type == 'expenses':
            # Extract expenses form data
            person = request.form.get('person-expenses')
            what_for = request.form.get('for-expenses')
            amount = request.form.get('amount-expenses')
            date = request.form.get('date-expenses')
            split_type = request.form.get('splitType')
            # now expense_collection.insert_one()

            url = 'http://database:5003/insert_item'
            item_data={
                'type': 'expenses',
                'egid': egid,
                'person_paid': person,
                'what_for': what_for,
                'amount': amount,
                'split_type': split_type,
                'date': date
            }
            response = requests.post(url, json=item_data)

          
        
        elif form_type == 'money_given':
            # Extract money given form data
            person = request.form.get('person-money-given')
            what_for = request.form.get('reason-money-given')
            amount = request.form.get('amount-money-given')
            to_whom = request.form.get('from-money-given')
            date = request.form.get('date-money-given')
            # Process the data here
            url = 'http://database:5003/insert_item'
            item_data={
                'type': 'money_given',
                'egid': egid,
                'person_gave': person,
                'what_for': what_for,
                'amount': amount,
                'to_whom': to_whom,
                'date': date
            }
            response = requests.post(url, json=item_data)
        
        elif form_type == 'income':
            # Extract income form data
            person = request.form.get('source-income')
            what_for = request.form.get('reason-income')
            amount = request.form.get('amount-income')
            date = request.form.get('date-income')
            split_type = request.form.get('splitType')
            # Process the data here
            url = 'http://database:5003/insert_item'
            item_data={
                'type': 'income',
                'egid': egid,
                'person': person,
                'what_for': what_for,
                'amount': amount,
                'split_type': split_type,
                'date': date
            }
            response = requests.post(url, json=item_data)
        
        # Redirect to item page
        response = jsonify({
            "message": "Expense added successfully",
            "redirect_url": "http://127.0.0.1:5001/item?id=" + str(egid)
        }), 200
        return response
    
    else:
        print('Invalid request method.', 'warning')
        response = jsonify({"error": "Invalid request method"}), 405
        return response
        

   
@app.route('/info')
def info():
    message = request.args.get('message')
    redirect_url = request.args.get('redirect_url')

    return render_template('info.html', message=message, redirect_url=redirect_url)

     


