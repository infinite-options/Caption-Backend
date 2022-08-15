# To run program:  python3 io_api.py

# README:  if conn error make sure password is set properly in RDS PASSWORD section

# README:  Debug Mode may need to be set to False when deploying live (although it seems to be working through Zappa)

# README:  if there are errors, make sure you have all requirements are loaded

import os
import uuid
import boto3
import json
import math

from datetime import time, date, datetime, timedelta
import calendar
import time
from pytz import timezone
import random
import string
import stripe

from flask import Flask, request, render_template
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_mail import Mail, Message

# used for serializer email and error handling
# from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
# from flask_cors import CORS

from werkzeug.exceptions import BadRequest, NotFound
from werkzeug.security import generate_password_hash, check_password_hash

#  NEED TO SOLVE THIS
# from NotificationHub import Notification
# from NotificationHub import NotificationHub

import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from twilio.rest import Client

from dateutil.relativedelta import *
from decimal import Decimal
from datetime import datetime, date, timedelta
from hashlib import sha512
from math import ceil
import string

# BING API KEY
# Import Bing API key into bing_api_key.py

#  NEED TO SOLVE THIS
# from env_keys import BING_API_KEY, RDS_PW

import decimal
import sys
import json
import pytz
import pymysql
import requests

from random import randint

RDS_HOST = "io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com"
RDS_PORT = 3306
RDS_USER = "admin"
RDS_DB = "captions"

# app = Flask(__name__)
app = Flask(__name__, template_folder="assets")

# --------------- Stripe Variables ------------------
# these key are using for testing. Customer should use their stripe account's keys instead
import stripe

# STRIPE AND PAYPAL KEYS
paypal_secret_test_key = os.environ.get('paypal_secret_key_test')
paypal_secret_live_key = os.environ.get('paypal_secret_key_live')

paypal_client_test_key = os.environ.get('paypal_client_test_key')
paypal_client_live_key = os.environ.get('paypal_client_live_key')

stripe_public_test_key = os.environ.get('stripe_public_test_key')
stripe_secret_test_key = os.environ.get('stripe_secret_test_key')

stripe_public_live_key = os.environ.get('stripe_public_live_key')
stripe_secret_live_key = os.environ.get('stripe_secret_live_key')

stripe.api_key = stripe_secret_test_key

# use below for local testing
# stripe.api_key = ""sk_test_51J0UzOLGBFAvIBPFAm7Y5XGQ5APR...WTenXV4Q9ANpztS7Y7ghtwb007quqRPZ3""


CORS(app)

# --------------- Mail Variables ------------------
#This should be on Github -- should work wth environmental variables
app.config["MAIL_USERNAME"] = os.environ.get("SUPPORT_EMAIL")
app.config["MAIL_PASSWORD"] = os.environ.get("SUPPORT_PASSWORD")

#This should not be on Github -- should work on localhost
# app.config['MAIL_USERNAME'] = "support@mealsfor..."
# app.config['MAIL_PASSWORD'] = "Support..."


# Setting for mydomain.com
app.config["MAIL_SERVER"] = "smtp.mydomain.com"
app.config["MAIL_PORT"] = 465

# Setting for gmail
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 465

app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True

# Set this to false when deploying to live application
# app.config['DEBUG'] = True
app.config["DEBUG"] = False

app.config["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY")

mail = Mail(app)

# API
api = Api(app)

# convert to UTC time zone when testing in local time zone
utc = pytz.utc


# # These statment return Day and Time in GMT
# def getToday(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d")
# def getNow(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d %H:%M:%S")

# # These statment return Day and Time in Local Time - Not sure about PST vs PDT
def getToday(): return datetime.strftime(datetime.now(), "%Y-%m-%d")


def getNow(): return datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")


# Not sure what these statments do
# getToday = lambda: datetime.strftime(date.today(), "%Y-%m-%d")
# print(getToday)
# getNow = lambda: datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
# print(getNow)


# Get RDS password from command line argument
def RdsPw():
    if len(sys.argv) == 2:
        return str(sys.argv[1])
    return ""


# RDS PASSWORD
# When deploying to Zappa, set RDS_PW equal to the password as a string
# When pushing to GitHub, set RDS_PW equal to RdsPw()
RDS_PW = "prashant"
# RDS_PW = RdsPw()


s3 = boto3.client('s3')
s3_res = boto3.resource('s3')
s3_cl = boto3.client('s3')

# aws s3 bucket where the image is stored
# BUCKET_NAME = os.environ.get('MEAL_IMAGES_BUCKET')
BUCKET_NAME = 'iocaptions'
# allowed extensions for uploading a profile photo file
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg"])

