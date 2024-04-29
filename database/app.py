from flask import Flask, request, render_template, redirect, url_for,session,jsonify, flash, Response

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
from bson import ObjectId
import json


load_dotenv()

uri  = os.getenv("DBURI")

client = MongoClient(uri, server_api=ServerApi('1'))


try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

app = Flask(__name__)
CORS(app,supports_credentials=True)
app.secret_key = os.getenv('SECRET_KEY')
app.debug = False


sendgridAPI = os.getenv('SENDGRID_API_KEY')
serializer = URLSafeTimedSerializer(sendgridAPI)


db = client.get_database('expenseSplitterDB')  
items_collection = db.expense_groups
expense_collection = db.expenses
users_collection = db.users  # assuming there's a users collection


@app.route('/ping_db', methods=['GET'])
def ping_db():
    try:
        client.admin.command('ping')
        return "Pinged your deployment. Successfully connected to MongoDB!"
    except Exception as e:
        return str(e)




class JSONEncoder(json.JSONEncoder):
    """ Extend json-encoder class """
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)  # Convert ObjectId to string for JSON
        return json.JSONEncoder.default(self, obj)


@app.route('/find_user_by_id', methods=['POST'])
def find_user_by_id():
    data = request.json
    user_id = data.get('user_id')
    # return 200 if the user is found, 404 if not found
    # also return the user data if found
    user = users_collection.find_one({'_id': (user_id)})
    if user:
        return Response(JSONEncoder().encode({'user':user}), mimetype='application/json'), 200
    return False, 404


@app.route('/find_user_by_email', methods=['POST'])
def find_user_by_email():
    data = request.json
    email = data.get('email')
    # return 200 if the user is found, 404 if not found
    # also return the user data if found
    user = users_collection.find_one({'email': (email)})
    # mongo will return None if the user is not found
    if user is not None:
        return Response(JSONEncoder().encode({'user':user}), mimetype='application/json'), 200
    return Response(JSONEncoder().encode({'error': 'User not found'}), mimetype='application/json'), 404


@app.route('/find_item_by_id', methods=['POST'])
def find_item_by_id():
    data = request.json
    item_id = data.get('item_id')
    item = items_collection.find_one({'_id': ObjectId(item_id)})
    if item:
        return Response(JSONEncoder().encode({'item':item}), mimetype='application/json'), 200
    return False, 404


@app.route('/list_expenses', methods=['POST'])
def list_expenses():
    data = request.json
    item_id = data.get('item_id')  # Extracting user_id from JSON

    items_cursor = expense_collection.find({'egid': item_id}).sort('_id', -1)
    items_list = list(items_cursor)

    if items_list:
        # Use the custom encoder here
        return Response(JSONEncoder().encode({'items': items_list}), mimetype='application/json'), 200
    else:
        return jsonify({'error': 'No items found for this user'}), 404
    

@app.route('/list_items', methods=['POST'])
def list_items():
    data = request.json
    user_id = data.get('user_id')  # Extracting user_id from JSON

    items_cursor = items_collection.find({'uid': user_id}).sort('_id', -1)
    items_list = list(items_cursor)

    if items_list:
        # Use the custom encoder here
        return Response(JSONEncoder().encode({'items': items_list}), mimetype='application/json'), 200
    else:
        return jsonify({'error': 'No items found for this user'}), 404
    

@app.route('/delete_item', methods=['GET'])
def delete_item(item_id):
    # will return 200 if the item is deleted, 404 if the item is not found
    try:
        result = items_collection.delete_one({'_id': ObjectId(item_id)})
        if result.deleted_count > 0:
            return True, 200
        return False, 404
    except Exception as e:
        return False, 500





@app.route('/insert_item', methods=['POST', 'GET'])
def insert_item():
    item_data = request.json
    try:
        if (item_data['type'] == 'expenses'):
            expense_collection.insert_one(item_data)
        elif (item_data['type'] == 'money_given'):
            expense_collection.insert_one(item_data)
        elif (item_data['type'] == 'income'):
            expense_collection.insert_one(item_data)
        else:
            pass
            #items_collection.insert_one(item_data)
        return jsonify({"message": "Item inserted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 400
        
@app.route('/insert_user', methods=['POST'])
def insert_user():
    user = request.json
    try:
        users_collection.insert_one(user)
        return jsonify({"message": "User inserted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 400
    
    
@app.route('/insert_items_collection', methods=['POST', 'GET'])
def insert_items_collection():
    item_data = request.json
    try:
        items_collection.insert_one(item_data)
        return Response(JSONEncoder().encode({'message': 'Item inserted successfully','redirect_url': 'http://127.0.0.1:5001/'}), mimetype='application/json'), 200
    except Exception as e:
        return Response(JSONEncoder().encode({'error': f'An error occurred: {str(e)}'}), mimetype='application/json'), 400


@app.route('/update_item', methods=['POST'])
def update_item(item_id, update_data):
    item_id = request.json.get('item_id')
    update_data = request.json.get('update_data')
    try:
        result = items_collection.update_one({'_id': ObjectId(item_id)}, {'$set': update_data})
        if (result.modified_count > 0):
            return jsonify({"message": "User inserted successfully"}), 200
        else:
            return jsonify({"error": "No changes made or item not found."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 400
    


def find_user_by_email_normal(email):
    # return 200 if the user is found, 404 if not found
    # also return the user data if found
    user = users_collection.find_one({'email': (email)})
    if user: # return user id
        return user
    else:
        return False


@app.route('/update_user', methods=['POST']) 
def update_user():
    email = request.json.get('email')
    updated_data = request.json.get('updated_data')
    
    user_id = find_user_by_email_normal(email).get('_id')
    try:
        users_collection.update_one({'_id': (user_id)}, {'$set': updated_data})
        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 400





@app.route('/is_admin', methods=['POST'])
def is_admin():
    # fetch user_id from request
    item_data = request.json
    user_id = item_data.get('user_id')
    
    if not user_id:
        return "user_id is required", 400
    
    # Find the user in the database
    user = users_collection.find_one({'_id': user_id})
    
    if user:
        # Check if the user is marked as an admin in the database
        if user.get('is_admin', False):
            return "User is admin", 200
        else:
            return "User is not admin", 403
    else:
        return "User not found", 404


@app.route('/get_all_users', methods=['POST'])
def get_all_users(): # excluding passwords
    return list(users_collection.find({}, {"password": 0}))




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)
