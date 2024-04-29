
from flask import Flask,request, jsonify, session
from passlib.hash import pbkdf2_sha256
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask import redirect, url_for
import uuid
from flask import flash
from flask import render_template
from flask_cors import cross_origin
from flask_cors import CORS
import requests




app = Flask(__name__)
CORS(app,supports_credentials=True)
app.secret_key = os.getenv('SECRET_KEY')


sendgridAPI = os.getenv('SENDGRID_API_KEY')
serializer = URLSafeTimedSerializer(sendgridAPI)





def send_verification_email(email, token):
    
    verification_url = f'http://127.0.0.1:5000/verify_your_email?token={token}'
    html_content = f'<p>Please click the link to verify your email: <a href="{verification_url}">Verify Email</a></p>'
    message = Mail(
        from_email='testmetu850@gmail.com',
        to_emails=email,
        subject='Verify your email address',
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(sendgridAPI)
        sg.send(message)
    except Exception as e:
        print(e.message)




@app.route('/verify_your_email')
def verify_email():
    token = request.args.get('token')
    redirect_url="http://127.0.0.1:5001/auth"
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=360000)  
      
        url =  'http://database:5003/find_user_by_email'
        headers = {'Content-Type': 'application/json'}
        data_item = {"email": email}
        response = requests.post(url, json=data_item, headers=headers)
        # if the response is 200, then the email already exists
        already = response.status_code == 200
        if already:
            #db.users.update_one({"email": email}, {"$set": {"email_verified": True}})
            clean_updated_data = {"email_verified": True}
            url = 'http://database:5003/update_user'
            headers = {'Content-Type': 'application/json'}
            data_item = {"email": email, "updated_data": clean_updated_data}
            response = requests.post(url, json=data_item, headers=headers)
            message="Email verified successfully. Please log in..."
            redirect_url="http://127.0.0.1:5001/"


            return render_template('info.html', message=message, redirect_url=redirect_url)
        else:
            message = "Email not found. Please sign up..."
            return render_template('info.html', message=message, redirect_url=redirect_url)
    except SignatureExpired:
        message = "The token is expired. Please sign up..."
        return render_template('info.html', message=message, redirect_url=redirect_url)



class User:
    @staticmethod
    def is_admin(user_id):
        """Check if the user is an admin."""
        if not session.get('logged_in'):
            return False
        #user = db.users.find_one({"_id": user_id})
        url = 'http://127.0.0.1:5003/is_admin'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json={"user_id": user_id}, headers=headers)
        return response.json().get('is_admin', False)

    @staticmethod
    def get_all_users():
        url = 'http://127.0.0.1:5003/get_all_users'
        headers = {'Content-Type': 'application/json'}
        response = requests.get(url, headers=headers)
        return response.json()



    def start_session(self, user):
        del user['password']
        session['logged_in'] = True
        session['user'] = user
        return jsonify(user), 200

    def signup(self):
        
        user = {
            "_id": uuid.uuid4().hex,
            "username": request.form.get('username'),
            "email": request.form.get('email'),
            "password": request.form.get('password'),
            "phone": request.form.get('phone'),
            "public": False,
            "email_verified": False,
            "favorites": []
        }


        user['password'] = pbkdf2_sha256.hash(user['password'])
        
        url =  'http://database:5003/find_user_by_email'
        headers = {'Content-Type': 'application/json'}
        data_item = {"email": user['email']}
        response = requests.post(url, json=data_item, headers=headers)
        # if the response is 200, then the email already exists
        already = response.status_code == 200
        
        redirect_url="http://127.0.0.1:5001/auth"

        if already:
            
            message="Email address already exists. Please register with a different email address."
         
            return jsonify({"message": message, "redirect_url": redirect_url}), 200
        
        url = 'http://database:5003/insert_user'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=user, headers=headers)
        user_added = response.status_code == 200

        if user_added:
            
            token = serializer.dumps(user['email'], salt='email-confirm')


            send_verification_email(user['email'], token)
      
            message="Signup successful. Please verify your email address."

            return jsonify({"message": message, "redirect_url": redirect_url}), 200

        
        message="An error occurred. Please try again."
        return jsonify({"message": message, "redirect_url": redirect_url}), 200 

    def update(self):
        redirect_url="http://127.0.0.1:5001/auth"
        # Check if the user is logged in by verifying the session
        if 'logged_in' not in session or not session['logged_in']:
            
            return jsonify({"error": "Unauthorized. Please log in.", "redirect_url":  redirect_url}), 200

        # Retrieve the user's email from the session
        session_email = session.get('user', {}).get('email')
        if not session_email:
            return jsonify({"error": "Session error. Please log in again.", "redirect_url":  redirect_url}), 200



        # Collect data to update
        updated_data = {
            "username": request.form.get('username'),
            "phone": request.form.get('phone'),
            "public": request.form.get('public') == 'on'
        }

        # Filter out None values
        clean_updated_data = {k: v for k, v in updated_data.items() if v is not None}
        redirect_url = "http://127.0.0.1:5001/auth"

        # Update the database if there is any data provided
        if clean_updated_data:
            try:
                #result = db.users.update_one({"email": session_email}, {"$set": clean_updated_data}
                
                url = 'http://database:5003/update_user'
                headers = {'Content-Type': 'application/json'}
                data_item = {"email": session_email, "updated_data": clean_updated_data}
                response = requests.post(url, json=data_item, headers=headers)

                if response.status_code == 200:
                    return jsonify({"message": "Profile updated successfully. Please log in again.", "redirect_url": redirect_url}), 200
                else:
                    return jsonify({"error": "No changes made or user not found.", "redirect_url": redirect_url}), 400
            except Exception as e:
                return jsonify({"error": f"An error occurred: {str(e)}", "redirect_url": redirect_url}), 400
        else:
            return jsonify({"error": "No valid data provided for update.", "redirect_url": redirect_url}), 400


    def signout(self):
        print("signout")


        session.clear()
        response = jsonify({
            "message": "User signed out successfully",
            "redirect_url": "http://127.0.0.1:5001/"
        }), 200
        return response
  
    def login(self):

        #user = db.users.find_one({"email": request.form.get('email')})
        url =  'http://database:5003/find_user_by_email'
        headers = {'Content-Type': 'application/json'}
        data_item = {"email": request.form.get('email')}
        response = requests.post(url, json=data_item, headers=headers)
        

        # if response is 404, then the email does not exist
        if response.status_code == 404:
            response = jsonify({"message":"Invalid login credentials","redirect_url": "http://127.0.0.1:5001/"}), 200
            return response

        user = response.json().get('user', None)
        if user and pbkdf2_sha256.verify(request.form.get('password'), user['password']):
            if not user.get("email_verified", False):
                return jsonify({"message":"Email not verified","redirect_url": "http://127.0.0.1:5001/"}), 200
            self.start_session(user)
            # return 301 status code to redirect 0.0.0.0:5001 port
            # fetch the session from Set-cookie header

            response = jsonify({
            "message": "Login successful",
            "redirect_url": "http://127.0.0.1:5001/"
        }), 200

            return response
        

        response = jsonify({"message":"Invalid login credentials","redirect_url": "http://127.0.0.1:5001/"}), 200
        return response









@app.route('/user/signup', methods=['POST'])
def signup():
    return User().signup()


@app.route('/user/signout', methods=['POST'])
def signout():
    return User().signout()

@app.route('/user/login', methods=['POST'])
def login():
    return User().login()


@app.route('/user/update', methods=['POST'])
def update():
    return User().update()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