def allowed_file(filename):
    """Checks if the file is allowed to upload"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def helper_upload_user_img(file, key):
    print("uploading image to s3 bucket.")
    bucket = 'iocaptions'
    if file and allowed_file(file.filename):
        # filename = 'https://' + bucket+ '.s3.us-west-1.amazonaws.com/' \
        #            + str(bucket) + '/' + str(key)
        filename = 'https://' + bucket+ '.s3.us-west-1.amazonaws.com/' + str(key)

        upload_file = s3.put_object(
            Bucket=bucket,
            Body=file,
            Key=key,
            ACL='public-read',
            ContentType='image/jpeg'
        )
        return filename
    return None


# For Push notification
isDebug = False
NOTIFICATION_HUB_KEY = os.environ.get("NOTIFICATION_HUB_KEY")
NOTIFICATION_HUB_NAME = os.environ.get("NOTIFICATION_HUB_NAME")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")


# Connect to MySQL database (API v2)
def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS (API v2)...")
    try:
        conn = pymysql.connect(
            host=RDS_HOST,
            user=RDS_USER,
            port=RDS_PORT,
            passwd=RDS_PW,
            db=RDS_DB,
            cursorclass=pymysql.cursors.DictCursor,
        )
        print("Successfully connected to RDS. (API v2)")
        return conn
    except:
        print("Could not connect to RDS. (API v2)")
        raise Exception("RDS Connection failed. (API v2)")


# Disconnect from MySQL database (API v2)
def disconnect(conn):
    try:
        conn.close()
        print("Successfully disconnected from MySQL database. (API v2)")
    except:
        print("Could not properly disconnect from MySQL database. (API v2)")
        raise Exception("Failure disconnecting from MySQL database. (API v2)")


# Serialize JSON
def serializeResponse(response):
    try:
        # print("In Serialize JSON")
        for row in response:
            for key in row:
                if type(row[key]) is Decimal:
                    row[key] = float(row[key])
                elif type(row[key]) is date or type(row[key]) is datetime:
                    row[key] = row[key].strftime("%Y-%m-%d")
        # print("In Serialize JSON response", response)
        return response
    except:
        raise Exception("Bad query JSON")


# Execute an SQL command (API v2)
# Set cmd parameter to 'get' or 'post'
# Set conn parameter to connection object
# OPTIONAL: Set skipSerialization to True to skip default JSON response serialization
def execute(sql, cmd, conn, skipSerialization=False):
    response = {}
    print("in Execute")
    print(cmd)
    try:
        with conn.cursor() as cur:
            print("before query")
            cur.execute(sql)
            print("after query")
            if cmd == "get":
                result = cur.fetchall()
                response["message"] = "Successfully executed SQL query."
                # Return status code of 280 for successful GET request
                response["code"] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response["result"] = result
            elif cmd == "post":
                print("in POST")
                conn.commit()
                print("after commit")
                response["message"] = "Successfully committed SQL command."
                # Return status code of 281 for successful POST request
                response["code"] = 281
            else:
                response["message"] = "Request failed. Unknown or ambiguous instruction given for MySQL command."
                # Return status code of 480 for unknown HTTP method
                response["code"] = 480
    except:
        response["message"] = "Request failed, could not execute MySQL command."
        # Return status code of 490 for unsuccessful HTTP request
        response["code"] = 490
    finally:
        response["sql"] = sql
        return response


# Close RDS connection
def closeRdsConn(cur, conn):
    try:
        cur.close()
        conn.close()
        print("Successfully closed RDS connection.")
    except:
        print("Could not close RDS connection.")


# Runs a select query with the SQL query string and pymysql cursor as arguments
# Returns a list of Python tuples
def runSelectQuery(query, cur):
    try:
        cur.execute(query)
        queriedData = cur.fetchall()
        return queriedData
    except:
        raise Exception("Could not run select query and/or return data")


# -- Stored Procedures start here -------------------------------------------------------------------------------


# RUN STORED PROCEDURES

def get_new_gameUID(conn):
    newGameQuery = execute("CALL captions.new_game_uid()", 'get', conn)
    if newGameQuery['code'] == 280:
        return newGameQuery['result'][0]['new_id']
    return "Could not generate new game UID", 500


def get_new_roundUID(conn):
    newRoundQuery = execute("CALL captions.new_round_uid()", 'get', conn)
    if newRoundQuery['code'] == 280:
        return newRoundQuery['result'][0]['new_id']
    return "Could not generate new game UID", 500


def get_new_userUID(conn):
    newPurchaseQuery = execute("CALL captions.new_user_uid()", 'get', conn)
    if newPurchaseQuery['code'] == 280:
        return newPurchaseQuery['result'][0]['new_id']
    return "Could not generate new user UID", 500


def get_new_historyUID(conn):
    newHistoryQuery = execute("CALL captions.new_history_uid()", 'get', conn)
    if newHistoryQuery['code'] == 280:
        return newHistoryQuery['result'][0]['new_id']
    return "Could not generate new history UID", 500

def get_new_imageUID(conn):
    # print("getting new image")
    newImageQuery = execute("CALL captions.new_image_uid()", 'get', conn)
    # print(newImageQuery)
    if newImageQuery['code'] == 280:
        return newImageQuery['result'][0]['new_id']
    return "Could not generate new image UID", 500

def get_new_deckUID(conn):
    # print("getting new image")
    newImageQuery = execute("CALL captions.new_deck_uid()", 'get', conn)
    # print(newImageQuery)
    if newImageQuery['code'] == 280:
        return newImageQuery['result'][0]['new_id']
    return "Could not generate new deck UID", 500

# --Caption Queries start here -------------------------------------------------------------------------------


# CHECK IF USER EXISTS
def checkUser(self, user_name, user_alias, user_email, user_zip):
    print("In checkUser")
    response = {}
    try:
        conn = connect()
        # print Received data to Terminal
        print("In checkUser:", user_name, user_alias, user_email, user_zip)

       
        message = "Email Verification Code Sent"


        # CHECK IF EMAIL EXISTS IN DB
        check_email = '''
                SELECT * FROM captions.user
                WHERE user_email= \'''' + user_email + '''\'
                '''

        userinfo = execute(check_email, "get", conn)
        print(userinfo, type(userinfo))
        print("User Info returned: ", userinfo['result'])


        # CHECK IF USER EXISTS
        if userinfo['result'] != ():
        # if len(userinfo['result'][0]['user_uid']) > 0:
            response["user_uid"] = userinfo['result'][0]['user_uid']

            # CHECK IF VALIDATION CODE IS TRUE
            if userinfo['result'][0]["email_validated"] != "TRUE":
                print("Not Validated")
                response["user_status"] = "User NOT Validated"
                response["user_code"] = userinfo["result"][0]["email_validated"]
                SendEmail.get(self, user_name, user_email, userinfo["result"][0]["email_validated"], message)
                # return response

            # CHECK IF ZIP CODE IS IN LIST
            if user_zip not in userinfo['result'][0]['user_zip_code']:
                print("Zip code not in list")
                response["user_zip"] = "Zip code not in list"


                query = '''
                    UPDATE captions.user
                    SET user_zip_code = JSON_ARRAY_APPEND(user_zip_code, '$', \'''' + user_zip + '''\')
                    WHERE user_email = \'''' + user_email + '''\';
                    '''

                addzip = execute(query, "post", conn)
                print("items: ", addzip)
                if addzip["code"] == 281:
                    response["user_zip_added"] = "Zip code added"

            # CHECK IF ALIAS HAS CHANGED
            if user_alias != userinfo['result'][0]['user_alias']:
                print("Alias changed")
                response["user_alias"] = "Alias changed"

                query = '''
                    UPDATE captions.user
                    SET user_alias = \'''' + user_alias + '''\'
                    WHERE user_email = \'''' + user_email + '''\';
                    '''

                update_alias = execute(query, "post", conn)
                print("items: ", update_alias)
                if update_alias["code"] == 281:
                    response["user_alias_added"] = "Alias updated"

            # CHECK IF USER NAME HAS CHANGED
            if user_name != userinfo['result'][0]['user_name']:
                print("Name changed")
                response["user_name"] = "Name Changed"

                query = '''
                    UPDATE captions.user
                    SET user_name = \'''' + user_name + '''\'
                    WHERE user_email = \'''' + user_email + '''\';
                    '''

                update_name = execute(query, "post", conn)
                print("items: ", update_name)
                if update_name["code"] == 281:
                    response["user_name_updated"] = "Name updated"


        # USER DOES NOT EXIST
        else:
            # Create Validation Code FOR NEW USER
            code = str(randint(100,999))
            print("Email validation code will be set to: ", code)

            new_user_uid = get_new_userUID(conn)
            print(new_user_uid)
            print(getNow())

            query = '''
                INSERT INTO captions.user
                SET user_uid = \'''' + new_user_uid + '''\',
                    user_created_at = \'''' + getNow() + '''\',
                    user_name = \'''' + user_name + '''\', 
                    user_alias = \'''' + user_alias + '''\', 
                    user_email = \'''' + user_email + '''\', 
                    user_zip_code = \'''' + user_zip + '''\',
                    email_validated = \'''' + code + '''\',
                    user_purchases = NULL
                '''

            items = execute(query, "post", conn)
            print("items: ", items)
            if items["code"] == 281:
                response["message"] = "Create User successful"
                response["user_uid"] = new_user_uid
                response["email_validated"] = code

                # Send Code to User
                SendEmail.get(self, user_name, user_email, code, message)

            print(response)
            return response, 200



        print(response)
        return response, 200


    except:
        raise BadRequest("Create User Request failed")
    finally:
        disconnect(conn)


class createUser(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)


            user_name = data["user_name"]
            user_alias = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
            user_email = data["user_email"]
            user_zip = data["user_zip"]
            # print(user_zip)


            response = checkUser(self, user_name, user_alias, user_email, user_zip)
            # print("after CheckEmail call")

            return response, 200


        except:
            raise BadRequest("Create User Request failed")
        finally:
            disconnect(conn)

class addUser(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            user_name = data["user_name"]
            user_alias = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
            user_email = data["user_email"]
            user_zip = data["user_zip"]
            # print(data)
            message = "Email Verification Code Sent"

            # Use statements below if we want to use def
            # user = CheckEmail(user_email)
            # print("after CheckEmail call")

            # CHECK IF EMAIL EXISTS IN DB
            check_user = '''SELECT * FROM captions.user
                            WHERE user_email= \'''' + user_email + '''\'
                            '''

            user = execute(check_user, "get", conn)
            print(user)


            # CHECK IF USER EXISTS
            if user['result'] != ():
            # if len(user['result'][0]['user_uid']) > 0:
                response["user_uid"] = user['result'][0]['user_uid']
                response["user_code"] = user["result"][0]["email_validated"]

                # CHECK IF VALIDATION CODE IS TRUE
                if user['result'][0]["email_validated"] != "TRUE":
                    print("Not Validated")
                    response["user_status"] = "User NOT Validated"
                    SendEmail.get(self, user_name, user_email, user["result"][0]["email_validated"], message)
                    # return response
            

                # CHECK IF ZIP CODE IS IN LIST
                if user_zip not in user['result'][0]['user_zip_code']:
                    print("Zip code not in list")
                    response["user_zip"] = "Zip code not in list"


                    query = '''
                        UPDATE captions.user
                        SET user_zip_code = JSON_ARRAY_APPEND(user_zip_code, '$', \'''' + user_zip + '''\')
                        WHERE user_email = \'''' + user_email + '''\';
                        '''

                    addzip = execute(query, "post", conn)
                    print("items: ", addzip)
                    if addzip["code"] == 281:
                        response["user_zip"] = "Zip code added"

                # CHECK IF ALIAS HAS CHANGED
                if user_alias != user['result'][0]['user_alias']:
                    print("Alias changed")
                    response["user_alias"] = "Alias changed"

                    query = '''
                        UPDATE captions.user
                        SET user_alias = \'''' + user_alias + '''\'
                        WHERE user_email = \'''' + user_email + '''\';
                        '''

                    update_alias = execute(query, "post", conn)
                    print("items: ", update_alias)
                    if update_alias["code"] == 281:
                        response["user_alias"] = "Alias updated"

                # CHECK IF USER NAME HAS CHANGED
                if user_name != user['result'][0]['user_name']:
                    print("Name changed")
                    response["user_name"] = "Name Changed"

                    query = '''
                        UPDATE captions.user
                        SET user_name = \'''' + user_name + '''\'
                        WHERE user_email = \'''' + user_email + '''\';
                        '''

                    update_name = execute(query, "post", conn)
                    print("items: ", update_name)
                    if update_name["code"] == 281:
                        response["user_name"] = "Name updated"

            # USER DOES NOT EXIST
            else:
                # Create Validation Code FOR NEW USER
                code = str(randint(100,999))
                print("Email validation code will be set to: ", code)

                new_user_uid = get_new_userUID(conn)
                print(new_user_uid)
                print(getNow())

                query = '''
                    INSERT INTO captions.user
                    SET user_uid = \'''' + new_user_uid + '''\',
                        user_created_at = \'''' + getNow() + '''\',
                        user_name = \'''' + user_name + '''\', 
                        user_alias = \'''' + user_alias + '''\', 
                        user_email = \'''' + user_email + '''\', 
                        user_zip_code = json_array(\'''' + user_zip + '''\'),
                        email_validated = \'''' + code + '''\',
                        user_purchases = NULL
                    '''

                items = execute(query, "post", conn)
                print("items: ", items)
                if items["code"] == 281:
                    response["message"] = "Create User successful"
                    response["user_uid"] = new_user_uid
                    response["email_validated"] = code

                    # Send Code to User
                    SendEmail.get(self, user_name, user_email, code, message)

                return response, 200




            return response, 200


        except:
            raise BadRequest("Create User Request failed")
        finally:
            disconnect(conn)

# ORIGINAL createUser
# class createUser(Resource):
#     def post(self):
#         response = {}
#         items = {}
#         try:
#             conn = connect()
#             data = request.get_json(force=True)
#             # print to Received data to Terminal
#             print("Received:", data)

#             user_name = data["user_name"]
#             user_alias = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
#             user_email = data["user_email"]
#             user_zip = data["user_zip"]
#             # print(data)
#             message = "Email Verification Code Sent"

#             # Use statements below if we want to use def
#             # user = CheckEmail(user_email)
#             # print("after CheckEmail call")

#             # CHECK IF EMAIL EXISTS IN DB
#             check_user = '''SELECT * FROM captions.user
#                             WHERE user_email= \'''' + user_email + '''\'
#                             '''

#             user = execute(check_user, "get", conn)
#             print(user)
#             print(user['result'][0]['user_uid'])
#             print(user['result'][0]['user_zip_code'])


#             # CHECK IF USER EXISTS
#             if len(user['result'][0]['user_uid']) > 0:
#                 response["user_uid"] = user['result'][0]['user_uid']

#                 # CHECK IF VALIDATION CODE IS TRUE
#                 if user['result'][0]["email_validated"] != "TRUE":
#                     print("Not Validated")
#                     response["user_status"] = "User NOT Validated"
#                     response["user_code"] = user["result"][0]["email_validated"]
#                     SendEmail.get(self, user_name, user_email, user["result"][0]["email_validated"], message)
#                     # return response

#                 # CHECK IF ZIP CODE IS IN LIST
#                 if user_zip not in user['result'][0]['user_zip_code']:
#                     print("Zip code not in list")
#                     response["user_zip"] = "Zip code not in list"


#                     query = '''
#                         UPDATE captions.user
#                         SET user_zip_code = JSON_ARRAY_APPEND(user_zip_code, '$', \'''' + user_zip + '''\')
#                         WHERE user_email = \'''' + user_email + '''\';
#                         '''

#                     addzip = execute(query, "post", conn)
#                     print("items: ", addzip)
#                     if addzip["code"] == 281:
#                         response["user_zip"] = "Zip code added"

#                 # CHECK IF ALIAS HAS CHANGED
#                 if user_alias != user['result'][0]['user_alias']:
#                     print("Alias changed")
#                     response["user_alias"] = "Alias changed"

#                     query = '''
#                         UPDATE captions.user
#                         SET user_alias = \'''' + user_alias + '''\'
#                         WHERE user_email = \'''' + user_email + '''\';
#                         '''

#                     update_alias = execute(query, "post", conn)
#                     print("items: ", update_alias)
#                     if update_alias["code"] == 281:
#                         response["user_alias"] = "Alias updated"

#                 # CHECK IF USER NAME HAS CHANGED
#                 if user_name != user['result'][0]['user_name']:
#                     print("Name changed")
#                     response["user_name"] = "Name Changed"

#                     query = '''
#                         UPDATE captions.user
#                         SET user_name = \'''' + user_name + '''\'
#                         WHERE user_email = \'''' + user_email + '''\';
#                         '''

#                     update_name = execute(query, "post", conn)
#                     print("items: ", update_name)
#                     if update_name["code"] == 281:
#                         response["user_name"] = "Name updated"

#             # USER DOES NOT EXIST
#             else:
#                 # Create Validation Code FOR NEW USER
#                 code = str(randint(100,999))
#                 print("Email validation code will be set to: ", code)

#                 new_user_uid = get_new_userUID(conn)
#                 print(new_user_uid)
#                 print(getNow())

#                 query = '''
#                     INSERT INTO captions.user
#                     SET user_uid = \'''' + new_user_uid + '''\',
#                         user_created_at = \'''' + getNow() + '''\',
#                         user_name = \'''' + user_name + '''\', 
#                         user_alias = \'''' + user_alias + '''\', 
#                         user_email = \'''' + user_email + '''\', 
#                         user_zip_code = \'''' + user_zip + '''\',
#                         email_validated = \'''' + code + '''\',
#                         user_purchases = NULL
#                     '''

#                 items = execute(query, "post", conn)
#                 print("items: ", items)
#                 if items["code"] == 281:
#                     response["message"] = "Create User successful"
#                     response["user_uid"] = new_user_uid
#                     response["email_validated"] = code

#                     # Send Code to User
#                     SendEmail.get(self, user_name, user_email, code, message)

#                 return response, 200




#             return response, 200


#         except:
#             raise BadRequest("Create User Request failed")
#         finally:
#             disconnect(conn)



# class createUserOLD(Resource):
#     def post(self):
#         response = {}
#         items = {}
#         try:
#             conn = connect()
#             data = request.get_json(force=True)
#             # print to Received data to Terminal
#             print("Received:", data)

#             user_name = data["user_name"]
#             user_alias = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
#             user_email = data["user_email"]
#             user_zip = data["user_zip"]
#             # print(data)


#             # Create Validation Code 
#             message = "Email Verification Code Sent"
#             code = str(randint(100,999))
#             print("Email validation code will be set to: ", code)



#             # check if the user is already present
#             # check_query = '''SELECT user_uid FROM captions.user 
#             #                     WHERE user_email= \'''' + user_email + '''\' 
#             #                     AND user_zip_code =\'''' + user_zip + '''\'
#             #                     '''


#             # Check if user exists
#             check_query = '''SELECT user_uid, email_validated FROM captions.user 
#                                 WHERE user_email= \'''' + user_email + '''\' 
#                                 AND user_zip_code =\'''' + user_zip + '''\'
#                                 '''

#             user = execute(check_query, "get", conn)
#             print(user)
#             new_user_uid = ""


#             if len(user["result"]) > 0:
#                 # if user is already present
#                 new_user_uid = user["result"][0]["user_uid"]
#                 print("Found User ID")
#                 print(new_user_uid)

#                 # If user is NOT Validated then send code
#                 if user["result"][0]["email_validated"] == "FALSE":

#                     # Set Code In Database
#                     set_code_query = '''
#                                     UPDATE captions.user
#                                     SET email_validated = \'''' + code + '''\' 
#                                     WHERE user_uid =\'''' + new_user_uid + '''\'
#                                     '''
#                     #print("valid modified example query\n", set_code_query)
#                     updateQueryResult = execute(set_code_query, "post", conn)
#                     print("Result of update query: ", updateQueryResult["message"])


#                     # Send Code to User
#                     SendEmail.get(self, user_name, user_email, code, message)

#                 return user["result"][0], 200
            
#             else:
#                 # New user
#                 new_user_uid = get_new_userUID(conn)
#                 print(new_user_uid)
#                 print(getNow())

#                 query = '''
#                     INSERT INTO captions.user
#                     SET user_uid = \'''' + new_user_uid + '''\',
#                         user_created_at = \'''' + getNow() + '''\',
#                         user_name = \'''' + user_name + '''\', 
#                         user_alias = \'''' + user_alias + '''\', 
#                         user_email = \'''' + user_email + '''\', 
#                         user_zip_code = \'''' + user_zip + '''\',
#                         email_validated = \'''' + code + '''\',
#                         user_purchases = NULL
#                     '''

#                 items = execute(query, "post", conn)
#                 print("items: ", items)
#                 if items["code"] == 281:
#                     response["message"] = "Create User successful"
#                     response["user_uid"] = new_user_uid
#                     response["email_validated"] = code

#                     # Send Code to User
#                     SendEmail.get(self, user_name, user_email, code, message)

#                 return response, 200

#         except:
#             raise BadRequest("Create User Request failed")
#         finally:
#             disconnect(conn)




class createGame(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            user_uid = data["user_uid"]
            num_rounds = data["rounds"]
            time_limit = data["round_time"]
            scoring = data["scoring_scheme"]
            print(user_uid)

            new_game_uid = get_new_gameUID(conn)
            print(new_game_uid)
            print(getNow())

            game_code = random.randint(10000000, 99999999)
            print(game_code)

            query = '''
                INSERT INTO captions.game
                SET game_uid = \'''' + new_game_uid + '''\',
                    game_created_at = \'''' + getNow() + '''\',
                    game_code = \'''' + str(game_code) + '''\',
                    num_rounds = \'''' + num_rounds + '''\',
                    time_limit = \'''' + time_limit + '''\',
                    game_host_uid = \'''' + user_uid + '''\',
                    scoring_scheme = \'''' + scoring + '''\'
                '''

            items = execute(query, "post", conn)
            print("items: ", items)
            if items["code"] == 281:
                response["message"] = "Create Game successful"
                response["game_code"] = str(game_code)
                response["game_uid"] = str(new_game_uid)
                return response, 200
        except:
            raise BadRequest("Create Game Request failed")
        finally:
            disconnect(conn)









# class createNewGame(Resource):
#     def post(self):
#         response = {}
#         items = {}
#         try:
#             conn = connect()
#             data = request.get_json(force=True)
#             # print to Received data to Terminal
#             print("Received:", data)

#             # User/Host data
#             user_uid = data["user_uid"]
#             # user_alias = data["user_alias"]
#             # user_name = data["user_name"]
#             # user_alias = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
#             # user_email = data["user_email"]
#             # user_zip = data["user_zip"]
#             # print(data)

#             # Game data
#             new_game_uid = get_new_gameUID(conn)
#             # print(new_game_uid)
#             num_rounds = "5"  # Default number of rounds
#             time_limit = "00:00:30"  # Default time-limit
#             game_code = random.randint(10000000, 99999999)
#             scoring_scheme = "R"
#             print(game_code)


#             create_game_query = '''
#                 INSERT INTO captions.game
#                 SET game_uid = \'''' + new_game_uid + '''\',
#                     game_created_at = \'''' + getNow() + '''\',
#                     game_code = \'''' + str(game_code) + '''\',
#                     num_rounds = \'''' + num_rounds + '''\',
#                     time_limit = \'''' + time_limit + '''\',
#                     game_host_uid = \'''' + user_uid + '''\',
#                     scoring_scheme = \'''' + scoring_scheme + '''\'
#                     '''
#             game_items = execute(create_game_query, "post", conn)
#             print("game_items: ", game_items)
#             if game_items["code"] == 281:
#                 response["game_message"] = "Create New Game successful"
#                 new_round_uid = get_new_roundUID(conn)
#                 add_user_to_round_query = '''
#                                         INSERT INTO captions.round
#                                         SET round_uid = \'''' + new_round_uid + '''\',
#                                         round_game_uid = \'''' + new_game_uid + '''\',
#                                         round_user_uid = \'''' + user_uid + '''\',
#                                         round_number = 1,
#                                         round_deck_uid = NULL,
#                                         round_image_uid = NULL ,
#                                         caption = NULL,
#                                         votes = 0,
#                                         score = 0, 
#                                         round_started_at = NULL'''
#                 add_user = execute(add_user_to_round_query, "post", conn)
#                 print("add_user_response: ", add_user)
#                 if add_user["code"] == 281:
#                     response["round_message"] = "Host added to the game."
#                     response["game_code"] = str(game_code)
#                     response["host_id"] = user_uid
#                     response["host_alias"] = user_alias
#                     return response, 200

#         except:
#             raise BadRequest("Create New Game Request failed")
#         finally:
#             disconnect(conn)






# class createNewGame(Resource):
#     def post(self):
#         response = {}
#         items = {}
#         try:
#             conn = connect()
#             data = request.get_json(force=True)
#             # print to Received data to Terminal
#             print("Received:", data)

#             # User/Host data
#             user_name = data["user_name"]
#             user_alias = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
#             user_email = data["user_email"]
#             user_zip = data["user_zip"]
#             # print(data)

#             # Game data
#             new_game_uid = get_new_gameUID(conn)
#             # print(new_game_uid)
#             num_rounds = "6"  # Default number of rounds
#             time_limit = "00:00:30"  # Default time-limit
#             game_code = random.randint(10000000, 99999999)
#             scoring_scheme = "R"
#             print(game_code)

#             # check if the user is already present
#             check_query = '''SELECT user_uid FROM captions.user 
#                                 WHERE user_email= \'''' + user_email + '''\' 
#                                 AND user_zip_code =\'''' + user_zip + '''\'
#                                 '''
#             user = execute(check_query, "get", conn)
#             print(user)
#             new_user_uid = ""
#             if len(user["result"]) > 0:
#                 # if user is already present
#                 new_user_uid = user["result"][0]["user_uid"]
#                 print(new_user_uid)
#             else:
#                 new_user_uid = get_new_userUID(conn)
#                 # print(new_user_uid)
#                 # print(getNow())
#                 query = '''
#                     INSERT INTO captions.user
#                     SET user_uid = \'''' + new_user_uid + '''\',
#                         user_created_at = \'''' + getNow() + '''\',
#                         user_name = \'''' + user_name + '''\', 
#                         user_alias = \'''' + user_alias + '''\', 
#                         user_email = \'''' + user_email + '''\', 
#                         user_zip_code = \'''' + user_zip + '''\',
#                         user_purchases = NULL
#                     '''

#                 items = execute(query, "post", conn)
#                 print("items: ", items)

#             if user["code"] == 280 or items["code"] == 281:
#                 create_game_query = '''
#                 INSERT INTO captions.game
#                 SET game_uid = \'''' + new_game_uid + '''\',
#                     game_created_at = \'''' + getNow() + '''\',
#                     game_code = \'''' + str(game_code) + '''\',
#                     num_rounds = \'''' + num_rounds + '''\',
#                     time_limit = \'''' + time_limit + '''\',
#                     game_host_uid = \'''' + new_user_uid + '''\',
#                     scoring_scheme = \'''' + scoring_scheme + '''\'
#                     '''
#                 game_items = execute(create_game_query, "post", conn)
#                 print("game_items: ", game_items)
#                 if game_items["code"] == 281:
#                     response["game_message"] = "Create New Game successful"
#                     new_round_uid = get_new_roundUID(conn)
#                     add_user_to_round_query = '''
#                                             INSERT INTO captions.round
#                                             SET round_uid = \'''' + new_round_uid + '''\',
#                                             round_game_uid = \'''' + new_game_uid + '''\',
#                                             round_user_uid = \'''' + new_user_uid + '''\',
#                                             round_number = 1,
#                                             round_deck_uid = NULL,
#                                             round_image_uid = NULL ,
#                                             caption = NULL,
#                                             votes = 0,
#                                             score = 0, 
#                                             round_started_at = NULL'''
#                     add_user = execute(add_user_to_round_query, "post", conn)
#                     print("add_user_response: ", add_user)
#                     if add_user["code"] == 281:
#                         response["round_message"] = "Host added to the game."
#                         response["game_code"] = str(game_code)
#                         response["host_id"] = new_user_uid
#                         response["host_alias"] = user_alias
#                         return response, 200

#         except:
#             raise BadRequest("Create New Game Request failed")
#         finally:
#             disconnect(conn)


class selectDeck(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)
            deck_uid = data["deck_uid"]
            game_code = data["game_code"]

            select_deck_query = '''
                                UPDATE captions.game
                                SET game_deck = \'''' + deck_uid + '''\'
                                WHERE game_code = \'''' + game_code + '''\';
                                '''

            selected_deck = execute(select_deck_query, "post", conn)
            print("selected deck info: ", selected_deck)

            if selected_deck["code"] == 281:
                response["message"] = "281, Deck successfully submitted."
                return response, 200

        except:
            raise BadRequest("Select deck Request failed")
        finally:
            disconnect(conn)


class assignDeck(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)
            deck_uid = data["deck_uid"]
            game_code = data["game_code"]

            assign_deck_query = '''


                                UPDATE captions.round
                                SET round_deck_uid = \'''' + deck_uid + '''\'
                                WHERE round_game_uid = (
                                    SELECT game_uid
                                    FROM captions.game
                                    WHERE game_code = \'''' + game_code + '''\');
                                '''

            assign_deck = execute(assign_deck_query, "post", conn)
            print("selected deck info: ", assign_deck)

            if assign_deck["code"] == 281:
                response["message"] = "281, Deck assigned successfully."
                return response, 200

        except:
            raise BadRequest("Assign deck Request failed")
        finally:
            disconnect(conn)





class joinGame(Resource):
    print("In joinGame")
    def post(self):
        response = {}
        returning_user = {}
        new_user = {}
        game_info = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            # player data
            user_uid = data["user_uid"]
            game_code = data["game_code"]

            # Check if game code exists and get game_uid
            check_game_code_query = '''
                                    SELECT * FROM captions.game
                                    WHERE game_code=\'''' + game_code + '''\'
                                    '''
            game_info = execute(check_game_code_query, "get", conn)
            print(game_info)
            if game_info["code"] == 280 and len(game_info["result"]) == 1:
                game_uid = game_info["result"][0]["game_uid"]
                print(game_uid)


                # Check if user is already in the game
                check_user_in_game_query = '''
                                            SELECT round_user_uid FROM captions.round
                                            WHERE round_game_uid = \'''' + game_uid + '''\'
                                            AND round_user_uid = \'''' + user_uid + '''\';
                                            '''

                existing_player = execute(check_user_in_game_query, "get", conn)
                print("player_info: ", existing_player)
                
                if existing_player["code"] == 280 and existing_player["result"] != ():
                        response["message"] = "280, Player has already joined the game."
                        response["user_uid"] = user_uid
                        return response, 200

                else:
                    # User has entered and existing game code and is not in the game
                    print("in else clause")
                    new_round_uid = get_new_roundUID(conn)
                    add_user_to_round_query = '''
                                            INSERT INTO captions.round
                                            SET round_uid = \'''' + new_round_uid + '''\',
                                            round_game_uid = \'''' + game_uid + '''\',
                                            round_user_uid = \'''' + user_uid + '''\',
                                            round_number = 1,
                                            round_deck_uid = NULL,
                                            round_image_uid = NULL ,
                                            caption = NULL,
                                            votes = 0,
                                            score = 0,
                                            round_started_at = NULL'''

                    add_user = execute(add_user_to_round_query, "post", conn)
                    print("add_user_response: ", add_user)
                    if add_user["code"] == 281:
                        response["message"] = "Player added to the game."
                        response["game_uid"] = game_uid
                        response["user_uid"] = user_uid
                        return response, 200

            else:
                response["warning"] = "Invalid game code."
                return response


        except:
            raise BadRequest("Join Game Request failed")
        finally:
            disconnect(conn)


# class joinGame(Resource):
#     def post(self):
#         response = {}
#         returning_user = {}
#         new_user = {}
#         game_info = {}
#         try:
#             conn = connect()
#             data = request.get_json(force=True)
#             # print to Received data to Terminal
#             print("Received:", data)

#             # player data
#             user_name = data["user_name"]
#             user_alias = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
#             user_email = data["user_email"]
#             user_zip = data["user_zip"]
#             game_code = data["game_code"]

#             # get the game_uid from the game code
#             check_game_code_query = '''
#                                     SELECT * FROM captions.game
#                                     WHERE game_code=\'''' + game_code + '''\'
#                                     '''
#             game_info = execute(check_game_code_query, "get", conn)
#             print(game_info)
#             if game_info["code"] == 280 and len(game_info["result"]) == 1:
#                 #We need to check if we got anything back or not
#                 game_uid = game_info["result"][0]["game_uid"]
#                 # game_created_at = game_info["result"][0]["game_created_at"]
#                 # game_code = game_info["result"][0]["game_code"]
#                 # num_rounds = game_info["result"][0]["num_rounds"]
#                 # time_limit = game_info["result"][0]["time_limit"]
#                 # game_host_uid = game_info["result"][0]["game_host_uid"]

#                 # check if the user is returning or new
#                 check_user_query = '''SELECT user_uid FROM captions.user 
#                                 WHERE user_email= \'''' + user_email + '''\' 
#                                 AND user_zip_code =\'''' + user_zip + '''\'
#                                 '''
#                 returning_user = execute(check_user_query, "get", conn)
#                 print("returning user: ", returning_user)
#                 user_uid = ""
#                 if len(returning_user["result"]) > 0:
#                     # if user is already present
#                     user_uid = returning_user["result"][0]["user_uid"]
#                     print("returning user id:", user_uid)
#                 else:
#                     user_uid = get_new_userUID(conn)
#                     # print(new_user_uid)
#                     # print(getNow())
#                     add_new_user_query = '''
#                                             INSERT INTO captions.user
#                                             SET user_uid = \'''' + user_uid + '''\',
#                                             user_created_at = \'''' + getNow() + '''\',
#                                             user_name = \'''' + user_name + '''\', 
#                                             user_alias = \'''' + user_alias + '''\', 
#                                             user_email = \'''' + user_email + '''\', 
#                                             user_zip_code = \'''' + user_zip + '''\',
#                                             user_purchases = NULL
#                                         '''

#                     new_user = execute(add_new_user_query, "post", conn)
#                     print("new user info: ", new_user)
#                 if returning_user["code"] == 280 or new_user["code"] == 281:
#                     # add the user to round from the game id
#                     check_user_in_game_query = '''
#                                                 SELECT round_user_uid FROM captions.round
#                                                 WHERE round_game_uid = \'''' + game_uid + '''\'
#                                                 AND round_user_uid = \'''' + user_uid + '''\'
#                                                 '''
#                     existing_player = execute(check_user_in_game_query, "get", conn)
#                     print("player_info: ", existing_player)
                    
#                     if existing_player["code"] == 280:
#                         if len(existing_player["result"]) > 0:
#                             response["message"] = "280, Player has already joined the game."
#                             response["user_uid"] = user_uid
#                             return response, 200
#                         else:
#                             new_round_uid = get_new_roundUID(conn)
#                             add_user_to_round_query = '''
#                                                     INSERT INTO captions.round
#                                                     SET round_uid = \'''' + new_round_uid + '''\',
#                                                     round_game_uid = \'''' + game_uid + '''\',
#                                                     round_user_uid = \'''' + user_uid + '''\',
#                                                     round_number = 1,
#                                                     round_deck_uid = NULL,
#                                                     round_image_uid = NULL ,
#                                                     caption = NULL,
#                                                     votes = 0,
#                                                     score = 0,
#                                                     round_started_at = NULL'''
#                             add_user = execute(add_user_to_round_query, "post", conn)
#                             print("add_user_response: ", add_user)
#                             if add_user["code"] == 281:
#                                 response["message"] = "Player added to the game."
#                                 response["game_uid"] = game_uid
#                                 response["user_uid"] = user_uid
#                                 response["user_alias"] = user_alias
#                                 return response, 200
#             else:
#                 response["warning"] = "Invalid game code."
#                 return response


#         except:
#             raise BadRequest("Join Game Request failed")
#         finally:
#             disconnect(conn)







class createRound(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            game_uid = data["game_uid"]
            # user_uid = data["user_uid"]
            # num_rounds = data["rounds"]
            # time_limit = data["round_time"]
            # scoring = data["scoring_scheme"]
            print(game_uid)

            new_round_uid = get_new_roundUID(conn)
            add_user_to_round_query = '''
                                    INSERT INTO captions.round
                                    SET round_uid = \'''' + new_round_uid + '''\',
                                    round_game_uid = \'''' + new_game_uid + '''\',
                                    round_user_uid = \'''' + user_uid + '''\',
                                    round_number = 1,
                                    round_deck_uid = NULL,
                                    round_image_uid = NULL ,
                                    caption = NULL,
                                    votes = 0,
                                    score = 0, 
                                    round_started_at = NULL'''
            add_user = execute(add_user_to_round_query, "post", conn)
            print("add_user_response: ", add_user)
            if add_user["code"] == 281:
                response["round_message"] = "Host added to the game."
                response["game_code"] = str(game_code)
                response["host_id"] = user_uid
                response["host_alias"] = user_alias
                return response, 200
                
        except:
            raise BadRequest("Create Game Request failed")
        finally:
            disconnect(conn)


class checkGame(Resource):
    def get(self, game_code):
        print(game_code)
        response = {}
        items = {}
        try:
            conn = connect()

            query = '''
                SELECT game_uid FROM captions.game
                WHERE game_code = \'''' + game_code + '''\';
                '''
            items = execute(query, "get", conn)
            print("items: ", items)

            if items["code"] == 280:
                response["message"] = "280, Check Game successful"
                if len(items["result"]) > 0:
                    response["game_uid"] = items["result"][0]["game_uid"]
                else:
                    response["warning"] = "Invalid game code"
                return response, 200
        except:
            raise BadRequest("Create Game Request failed")
        finally:
            disconnect(conn)




class getPlayers(Resource):
    def get(self, game_code):
        print("requested game_uid: ", game_code)
        response = {}
        items = {}
        try:
            conn = connect()
            get_players_query = '''
                                SELECT DISTINCT user_uid, user_alias FROM captions.user 
                                INNER JOIN captions.round 
                                ON user.user_uid = round.round_user_uid
                                WHERE round_game_uid= (SELECT game_uid FROM captions.game
                                WHERE game_code=\'''' + game_code + '''\') AND user.email_validated = "TRUE"
                                '''
            players = execute(get_players_query, "get", conn)
            print("players info: ", players)
            if players["code"] == 280:
                response["message"] = "280, Get players request successful."
                response["players_list"] = players["result"]
                return response, 200
        except:
            raise BadRequest("Get players in the game request failed")
        finally:
            disconnect(conn)


class decks(Resource):
    def get(self, user_uid, public_decks):
        print(user_uid)
        print(public_decks)
        response = {}
        try:
            conn = connect()

            # data = request.get_json(force=True)
            # print("Received: ", data)
            #
            #user_uid = data["user_uid"] #public => "" or personal => "xxx-xxxxxx"

            #we need to know user_uid
                #if it matches or anything that is public (user_uid is provided, match it with that or


            get_all_decks_query = '''
                                SELECT deck_uid, deck_title, deck_thumbnail_url, deck_description FROM captions.deck
                                '''

            get_all_decks_query1 = '''
                                SELECT deck_uid, deck_title, deck_thumbnail_url, deck_description
                                FROM captions.deck
                                WHERE deck_user_uid =\'''' + user_uid + '''\'
                                '''

            get_all_decks_query2 = '''
                                SELECT deck_uid, deck_title, deck_thumbnail_url, deck_description
                                FROM captions.deck
                                WHERE
                                    deck_user_uid =\'''' + user_uid + '''\' OR
                                    deck_user_uid = \'''' + "PUBLIC" + '''\'
                                '''

            if(public_decks == "false"):
                decks = execute(get_all_decks_query1, "get", conn)
            else:
                decks = execute(get_all_decks_query2, "get", conn)
            #decks = execute(get_all_decks_query2, "get", conn)
            print("players info: ", decks)
            if decks["code"] == 280:
                response["message"] = "280, get available decks request successful."
                response["decks_info"] = decks["result"]

                return response, 200
        except:
            raise BadRequest("get available decks request failed")
        finally:
            disconnect(conn)


# class selectDeck(Resource):
#     def post(self):
#         response = {}
#         items = {}
#         try:
#             conn = connect()
#             data = request.get_json(force=True)
#             # print to Received data to Terminal
#             print("Received:", data)
#             deck_uid = data["deck_uid"]
#             game_code = data["game_code"]

#             select_deck_query = '''
#                                 UPDATE captions.game
#                                 SET game_deck = \'''' + deck_uid + '''\'
#                                 WHERE game_code = \'''' + game_code + '''\';
#                                 '''

#             selected_deck = execute(select_deck_query, "post", conn)
#             print("selected deck info: ", selected_deck)

#             if selected_deck["code"] == 281:
#                 response["message"] = "281, Deck successfully submitted."
#                 return response, 200

#         except:
#             raise BadRequest("Select deck Request failed")
#         finally:
#             disconnect(conn)


    # def post(self):
    #     response = {}
    #     items = {}
    #     try:
    #         conn = connect()
    #         data = request.get_json(force=True)
    #         # print to Received data to Terminal
    #         print("Received:", data)

    #         deck_uid = get_new_deckUID(conn)
    #         #deck_uid = execute(get_new_deckUID(), "get", conn)
    #         deck_title = data["deck_title"]
    #         deck_user_uid = data["user_uid"]

    #         insert_deck_query = '''
    #                             INSERT INTO captions.deck
    #                             SET 
    #                                 deck_uid = \'''' + deck_uid + '''\',
    #                                 deck_title = \'''' + deck_title + '''\',
    #                                 deck_user_uid = \'''' + deck_user_uid + '''\';
    #                             '''

    #         insertResponse = execute(insert_deck_query, "post", conn)
    #         print("insert response ", insertResponse)

    #         if insertResponse["code"] == 280:
    #             response["message"] = "280, User custom deck has been successfully uploaded"
    #             response["insert info"] = insertResponse["result"]
    #             return response, 200
    #     except:
    #         raise BadRequest("Create deck Request failed")
    #     finally:
    #         disconnect(conn)


# class selectDeck(Resource):
#     def post(self):
#         response = {}
#         items = {}
#         try:
#             conn = connect()
#             data = request.get_json(force=True)
#             # print to Received data to Terminal
#             print("Received:", data)
#             deck_uid = data["deck_uid"]
#             game_code = data["game_code"]
#             round_number = data["round_number"]

#             select_deck_query = '''
#                                 UPDATE captions.round 
#                                 SET round_deck_uid=\'''' + deck_uid + '''\'
#                                 WHERE round_game_uid=(SELECT game_uid FROM captions.game
#                                 WHERE game_code=\'''' + game_code + '''\') 
#                                 AND round_number=\'''' + round_number + '''\'
#                                 '''
#             selected_deck = execute(select_deck_query, "post", conn)
#             print("selected deck info: ", selected_deck)
#             if selected_deck["code"] == 281:
#                 response["message"] = "281, Deck successfully submitted."
#                 return response, 200
#         except:
#             raise BadRequest("Select deck Request failed")
#         finally:
#             disconnect(conn)


class gameTimer(Resource):
    def get(self, game_code, round_number):
        print("requested game_uid: ", game_code)
        response = {}
        items = {}
        try:
            conn = connect()
            # round_start_time = 0
            # round_duration = 0
            current_time = getNow()
            get_game_timer_info = '''
                                SELECT captions.round.round_started_at, captions.game.time_limit, captions.game.num_rounds
                                FROM captions.round
                                JOIN captions.game
                                ON captions.round.round_game_uid = captions.game.game_uid
                                WHERE captions.game.game_code = \'''' + game_code + '''\'
                                AND round_number=\'''' + round_number + '''\'
                                '''
            timer = execute(get_game_timer_info, "get", conn)

            print("timer info: ", timer)
            if timer["code"] == 280:
                response["message"] = "280, Timer information request successful."
                response["current_time"] = current_time
                round_start_time = timer["result"][0]["round_started_at"]
                round_duration = timer["result"][0]["time_limit"]
                response["round_started_at"] = round_start_time
                response["round_duration"] = round_duration
                response["total_number_of_rounds"] = timer["result"][0]["num_rounds"]
                return response, 200
        except:
            raise BadRequest("Get game timer request failed")
        finally:
            disconnect(conn)


class changeRoundsAndDuration(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)
            game_code = data["game_code"]
            num_rounds = data["number_of_rounds"]
            seconds = data["round_duration"]
            scoring_scheme = data["scoring_scheme"]
            round_duration = time.strftime('%H:%M:%S', time.gmtime(int(seconds)))

            change_rounds_and_duration_query = '''
                                UPDATE captions.game 
                                SET num_rounds=\'''' + num_rounds + '''\',
                                time_limit=\'''' + round_duration + '''\',
                                scoring_scheme = \'''' + scoring_scheme + '''\'
                                WHERE game_code=\'''' + game_code + '''\'
                                '''
            update_game_attr = execute(change_rounds_and_duration_query, "post", conn)
            print("game_attr_update info: ", update_game_attr)
            if update_game_attr["code"] == 281:
                response["message"] = "281, Rounds and duration successfully updated."
                return response, 200
        except:
            raise BadRequest("Update rounds and time Request failed")
        finally:
            disconnect(conn)


class startPlaying(Resource):
    def get(self, game_code, round_number):
        print("game_code: ", game_code)
        print("round_number: ", round_number)
        response = {}
        try:
            conn = connect()
            current_time = getNow()

            start_round_query = '''
                                UPDATE captions.round
                                SET round_started_at=\'''' + current_time + '''\'
                                WHERE round_game_uid = (SELECT game_uid FROM captions.game 
                                WHERE game_code=\'''' + game_code + '''\')
                                AND round_number=\'''' + round_number + '''\'
                                '''
            round_timestamp = execute(start_round_query, "post", conn)
            print("round_timestamp_result: ", round_timestamp)
            if round_timestamp["code"] == 281:
                response["message"] = "281, game started."
                response["round_start_time"] = current_time
                return response, 200
        except:
            raise BadRequest("Get image in round request failed")
        finally:
            disconnect(conn)


class getUniqueImageInRound(Resource):
    def get(self, game_code, round_number):
        print("requested game_code: ", game_code)
        print("requested round_number: ", round_number)
        response = {}
        items = {}
        try:
            conn = connect()

            # check_deck_harvard_query = '''
            #                     SELECT deck_title
            #                     FROM captions.deck
            #                     WHERE deck_uid = 
            #                         (SELECT DISTINCT round_deck_uid FROM captions.round WHERE round_game_uid = (
            #                             SELECT game_uid FROM captions.game WHERE game_code =\'''' + game_code + '''\'))'''

            print("Check if Harvard Deck")
            check_deck_harvard_query = '''
                                SELECT deck_title
                                FROM captions.deck
                                WHERE deck_uid = (
                                        SELECT game_deck 
                                        FROM captions.game 
                                        WHERE game_code = \'''' + game_code + '''\');'''

            deck_is_harvard = execute(check_deck_harvard_query, "get", conn)

            

            if(deck_is_harvard["result"][0]["deck_title"] == "Harvard Art Museum"):
                print("User selected Harvard Deck")
                get_images_query = '''
                                            SELECT distinct captions.round.round_image_uid
                                            FROM captions.round
                                            INNER Join captions.deck
                                            ON captions.round.round_deck_uid=captions.deck.deck_uid
                                            WHERE round_game_uid =  (SELECT game_uid FROM captions.game
                                            WHERE game_code=\'''' + game_code + '''\')
                                            '''
                image_info = execute(get_images_query, "get", conn)
                print("harvard image info: ", image_info)

                images_used = set()
                for result in image_info["result"]:
                    if result["round_image_uid"] not in images_used:
                        images_used.add(result["round_image_uid"])
                print(images_used, type(images_used))
                flag = True
                image_id = ""
                while flag:
                    image_uid = randint(1,376513)
                    page = image_uid // 10 + 1
                    index = image_uid % 10

                    harvardURL = "https://api.harvardartmuseums.org/image?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633&page=" + str(
                        page)
                    print(harvardURL)
                    r = requests.get(harvardURL)
                    print(index)
                    # print("before return for getUniqueImage ", r.json()["records"][index]["baseimageurl"])

                    # image_uid = index
                    image_uid = r.json()["records"][index]["imageid"]
                    image_id = str(image_uid)
                    print("curr index: ", image_uid)
                    if image_uid not in images_used:
                        flag = False

                print("next_image_id: ", image_id, type(image_id))

                write_to_round_query = '''
                                                        UPDATE captions.round
                                                        SET round_image_uid=\'''' + image_id + '''\'
                                                        WHERE round_game_uid=(SELECT game_uid FROM captions.game
                                                        WHERE game_code=\'''' + game_code + '''\')
                                                        AND round_number = \'''' + round_number + '''\'
                                                        '''
                updated_round = execute(write_to_round_query, "post", conn)
                print("game_attr_update info: ", updated_round)

                if updated_round["code"] == 281:
                    response["message"] = "281, image in the Round updated."
                    #print("Return url for getUniqueImageInRound ", r.json()["records"][index]["baseimageurl"])
                    response["image_url"] = r.json()["records"][index]["baseimageurl"]
                    response["image_uid"] = image_uid
                    return response, 200

               # return //the end


            #maintain a set of already used integers and choose integers as we need
            # if it is already

            #Below is the code for the non-harvard api decks(do not touch)  >:(
            ################################################################################
            print("User selected deck other than Harvard")

            # RETURN ALL IMAGES ASSOCIATED WITH A DATABASE DECK
            get_images_query = '''
                            SELECT distinct(captions.deck.deck_image_uids), captions.round.round_image_uid
                            FROM captions.round
                            INNER Join captions.deck
                            ON captions.round.round_deck_uid=captions.deck.deck_uid
                            WHERE round_game_uid =  (SELECT game_uid FROM captions.game 
                            WHERE game_code=\'''' + game_code + '''\')                                
                            '''
            image_info = execute(get_images_query, "get", conn)

            print("\nimage info: ", image_info)
            print("\nimage result: ", image_info["result"][0])
            print("\nround image: ", image_info["result"][0]["round_image_uid"])

            if image_info["code"] == 280:
                images_in_deck_str = image_info["result"][0]["deck_image_uids"][2:-2]#.split(', ')
                images_in_deck_str = images_in_deck_str.replace('"', " ")
                images_in_deck = images_in_deck_str.split(" ,  ")
                print("\nImages in deck: ", images_in_deck)

                images_used = set()
                for result in image_info["result"]:
                    if result["round_image_uid"] not in images_used:
                        images_used.add(result["round_image_uid"])
                print(images_in_deck, type(images_in_deck))
                print(images_used, type(images_used))
                flag = True
                image_uid = ""
                while flag:
                    index = random.randint(0, len(images_in_deck)-1)
                    print("curr index: ", index)
                    if images_in_deck[index] not in images_used:
                        image_uid = images_in_deck[index]
                        flag = False

                print("next_image_uid: ", image_uid, type(image_uid))

                response["message1"] = "280, get image request successful."
                get_image_url_query = '''
                                    SELECT image_url FROM captions.image
                                    WHERE image_uid=\'''' + image_uid + '''\'
                                    '''
                image_url = execute(get_image_url_query, "get", conn)
                print("image_url: ", image_url)
                if image_url["code"] == 280:
                    #update round image query
                    write_to_round_query = '''
                                        UPDATE captions.round
                                        SET round_image_uid=\'''' + image_uid + '''\'
                                        WHERE round_game_uid=(SELECT game_uid FROM captions.game
                                        WHERE game_code=\'''' + game_code + '''\')
                                        AND round_number = \'''' + round_number + '''\'
                                        '''
                    updated_round = execute(write_to_round_query, "post", conn)
                    print("game_attr_update info: ", updated_round)
                    if updated_round["code"] == 281:
                        response["message"] = "281, image in the Round updated."
                        response["image_url"] = image_url["result"][0]["image_url"]
                        return response, 200
        except:
            raise BadRequest("Get image in round request failed")
        finally:
            disconnect(conn)


# class getUniqueImageInRound(Resource):
#     def get(self, game_code, round_number):
#         print("requested game_code: ", game_code)
#         print("requested round_number: ", round_number)
#         response = {}
#         items = {}
#         try:
#             conn = connect()

#             # check_deck_harvard_query = '''
#             #                     SELECT deck_title
#             #                     FROM captions.deck
#             #                     WHERE deck_uid = 
#             #                         (SELECT DISTINCT round_deck_uid FROM captions.round WHERE round_game_uid = (
#             #                             SELECT game_uid FROM captions.game WHERE game_code =\'''' + game_code + '''\'))'''

#             check_deck_harvard_query = '''
#                                 SELECT deck_title
#                                 FROM captions.deck
#                                 WHERE deck_uid = (
#                                         SELECT game_deck 
#                                         FROM captions.game 
#                                         WHERE game_code = \'''' + game_code + '''\');'''

#             deck_is_harvard = execute(check_deck_harvard_query, "get", conn)

#             # #Version 2 --> post the baseimageurl into the database
#             # if (deck_is_harvard["result"][0]["deck_title"] == "Harvard Art Museum"):
#             #     get_images_query = '''
#             #                                             SELECT distinct captions.round.round_image_uid
#             #                                             FROM captions.round
#             #                                             INNER Join captions.deck
#             #                                             ON captions.round.round_deck_uid=captions.deck.deck_uid
#             #                                             WHERE round_game_uid =  (SELECT game_uid FROM captions.game
#             #                                             WHERE game_code=\'''' + game_code + '''\')
#             #                                             '''
#             #     image_info = execute(get_images_query, "get", conn)
#             #     print("harvard image info: ", image_info)
#             #
#             #     images_used = set()
#             #     for result in image_info["result"]:
#             #         if result["round_image_uid"] not in images_used:
#             #             images_used.add(result["round_image_uid"])
#             #     print(images_used, type(images_used))
#             #     flag = True
#             #     # image_uid = ""
#             #     while flag:
#             #         image_uid = randint(1, 376513)
#             #         page = image_uid // 10 + 1
#             #         index = image_uid % 10
#             #
#             #         harvardURL = "https://api.harvardartmuseums.org/image?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633&page=" + str(
#             #             page)
#             #         print(harvardURL, "(page,index) = (", page, ",", index,")")
#             #         r = requests.get(harvardURL)
#             #         image_url = r.json()["records"][index]["baseimageurl"]
#             #         print("curr index: ", image_uid)
#             #         if image_url not in images_used:
#             #             flag = False
#             #
#             #     print("next_image_index: ", image_uid, type(image_uid))
#             #     print("next_image_url: ", image_url, type(image_url))
#             #     # page = index/10 + 1
#             #     # index = index%10
#             #     # page = image_uid // 10 + 1
#             #     # index = image_uid % 10
#             #     #
#             #     # harvardURL = "https://api.harvardartmuseums.org/image?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633&page=" + str(
#             #     #     page)
#             #     # print(harvardURL)
#             #     # r = requests.get(harvardURL)
#             #     # print(index)
#             #     # print("before return for getUniqueImage ", r.json()["records"][index]["baseimageurl"])
#             #
#             #     # image_uid = index
#             #     image_uid = str(image_uid)
#             #     # write_to_round_query = '''
#             #     #                                         UPDATE captions.round
#             #     #                                         SET round_image_uid=\'''' + image_uid + '''\'
#             #     #                                         WHERE round_game_uid=(SELECT game_uid FROM captions.game
#             #     #                                         WHERE game_code=\'''' + game_code + '''\')
#             #     #                                         AND round_number = \'''' + round_number + '''\'
#             #     #                                         '''
#             #     write_to_round_query = '''
#             #                                                         UPDATE captions.round
#             #                                                         SET round_image_uid=\'''' + "("+ image_url +")"+ '''\'
#             #                                                         WHERE round_game_uid=(SELECT game_uid FROM captions.game
#             #                                                         WHERE game_code=\'''' + game_code + '''\')
#             #                                                         AND round_number = \'''' + round_number + '''\'
#             #                                                         '''
#             #     updated_round = execute(write_to_round_query, "post", conn)
#             #     print("game_attr_update info: ", updated_round)
#             #
#             #     if updated_round["code"] == 281:
#             #         response["message"] = "281, image in the Round updated."
#             #         #print("Return url for getUniqueImageInRound ", r.json()["records"][index]["baseimageurl"])
#             #         response["image_url"] = r.json()["records"][index]["baseimageurl"]
#             #         response["image_uid"] = image_uid
#             #         return response, 200

#             if(deck_is_harvard["result"][0]["deck_title"] == "Harvard Art Museum"):
#                 get_images_query = '''
#                                             SELECT distinct captions.round.round_image_uid
#                                             FROM captions.round
#                                             INNER Join captions.deck
#                                             ON captions.round.round_deck_uid=captions.deck.deck_uid
#                                             WHERE round_game_uid =  (SELECT game_uid FROM captions.game
#                                             WHERE game_code=\'''' + game_code + '''\')
#                                             '''
#                 image_info = execute(get_images_query, "get", conn)
#                 print("harvard image info: ", image_info)

#                 images_used = set()
#                 for result in image_info["result"]:
#                     if result["round_image_uid"] not in images_used:
#                         images_used.add(result["round_image_uid"])
#                 print(images_used, type(images_used))
#                 flag = True
#                 image_id = ""
#                 while flag:
#                     image_uid = randint(1,376513)
#                     page = image_uid // 10 + 1
#                     index = image_uid % 10

#                     harvardURL = "https://api.harvardartmuseums.org/image?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633&page=" + str(
#                         page)
#                     print(harvardURL)
#                     r = requests.get(harvardURL)
#                     print(index)
#                     # print("before return for getUniqueImage ", r.json()["records"][index]["baseimageurl"])

#                     # image_uid = index
#                     image_uid = r.json()["records"][index]["imageid"]
#                     image_id = str(image_uid)
#                     print("curr index: ", image_uid)
#                     if image_uid not in images_used:
#                         flag = False

#                 print("next_image_id: ", image_id, type(image_id))

#                 write_to_round_query = '''
#                                                         UPDATE captions.round
#                                                         SET round_image_uid=\'''' + image_id + '''\'
#                                                         WHERE round_game_uid=(SELECT game_uid FROM captions.game
#                                                         WHERE game_code=\'''' + game_code + '''\')
#                                                         AND round_number = \'''' + round_number + '''\'
#                                                         '''
#                 updated_round = execute(write_to_round_query, "post", conn)
#                 print("game_attr_update info: ", updated_round)

#                 if updated_round["code"] == 281:
#                     response["message"] = "281, image in the Round updated."
#                     #print("Return url for getUniqueImageInRound ", r.json()["records"][index]["baseimageurl"])
#                     response["image_url"] = r.json()["records"][index]["baseimageurl"]
#                     response["image_uid"] = image_uid
#                     return response, 200

#                # return //the end


#         #maintain a set of already used integers and choose integers as we need
#             # if it is already

#             #Below is the code for the non-harvard api decks(do not touch)  >:(
#             ################################################################################
#             get_images_query = '''
#                             SELECT distinct(captions.deck.deck_image_uids), captions.round.round_image_uid
#                             FROM captions.round
#                             INNER Join captions.deck
#                             ON captions.round.round_deck_uid=captions.deck.deck_uid
#                             WHERE round_game_uid =  (SELECT game_uid FROM captions.game 
#                             WHERE game_code=\'''' + game_code + '''\')                                
#                             '''
#             image_info = execute(get_images_query, "get", conn)

#             print("image info: ", image_info)
#             if image_info["code"] == 280:
#                 images_in_deck_str = image_info["result"][0]["deck_image_uids"][2:-2]#.split(', ')
#                 images_in_deck_str = images_in_deck_str.replace('"', " ")
#                 images_in_deck = images_in_deck_str.split(" ,  ")
#                 images_used = set()
#                 for result in image_info["result"]:
#                     if result["round_image_uid"] not in images_used:
#                         images_used.add(result["round_image_uid"])
#                 print(images_in_deck, type(images_in_deck))
#                 print(images_used, type(images_used))
#                 flag = True
#                 image_uid = ""
#                 while flag:
#                     index = random.randint(0, len(images_in_deck)-1)
#                     print("curr index: ", index)
#                     if images_in_deck[index] not in images_used:
#                         image_uid = images_in_deck[index]
#                         flag = False

#                 print("next_image_uid: ", image_uid, type(image_uid))

#                 response["message1"] = "280, get image request successful."
#                 get_image_url_query = '''
#                                     SELECT image_url FROM captions.image
#                                     WHERE image_uid=\'''' + image_uid + '''\'
#                                     '''
#                 image_url = execute(get_image_url_query, "get", conn)
#                 print("image_url: ", image_url)
#                 if image_url["code"] == 280:
#                     #update round image query
#                     write_to_round_query = '''
#                                         UPDATE captions.round
#                                         SET round_image_uid=\'''' + image_uid + '''\'
#                                         WHERE round_game_uid=(SELECT game_uid FROM captions.game
#                                         WHERE game_code=\'''' + game_code + '''\')
#                                         AND round_number = \'''' + round_number + '''\'
#                                         '''
#                     updated_round = execute(write_to_round_query, "post", conn)
#                     print("game_attr_update info: ", updated_round)
#                     if updated_round["code"] == 281:
#                         response["message"] = "281, image in the Round updated."
#                         response["image_url"] = image_url["result"][0]["image_url"]
#                         return response, 200
#         except:
#             raise BadRequest("Get image in round request failed")
#         finally:
#             disconnect(conn)


# THIS ENDPOINT RETURNS A IMAGE (NOT UNIQUE) FROM UPLOADED IMAGES (NOT FROM A SPECIFIC DECK)
class getImageInRound(Resource):
    def get(self, game_code, round_number):
        print("requested game_code: ", game_code)
        print("requested round_number: ", round_number)
        response = {}
        items = {}
        try:
            conn = connect()
            get_image_query = '''
                            SELECT image_uid, image_url FROM captions.image
                            ORDER BY RAND()
                            LIMIT 1                                  
                            '''
            image_info = execute(get_image_query, "get", conn)

            print("image info: ", image_info)
            if image_info["code"] == 280:
                response["message1"] = "280, get image request successful."
                response["image_url"] = image_info["result"][0]["image_url"]
                image_uid = image_info["result"][0]["image_uid"]
                #another update round_image query
                write_to_round_query = '''
                                    UPDATE captions.round
                                    SET round_image_uid=\'''' + image_uid + '''\'
                                    WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                    WHERE game_code=\'''' + game_code + '''\')
                                    AND round_number = \'''' + round_number + '''\'
                                    '''
                updated_round = execute(write_to_round_query, "post", conn)
                print("game_attr_update info: ", updated_round)
                if updated_round["code"] == 281:
                    response["message2"] = "281, Round updated."
                    return response, 200
        except:
            raise BadRequest("Get image in round request failed")
        finally:
            disconnect(conn)


class getImageForPlayers(Resource):
    def get(self, game_code, round_number):
        print("requested game_code: ", game_code)
        print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            conn = connect()

            #####  HARVARD ART MUSEUM IF CLAUSE #####
            check_deck_harvard_query = '''
                                SELECT deck_title
                                FROM captions.deck
                                WHERE deck_uid = 
                                    (SELECT DISTINCT round_deck_uid FROM captions.round WHERE round_game_uid = (
                                        SELECT game_uid FROM captions.game WHERE game_code =\'''' + game_code + '''\'))'''
            deck_is_harvard = execute(check_deck_harvard_query, "get", conn)

            # #Version 2 --> get the baseimageurl rom the database
            # if (deck_is_harvard["result"][0]["deck_title"] == "Harvard Art Museum"):
            #     # get_image_query = '''
            #     #                 SELECT DISTINCT captions.round.round_image_uid
            #     #                 FROM captions.image
            #     #                 INNER JOIN captions.round
            #     #                 ON captions.image.image_uid = captions.round.round_image_uid
            #     #                 WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code=\'''' + game_code + '''\')
            #     #                 AND round_number=(SELECT MAX(round_number)
            #     #                                 FROM captions.round
            #     #                                 WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code=\'''' + game_code + '''\'))
            #     #                 '''
            #     get_image_query = '''
            #                                    SELECT DISTINCT captions.round.round_image_uid
            #                                    FROM captions.round
            #                                    WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code =\'''' + game_code + '''\')
            #                                    AND round_number = (SELECT MAX(round_number)
            #                                                        FROM captions.round
            #                                                        WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code =\'''' + game_code + '''\'))
            #                                    '''
            #
            #     image_info = execute(get_image_query, "get", conn)
            #     # image_uid = int(image_info["result"][0]["round_image_uid"])
            #     # print(image_uid, type(image_uid))
            #     # page = image_uid // 10 + 1
            #     # index = image_uid % 10
            #     #
            #     # harvardURL = "https://api.harvardartmuseums.org/image?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633&page=" + str(
            #     #     page)
            #     # print(harvardURL)
            #     # print(index)
            #     # r = requests.get(harvardURL)
            #     # print("before return getImageForPlayers ", r.json()["records"][index]["baseimageurl"])
            #     #
            #     # print("image info: ", image_info)
            #     if image_info["code"] == 280:
            #         response["message"] = "280, get image for players other than host request successful."
            #         #response["image_uid="] = image_info["result"][0]["round_image_uid"]
            #         # response["image_url"] = image_info["result"][0]["image_url"]
            #         #print("Return url for getImageForPlayers ", r.json()["records"][index]["baseimageurl"])
            #         response["image_url"] = image_info["result"][0]["round_image_uid"]
            #         return response, 200

            if(deck_is_harvard["result"][0]["deck_title"] == "Harvard Art Museum"):
                # get_image_query = '''
                #                 SELECT DISTINCT captions.round.round_image_uid
                #                 FROM captions.image
                #                 INNER JOIN captions.round
                #                 ON captions.image.image_uid = captions.round.round_image_uid
                #                 WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code=\'''' + game_code + '''\')
                #                 AND round_number=(SELECT MAX(round_number)
                #                                 FROM captions.round
                #                                 WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code=\'''' + game_code + '''\'))
                #                 '''
                get_image_query = '''
                                    SELECT DISTINCT captions.round.round_image_uid
                                    FROM captions.round
                                    WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code =\'''' + game_code + '''\')
                                    AND round_number = (SELECT MAX(round_number)
                                                        FROM captions.round
                                                        WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code =\'''' + game_code + '''\'))
                                    '''

                image_info = execute(get_image_query, "get", conn)
                image_uid = image_info["result"][0]["round_image_uid"]
                print(image_uid, type(image_uid))
                # page = image_uid//10 + 1
                # index = image_uid%10

                harvardURL = "https://api.harvardartmuseums.org/image/"+ image_uid +"?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633"
                #harvardURL = "https://api.harvardartmuseums.org/image?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633&page="
                print(harvardURL)
                #print(index)
                r = requests.get(harvardURL)
                #print("before return getImageForPlayers ", r.json()["records"][index]["baseimageurl"])


                print("image info: ", image_info)
                if image_info["code"] == 280:
                    response["message"] = "280, get image for players other than host request successful."
                    response["image_id"] = image_uid
                    #response["image_uid"] = image_info["result"][0]["round_image_uid"]
                    #response["image_url"] = image_info["result"][0]["image_url"]
                    #print("Return url for getImageForPlayers ", r.json()["records"][index]["baseimageurl"])
                    #response["image_url"] = r.json()["records"][index]["baseimageurl"]
                    response["image_url"] = r.json()["baseimageurl"]
                    return response, 200

            ####  Non-HARVARD #####

            get_image_query = '''
                            SELECT DISTINCT captions.image.image_url, captions.round.round_image_uid
                            FROM captions.image
                            INNER JOIN captions.round
                            ON captions.image.image_uid = captions.round.round_image_uid
                            WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code=\'''' + game_code + '''\')
                            AND round_number=(SELECT MAX(round_number) 
                                            FROM captions.round 
                                            WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code=\'''' + game_code + '''\'))             
                            '''
            image_info = execute(get_image_query, "get", conn)

            print("image info: ", image_info)
            if image_info["code"] == 280:
                response["message"] = "280, get image for players other than host request successful."
                response["image_uid"] = image_info["result"][0]["round_image_uid"]
                response["image_url"] = image_info["result"][0]["image_url"]
                return response, 200
        except:
            raise BadRequest("Get image for players other than host request failed")
        finally:
            disconnect(conn)


class submitCaption(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)
            caption = data["caption"]
            caption = caption.replace("'", '"')
            round_number = data["round_number"]
            game_code = data["game_code"]
            user_uid = data["user_uid"]

            submit_caption_query = '''
                                UPDATE captions.round 
                                SET caption=\'''' + caption + '''\' 
                                WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                WHERE game_code=\'''' + game_code + '''\') 
                                AND round_number=\'''' + round_number + '''\'
                                AND round_user_uid=\'''' + user_uid + '''\' 
                                '''
            caption = execute(submit_caption_query, "post", conn)
            print("caption info: ", caption)
            if caption["code"] == 281:
                response["message"] = "281, Caption for the user updated."
                return response, 200
        except:
            raise BadRequest("submit caption Request failed")
        finally:
            disconnect(conn)


class getPlayersRemainingToSubmitCaption(Resource):
    def get(self, game_code, round_number):
        print("requested game_code: ", game_code)
        print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            conn = connect()
            get_players_query = '''
                            SELECT captions.round.round_user_uid, captions.user.user_alias
                            FROM captions.round
                            INNER JOIN captions.user 
                            ON captions.round.round_user_uid=captions.user.user_uid
                            WHERE round_game_uid = (SELECT game_uid FROM captions.game 
                            WHERE game_code=\'''' + game_code + '''\')
                            AND round_number=\'''' + round_number + '''\'
                            AND caption IS NULL                         
                            '''
            players_info = execute(get_players_query, "get", conn)

            print("players info: ", players_info)
            if players_info["code"] == 280:
                response["message1"] = "280, get players yet to submit captions request successful."
                response["players"] = players_info["result"]
                return response, 200
        except:
            raise BadRequest("Get players who haven't submitted captions request failed")
        finally:
            disconnect(conn)


class getAllSubmittedCaptions(Resource):
    def get(self, game_code, round_number):
        print("requested game_code: ", game_code)
        print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            conn = connect()
            get_captions_query = '''
                            SELECT round_user_uid, caption FROM captions.round
                            WHERE round_game_uid = (SELECT game_uid FROM captions.game 
                            WHERE game_code=\'''' + game_code + '''\')
                            AND round_number=\'''' + round_number + '''\'
                            AND caption IS NOT NULL                         
                            '''
            captions = execute(get_captions_query, "get", conn)

            print("players info: ", captions)
            if captions["code"] == 280:
                response["message1"] = "280, get players who submitted captions request successful."
                response["players"] = captions["result"]
                return response, 200
        except:
            raise BadRequest("Get all captions in round request failed")
        finally:
            disconnect(conn)


class voteCaption(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)
            caption = data["caption"]
            print("caption info: ", caption)
            round_number = data["round_number"]
            game_code = data["game_code"]
            # bring in User ID
            user_id = data["user_id"]

            # Add caption check here
            if caption == None:
                response["message"] = "No Vote Cast."

                # Need to add NoVotes quote
                submit_novote_query = '''
                                UPDATE captions.round
                                SET novotes = 1 
                                WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                WHERE game_code=\'''' + game_code + '''\')
                                AND round_number=\'''' + round_number + '''\'
                                AND round_user_uid=\'''' + user_id + '''\'                                  
                                '''
                novote = execute(submit_novote_query, "post", conn)
                print("no vote info: ", novote)
                if novote["code"] == 281:
                    response["message"] = "281, No Vote Recorded."
                    return response, 200

            else:
                submit_caption_query = '''
                                UPDATE captions.round
                                SET votes = votes + 1 
                                WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                WHERE game_code=\'''' + game_code + '''\')
                                AND round_number=\'''' + round_number + '''\'
                                AND caption=\'''' + caption + '''\'                                  
                                '''
                caption = execute(submit_caption_query, "post", conn)
                print("caption info: ", caption)
                if caption["code"] == 281:
                    response["message"] = "281, Vote Recorded."
                    return response, 200
        except:
            raise BadRequest("Voting failed")
        finally:
            disconnect(conn)


class getPlayersWhoHaventVoted(Resource):
    def get(self, game_code, round_number):
        print("requested game_code: ", game_code)
        print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            conn = connect()
            get_players_count_query = '''
                            SELECT COUNT(votes)-SUM(votes)-SUM(novotes) AS notvoted FROM captions.round
                            INNER JOIN captions.user
                            ON captions.round.round_user_uid=captions.user.user_uid
                            WHERE round_game_uid = (SELECT game_uid FROM captions.game
                            WHERE game_code=\'''' + game_code + '''\')
                            AND round_number=\'''' + round_number + '''\'
                            '''
            players_count = execute(get_players_count_query, "get", conn)

            print("players info: ", players_count)
            print("players info code: ", players_count["code"])
            if players_count["code"] == 280:

                response["message1"] = "280, get players who haven't submitted votes request successful."
                response["players_count"] = players_count["result"][0]["notvoted"]
                return response, 200
        except:
            raise BadRequest("Get players who haven't submitted votes request failed")
        finally:
            disconnect(conn)


class getScoreBoard(Resource):
    def get(self, game_code, round_number):
        print("requested game_code: ", game_code)
        print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            conn = connect()
            get_game_score = '''
                            SELECT round_user_uid, SUM(score) as game_score FROM captions.round
                            WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                WHERE game_code=\'''' + game_code + '''\')
                            GROUP BY round_user_uid
                            '''
            game_score = execute(get_game_score, "get", conn)
            print("game_score_info:", game_score)
            if game_score["code"] == 280:
                get_score_query = '''
                                SELECT captions.round.round_user_uid, captions.user.user_alias,
                                captions.round.caption, captions.round.votes, captions.round.score
                                FROM captions.round
                                INNER JOIN captions.user
                                ON captions.round.round_user_uid=captions.user.user_uid
                                WHERE round_game_uid = (SELECT game_uid FROM captions.game
                                WHERE game_code=\'''' + game_code + '''\')
                                AND round_number=\'''' + round_number + '''\'
                                '''
                scoreboard = execute(get_score_query, "get", conn)
                print("score info: ", scoreboard)
                if scoreboard["code"] == 280:
                    response["message"] = "280, scoreboard is updated and get_score_board request " \
                                          "successful."
                    index = 0
                    for game_info, round_info in zip(game_score["result"], scoreboard["result"]):
                        # print("game_score:", game_info)
                        # print("round_info:", round_info)
                        scoreboard["result"][index]["game_score"] = game_info["game_score"]
                        index += 1
                    response["scoreboard"] = scoreboard["result"]
                    return response, 200
        except:
            raise BadRequest("Get scoreboard request failed")
        finally:
            disconnect(conn)


class updateScores(Resource):
    def get(self, game_code, round_number):
        print("requested game_code: ", game_code)
        print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            conn = connect()
            get_scoring = '''
                            SELECT scoring_scheme FROM captions.game
                            WHERE game_code=\'''' + game_code + '''\'
                            '''
            scoring_info = execute(get_scoring, "get", conn)
            print("scoring info: ", scoring_info)
            if scoring_info["code"] == 280:
                scoring = scoring_info["result"][0]["scoring_scheme"]
                print(scoring)
                if scoring == "R" or scoring == 'r':
                    highest_votes = 0
                    second_highest_votes = 0
                    get_highest_votes = '''
                                        SELECT MAX(votes) FROM captions.round
                                        WHERE round_game_uid = (SELECT game_uid FROM captions.game 
                                            WHERE game_code=\'''' + game_code + '''\')
                                        AND round_number=\'''' + round_number + '''\'
                                        '''
                    winner = execute(get_highest_votes, "get", conn)
                    print("winner_info:", winner)
                    if winner["code"] == 280:
                        highest_votes = str(winner["result"][0]["MAX(votes)"])
                        print("highest votes: ", highest_votes, type(highest_votes))
                        get_second_highest_votes = '''
                                                    SELECT votes FROM captions.round 
                                                    WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                                        WHERE game_code=\'''' + game_code + '''\') 
                                                    AND round_number=\'''' + round_number + '''\'
                                                    AND votes<\'''' + highest_votes + '''\'
                                                    ORDER BY votes DESC
                                                    '''
                        runner_up = execute(get_second_highest_votes, "get", conn)
                        print("runner-up info:", runner_up)
                        if runner_up["code"] == 280:
                            second_highest_votes = str(runner_up["result"][0]["votes"]) if runner_up["result"] and \
                                                                                           runner_up["result"][0][
                                                                                               "votes"] > 0 else "-1"
                            print("second highest votes: ", second_highest_votes, type(second_highest_votes))
                            update_scores_query = '''
                                                UPDATE captions.round	
                                                SET score = CASE
                                                    WHEN votes=\'''' + highest_votes + '''\' THEN score+5 
                                                    WHEN votes=\'''' + second_highest_votes + '''\' THEN score+3
                                                    ELSE 0
                                                    END
                                                WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                                    WHERE game_code=\'''' + game_code + '''\')
                                                AND round_number=\'''' + round_number + '''\'
                                                '''
                            update_scores = execute(update_scores_query, "post", conn)
                            if update_scores["code"] == 281:
                                response["message"] = "281, update scoreboard by ranking request successful."
                                return response, 200
                elif scoring == "V" or scoring == 'v':
                    update_score_by_votes_query = '''
                                                    UPDATE captions.round
                                                    SET score = 2 * votes
                                                    WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                                            WHERE game_code=\'''' + game_code + '''\')
                                                    AND round_number=\'''' + round_number + '''\'
                                                    '''
                    update_scores = execute(update_score_by_votes_query, "post", conn)
                    print("update_score_info: ", update_scores)
                    if update_scores["code"] == 281:
                        response["message"] = "281, update scoreboard by votes request successful."
                        return response, 200
        except:
            raise BadRequest("update scoreboard request failed")
        finally:
            disconnect(conn)


class createNextRound(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)
            round_number = data["round_number"]
            game_code = data["game_code"]
            new_round_number = str(int(round_number) + 1)
            print("Next Round Number:", new_round_number)

            players_query = '''
                                SELECT round_user_uid, round_deck_uid FROM captions.round
                                WHERE round_game_uid = (SELECT game_uid FROM captions.game 
                                WHERE game_code=\'''' + game_code + '''\')
                                AND round_number=\'''' + round_number + '''\'
                                '''
            players = execute(players_query, "get", conn)
            print("players count:", players)
            if players["code"] == 280:
                num_players = len(players["result"])
                print("players in the game: ", num_players)
                for i in range(num_players):
                    new_round_uid = get_new_roundUID(conn)
                    user_uid = players["result"][i]["round_user_uid"]
                    deck_uid = players["result"][i]["round_deck_uid"]
                    add_user_to_next_round_query = '''
                                                    INSERT INTO captions.round
                                                    SET round_uid =\'''' + new_round_uid + '''\',
                                                    round_user_uid=\'''' + user_uid + '''\',
                                                    round_game_uid=(SELECT game_uid FROM captions.game
                                                    WHERE game_code=\'''' + game_code + '''\'),
                                                    round_number=\'''' + new_round_number + '''\', 
                                                    round_deck_uid=\'''' + deck_uid + '''\',
                                                    votes=0,
                                                    score=0
                                                    '''
                    next_round = execute(add_user_to_next_round_query, "post", conn)
                    print("next_round info: ", next_round)
                    if next_round["code"] == 281:
                        continue
                    else:
                        response["message"] = "Could not add user to the next round."
                        response["user_uid"] = user_uid
                        return response, 200
                response["message"] = "281, Next Round successfully created."
                return response, 200
        except:
            raise BadRequest("create next round Request failed")
        finally:
            disconnect(conn)


class endGame(Resource):
    def get(self, game_code):
        print("game code: ", game_code)
        response = {}
        history_object = {}
        try:
            conn = connect()
            get_game_info_query = '''select json_object('round_number', round_number, 
                                                        'round_deck_uid', round_deck_uid, 
                                                        'round_image_uid', round_image_uid
                                                        ) as json_round_info, 
                                                    json_arrayagg(
                                                              json_object('round_user_uid', round_user_uid,
                                                              'caption', caption, 
                                                              'votes', votes,
                                                              'score', score)
                                                    ) as json_user_object from captions.round 
                                                    WHERE round_game_uid = (SELECT game_uid FROM captions.game 
                                                        WHERE game_code=\'''' + game_code + '''\')
                                                    group by round_number;
                                                    '''
            game_info = execute(get_game_info_query, "get", conn)
            # print("game_info: ", game_info)
            if game_info["code"] == 280:
                print("num_rounds:", len(game_info["result"]))
                for i in range(len(game_info["result"])):
                    key = "round "+str(i+1)
                    history_object[key] = {}
                    round_info = json.loads(game_info["result"][i]["json_round_info"])
                    # print(round_info, type(round_info))
                    history_object[key]["round_deck_uid"] = round_info["round_deck_uid"]
                    history_object[key]["round_image_uid"] = round_info["round_image_uid"]
                    user_info_str = json.loads(game_info["result"][i]["json_user_object"])
                    history_object[key]["user_data"] = user_info_str
                    # print(user_info_str, type(user_info_str))

                # print(history_object)
                json_history_object = json.dumps(history_object, indent=4)
                # print(json_history_object)
                new_history_uid = get_new_historyUID(conn)
                update_history_table = '''
                                        INSERT INTO captions.game_history
                                        SET history_uid = \'''' + new_history_uid + '''\',
                                            history_game_uid = (SELECT game_uid FROM captions.game
                                                    WHERE game_code=\'''' + game_code + '''\'),
                                            history_obj = \'''' + json_history_object + '''\'
                                        '''
                history_update = execute(update_history_table, "post", conn)
                # print("history_update_info: ", history_update)
                if history_update["code"] == 281:
                    response["message"] = "281, end game request successful."
                    return response, 200
        except:
            raise BadRequest("end game Request failed")
        finally:
            disconnect(conn)

class uploadImage(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            print("receiving_data")
            image_title = request.form.get("image_title")
            print("image_title: ", image_title)
            image_cost = request.form.get("image_cost")
            print("image_cost: ", image_cost)
            image_description = request.form.get("image_description")
            print("image_description: ", image_description)
            image = request.files.get("image_file")
            print("image: ", image)

            #deck name
            deck_name = request.form.get("deck_name")
            print("deck_name: ", deck_name)

            new_image_uid = get_new_imageUID(conn)
            print("new_image_uid: ", new_image_uid)

            key = "caption_image/" + str(new_image_uid)
            print("image_key: ", key)

            image_url = helper_upload_user_img(image, key)
            print("image_url: ", image_url)

            add_image_query = '''
                            INSERT INTO captions.image
                            SET image_uid = \'''' + new_image_uid + '''\',
                                image_title = \'''' + image_title + '''\',
                                image_url = \'''' + image_url + '''\',
                                image_cost = \'''' + image_cost + '''\',
                                image_description = \'''' + image_description + '''\'                    
                            ''' 
            image_response = execute(add_image_query, "post", conn)
            print("image_response: ", image_response)


            get_image_uids_query = '''
                            SELECT deck_image_uids
                            FROM captions.deck    
                            WHERE deck_title =\'''' + deck_name + '''\'                
                            '''
            deck_response = execute(get_image_uids_query, "get", conn)
            print("deck_response: ", deck_response)

            uid_string = deck_response["result"][0]["deck_image_uids"]
            print("The following is the uid string", uid_string)

            if(uid_string == "()"): #is this how we check for string deep equality in python?
                uid_string = "(\"" + new_image_uid + "\")"
            else:
                uid_string = uid_string[:-1] + ", \"" + new_image_uid + "\")"

            print("The following is the new uid string", uid_string)



            add_to_image_uids_query = '''
                                            UPDATE captions.deck
                                            SET deck_image_uids = \'''' + uid_string + '''\' 
                                            WHERE deck_title =\'''' + deck_name + '''\' 
                                            '''
            update_deck_response = execute(add_to_image_uids_query, "post", conn)
            print("update_deck_response: ", update_deck_response)

            if image_response["code"] == 281:
                response["message"] = "281, image successfully added to the database."
                return response, 200
        except:
            raise BadRequest("upload image Request failed")
        finally:
            disconnect(conn)

class CheckEmailValidated(Resource):
    def post(self):
        response = {}
        items = {}
        cus_id = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            print("Received:", data)

            name = data["name"]
            email = data["email"]
            phone_no = data["phone_no"]
            message = data["message"]

            print("name", name)
            print("email", email)
            print("phone_no", phone_no)
            print("message", message)


            # CHECK THE DATABASE FOR THE EXISTING STATE OF THE EMAIL_VALIDATED COLUMN.
            get_verification_code_query = '''
                                SELECT user_uid, email_validated FROM captions.user WHERE user_email=\'''' + email + '''\'
                                '''
            validation = execute(get_verification_code_query, "get", conn)
            print("validation info: ", validation)


            if len(validation["result"]) == 0:
                print("List is empty --> Please create a new user")

                #Roshan caught a bug. :)
                #response[message] = "User does not exist. Please create an account with this email."
                response["message"] = "User does not exist. Please create an account with this email."

                return response, 200
            else:
                print("first element of list", validation["result"][0])

            print("User info retrieved --> Checking status of email_validated")
            if validation["result"][0]["email_validated"] != 'TRUE':
                code = randint(100,999)
                print("Email validation code will be set to: ", code)
                phone_no += str(code)
                print("Phone #", phone_no)
                user_uid = validation["result"][0]["user_uid"]

                #Want to remain in safe mode and change only one row? Use this query!
                set_code_query1 = '''
                                            UPDATE captions.user
                                            SET email_validated = \'''' + str(code) + '''\' 
                                            WHERE user_uid =\'''' + user_uid + '''\' 
                                            AND user_email=\'''' + email + '''\'
                                            '''

                #Want to break some rules and possibly change multiple rows at a time? Use this one.
                set_code_query2 = '''
                                UPDATE captions.user
                                SET email_validated =\'''' + str(code) + '''\'
                                WHERE user_email=\'''' + email + '''\'
                                '''
                #print("valid modified example query\n", set_code_query)
                updateQueryResult = execute(set_code_query2, "post", conn)
                print("Result of update query: ", updateQueryResult["message"])

            else:
                print("abandon ship")
                response["message"] = "User has already been verified."
                return response, 200
                disconnect(conn)

            #SendEmail.get(self, name, email, phone_no, message)

            # #  GET CUSTOMER APPOINTMENT INFO
            # first_name = data["first_name"]
            # last_name = data["last_name"]
            # email = data["email"]
            # phone_no = data["phone_no"]
            # treatment_uid = data["appt_treatment_uid"]
            # notes = data["notes"]
            # datevalue = data["appt_date"]
            # timevalue = data["appt_time"]
            # purchase_price = data["purchase_price"]
            # purchase_date = data["purchase_date"]
            #
            # #  PRINT CUSTOMER APPOINTMENT INFO
            # print("first_name", first_name)
            # print("last_name", last_name)
            # print("email", email)
            # print("phone_no", phone_no)
            # print("treatment_uid", treatment_uid)
            # print("notes", notes)
            # print("date", datevalue)
            # print("time", timevalue)
            # print("purchase_price", purchase_price)
            # print("purchase_date", purchase_date)

            # #  CREATE CUSTOMER APPOINTMENT UID
            # # Query [0]  Get New UID
            # # query = ["CALL new_refund_uid;"]
            # query = ["CALL nitya.new_appointment_uid;"]
            # NewIDresponse = execute(query[0], "get", conn)
            # NewID = NewIDresponse["result"][0]["new_id"]
            # print("NewID = ", NewID)
            # # NewID is an Array and new_id is the first element in that array
            #
            # #  FIND EXISTING CUSTOMER UID
            # query1 = (
            #     """
            #         SELECT customer_uid FROM nitya.customers
            #         WHERE customer_email = \'"""
            #     + email
            #     + """\'
            #         AND   customer_phone_num = \'"""
            #     + phone_no
            #     + """\';
            #     """
            # )
            # cus_id = execute(query1, "get", conn)
            # print(cus_id["result"])
            # for obj in cus_id["result"]:
            #     NewcustomerID = obj["customer_uid"]
            #     print(NewcustomerID)
            #
            # print(len(cus_id["result"]))
            #
            # #  FOR NEW CUSTOMERS - CREATE NEW CUSTOMER UID AND INSERT INTO CUSTOMER TABLE
            # if len(cus_id["result"]) == 0:
            #     query = ["CALL nitya.new_customer_uid;"]
            #     NewIDresponse = execute(query[0], "get", conn)
            #     NewcustomerID = NewIDresponse["result"][0]["new_id"]

                # customer_insert_query = (
                #     """
                #     INSERT INTO nitya.customers
                #     SET customer_uid = \'"""
                #     + NewcustomerID
                #     + """\',
                #         customer_first_name = \'"""
                #     + first_name
                #     + """\',
                #         customer_last_name = \'"""
                #     + last_name
                #     + """\',
                #         customer_phone_num = \'"""
                #     + phone_no
                #     + """\',
                #         customer_email = \'"""
                #     + email
                #     + """\'
                #     """
                # )
            #
            #     customer_items = execute(customer_insert_query, "post", conn)
            #     print("NewcustomerID=", NewcustomerID)
            #
            # #  FOR EXISTING CUSTOMERS - USE EXISTING CUSTOMER UID
            # else:
            #     for obj in cus_id["result"]:
            #         NewcustomerID = obj["customer_uid"]
            #         print("customerID = ", NewcustomerID)

            #  convert to new format:  payment_time_stamp = \'''' + getNow() + '''\',

            #  INSERT INTO APPOINTMENTS TABLE
            # query2 = (
            #     """
            #         INSERT INTO nitya.appointments
            #         SET appointment_uid = \'"""
            #     + NewID
            #     + """\',
            #             appt_customer_uid = \'"""
            #     + NewcustomerID
            #     + """\',
            #             appt_treatment_uid = \'"""
            #     + treatment_uid
            #     + """\',
            #             notes = \'"""
            #     + str(notes)
            #     + """\',
            #             appt_date = \'"""
            #     + datevalue
            #     + """\',
            #             appt_time = \'"""
            #     + timevalue
            #     + """\',
            #             purchase_price = \'"""
            #     + purchase_price
            #     + """\',
            #             purchase_date = \'"""
            #     + purchase_date
            #     + """\'
            #         """
            # )
            # items = execute(query2, "post", conn)
            # query3 = (
            #     """
            #         SELECT title FROM nitya.treatments
            #         WHERE treatment_uid = \'"""
            #     + treatment_uid
            #     + """\';
            #     """
            # )
            # treatment = execute(query3, "get", conn)
            # print(treatment['result'][0]['title'])
            # # Send receipt emails
            # name = first_name + " " + last_name
            # message = treatment['result'][0]['title'] + "," + \
            #     purchase_price + "," + datevalue + "," + timevalue
            # print(name)

            SendEmail.get(self, name, email, phone_no, message)  #Temporary comment out for testing purposes
            print("send email successful")

            response["message"] = "Code has been sent to email"
            response["result"] = items
            return response, 200
        except:
            raise BadRequest("Check Email Validated Request failed, please try again later.")
        finally:
            disconnect(conn)

        # ENDPOINT AND JSON OBJECT THAT WORKS
        # http://localhost:4000/api/v2/createappointment

