# To run program:  python3 io_api.py

# README:  if conn error make sure password is set properly in RDS PASSWORD section

# README:  Debug Mode may need to be set to False when deploying live (although it seems to be working through Zappa)

# README:  if there are errors, make sure you have all requirements are loaded

from contextlib import nullcontext
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

from flask import Flask, request, render_template, Response, g
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_mail import Mail, Message

from prometheus_client import Counter, generate_latest, Summary
import logging

# from cnn_webscrape import lambda_handler
# used for serializer email and error handling
# from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
# from flask_cors import CORS

from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
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
from dotenv import load_dotenv
load_dotenv()

from random import randint

RDS_HOST = "io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com"
RDS_PORT = 3306
RDS_USER = "admin"
RDS_DB = "captions"

# RDS_HOST = os.getenv("RDS_HOST")
# RDS_PORT = os.getenv("RDS_PORT")
# RDS_USER = os.getenv("RDS_USER")
# RDS_DB = os.getenv("RDS_DB")



# app = Flask(__name__)
app = Flask(__name__, template_folder="assets")

# --------------- Stripe Variables ------------------
# these key are using for testing. Customer should use their stripe account's keys instead
import stripe

# STRIPE AND PAYPAL KEYS
paypal_secret_test_key = os.getenv('paypal_secret_key_test')
paypal_secret_live_key = os.getenv('paypal_secret_key_live')

paypal_client_test_key = os.getenv('paypal_client_test_key')
paypal_client_live_key = os.getenv('paypal_client_live_key')

stripe_public_test_key = os.getenv('stripe_public_test_key')
stripe_secret_test_key = os.getenv('stripe_secret_test_key')

stripe_public_live_key = os.getenv('stripe_public_live_key')
stripe_secret_live_key = os.getenv('stripe_secret_live_key')

stripe.api_key = stripe_secret_test_key

# use below for local testing
# stripe.api_key = ""sk_test_51J0UzOLGBFAvIBPFAm7Y5XGQ5APR...WTenXV4Q9ANpztS7Y7ghtwb007quqRPZ3""


CORS(app)

# --------------- Mail Variables ------------------
#This should be on Github -- should work wth environmental variables
app.config["MAIL_USERNAME"] = os.getenv("SUPPORT_EMAIL")
app.config["MAIL_PASSWORD"] = os.getenv("SUPPORT_PASSWORD")
# print("Backend Running")
# print(os.getenv("SUPPORT_EMAIL"))
# print(os.getenv("RDS_DB"))

#This should not be on Github -- should work on localhost
# app.config['MAIL_USERNAME'] = "support@mealsfor..."
# app.config['MAIL_USERNAME'] = "support@capshnz.com"
# app.config['MAIL_PASSWORD'] = "Supportcapshnz1!"



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

app.config["STRIPE_SECRET_KEY"] = os.getenv("STRIPE_SECRET_KEY")

mail = Mail(app)

# API
api = Api(app)

# convert to UTC time zone when testing in local time zone
utc = pytz.utc

# REQUEST_COUNTER = Counter(
#                     'capshnz_http_requests_total', 
#                     'Total HTTP requests by status code and endpoint',
#                     ['endpoint', 'status_code', 'client_ip']
#                 )

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

REQUEST_COUNTER = Counter(
    'capshnz_http_requests_total',
    'Total HTTP requests by method, endpoint, status code, and client IP',
    ['method', 'endpoint', 'status_code', 'client_ip']
)
LATENCY_SUMMARY = Summary(
    'capshnz_http_request_latency_seconds', 'Request latency by endpoint', ['endpoint']
)


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
# BUCKET_NAME = os.getenv('MEAL_IMAGES_BUCKET')
BUCKET_NAME = 'iocaptions'
# allowed extensions for uploading a profile photo file
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg"])

