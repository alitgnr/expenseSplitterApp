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


# CONNECT TO ATLAS CLUSTER




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



@app.route('/add_expense_group', methods=['GET', 'POST'])
def add_expense_group():
    if not session.get('logged_in'):
        return redirect('/')

    if request.method == 'POST':
        try:
            item_type = request.form.get('item_type', '').lower()


            predefined_fields = get_fields_for_item_type_add(item_type)


            data = {field: request.form.get(field, '') for field in predefined_fields}
        
    


            custom_field_names = request.form.getlist('custom_field_name[]')
            custom_field_values = request.form.getlist('custom_field_value[]')
            counter = 3
            for name in custom_field_values:
                if name:
                    name = name.replace(' ', '_')
                    str_ = f"person{counter}"
                    data[str_] = name
                    counter += 1
                


            data['uid'] = session['user']['_id']


            sanitized_data = sanitize_input(data)
            
            current_datetime = datetime.now()
            
            formatted_datetime = current_datetime.strftime("%d %B %Y, %H:%M")
            
            sanitized_data['date'] = formatted_datetime
            
            sanitized_data['hide_item'] = False
    

            #items_collection.insert_one(sanitized_data)
            url = 'http://database:5003/insert_items_collection'
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=sanitized_data, headers=headers)

        except Exception as e:
            print(e)



        response = jsonify({
            "message": "Expense group added successfully",
            "redirect_url": "http://127.0.0.1:5001/"
        }), 200
        return response
    else:
        
        item_type = request.args.get('item', '')
        fields = get_fields_for_item_type_add(item_type)
        return render_template('add_expense_group.html', fields=fields, item_type=item_type, number=2)



@app.route('/info')
def info():
    message = request.args.get('message')
    redirect_url = request.args.get('redirect_url')

    return render_template('info.html', message=message, redirect_url=redirect_url)

     

@app.route('/health')
def health():
    return "HEALTHY", 200