class CheckEmailValidationCode(Resource):
    def post(self):
        response = {}
        items = {}
        cus_id = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            print("Received JSON data: ", data)

            user_uid = data["user_uid"]
            code = data["code"]
            print("user uid = ", user_uid, ", code = ", code)

            get_verification_code_query = '''
                            SELECT email_validated FROM captions.user WHERE user_uid=\'''' + user_uid + '''\'
                            '''

            validation = execute(get_verification_code_query, "get", conn)
            print("validation info: ", validation)

            #If for some reason we can't find a user in the table with the given user_uid....
            if len(validation["result"]) == 0:
                response["message"] = "No user has been found for the following user_uid. " \
                                      "Perhaps you have entered an invalid user_uid, " \
                                      "or the endpoint to createNewUsers is broken"
                return response, 200

            #If we do find such a user,
            # we will cross-examine the code they have typed in against what we have stored in the database.
            #If it matches --> hooray! We set the email_validated of that user to true.
            #If it DOES NOT match --> whoops! They typed in a bad code.
            print("first element of list", validation["result"][0])
            if validation["result"][0]["email_validated"] == "TRUE":
                response["message"] = "User Email for this specific user has already been verified." \
                                      " No need for a code! :)"
                response["email_validated_status"] = "TRUE"

            elif validation["result"][0]["email_validated"] == "FALSE":
                response["message"] = "You need to generate a code for this user before you verify it."
                response["email_validated_status"] = "FALSE"

            elif validation["result"][0]["email_validated"] == code:
                set_code_query = '''
                                UPDATE captions.user
                                SET email_validated =\'''' + "TRUE" + '''\'
                                WHERE user_uid=\'''' + user_uid + '''\'
                                '''
                verification = execute(set_code_query, "post", conn)
                print("User code has been updated to TRUE")
                response["message"] = "User Email Verification Code has been validated. Have fun!"
                response["email_validated_status"] = "TRUE"

            else:
                response["message"] = "Invalid Verification Code." \
                                      "The code provided does not match what we have in the database"
                response["email_validated_status"] = "..."

            return response, 200
        except:
            raise BadRequest("Validate Email Verification Code Request Failed. Try again later. :(")
        finally:
            disconnect(conn)

        # ENDPOINT AND JSON OBJECT THAT WORKS
        # http://localhost:4000/api/v2/createappointmen