def allowed_file(filename):
    """Checks if the file is allowed to upload"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def helper_upload_user_img(file, key):
    # print("uploading image to s3 bucket.")
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
NOTIFICATION_HUB_KEY = os.getenv("NOTIFICATION_HUB_KEY")
NOTIFICATION_HUB_NAME = os.getenv("NOTIFICATION_HUB_NAME")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")


# Connect to MySQL database (API v2)
def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    # print("Trying to connect to RDS (API v2)...")
    try:
        conn = pymysql.connect(
            host=RDS_HOST,
            user=RDS_USER,
            port=RDS_PORT,
            passwd=RDS_PW,
            db=RDS_DB,
            cursorclass=pymysql.cursors.DictCursor,
        )
        # print("Successfully connected to RDS. (API v2)")
        return conn
    except:
        # print("Could not connect to RDS. (API v2)")
        raise Exception("RDS Connection failed. (API v2)")


# Disconnect from MySQL database (API v2)
def disconnect(conn):
    try:
        conn.close()
        # print("Successfully disconnected from MySQL database. (API v2)")
    except:
        # print("Could not properly disconnect from MySQL database. (API v2)")
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
    # print("in Execute", cmd)
    try:
        with conn.cursor() as cur:
            # print("before query")
            cur.execute(sql)
            # print("after query")
            if cmd == "get":
                result = cur.fetchall()
                response["message"] = "Successfully executed SQL query."
                # Return status code of 280 for successful GET request
                response["code"] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response["result"] = result
            elif cmd == "post":
                # print("in POST")
                conn.commit()
                # print("after commit")
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
        # print("Successfully closed RDS connection.")
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


# --Email Support -------------------------------------------------------------------------------


def sendEmail(name, email, code, subject):
    # print("In sendEmail")
    with app.app_context():
        # print("In sendEmail: ", email, code, subject)
        sender="support@capshnz.com"
        # print("sender: ", sender)
        # print("code: ", code)

        message = (
            f"Hello {name if name else ''}!\n\n"
            "Here is the Capshnz Code: \n"
            f"{code}\n"
            "Have Fun!\n\n"
            "PS: Please send any game feedback to support@capshnz.com"
            )

        # print("Body: ", message)

        # subject=f"Capshnz code: {code}",

        msg = Message(
            subject=f"Capshnz code: {code}",
            sender = "support@capshnz.com",
            recipients = [email],
            body = message
        )
        
        # print("recipients: ", email)
        # print("Email message: ", msg)
        mail.send(msg)
        # print("email sent")


class SendError(Resource):
    def __call__(self):
        print("In SendError")

    def get(self, code1, code2):
        # print("In Send Error get")
        try:
            conn = connect()
            email = 'pmarathay@gmail.com'

            # print("code 1", code1)
            # print("code 2", code2)
        
            # Send email to Client
            msg = Message(
                "Captions Error Code Generated",
                # sender="support@nityaayurveda.com",
                # sender="support@mealsfor.me",
                sender="support@capshnz.com",

                recipients = ["pmarathay@gmail.com", email]
                
            )
            # print("past message")
            # print(msg)

            # msg.body = code1

            msg.body = (
                "Code 1: " + str(code1) + "\n"
                "Code 2: " + str(code2) + "\n"
            )

            # print("past body")
            # print(msg.body)
            try: 
                # print(msg)
                mail.send(msg)
                # print("after mail.send(msg)")
                
            except:
                print("Likely an EMail Credential Issue")

            return "Email Sent", 200

        except:
            raise BadRequest("Email Request failed, please try again later.")
        finally:
            disconnect(conn)


# --Caption Queries start here -------------------------------------------------------------------------------


class addUserByEmail(Resource):
    def post(self):
        response = {}
        message = "Email Verification Code Sent"
        try:
            conn = connect()
            data = request.get_json()
            email = data["user_email"]
            query = """SELECT * FROM captions.user
                        WHERE user_email= \'""" + email + """\'
                    """
            user = execute(query, "get", conn)
            if user['result'] != ():
                response["user_uid"] = user['result'][0]['user_uid']
                response["user_code"] = user["result"][0]["email_validated"]
                response["name"] = user["result"][0]["user_name"]
                response["alias"] =  user["result"][0]["user_alias"]
                if user['result'][0]["email_validated"] != "TRUE":
                    response["user_status"] = "User NOT Validated"
                    
                    sendEmail( user["result"][0]["user_name"], email, user['result'][0]["email_validated"], "User NOT Validated")
            else:
                code = str(randint(100,999))
                new_user_uid = get_new_userUID(conn)
                # print("New User Info: ", new_user_uid, code)
                query = '''
                    INSERT INTO captions.user
                    SET user_uid = \'''' + new_user_uid + '''\',
                        user_created_at = \'''' + getNow() + '''\',
                        user_email = \'''' + email + '''\', 
                        email_validated = \'''' + code + '''\',
                        user_purchases = NULL
                    '''
                items = execute(query, "post", conn)
                if items["code"] == 281:
                    response["message"] = "Create User successful"
                    response["user_uid"] = new_user_uid
                    response["email_validated"] = code
                    
                    sendEmail( "", email, code, "User NOT Validated")
                return response, 200
        except Exception as e:
            raise InternalServerError("An unknown error occurred. If running locally, check email credentials") from e
        finally:
            disconnect(conn)
        return response, 200


class addUser(Resource):
    def post(self):
        # print("In addUser")
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print("Received:", data)

            user_name = data["user_name"]
            user_alias = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
            user_email = data["user_email"]
            message = "Email Verification Code Sent"
            # user_zip = data["user_zip"]

            # print(user_name, user_alias, user_email, message)
            

            # CHECK IF EMAIL EXISTS IN DB
            check_user = '''SELECT * FROM captions.user
                            WHERE user_email= \'''' + user_email + '''\'
                            '''

            user = execute(check_user, "get", conn)
            # print("User Info: ", user["result"])


            # CHECK IF USER EXISTS
            if user['result'] != ():
                # print("User Exists")
            # if len(user['result'][0]['user_uid']) > 0:
                response["user_uid"] = user['result'][0]['user_uid']
                response["user_code"] = user["result"][0]["email_validated"]

                # CHECK IF VALIDATION CODE IS TRUE
                if user['result'][0]["email_validated"] != "TRUE":
                    # print("Not Validated")
                    
                    sendEmail( user["result"][0]["user_name"], user_email, user["result"][0]["email_validated"], "User NOT Validated")

                    response["user_status"] = "User NOT Validated"
                    
                    # return response
            

                # CHECK IF ALIAS HAS CHANGED
                if user_alias != user['result'][0]['user_alias']:
                    # print("Alias changed")
                    response["user_alias"] = "Alias changed"

                    query = '''
                        UPDATE captions.user
                        SET user_alias = \'''' + user_alias + '''\'
                        WHERE user_email = \'''' + user_email + '''\';
                        '''

                    update_alias = execute(query, "post", conn)
                    # print("items: ", update_alias)
                    if update_alias["code"] == 281:
                        response["user_alias"] = "Alias updated"

                # CHECK IF USER NAME HAS CHANGED
                if user_name != user['result'][0]['user_name']:
                    # print("Name changed")
                    response["user_name"] = "Name Changed"

                    query = '''
                        UPDATE captions.user
                        SET user_name = \'''' + user_name + '''\'
                        WHERE user_email = \'''' + user_email + '''\';
                        '''
                    # print("uncomment execute command here")
                    update_name = execute(query, "post", conn)
                    # print("items: ", update_name)
                    if update_name["code"] == 281:
                        response["user_name"] = "Name updated"

            # USER DOES NOT EXIST
            else:
                # Create Validation Code FOR NEW USER
                code = str(randint(100,999))
                # print(f"Email validation code {code} will be set to: {user_email}")

                new_user_uid = get_new_userUID(conn)
                # print(new_user_uid)
                # print(getNow())

                query = '''
                    INSERT INTO captions.user
                    SET user_uid = \'''' + new_user_uid + '''\',
                        user_created_at = \'''' + getNow() + '''\',
                        user_name = \'''' + user_name + '''\', 
                        user_alias = \'''' + user_alias + '''\', 
                        user_email = \'''' + user_email + '''\',
                        email_validated = \'''' + code + '''\',
                        user_purchases = NULL
                    '''

                items = execute(query, "post", conn)

                # print("items: ", items)
                if items["code"] == 281:
                    response["message"] = "Create User successful"
                    response["user_uid"] = new_user_uid
                    response["email_validated"] = code

                    # Send Code to User
                    # print("\nSending Code to New User")
                    sendEmail( user_name, user_email, code, message)

                return response, 200




            return response, 200


        except:
            raise BadRequest("Create User Request failed. If running on local host make sure your have the MAIL_USERNAME and MAIL_PASSWORD")
        finally:
            disconnect(conn)


class createGame(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            user_uid = data["user_uid"]
            num_rounds = data["rounds"]
            time_limit = data["round_time"]
            scoring = data["scoring_scheme"]
            # print(user_uid)

            new_game_uid = get_new_gameUID(conn)
            # print(new_game_uid)
            # print(getNow())

            game_code = random.randint(10000000, 99999999)
            # print(game_code)

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
            # print("items: ", items)
            if items["code"] == 281:
                response["message"] = "Create Game successful"
                response["game_code"] = str(game_code)
                response["game_uid"] = str(new_game_uid)
                return response, 200
        except:
            raise BadRequest("Create Game Request failed")
        finally:
            disconnect(conn)


class joinGame(Resource):
    def post(self):
        # print("In joinGame")
        response = {}
        returning_user = {}
        new_user = {}
        game_info = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            # player data
            user_uid = data["user_uid"]
            game_code = data["game_code"]

            # Check if game code exists and get game_uid
            check_game_code_query = '''
                                    SELECT * FROM captions.game
                                    WHERE game_code=\'''' + game_code + '''\'
                                    '''
            game_info = execute(check_game_code_query, "get", conn)
            # print(game_info)
            if game_info["code"] == 280 and len(game_info["result"]) == 1:
                game_uid = game_info["result"][0]["game_uid"]
                # print(game_uid)
                response["num_rounds"] = game_info["result"][0]["num_rounds"]
                # print(game_info["result"][0]["num_rounds"])
                response["round_duration"] = game_info["result"][0]["time_limit"]
                # print(game_info["result"][0]["time_limit"])


                # Check if user is already in the game
                check_user_in_game_query = '''
                                            SELECT round_user_uid FROM captions.round
                                            WHERE round_game_uid = \'''' + game_uid + '''\'
                                            AND round_user_uid = \'''' + user_uid + '''\';
                                            '''

                existing_player = execute(check_user_in_game_query, "get", conn)
                # print("player_info: ", existing_player)
                
                if existing_player["code"] == 280 and existing_player["result"] != ():
                        response["message"] = "280, Player has already joined the game."
                        response["user_uid"] = user_uid
                        return response, 409

                else:
                    # User has entered and existing game code and is not in the game
                    # print("in else clause")
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
                    # print("add_user_response: ", add_user)
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


class selectDeck(Resource):
    def post(self):
        # print("in select deck")
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)
            deck_uid = data["deck_uid"]
            game_code = data["game_code"]

            select_deck_query = '''
                                UPDATE captions.game
                                SET game_deck = \'''' + deck_uid + '''\'
                                WHERE game_code = \'''' + game_code + '''\';
                                '''

            selected_deck = execute(select_deck_query, "post", conn)
            # print("selected deck info: ", selected_deck)

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
            # print("Received:", data)
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
            # print("selected deck info: ", assign_deck)

            if assign_deck["code"] == 281:
                response["message"] = "281, Deck assigned successfully."
                return response, 200

        except:
            raise BadRequest("Assign deck Request failed")
        finally:
            disconnect(conn)


class checkGame(Resource):
    def get(self, game_code):
        # print(game_code)
        response = {}
        items = {}
        try:
            conn = connect()

            query = '''
                SELECT game_uid FROM captions.game
                WHERE game_code = \'''' + game_code + '''\';
                '''
            items = execute(query, "get", conn)
            # print("items: ", items)

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
        # print("requested game_uid: ", game_code)
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
            # print("players info: ", players)
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
        # print(user_uid)
        # print(public_decks)
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
            # print("players info: ", decks)
            if decks["code"] == 280:
                response["message"] = "280, get available decks request successful."
                response["decks_info"] = decks["result"]

                return response, 200
        except:
            raise BadRequest("get available decks request failed")
        finally:
            disconnect(conn)


class gameTimer(Resource):
    def get(self, game_code, round_number):
        # print("requested game_uid: ", game_code)
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

            # print("timer info: ", timer)
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
            # print("Received:", data)
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
            # print("game_attr_update info: ", update_game_attr)
            if update_game_attr["code"] == 281:
                response["message"] = "281, Rounds and duration successfully updated."
                return response, 200
        except:
            raise BadRequest("Update rounds and time Request failed")
        finally:
            disconnect(conn)


class startPlaying(Resource):
    def get(self, game_code, round_number):
        # print("game_code: ", game_code)
        # print("round_number: ", round_number)
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
            # print("round_timestamp_result: ", round_timestamp)
            if round_timestamp["code"] == 281:
                response["message"] = "281, game started."
                response["round_start_time"] = current_time
                return response, 200
        except:
            raise BadRequest("Get image in round request failed")
        finally:
            disconnect(conn)


# ENDPOINT IN USE - TEST PRINT STATEMENTS ADDED
class getUniqueImageInRound(Resource):
    def get(self, game_code, round_number):
        # print("requested game_code: ", game_code)
        # print("requested round_number: ", round_number)
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

            # print("Check if Harvard Deck")
            check_deck_harvard_query = '''
                                SELECT deck_title
                                FROM captions.deck
                                WHERE deck_uid = (
                                        SELECT game_deck 
                                        FROM captions.game 
                                        WHERE game_code = \'''' + game_code + '''\');'''

            deck_is_harvard = execute(check_deck_harvard_query, "get", conn)

            

            if(deck_is_harvard["result"][0]["deck_title"] == "Harvard Art Museum"):
                # print("User selected Harvard Deck")
                get_images_query = '''
                                            SELECT distinct captions.round.round_image_uid
                                            FROM captions.round
                                            INNER Join captions.deck
                                            ON captions.round.round_deck_uid=captions.deck.deck_uid
                                            WHERE round_game_uid =  (SELECT game_uid FROM captions.game
                                            WHERE game_code=\'''' + game_code + '''\')
                                            '''
                image_info = execute(get_images_query, "get", conn)
                # print("harvard image info: ", image_info)

                images_used = set()
                for result in image_info["result"]:
                    if result["round_image_uid"] not in images_used:
                        images_used.add(result["round_image_uid"])
                # print(images_used, type(images_used))
                flag = True
                image_id = ""
                while flag:
                    image_uid = randint(1,376513)
                    page = image_uid // 10 + 1
                    index = image_uid % 10

                    harvardURL = "https://api.harvardartmuseums.org/image?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633&page=" + str(
                        page)
                    # print(harvardURL)
                    r = requests.get(harvardURL)
                    # print(index)
                    # print("before return for getUniqueImage ", r.json()["records"][index]["baseimageurl"])

                    # image_uid = index
                    image_uid = r.json()["records"][index]["imageid"]
                    image_id = str(image_uid)
                    # print("curr index: ", image_uid)
                    if image_uid not in images_used:
                        flag = False

                # print("next_image_id: ", image_id, type(image_id))

                write_to_round_query = '''
                                                        UPDATE captions.round
                                                        SET round_image_uid=\'''' + image_id + '''\'
                                                        WHERE round_game_uid=(SELECT game_uid FROM captions.game
                                                        WHERE game_code=\'''' + game_code + '''\')
                                                        AND round_number = \'''' + round_number + '''\'
                                                        '''
                updated_round = execute(write_to_round_query, "post", conn)
                # print("game_attr_update info: ", updated_round)

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
            # print("User selected deck other than Harvard")

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

            # print("\nimage info: ", image_info)
            # print("\nimage result: ", image_info["result"][0])
            # print("\nround image: ", image_info["result"][0]["round_image_uid"])

            if image_info["code"] == 280:
                images_in_deck_str = image_info["result"][0]["deck_image_uids"][2:-2]#.split(', ')
                images_in_deck_str = images_in_deck_str.replace('"', " ")
                images_in_deck = images_in_deck_str.split(" ,  ")
                # print("\nImages in deck: ", images_in_deck)

                images_used = set()
                for result in image_info["result"]:
                    if result["round_image_uid"] not in images_used:
                        images_used.add(result["round_image_uid"])
                # print(images_in_deck, type(images_in_deck))
                # print(images_used, type(images_used))
                flag = True
                image_uid = ""
                while flag:
                    index = random.randint(0, len(images_in_deck)-1)
                    # print("curr index: ", index)
                    if images_in_deck[index] not in images_used:
                        image_uid = images_in_deck[index]
                        flag = False

                # print("next_image_uid: ", image_uid, type(image_uid))

                response["message1"] = "280, get image request successful."
                get_image_url_query = '''
                                    SELECT image_url FROM captions.image
                                    WHERE image_uid=\'''' + image_uid + '''\'
                                    '''
                image_url = execute(get_image_url_query, "get", conn)
                # print("image_url: ", image_url)
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
                    # print("game_attr_update info: ", updated_round)
                    if updated_round["code"] == 281:
                        response["message"] = "281, image in the Round updated."
                        response["image_url"] = image_url["result"][0]["image_url"]
                        return response, 200
        except:
            raise BadRequest("Get image in round request failed")
        finally:
            disconnect(conn)


# ENDPOINT IN USE - TEST PRINT STATEMENTS ADDED
class getImageForPlayers(Resource):
    def get(self, game_code, round_number):
        # print("requested game_code: ", game_code)
        # print("requested round_number:", round_number)
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

            

            if(deck_is_harvard["result"][0]["deck_title"] == "Harvard Art Museum"):
                # print("In getImageForPlayers in Harvard Deck")
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
                # print(image_uid, type(image_uid))
                # page = image_uid//10 + 1
                # index = image_uid%10

                harvardURL = "https://api.harvardartmuseums.org/image/"+ image_uid +"?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633"
                #harvardURL = "https://api.harvardartmuseums.org/image?apikey=332993bc-6aca-4a69-bc9d-ae6cca29f633&page="
                # print(harvardURL)
                #print(index)
                r = requests.get(harvardURL)
                #print("before return getImageForPlayers ", r.json()["records"][index]["baseimageurl"])


                # print("image info: ", image_info)
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
            # print("In getImageForPlayers Non Harvard Deck")
            image_info = execute(get_image_query, "get", conn)

            # print("image info: ", image_info)
            if image_info["code"] == 280:
                response["message"] = "280, get image for players other than host request successful."
                response["image_uid"] = image_info["result"][0]["round_image_uid"]
                response["image_url"] = image_info["result"][0]["image_url"]
                return response, 200
        except:
            raise BadRequest("Get image for players other than host request failed")
        finally:
            disconnect(conn)


class getRoundImage(Resource):

    def get(self, game_code, round_number):
        response = {}
        items = {}
        try:
            conn = connect()
            
            # print to Received data to Terminal

            # Tried to pass JSON object into GET.  Worked in LOCAL HOST but not live.
            # data = request.get_json(force=True)
            # print("Received:", data)
            # round_number = data["round_number"]
            # game_code = data["game_code"]
            # print(game_code)
            # print(round_number)

            if round_number != "0":

                images_used_in_round = '''
                                    SELECT round_image_uid,
                                        COUNT(round_image_uid) AS num_occurances
                                    FROM captions.round
                                    WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code=\'''' + game_code + '''\')
                                        AND round_number=\'''' + round_number + '''\'
                                    GROUP BY round_image_uid;
                                    '''
                images = execute(images_used_in_round, "get", conn)
                # print("caption info: ", images["result"])
                if images["code"] == 280:
                    response["result"] = images["result"]
                    response["message"] = "280, Found Images used in Round."
                    return response, 200
            else:
                images_used_in_round = '''
                                    SELECT round_number,
                                        round_image_uid,
                                        COUNT(*) AS num_occurances
                                    FROM captions.round
                                    WHERE round_game_uid = (SELECT game_uid FROM captions.game WHERE game_code=\'''' + game_code + '''\')
                                    GROUP BY round_image_uid, round_number;
                                    '''
                images = execute(images_used_in_round, "get", conn)
                # print("caption info: ", images["result"])
                if images["code"] == 280:
                    response["result"] = images["result"]
                    response["message"] = "280, Found Images used in Round."
                    return response, 200

        except:
            raise BadRequest("Could not find Images used in Round")
        finally:
            disconnect(conn)


class postRoundImage(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)
            round_number = data["round_number"]
            game_code = data["game_code"]
            image_uid = data["image"]
            # print(round_number)

            write_to_round_query = '''
                                    UPDATE captions.round
                                    SET round_image_uid=\'''' + image_uid + '''\'
                                    WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                    WHERE game_code=\'''' + game_code + '''\')
                                    AND round_number = \'''' + round_number + '''\'
                                    '''
            updated_round = execute(write_to_round_query, "post", conn)
            # print("Image info written to db: ", updated_round)
            if updated_round["code"] == 281:
                response["message2"] = "281, Round updated."
                return response, 200
        except:
            raise BadRequest("Post image in round request failed")
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
            # print("Received:", data)
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
            # print("caption info: ", caption)
            if caption["code"] == 281:
                response["message"] = "281, Caption for the user updated."

                no_caption_submitted_query = '''
                                            SELECT count(round_user_uid) AS NoCaptionSubmitted
                                            FROM captions.round
                                            WHERE round_game_uid = (SELECT game_uid FROM captions.game 
                                                                    WHERE game_code = \'''' + game_code + '''\') AND
                                                round_number = \'''' + round_number + '''\' AND
                                                caption IS NULL
                                            '''
                no_caption = execute(no_caption_submitted_query, "get", conn)
                # print("no caption info: ", no_caption["result"][0]["NoCaptionSubmitted"])
                response["no_caption_submitted"] = no_caption["result"][0]["NoCaptionSubmitted"]

                return response, 200
        except:
            raise BadRequest("submit caption Request failed")
        finally:
            disconnect(conn)


class getPlayersRemainingToSubmitCaption(Resource):
    def get(self, game_code, round_number):
        # print("requested game_code: ", game_code)
        # print("requested round_number:", round_number)
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

            # print("players info: ", players_info)
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
        # print("requested game_code: ", game_code)
        # print("requested round_number:", round_number)
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

            # print("players info: ", captions)
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
            # print("Received:", data)
            caption = data["caption"]
            # print("caption info: ", caption)
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
                # print("no vote info: ", novote)
                if novote["code"] == 281:
                    response["message"] = "281, No Vote Recorded."
                    # return response, 200

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
                # print("caption info: ", caption)
                if caption["code"] == 281:
                    response["message"] = "281, Vote Recorded."
                    # return response, 200

            get_players_count_query = '''
                            SELECT 
                                IF(COUNT(votes)-SUM(votes)-SUM(novotes) < 0,0, COUNT(votes)-SUM(votes)-SUM(novotes)) AS notvoted FROM captions.round
                            INNER JOIN captions.user
                            ON captions.round.round_user_uid=captions.user.user_uid
                            WHERE round_game_uid = (SELECT game_uid FROM captions.game
                            WHERE game_code=\'''' + game_code + '''\')
                            AND round_number=\'''' + round_number + '''\'
                            '''
            players_count = execute(get_players_count_query, "get", conn)

            # print("players info: ", players_count)
            # print("players info code: ", players_count["code"])
            if players_count["code"] == 280:

                response["message1"] = "280, get players who haven't submitted votes request successful."
                response["players_count"] = players_count["result"][0]["notvoted"]
                return response, 200


                    
        except:
            raise BadRequest("Voting failed")
        finally:
            disconnect(conn)


class getPlayersWhoHaventVoted(Resource):
    def get(self, game_code, round_number):
        # print("requested game_code: ", game_code)
        # print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            conn = connect()
            get_players_count_query = '''
                            SELECT 
                                IF(COUNT(votes)-SUM(votes)-SUM(novotes) < 0,0, COUNT(votes)-SUM(votes)-SUM(novotes)) AS notvoted FROM captions.round
                            INNER JOIN captions.user
                            ON captions.round.round_user_uid=captions.user.user_uid
                            WHERE round_game_uid = (SELECT game_uid FROM captions.game
                            WHERE game_code=\'''' + game_code + '''\')
                            AND round_number=\'''' + round_number + '''\'
                            '''
            players_count = execute(get_players_count_query, "get", conn)

            # print("players info: ", players_count)
            # print("players info code: ", players_count["code"])
            if players_count["code"] == 280:

                response["message1"] = "280, get players who haven't submitted votes request successful."
                response["players_count"] = players_count["result"][0]["notvoted"]
                return response, 200
        except:
            raise BadRequest("Get players who haven't submitted votes request failed")
        finally:
            disconnect(conn)


class getScores(Resource):
    def get(self, game_code, round_number):
        print("In getScores")
        # print("requested game_code: ", game_code)
        # response = {}
        # items = {}
        # try:
        #     conn = connect()

        #     get_game_score = '''
        #                     SELECT captions.round.round_user_uid, captions.user.user_alias, SUM(score) as game_score
        #                     FROM captions.round
        #                     INNER JOIN captions.user
        #                     ON captions.round.round_user_uid=captions.user.user_uid
        #                     WHERE round_game_uid = (
        #                         SELECT game_uid FROM captions.game
        #                         WHERE game_code=\'''' + game_code + '''\')
        #                     GROUP BY round_user_uid;
        #                     '''
        #     game_score = execute(get_game_score, "get", conn)
        #     # print("game_score_info:", game_score)
        #     if game_score["code"] == 280:
        #             response["message"] = "280, getScores request successful."
        #             response["game score"] = game_score["result"]
        #             return response, 200
        # except:
        #     raise BadRequest("Get scores request failed")
        # finally:
        #     disconnect(conn)
        # print("requested game_code: ", game_code)
        # print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            print("In Try")
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
                                captions.round.caption, captions.round.votes, captions.round.score, captions.round.round_image_uid
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
            print("In except")
            raise BadRequest("Get scoreboard request failed")
        finally:
            disconnect(conn)


class getScoreBoard(Resource):
    print("in getScoreBoard")
    def get(self, game_code, round_number):
        # print("requested game_code: ", game_code)
        # print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            conn = connect()

            # INCORPORATING updateScores ENDPOINT
            get_scoring = '''
                            SELECT scoring_scheme FROM captions.game
                            WHERE game_code=\'''' + game_code + '''\'
                            '''
            scoring_info = execute(get_scoring, "get", conn)
            # print("scoring info: ", scoring_info)
            if scoring_info["code"] == 280:
                scoring = scoring_info["result"][0]["scoring_scheme"]
                # print(scoring)
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
                    # print("winner_info:", winner)
                    if winner["code"] == 280:
                        highest_votes = str(winner["result"][0]["MAX(votes)"])
                        # print("highest votes: ", highest_votes, type(highest_votes))
                        get_second_highest_votes = '''
                                                    SELECT votes FROM captions.round 
                                                    WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                                        WHERE game_code=\'''' + game_code + '''\') 
                                                    AND round_number=\'''' + round_number + '''\'
                                                    AND votes<\'''' + highest_votes + '''\'
                                                    ORDER BY votes DESC
                                                    '''
                        runner_up = execute(get_second_highest_votes, "get", conn)
                        # print("runner-up info:", runner_up)
                        if runner_up["code"] == 280:
                            second_highest_votes = str(runner_up["result"][0]["votes"]) if runner_up["result"] and \
                                                                                           runner_up["result"][0][
                                                                                               "votes"] > 0 else "-1"
                            # print("second highest votes: ", second_highest_votes, type(second_highest_votes))
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
                                # return response, 200
                elif scoring == "V" or scoring == 'v':
                    update_score_by_votes_query = '''
                                                    UPDATE captions.round
                                                    SET score = 2 * votes
                                                    WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                                            WHERE game_code=\'''' + game_code + '''\')
                                                    AND round_number=\'''' + round_number + '''\'
                                                    '''
                    update_scores = execute(update_score_by_votes_query, "post", conn)
                    # print("update_score_info: ", update_scores)
                    if update_scores["code"] == 281:
                        response["message"] = "281, update scoreboard by votes request successful."
                        # return response, 200




            get_game_score = '''
                            SELECT round_user_uid, SUM(score) as game_score FROM captions.round
                            WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                WHERE game_code=\'''' + game_code + '''\')
                            GROUP BY round_user_uid
                            '''
            game_score = execute(get_game_score, "get", conn)
            # print("game_score_info:", game_score)
            if game_score["code"] == 280:
                get_score_query = '''
                                SELECT captions.round.round_user_uid, captions.user.user_alias,
                                captions.round.caption, captions.round.votes, captions.round.score, captions.round.round_image_uid
                                FROM captions.round
                                INNER JOIN captions.user
                                ON captions.round.round_user_uid=captions.user.user_uid
                                WHERE round_game_uid = (SELECT game_uid FROM captions.game
                                WHERE game_code=\'''' + game_code + '''\')
                                AND round_number=\'''' + round_number + '''\'
                                '''
                scoreboard = execute(get_score_query, "get", conn)
                # print("score info: ", scoreboard)
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
        # print("requested game_code: ", game_code)
        # print("requested round_number:", round_number)
        response = {}
        items = {}
        try:
            conn = connect()
            get_scoring = '''
                            SELECT scoring_scheme FROM captions.game
                            WHERE game_code=\'''' + game_code + '''\'
                            '''
            scoring_info = execute(get_scoring, "get", conn)
            # print("scoring info: ", scoring_info)
            if scoring_info["code"] == 280:
                scoring = scoring_info["result"][0]["scoring_scheme"]
                # print(scoring)
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
                    # print("winner_info:", winner)
                    if winner["code"] == 280:
                        highest_votes = str(winner["result"][0]["MAX(votes)"])
                        # print("highest votes: ", highest_votes, type(highest_votes))
                        get_second_highest_votes = '''
                                                    SELECT votes FROM captions.round 
                                                    WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                                        WHERE game_code=\'''' + game_code + '''\') 
                                                    AND round_number=\'''' + round_number + '''\'
                                                    AND votes<\'''' + highest_votes + '''\'
                                                    ORDER BY votes DESC
                                                    '''
                        runner_up = execute(get_second_highest_votes, "get", conn)
                        # print("runner-up info:", runner_up)
                        if runner_up["code"] == 280:
                            second_highest_votes = str(runner_up["result"][0]["votes"]) if runner_up["result"] and \
                                                                                           runner_up["result"][0][
                                                                                               "votes"] > 0 else "-1"
                            # print("second highest votes: ", second_highest_votes, type(second_highest_votes))
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
                    # print("update_score_info: ", update_scores)
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
            # print("Received:", data)
            round_number = data["round_number"]
            game_code = data["game_code"]
            new_round_number = str(int(round_number) + 1)
            # print("Next Round Number:", new_round_number)

            players_query = '''
                                SELECT round_user_uid, round_deck_uid FROM captions.round
                                WHERE round_game_uid = (SELECT game_uid FROM captions.game 
                                WHERE game_code=\'''' + game_code + '''\')
                                AND round_number=\'''' + round_number + '''\'
                                '''
            players = execute(players_query, "get", conn)
            # print("players count:", players)
            if players["code"] == 280:
                num_players = len(players["result"])
                # print("players in the game: ", num_players)
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
                    # print("next_round info: ", next_round)
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



# INSERT ROWS IN Rounds TABLE FOR EACH PLAYER FOR EACH ROUND 
class createRounds(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            game_code = data["game_code"]
            imageURLs = data["images"]
            # deck_uid = data["deck_uid"]
            # user_uid = data["user_uid"]
            # num_rounds = data["rounds"]
            # time_limit = data["round_time"]
            # scoring = data["scoring_scheme"]
            # print(game_code)
            # print("all images: ", imageURLs)
            # print("individual image: ", imageURLs[0])
            image_count = len(imageURLs)
            # print("Number of images received: ", image_count)
            # print(len(data))
            
            i = 0

            # NEED NUMBER OF ROUNDS, DECK UID AND GAME UID
            game_query = '''
                    SELECT *
                    FROM captions.game
                    WHERE game_code = \'''' + game_code + '''\';
                    '''
            game_data = execute(game_query, "get", conn)
            # print("game data:", game_data["result"])
            num_rounds = game_data["result"][i]["num_rounds"]
            # print("number of rounds:",  num_rounds )
            deck_uid = game_data["result"][i]["game_deck"]
            # print("game deck:", deck_uid )
            game_uid = game_data["result"][i]["game_uid"]
            # print("game UID:", game_uid )

            if image_count != num_rounds:
                # print("image count mismatch")
                response["message"] = "Image count mismatch."
                return response

            # NEED NUMBER OF PLAYERS AND PLAYER UID
            player_query = '''
                    SELECT DISTINCT round_user_uid
                    FROM captions.round
                    WHERE round_game_uid = \'''' + game_uid + '''\';
                    '''
            player_data = execute(player_query, "get", conn)
            # print("player data:", player_data["result"])
            num_players = len(player_data["result"])
            # print("number of players: ", num_players)

            p = 0
            for p in range(num_players):
                user_uid = player_data["result"][p]["round_user_uid"]
                # print(user_uid)


            # CREATE ROWS FOR EACH PLAYER, EACH ROUND
            p = 0
            for n in range(num_rounds):
                for p in range(num_players):
                    # print("In loop: ", n, p)
                    new_round_uid = get_new_roundUID(conn)
                    # print(new_round_uid)
                    user_uid = player_data["result"][p]["round_user_uid"]
                    # print(user_uid)
                    round = n + 1
                    image = imageURLs[n]
                    # print(new_round_uid, user_uid, game_uid, round, deck_uid)

                    if round == 1:
                        add_user_to_next_round_query = '''
                                                    UPDATE captions.round
                                                    SET 
                                                        round_deck_uid= \'''' + deck_uid + '''\',
                                                        round_image_uid = \'''' + image + '''\'
                                                    WHERE
                                                        round_user_uid= \'''' + user_uid + '''\' AND
                                                        round_game_uid= \'''' + game_uid + '''\';
                                                    '''
                    else:
                        add_user_to_next_round_query = '''
                                                    INSERT INTO captions.round
                                                    SET round_uid = \'''' + new_round_uid + '''\',
                                                    round_user_uid= \'''' + user_uid + '''\',
                                                    round_game_uid= \'''' + game_uid + '''\',
                                                    round_number= \'''' + str(round) + '''\', 
                                                    round_deck_uid= \'''' + deck_uid + '''\',
                                                    round_image_uid = \'''' + image + '''\',
                                                    votes=0,
                                                    score=0
                                                    '''
                    next_round = execute(add_user_to_next_round_query, "post", conn)
                    # print("next_round info: ", next_round)
                    if next_round["code"] == 281:
                        continue
                    else:
                        response["message"] = "Could not add user to the next round."
                        response["user_uid"] = user_uid
                        return response, 200
                continue

            # GET FIRST ROUND IMAGE
            first_image_query = '''
                            SELECT DISTINCT round_image_uid 
                            FROM captions.round
                            WHERE
                                round_game_uid = \'''' + game_uid + '''\' AND
                                round_number = '1';
                            '''
            first_image_data = execute(first_image_query, "get", conn)
            # print("first image URL:", first_image_data["result"])

            response["message"] = "281, Next Round successfully created."
            response["image"] = first_image_data["result"][0]["round_image_uid"]
            return response, 200

        except:
            raise BadRequest("Create Game Request failed")
        finally:
            disconnect(conn)


class getNextImage(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)
            round_number = data["round_number"]
            game_code = data["game_code"]

            image_query = '''
                            SELECT DISTINCT round_image_uid 
                            FROM captions.round
                            WHERE
                                round_game_uid = (SELECT game_uid FROM captions.game 
                                                    WHERE game_code=\'''' + game_code + '''\')
                                AND round_number=\'''' + round_number + '''\';
                        '''
            image = execute(image_query, "get", conn)
            # print("image URL:", image["result"])
            response["image"] = image["result"][0]["round_image_uid"]
            return response, 200

        except:
            raise BadRequest("create next round Request failed")
        finally:
            disconnect(conn)


class endGame(Resource):
    def get(self, game_code):
        # print("game code: ", game_code)
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
                # print("num_rounds:", len(game_info["result"]))
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
            # print("receiving_data")
            image_title = request.form.get("image_title")
            # print("image_title: ", image_title)
            image_cost = request.form.get("image_cost")
            # print("image_cost: ", image_cost)
            image_description = request.form.get("image_description")
            # print("image_description: ", image_description)
            image = request.files.get("image_file")
            # print("image: ", image)

            #deck name
            deck_name = request.form.get("deck_name")
            # print("deck_name: ", deck_name)

            new_image_uid = get_new_imageUID(conn)
            # print("new_image_uid: ", new_image_uid)

            key = "caption_image/" + str(new_image_uid)
            # print("image_key: ", key)

            image_url = helper_upload_user_img(image, key)
            # print("image_url: ", image_url)

            add_image_query = '''
                            INSERT INTO captions.image
                            SET image_uid = \'''' + new_image_uid + '''\',
                                image_title = \'''' + image_title + '''\',
                                image_url = \'''' + image_url + '''\',
                                image_cost = \'''' + image_cost + '''\',
                                image_description = \'''' + image_description + '''\'                    
                            ''' 
            image_response = execute(add_image_query, "post", conn)
            # print("image_response: ", image_response)


            get_image_uids_query = '''
                            SELECT deck_image_uids
                            FROM captions.deck    
                            WHERE deck_title =\'''' + deck_name + '''\'                
                            '''
            deck_response = execute(get_image_uids_query, "get", conn)
            # print("deck_response: ", deck_response)

            uid_string = deck_response["result"][0]["deck_image_uids"]
            # print("The following is the uid string", uid_string)

            if(uid_string == "()"): #is this how we check for string deep equality in python?
                uid_string = "(\"" + new_image_uid + "\")"
            else:
                uid_string = uid_string[:-1] + ", \"" + new_image_uid + "\")"

            # print("The following is the new uid string", uid_string)



            add_to_image_uids_query = '''
                                            UPDATE captions.deck
                                            SET deck_image_uids = \'''' + uid_string + '''\' 
                                            WHERE deck_title =\'''' + deck_name + '''\' 
                                            '''
            update_deck_response = execute(add_to_image_uids_query, "post", conn)
            # print("update_deck_response: ", update_deck_response)

            if image_response["code"] == 281:
                response["message"] = "281, image successfully added to the database."
                return response, 200
        except:
            raise BadRequest("upload image Request failed")
        finally:
            disconnect(conn)


class CheckEmailValidationCode(Resource):
    def post(self):
        response = {}
        items = {}
        cus_id = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print("Received JSON data: ", data)

            user_uid = data["user_uid"]
            code = data["code"]
            # print("user uid = ", user_uid, ", code = ", code)

            get_verification_code_query = '''
                            SELECT email_validated FROM captions.user WHERE user_uid=\'''' + user_uid + '''\'
                            '''

            validation = execute(get_verification_code_query, "get", conn)
            # print("validation info: ", validation)

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
            # print("first element of list", validation["result"][0])
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
                # print("User code has been updated to TRUE")
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




class testHarvard(Resource):
    def get(self):
        # print("beginning testHarvard")
        response = {}
        items = {}
        try:
            conn = connect()
            # print("connection established")

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


class addFeedback(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()
            data = request.get_json()
            name = data["name"]
            email = data["email"]
            feedback = data["feedback"]
            query = '''
                    UPDATE captions.user
                    SET feedback = CONCAT_WS(\',\', feedback, \'''' + feedback + '''\')
                    WHERE user_email = \'''' + email + '''\';
                    '''
            execute(query, "post", conn)
            msg = Message(
                "Feedback by " + name,
                sender = "support@capshnz.com",
                recipients = ["pmarathay@gmail.com"],
                body = feedback
            )
            mail.send(msg)
        except Exception as e:
            raise InternalServerError("An unknown error occurred") from e
        finally:
            disconnect(conn)
        return response, 200
    

class summary(Resource):
    def get(self):
        response = {}
        try:
            conn = connect()
            game_uid = request.args.get("gameUID")
            query = '''
                    SELECT r1.*
                    FROM captions.round r1
                        INNER JOIN (
                            SELECT round_game_uid, 
                                round_number, 
                                MAX(score) AS max_score
                            FROM captions.round
                            WHERE round_game_uid = \'''' + game_uid + '''\'
                            GROUP BY round_number
                        ) r2 ON r1.round_game_uid = r2.round_game_uid 
                        AND r1.round_number = r2.round_number 
                        AND r1.score = r2.max_score
                        GROUP BY r1.round_uid, r1.round_number
                        ORDER BY r1.round_number;
                    '''
            captions = execute(query, "get", conn)["result"]
            round_number_set = set()
            for caption in captions:
                if caption["round_number"] in round_number_set:
                    del caption["round_number"]
                    del caption["round_image_uid"]
                else:
                    round_number_set.add(caption["round_number"])
            response["captions"] = captions
        except Exception as e:
            raise InternalServerError("An unknown error occurred") from e
        finally:
            disconnect(conn)
        return response, 200


class summaryEmail(Resource):
    def post(self):
        # print("In Summary Email")
        try:
            conn = connect()
            response = {}
            data = request.get_json()
            # print("Data Received: ", data)
            game_uid = data["gameUID"]
            host_email = data["email"]
            recipients = [host_email, 'pmarathay@yahoo.com']


            # Get participant emails
            emailQuery = '''
                    SELECT -- *
                        DISTINCT round_game_uid, round_user_uid, user_name, user_email
                    FROM captions.round
                    LEFT JOIN captions.user ON round_user_uid = user_uid
                    -- WHERE round_game_uid = "200-004165"
                    WHERE round_game_uid = \'''' + game_uid + '''\'
                    '''
            emails = execute(emailQuery, "get", conn)["result"]
            # print(emails)

            # Extract emails, add to recipients, ensure uniqueness, and format as a list
            recipients = list(set(recipients + [player['user_email'] for player in emails]))

            # Print the final list
            # print(recipients)



            # Get Game Images and Winning Captions
            query = '''
                    SELECT r1.*
                    FROM captions.round r1
                        INNER JOIN (
                            SELECT round_game_uid, 
                                round_number, 
                                MAX(score) AS max_score
                            FROM captions.round
                            WHERE round_game_uid = \'''' + game_uid + '''\'
                            GROUP BY round_number
                        ) r2 ON r1.round_game_uid = r2.round_game_uid 
                        AND r1.round_number = r2.round_number 
                        AND r1.score = r2.max_score
                        GROUP BY r1.round_uid, r1.round_number
                        ORDER BY r1.round_number;
                    '''
            captions = execute(query, "get", conn)["result"]
            content = ""
            round_number_set = set()
            for caption in captions:
                round_img = "" 
                if caption["round_number"] not in round_number_set:
                    round_img = """
                        <h3>Round: """ + str(caption["round_number"]) + """</h3>
                        <img src= """ + caption["round_image_uid"] + """ style="display:block;margin-left:auto;margin-right:auto;width:50%;height:50%;">
                    """    
                content = content + """
                    <div style="text-align:center;display:block;margin-left:auto;margin-right:auto;">
                        """ + round_img + """
                        <h4>Caption: """ + caption["caption"] + """</h4>
                    </div>
                """
                round_number_set.add(caption["round_number"])

            msg_html = """
                <!DOCTYPE html>
                <html>
                    <body style="align:center">
                        <div style="padding:20px 0px">
                            <h2>Winning captions</h2>
                            """ + content + """
                        </div>
                    </body>
                </html>
            """

            # Send Email
            msg = Message(
                "Capshnz summary",
                sender = "support@capshnz.com",
                # recipients = [host_email,'pmarathay@yahoo.com'],
                recipients = recipients,
                html = msg_html
            )
            # print("message: ", msg)

            mail.send(msg)
            response["Confrimation"] = 'email sent'
            response["Recipients"] = recipients

        except Exception as e:
            response["Confrimation"] = 'email failure'
            # print(recipients)
            response["Recipients"] = recipients
            raise InternalServerError("An unknown error occurred") from e
        finally:
            disconnect(conn)

        return response, 200



class CNNWebScrape(Resource):
     def get(self):
        # print("in cnn web scraper")
        response={}
        try:
            conn = connect()
            # query = '''
            #     SELECT game_uid FROM captions.game
            #     WHERE game_code = \'''' + game_code + '''\';
            #     '''
            # query  = 'SELECT * FROM cnn_images'
            query = 'SELECT id, article_link,date, week_no, year, thumbnail_link, title FROM cnn_images'
            items = execute(query, "get", conn)
            # print("items: ", items)
            if items["code"] == 280:
                response["message"] = "Fetch successful"
                response["data"] = items["result"]
            else:
                response["message"] = "Fetch was unsuccessful"

        except:
            raise BadRequest("CNN Image fetch failed")
        finally:
            disconnect(conn)
        return response

@app.before_request
def before_request():
    g.start_time = time.time()
    # client_ip = request.remote_addr
    # print(f"Incoming request from IP: {client_ip} to {request.path} with method {request.method}")

@app.after_request
def after_request(response):
    # Calculate request latency
    latency = time.time() - g.start_time

    # Get request details
    endpoint = request.path
    method = request.method
    status_code = response.status_code
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    user_agent = request.headers.get('User-Agent', 'Unknown')

    # Log details
    logger.info(
        f"IP: {client_ip}, Endpoint: {endpoint}, Method: {method}, "
        f"Status: {status_code}, Latency: {latency:.3f}s, User-Agent: {user_agent}"
    )

    # Update Prometheus metrics
    REQUEST_COUNTER.labels(method=method, endpoint=endpoint, status_code=status_code, client_ip=client_ip).inc()
    LATENCY_SUMMARY.labels(endpoint=endpoint).observe(latency)

    return response
    # endpoint = request.path
    # status_code = response.status_code
    # client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    # REQUEST_COUNTER.labels(endpoint=endpoint, status_code=status_code, client_ip=client_ip).inc()
    # # print(f"Request from IP: {client_ip}, Endpoint: {endpoint}, Status: {status_code}")
    # return response

class Metrics(Resource):
    def get(self):
        return Response(generate_latest(), mimetype="text/plain")
    
# -- DEFINE APIS -------------------------------------------------------------------------------


# Define API routes
api.add_resource(createGame, "/api/v2/createGame")
api.add_resource(checkGame, "/api/v2/checkGame/<string:game_code>")
# api.add_resource(createUser, "/api/v2/createUser")
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
# api.add_resource(getImageInRound, "/api/v2/getImageInRound/<string:game_code>,<string:round_number>")


api.add_resource(createRounds, "/api/v2/createRounds")
api.add_resource(getNextImage, "/api/v2/getNextImage")


api.add_resource(getRoundImage, "/api/v2/getRoundImage/<string:game_code>,<string:round_number>")
api.add_resource(postRoundImage, "/api/v2/postRoundImage")
# api.add_resource(roundImage, "/api/v2/roundImage/<string:game_code>,<string:round_number>")


api.add_resource(submitCaption, "/api/v2/submitCaption")
api.add_resource(getPlayersRemainingToSubmitCaption,
                 "/api/v2/getPlayersRemainingToSubmitCaption/<string:game_code>,<string:round_number>")
api.add_resource(getAllSubmittedCaptions, "/api/v2/getAllSubmittedCaptions/<string:game_code>,<string:round_number>")
api.add_resource(voteCaption, "/api/v2/voteCaption")
api.add_resource(getPlayersWhoHaventVoted, "/api/v2/getPlayersWhoHaventVoted/<string:game_code>,<string:round_number>")
api.add_resource(createNextRound, "/api/v2/createNextRound")
api.add_resource(updateScores, "/api/v2/updateScores/<string:game_code>,<string:round_number>")
api.add_resource(getScoreBoard, "/api/v2/getScoreBoard/<string:game_code>,<string:round_number>")
api.add_resource(getScores, "/api/v2/getScores/<string:game_code>,<string:round_number>")
api.add_resource(startPlaying, "/api/v2/startPlaying/<string:game_code>,<string:round_number>")
api.add_resource(getImageForPlayers, "/api/v2/getImageForPlayers/<string:game_code>,<string:round_number>")
api.add_resource(endGame, "/api/v2/endGame/<string:game_code>")
api.add_resource(getUniqueImageInRound, "/api/v2/getUniqueImageInRound/<string:game_code>,<string:round_number>")
api.add_resource(uploadImage, "/api/v2/uploadImage")
api.add_resource(SendError, "/api/v2/sendError/<string:code1>*<string:code2>")
# api.add_resource(CheckEmailValidated, "/api/v2/checkEmailValidated")
api.add_resource(CheckEmailValidationCode, "/api/v2/checkEmailValidationCode")
api.add_resource(testHarvard, "/api/v2/testHarvard")
api.add_resource(addUserByEmail, "/api/v2/addUserByEmail")
api.add_resource(addFeedback, "/api/v2/addFeedback")
api.add_resource(summary, "/api/v2/summary")
api.add_resource(summaryEmail, "/api/v2/summaryEmail")

api.add_resource(Metrics, "/metrics")

## webscrape api
api.add_resource(CNNWebScrape , "/api/v2/cnn_webscrape")
# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4030)