# SEND EMAIL
class SendEmail(Resource):
    def __call__(self):
        print("In SendEmail")

    def get(self, name, email, phone, subject):
        print("In Send EMail get")
        try:
            conn = connect()
            subject = subject.split(',')

            print("name", name)
            print("email", email)
            print("phone", phone)
            code = phone[-3:]
            print("code", code)
            print("subject", subject)

            # month_num = subject[2][5:7]
            # datetime_object1 = datetime.strptime(month_num, "%m")
            # month_name = datetime_object1.strftime("%B")
            #
            # datetime_object2 = datetime.strptime(subject[2], "%Y-%m-%d")
            # day = datetime_object2.strftime("%A")
            #
            # datetime_object3 = datetime.strptime(subject[3], "%H:%M")
            # time = datetime_object3.strftime("%I:%M %p")
            # print(time)

            # phone = phone[0:3] + "-" + phone[3:6] + "-" + phone[6:]
            print(phone)
            # Send email to Client
            msg = Message(
                "Thanks for your Email!",
                # sender="support@nityaayurveda.com",
                sender="support@mealsfor.me",
                # recipients=[email],
                # recipients=[email, "Lmarathay@yahoo.com",
                #             "pmarathay@gmail.com"],

                #hello9 (does work)
                # recipients=[email,
                #             "pmarathay@gmail.com"],

                #hello10 (does work)
                # recipients=[email,"pmarathay@gmail.com"]

                # hello11 & hello15 (does work also??)
                # recipients = [email, "pmarathay@gmail.com"],

                # recipients=["mayukh.das@sjsu.edu"]
                # recipients=["pmarathay@gmail.com"]

                # hello16 (works)
                # recipients=["pmarathay@gmail.com", "mayukh.das@sjsu.edu"]

                # hello17 ()
                # recipients = ["pmarathay@gmail.com", "mayukh.das@sjsu.edu", "roshan.nadavi@gmail.com", email]

                recipients = ["pmarathay@gmail.com", email]
                
            )
            print("past message")
            # msg = Message("Test email", sender='support@mealsfor.me', recipients=["pmarathay@gmail.com"])
            #some kind of function missing?
            #another reason: missing the env files?
            print(msg)
            msg.body = code
            #msg.body = "hello17"
            # msg.body = (
            #     "Hello " + str(name) + "," + "\n"
            #     "\n"
            #     "Thank you for making your appointment with us. \n"
            #     "Here are your  appointment details: \n"
            #     "Date: " +
            #     # str(day) + ", " + str(month_name) + " " +
            #     str(subject[2][8:10]) + ", " + str(subject[2][0:4]) + "\n"
            #     "Time: " + str(time) + "\n"
            #     "Location: 6055 Meridian Ave. Suite 40 A, San Jose, CA 95120. \n"
            #     "\n"
            #     "Name: " + str(name) + "\n"
            #     "Phone: " + str(phone) + "\n"
            #     "Email: " + str(email) + "\n"
            #     "\n"
            #     "Package purchased: " + str(subject[0]) + "\n"
            #     "Total amount paid: " + str(subject[1]) + "\n"
            #     "\n"
            #     "If you have any questions please call or text: \n"
            #     "Leena Marathay at 408-471-7004, \n"
            #     "Email Leena@nityaayurveda.com \n"
            #     "\n"
            #     "Thank you - Nitya Ayurveda\n\n"
            # )
            print("past body")
            print(msg.body)
            try: 
                mail.send(msg)
                print("after mail.send(msg)")
                print(msg)
            except:
                print("Likely an EMail Credential Issue")

            # # print("first email sent")
            # # Send email to Host
            # msg = Message(
            #     "New Email from Website!",
            #     sender="support@nityaayurveda.com",
            #     recipients=["Lmarathay@yahoo.com"],
            # )
            # msg.body = (
            #     "Hi !\n\n"
            #     "You just got an email from your website! \n"
            #     "Here are the particulars:\n"
            #     "Name:      " + name + "\n"
            #     "Email:     " + email + "\n"
            #     "Phone:     " + phone + "\n"
            #     "Subject:   " + subject + "\n"
            # )
            # "Thx - Nitya Ayurveda\n\n"
            # # print('msg-bd----', msg.body)
            # mail.send(msg)

            return "Email Sent", 200

        except:
            raise BadRequest("Email Request failed, please try again later.")
        finally:
            disconnect(conn)

    def post(self):

        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            email = data["email"]

            # msg = Message("Thanks for your Email!", sender='pmarathay@manifestmy.space', recipients=[email])
            # msg = Message("Thanks for your Email!", sender='info@infiniteoptions.com', recipients=[email])
            # msg = Message("Thanks for your Email!", sender='leena@nityaayurveda.com', recipients=[email])
            # msg = Message("Thanks for your Email!", sender='pmarathay@buildsuccess.org', recipients=[email])
            msg = Message(
                "Thanks for your Email!",
                sender="support@nityaayurveda.com",
                recipients=[email, "Lmarathay@gmail.com",
                            "pmarathay@gmail.com"],
            )
            # msg = Message("Test email", sender='support@mealsfor.me', recipients=["pmarathay@gmail.com"])
            msg.body = (
                "Hi !\n\n"
                "We are looking forward to meeting with you! \n"
                "Email support@nityaayurveda.com if you need to get in touch with us directly.\n"
                "Thx - Nitya Ayurveda\n\n"
            )
            # print('msg-bd----', msg.body)
            # print('msg-')
            mail.send(msg)

            # Send email to Host
            # msg = Message("Email Verification", sender='support@mealsfor.me', recipients=[email])

            # print('MESSAGE----', msg)
            # print('message complete')
            # # print("1")
            # link = url_for('confirm', token=token, hashed=password, _external=True)
            # # print("2")
            # print('link---', link)
            # msg.body = "Click on the link {} to verify your email address.".format(link)
            # print('msg-bd----', msg.body)
            # mail.send(msg)
            return "Email Sent", 200

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

#Wow! This is my first customized endpoint. More than happy that it actually works :).
class goaway(Resource):
    def get(self):
        print("go away requested")
        response = {}
        items = {}
        try:
            conn = connect()
            print("connection established")

            response["message"] = "i told you to go away"
            return response, 200
        except:
            raise BadRequest("Go Away Request Failed :(")
        finally:
            disconnect(conn)

class testHarvard(Resource):
    def get(self):
        print("beginning testHarvard")
        response = {}
        items = {}
        try:
            conn = connect()
            print("connection established")

            num = randint(1,376513)
            page = num/10 + 1
            index = num%10

            # page = randint(1,3751)
            # print(page)
            # index = randint(1,10)
            # print(index)

            # harvardURL = "https://api.harvardartmuseums.org/image"
            # print(harvardURL)
            # params = {
            #     "apikey": "332993bc-6aca-4a69-bc9d-ae6cca29f633",
            #     "page": "37650"
            #     #"page": str(page),
            # }
            # print("Params = ", params)
            # r = requests.get(url = harvardURL, data=params)
            # print(r.json())

            harvardURL = "https://api.harvardartmuseums.org/image?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633&page="
            harvardURL = harvardURL + str(page)
            #print(harvardURL)
            r = requests.get(harvardURL)
            #print(r.json()["records"][index]["baseimageurl"])


            response["message"] = "testHarvard complete"
            response["result"] = r.json()["records"][index]["baseimageurl"]
            return response, 200
        except:
            raise BadRequest("Harvard Request Failed :(")
        finally:
            disconnect(conn)

# -- DEFINE APIS -------------------------------------------------------------------------------


# Define API routes
api.add_resource(createGame, "/api/v2/createGame")
api.add_resource(checkGame, "/api/v2/checkGame/<string:game_code>")
api.add_resource(createUser, "/api/v2/createUser")
api.add_resource(addUser, "/api/v2/addUser")
# api.add_resource(createNewGame, "/api/v2/createNewGame")
api.add_resource(joinGame, "/api/v2/joinGame")
api.add_resource(getPlayers, "/api/v2/getPlayers/<string:game_code>")
#api.add_resource(decks, "/api/v2/decks")
api.add_resource(decks, "/api/v2/decks/<string:user_uid>,<string:public_decks>")
api.add_resource(gameTimer, "/api/v2/gameTimer/<string:game_code>,<string:round_number>")
api.add_resource(selectDeck, "/api/v2/selectDeck")
api.add_resource(assignDeck, "/api/v2/assignDeck")
api.add_resource(changeRoundsAndDuration, "/api/v2/changeRoundsAndDuration")
api.add_resource(getImageInRound, "/api/v2/getImageInRound/<string:game_code>,<string:round_number>")
api.add_resource(submitCaption, "/api/v2/submitCaption")
api.add_resource(getPlayersRemainingToSubmitCaption,
                 "/api/v2/getPlayersRemainingToSubmitCaption/<string:game_code>,<string:round_number>")
api.add_resource(getAllSubmittedCaptions, "/api/v2/getAllSubmittedCaptions/<string:game_code>,<string:round_number>")
api.add_resource(voteCaption, "/api/v2/voteCaption")
api.add_resource(getPlayersWhoHaventVoted, "/api/v2/getPlayersWhoHaventVoted/<string:game_code>,<string:round_number>")
api.add_resource(createNextRound, "/api/v2/createNextRound")
api.add_resource(updateScores, "/api/v2/updateScores/<string:game_code>,<string:round_number>")
api.add_resource(getScoreBoard, "/api/v2/getScoreBoard/<string:game_code>,<string:round_number>")
api.add_resource(startPlaying, "/api/v2/startPlaying/<string:game_code>,<string:round_number>")
api.add_resource(getImageForPlayers, "/api/v2/getImageForPlayers/<string:game_code>,<string:round_number>")
api.add_resource(endGame, "/api/v2/endGame/<string:game_code>")
api.add_resource(getUniqueImageInRound, "/api/v2/getUniqueImageInRound/<string:game_code>,<string:round_number>")
api.add_resource(uploadImage, "/api/v2/uploadImage")
api.add_resource(goaway, "/api/v2/goaway")
api.add_resource(SendEmail, "/api/v2/sendEmail")
api.add_resource(CheckEmailValidated, "/api/v2/checkEmailValidated")
api.add_resource(CheckEmailValidationCode, "/api/v2/checkEmailValidationCode")
api.add_resource(testHarvard, "/api/v2/testHarvard")

# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4000)
