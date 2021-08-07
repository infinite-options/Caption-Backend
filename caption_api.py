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

#use below for local testing
#stripe.api_key = ""sk_test_51J0UzOLGBFAvIBPFAm7Y5XGQ5APR...WTenXV4Q9ANpztS7Y7ghtwb007quqRPZ3"" 


CORS(app)

# --------------- Mail Variables ------------------
app.config["MAIL_USERNAME"] = os.environ.get("EMAIL")
app.config["MAIL_PASSWORD"] = os.environ.get("PASSWORD")
# app.config['MAIL_USERNAME'] = ''
# app.config['MAIL_PASSWORD'] = ''

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
def getNow(): return datetime.strftime(datetime.now(),"%Y-%m-%d %H:%M:%S")

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


# s3 = boto3.client('s3')

# aws s3 bucket where the image is stored
# BUCKET_NAME = os.environ.get('MEAL_IMAGES_BUCKET')
# BUCKET_NAME = 'servingnow'
# allowed extensions for uploading a profile photo file
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg"])



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
            if cmd is "get":
                result = cur.fetchall()
                response["message"] = "Successfully executed SQL query."
                # Return status code of 280 for successful GET request
                response["code"] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response["result"] = result
            elif cmd in "post":
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

def get_new_paymentID(conn):
    newPaymentQuery = execute("CALL new_payment_uid", 'get', conn)
    if newPaymentQuery['code'] == 280:
        return newPaymentQuery['result'][0]['new_id']
    return "Could not generate new payment ID", 500

def get_new_contactUID(conn):
    newPurchaseQuery = execute("CALL io.new_contact_uid()", 'get', conn)
    if newPurchaseQuery['code'] == 280:
        return newPurchaseQuery['result'][0]['new_id']
    return "Could not generate new contact UID", 500

def get_new_appointmentUID(conn):
    newAppointmentQuery = execute("CALL io.new_appointment_uid()", 'get', conn)
    if newAppointmentQuery['code'] == 280:
        return newAppointmentQuery['result'][0]['new_id']
    return "Could not generate new appointment UID", 500


# --Caption Queries start here -------------------------------------------------------------------------------


class createGame(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            num_rounds = data["rounds"]
            time_limit = data["round_time"]
            print(data) 

            new_game_uid = get_new_gameUID(conn)
            print(new_game_uid)
            print(getNow())

            game_code = random.randint(10000000, 99999999)
            print(game_code)
            
            query =  '''
                INSERT INTO captions.game
                SET game_uid = \'''' + new_game_uid + '''\',
                    game_created_at = \'''' + getNow() + '''\',
                    game_code = \'''' + str(game_code) + '''\',
                    num_rounds = \'''' + num_rounds + '''\',
                    time_limit = \'''' + time_limit + '''\',
                    game_host_uid = NULL
                '''
            
            items = execute(query, "post", conn)
            print("items: ", items)
            if items["code"] == 281:
                response["message"] = "Create Game successful"
                response["game_code"] = str(game_code)
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
            
            query =  '''
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


class createUser(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            user_name   = data["user_name"]
            user_alias  = data["user_alias"]
            user_email  = data["user_email"]
            user_zip    = data["user_zip"]
            # print(data)

            new_user_uid = get_new_userUID(conn)
            print(new_user_uid)
            print(getNow())

            query =  '''
                INSERT INTO captions.user
                SET user_uid = \'''' + new_user_uid + '''\',
                    user_created_at = \'''' + getNow() + '''\',
                    user_name = \'''' + user_name + '''\', 
                    user_alias = \'''' + user_alias + '''\', 
                    user_email = \'''' + user_email + '''\', 
                    user_zip_code = \'''' + user_zip + '''\',
                    user_purchases = NULL
                '''

            items = execute(query, "post", conn)
            print("items: ", items)
            if items["code"] == 281:
                response["message"] = "Create User successful"
                return response, 200
        except:
            raise BadRequest("Create User Request failed")
        finally:
            disconnect(conn)


class createNewGame(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            # User/Host data
            user_name   = data["user_name"]
            user_alias  = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
            user_email  = data["user_email"]
            user_zip    = data["user_zip"]
            # print(data)

            # Game data
            new_game_uid = get_new_gameUID(conn)
            # print(new_game_uid)
            num_rounds = "6"    # Default number of rounds
            time_limit = "00:00:10"  # Default time-limit
            game_code = random.randint(10000000, 99999999)
            print(game_code)

            # check if the user is already present
            check_query = '''SELECT user_uid FROM captions.user 
                                WHERE user_email= \'''' + user_email + '''\' 
                                AND user_zip_code =\'''' + user_zip + '''\'
                                '''
            user = execute(check_query, "get", conn)
            print(user)
            new_user_uid = ""
            if len(user["result"]) > 0:
                # if user is already present
                new_user_uid = user["result"][0]["user_uid"]
                print(new_user_uid)
            else:
                new_user_uid = get_new_userUID(conn)
                # print(new_user_uid)
                # print(getNow())
                query ='''
                    INSERT INTO captions.user
                    SET user_uid = \'''' + new_user_uid + '''\',
                        user_created_at = \'''' + getNow() + '''\',
                        user_name = \'''' + user_name + '''\', 
                        user_alias = \'''' + user_alias + '''\', 
                        user_email = \'''' + user_email + '''\', 
                        user_zip_code = \'''' + user_zip + '''\',
                        user_purchases = NULL
                    '''

                items = execute(query, "post", conn)
                print("items: ", items)

            if user["code"] == 280 or items["code"] == 281:
                create_game_query = '''
                INSERT INTO captions.game
                SET game_uid = \'''' + new_game_uid + '''\',
                    game_created_at = \'''' + getNow() + '''\',
                    game_code = \'''' + str(game_code) + '''\',
                    num_rounds = \'''' + num_rounds + '''\',
                    time_limit = \'''' + time_limit + '''\',
                    game_host_uid = \'''' + new_user_uid + '''\'
                    '''
                game_items = execute(create_game_query, "post", conn)
                print("game_items: ", game_items)
                if game_items["code"] == 281:
                    response["game_message"] = "Create New Game successful"
                    new_round_uid = get_new_roundUID(conn)
                    add_user_to_round_query = '''
                                            INSERT INTO captions.round
                                            SET round_uid = \'''' + new_round_uid + '''\',
                                            round_game_uid = \'''' + new_game_uid + '''\',
                                            round_user_uid = \'''' + new_user_uid + '''\',
                                            round_number = 1,
                                            round_deck_uid = NULL,
                                            round_image_uid = NULL ,
                                            caption = NULL,
                                            votes = NULL,
                                            score = NULL, 
                                            round_started_at = NULL'''
                    add_user = execute(add_user_to_round_query, "post", conn)
                    print("add_user_response: ", add_user)
                    if add_user["code"] == 281:
                        response["round_message"] = "Host added to the game."
                        response["game_code"] = str(game_code)
                        response["host_id"] = new_user_uid
                        response["host_alias"] = user_alias
                        return response, 200

        except:
            raise BadRequest("Create New Game Request failed")
        finally:
            disconnect(conn)


class joinGame(Resource):
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
            user_name   = data["user_name"]
            user_alias  = data["user_alias"] if data.get("user_alias") is not None else data["user_name"].split[0]
            user_email  = data["user_email"]
            user_zip    = data["user_zip"]
            game_code   = data["game_code"]

            # get the game_uid from the game code
            check_game_code_query = '''
                                    SELECT * FROM captions.game
                                    WHERE game_code=\'''' + game_code + '''\'
                                    '''
            game_info = execute(check_game_code_query, "get", conn)
            print(game_info)
            if game_info["code"] == 280:
                game_uid = game_info["result"][0]["game_uid"]
                # game_created_at = game_info["result"][0]["game_created_at"]
                # game_code = game_info["result"][0]["game_code"]
                # num_rounds = game_info["result"][0]["num_rounds"]
                # time_limit = game_info["result"][0]["time_limit"]
                # game_host_uid = game_info["result"][0]["game_host_uid"]

                # check if the user is returning or new
                check_user_query = '''SELECT user_uid FROM captions.user 
                                WHERE user_email= \'''' + user_email + '''\' 
                                AND user_zip_code =\'''' + user_zip + '''\'
                                '''
                returning_user = execute(check_user_query, "get", conn)
                print("returning user: ", returning_user)
                user_uid = ""
                if len(returning_user["result"]) > 0:
                    # if user is already present
                    user_uid = returning_user["result"][0]["user_uid"]
                    print("returning user id:", user_uid)
                else:
                    user_uid = get_new_userUID(conn)
                    # print(new_user_uid)
                    # print(getNow())
                    add_new_user_query ='''
                                            INSERT INTO captions.user
                                            SET user_uid = \'''' + user_uid + '''\',
                                            user_created_at = \'''' + getNow() + '''\',
                                            user_name = \'''' + user_name + '''\', 
                                            user_alias = \'''' + user_alias + '''\', 
                                            user_email = \'''' + user_email + '''\', 
                                            user_zip_code = \'''' + user_zip + '''\',
                                            user_purchases = NULL
                                        '''

                    new_user = execute(add_new_user_query, "post", conn)
                    print("new user info: ", new_user)
                if returning_user["code"] == 280 or new_user["code"] == 281:
                    # add the user to round from the game id
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
                                            votes = NULL,
                                            score = NULL,
                                            round_started_at = NULL'''
                    add_user = execute(add_user_to_round_query, "post", conn)
                    print("add_user_response: ", add_user)
                    if add_user["code"] == 281:
                        response["message"] = "Player added to the game."
                        response["game_uid"] = game_uid
                        response["user_uid"] = user_uid
                        response["user_alias"] = user_alias
                        return response, 200
            else:
                response["warning"] = "Invalid game code."


        except:
            raise BadRequest("Join Game Request failed")
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
                                WHERE game_code=\'''' + game_code + '''\')
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
    def get(self):
        response = {}
        try:
            conn = connect()
            get_all_decks_query = '''
                                SELECT deck_uid, deck_title, deck_thumbnail_url, deck_description FROM captions.deck
                                '''
            decks = execute(get_all_decks_query, "get", conn)
            print("players info: ", decks)
            if decks["code"] == 280:
                response["message"] = "280, get available decks request successful."
                response["decks_info"] = decks["result"]

                return response, 200
        except:
            raise BadRequest("get available decks request failed")
        finally:
            disconnect(conn)

    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)
        except:
            raise BadRequest("Create deck Request failed")
        finally:
            disconnect(conn)


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
            round_number = data["round_number"]

            select_deck_query = '''
                                UPDATE captions.round 
                                SET round_deck_uid=\'''' + deck_uid + '''\'
                                WHERE round_game_uid=(SELECT game_uid FROM captions.game
                                WHERE game_code=\'''' + game_code + '''\') 
                                AND round_number=\'''' + round_number + '''\'
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


class gameTimer(Resource):
    def get(self, game_code):
        print("requested game_uid: ", game_code)
        response = {}
        items = {}
        try:
            conn = connect()
            # round_start_time = 0
            # round_duration = 0
            current_time = getNow()
            get_game_timer_info = '''
                                SELECT captions.round.round_started_at, captions.game.time_limit
                                FROM captions.round
                                JOIN captions.game
                                ON captions.round.round_game_uid = captions.game.game_uid
                                WHERE captions.game.game_code = \'''' + game_code + '''\'
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
            round_duration = time.strftime('%H:%M:%S', time.gmtime(int(seconds)))

            change_rounds_and_duration_query = '''
                                UPDATE captions.game 
                                SET num_rounds=\'''' + num_rounds + '''\',
                                time_limit=\'''' + round_duration + '''\' 
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

class getImageInRound(Resource):
    def get(self, game_code):
        print("requested game_uid: ", game_code)
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
                write_to_round_query = '''
                                    UPDATE captions.round
                                    SET round_image_uid=\'''' + image_uid + '''\'
                                    WHERE round_game_uid=(SELECT game_uid FROM captions.game 
                                    WHERE game_code=\'''' + game_code + '''\')
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
                            AND caption=NULL                         
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
            round_number = data["round_number"]
            game_code = data["game_code"]

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
                response["message"] = "281, Caption for the user updated."
                return response, 200
        except:
            raise BadRequest("submit caption Request failed")
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
                            SELECT COUNT(votes)-SUM(votes) FROM captions.round
                            INNER JOIN captions.user
                            ON captions.round.round_user_uid=captions.user.user_uid
                            WHERE round_game_uid = (SELECT game_uid FROM captions.game
                            WHERE game_code=\'''' + game_code + '''\')
                            AND round_number=\'''' + round_number + '''\'
                            '''
            players_count = execute(get_players_count_query, "get", conn)

            print("players info: ", players_count)
            if players_count["code"] == 280:
                response["message1"] = "280, get players who haven't submitted votes request successful."
                response["players_count"] = players_count["result"][0]["COUNT(votes)-SUM(votes)"]
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
            get_score_query = '''
                            SELECT captions.round.round_user_uid, captions.user.user_alias,
                            captions.round.caption, captions.round.votes, captions.round.score 
                            FROM captions.round
                            INNER JOIN captions.user 
                            ON captions.round.round_user_uid=captions.user.user_uid
                            WHERE round_game_uid = (SELECT game_uid FROM captions.game 
                            WHERE game_code=\'''' + game_code + '''\')
                            AND round_number=\'''' + round_number + '''\'
                            AND caption IS NOT NULL                         
                            '''
            scoreboard = execute(get_score_query, "get", conn)

            print("score info: ", scoreboard)
            if scoreboard["code"] == 280:
                response["message1"] = "280, get scoreboard request successful."
                response["players"] = scoreboard["result"]
                return response, 200
        except:
            raise BadRequest("Get scoreboard request failed")
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

            players_query = '''
                                SELECT round_user_uid FROM captions.round
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
                    add_user_to_next_round_query = '''
                                                    INSERT INTO captions.round
                                                    SET round_uid =\'''' + new_round_uid + '''\',
                                                    round_user_uid=\'''' + user_uid + '''\',
                                                    round_game_uid=(SELECT game_uid FROM captions.game
                                                    WHERE game_code=\'''' + game_code + '''\'),
                                                    round_number=\'''' + new_round_number + '''\'
                                                    '''
                    next_round = execute(add_user_to_next_round_query, "post", conn)
                    print("caption info: ", next_round)
                    if next_round["code"] == 281:
                        continue
                    else:
                        response["message"] = "Could not add user to the next round."
                        response["user_uid"] = user_uid
                        return response, 200
                response["message"] = "281, Next Round successfully created."
                return response, 200
        except:
            raise BadRequest("submit caption Request failed")
        finally:
            disconnect(conn)









# -- Examples of Other Queries start here -------------------------------------------------------------------------------


# AVAILABLE APPOINTMENTS
class AvailableAppointments(Resource):
    def get(self, date_value):
        print("\nInside Available Appointments")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block", date_value)

            # CALCULATE AVAILABLE TIME SLOTS
            query = """
                    -- FIND AVAILABLE TIME SLOTS - WORKS
                    SELECT -- *
                        DATE_FORMAT(ts_begin, '%T') AS start_time
                    FROM (
                        -- GET ALL TIME SLOTS
                        SELECT *,
                            TIME(ts.begin_datetime) AS ts_begin
                        FROM io.time_slots ts
                        -- LEFT JOIN WITH CURRENT APPOINTMENTS
                        LEFT JOIN (
                            SELECT * FROM io.appointments
                            WHERE appt_date = '""" + date_value + """') AS appt
                        ON TIME(ts.begin_datetime) = appt.appt_time
                        -- LEFT JOIN WITH AVAILABILITY
                        LEFT JOIN (
                            SELECT * FROM io.availability
                            WHERE date = '""" + date_value + """') AS avail
                        ON TIME(ts.begin_datetime) = avail.start_time_notavailable
                            OR (TIME(ts.begin_datetime) > avail.start_time_notavailable AND TIME(ts.end_datetime) <= ADDTIME(avail.end_time_notavailable,"0:29"))
                        -- LEFT JOIN WITH OPEN HOURS
                        LEFT JOIN (
                            SELECT * FROM nitya.days
                            WHERE dayofweek = DAYOFWEEK('""" + date_value + """')) AS openhrs
                        ON TIME(ts.begin_datetime) = openhrs.morning_start_time
                            OR (TIME(ts.begin_datetime) > openhrs.morning_start_time AND TIME(ts.end_datetime) <= ADDTIME(openhrs.morning_end_time,"0:29"))
                            OR TIME(ts.begin_datetime) = openhrs.afternoon_start_time
                            OR (TIME(ts.begin_datetime) > openhrs.afternoon_start_time AND TIME(ts.end_datetime) <= ADDTIME(openhrs.afternoon_end_time,"0:29"))
                    ) AS ts_avail
                    WHERE ISNULL(ts_avail.appointment_uid)   -- NO APPOINTMENTS SCHEDULED
                        AND ISNULL(ts_avail.prac_avail_uid)  -- NO AVAILABILITY RESTRICTIONS
                        AND !ISNULL(days_uid);               -- OPEN HRS ONLY
                    """

            available_times = execute(query, 'get', conn)
            print("Available Times: ", str(available_times['result']))
            print("Number of time slots: ", len(available_times['result']))
            # print("Available Times: ", str(available_times['result'][0]["start_time"]))

            return available_times
        
        except:
            raise BadRequest('Available Time Request failed, please try again later.')
        finally:
            disconnect(conn)

# BOOK APPOINTMENT
class CreateAppointment(Resource):
    def post(self):
        print("in Create Appointment class")
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            print(data)
            # print to Received data to Terminal
            # print("Received:", data)
            name = data["name"]
            phone_no = data["phone"]
            datevalue = data["appt_date"]
            timevalue = data["appt_time"]
            email = data["email"]
            company_name = data["company"]
            company_url = data["url"]
            message = data["message"]

            print("name", name)
            print("phone_no", phone_no)
            print("date", datevalue)
            print("time", timevalue)
            print("email", email)
            print("company_name", company_name)
            print("company_name", company_url)
            print("message", message)

            new_appointment_uid = get_new_appointmentUID(conn)
            print("NewID = ", new_appointment_uid)
            print(getNow())

            query =  '''
                INSERT INTO io.appointments
                SET appointment_uid = \'''' + new_appointment_uid + '''\',
                    appt_created_at = \'''' + getNow() + '''\',
                    name = \'''' + name + '''\',
                    phone_no = \'''' + phone_no + '''\',
                    appt_date = \'''' + datevalue + '''\',
                    appt_time = \'''' + timevalue + '''\',
                    email = \'''' + email + '''\',
                    company = \'''' + company_name + '''\',
                    url = \'''' + company_url + '''\',
                    message = \'''' + message + '''\'
                '''

            items = execute(query, "post", conn)
            print("items: ", items)
            if items["code"] == 281:
                response["message"] = "Appointments Post successful"
                return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

        # ENDPOINT AND JSON OBJECT THAT WORKS
        # http://localhost:4000/api/v2/createappointment

# ADD CONTACT
class AddContact(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            fname = data["first_name"]
            lname = data["last_name"]
            email = data["email"]
            phone = data["phone"]
            subject = data["subject"]
            print(data)

            new_contact_uid = get_new_contactUID(conn)
            print(new_contact_uid)
            print(getNow())

            
            query =  '''
                INSERT INTO io.contact
                SET contact_uid = \'''' + new_contact_uid + '''\',
                    contact_created_at = \'''' + getNow() + '''\',
                    first_name = \'''' + fname + '''\',
                    last_name = \'''' + lname + '''\',
                    email = \'''' + email + '''\',
                    phone = \'''' + phone + '''\',
                    subject = \'''' + subject + '''\'
                '''
            
            items = execute(query, "post", conn)
            print("items: ", items)
            if items["code"] == 281:
                response["message"] = "Contact Post successful"
                return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)



# -- ACCOUNT APIS -------------------------------------------------------------------------------

class createAccount(Resource):
    def post(self):
        response = {}
        items = []
        try:
            conn = connect()
            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            firstName = data["first_name"]
            lastName = data["last_name"]
            phone = data["phone_number"]
            address = data["address"]
            unit = data["unit"] if data.get("unit") is not None else "NULL"
            social_id = (
                data["social_id"] if data.get("social_id") is not None else "NULL"
            )
            city = data["city"]
            state = data["state"]
            zip_code = data["zip_code"]
            latitude = data["latitude"]
            longitude = data["longitude"]
            referral = data["referral_source"]
            role = data["role"]
            cust_id = data["cust_id"] if data.get("cust_id") is not None else "NULL"

            if (
                data.get("social") is None
                or data.get("social") == "FALSE"
                or data.get("social") == False
                or data.get("social") == "NULL"
            ):
                social_signup = False
            else:
                social_signup = True

            print(social_signup)
            get_user_id_query = "CALL new_customer_uid();"
            NewUserIDresponse = execute(get_user_id_query, "get", conn)

            print("New User Code: ", NewUserIDresponse["code"])

            if NewUserIDresponse["code"] == 490:
                string = " Cannot get new User id. "
                print("*" * (len(string) + 10))
                print(string.center(len(string) + 10, "*"))
                print("*" * (len(string) + 10))
                response["message"] = "Internal Server Error."
                return response, 500
            NewUserID = NewUserIDresponse["result"][0]["new_id"]
            print("New User ID: ", NewUserID)

            if social_signup == False:

                salt = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

                password = sha512((data["password"] + salt).encode()).hexdigest()
                print("password------", password)
                algorithm = "SHA512"
                mobile_access_token = "NULL"
                mobile_refresh_token = "NULL"
                user_access_token = "NULL"
                user_refresh_token = "NULL"
                user_social_signup = "NULL"
            else:

                mobile_access_token = data["mobile_access_token"]
                mobile_refresh_token = data["mobile_refresh_token"]
                user_access_token = data["user_access_token"]
                user_refresh_token = data["user_refresh_token"]
                salt = "NULL"
                password = "NULL"
                algorithm = "NULL"
                user_social_signup = data["social"]

                print("ELSE- OUT")

            if cust_id != "NULL" and cust_id:

                NewUserID = cust_id

                query = (
                    """
                        SELECT user_access_token, user_refresh_token, mobile_access_token, mobile_refresh_token 
                        FROM io.customers
                        WHERE customer_uid = \'""" + cust_id + """\';
                    """
                )
                it = execute(query, "get", conn)
                print("it-------", it)

                if it["result"][0]["user_access_token"] != "FALSE":
                    user_access_token = it["result"][0]["user_access_token"]

                if it["result"][0]["user_refresh_token"] != "FALSE":
                    user_refresh_token = it["result"][0]["user_refresh_token"]

                if it["result"][0]["mobile_access_token"] != "FALSE":
                    mobile_access_token = it["result"][0]["mobile_access_token"]

                if it["result"][0]["mobile_refresh_token"] != "FALSE":
                    mobile_refresh_token = it["result"][0]["mobile_refresh_token"]

                customer_insert_query = [
                    """
                        UPDATE io.customers 
                        SET 
                        customer_created_at = \'"""+ (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")+ """\',
                        customer_first_name = \'"""+ firstName+ """\',
                        customer_last_name = \'"""+ lastName+ """\',
                        customer_phone_num = \'"""+ phone+ """\',
                        customer_address = \'"""+ address+ """\',
                        customer_unit = \'"""+ unit+ """\',
                        customer_city = \'"""+ city+ """\',
                        customer_state = \'"""+ state+ """\',
                        customer_zip = \'"""+ zip_code+ """\',
                        customer_lat = \'"""+ latitude+ """\',
                        customer_long = \'"""+ longitude+ """\',
                        password_salt = \'"""+ salt+ """\',
                        password_hashed = \'"""+ password+ """\',
                        password_algorithm = \'"""+ algorithm+ """\',
                        referral_source = \'"""+ referral+ """\',
                        role = \'"""+ role+ """\',
                        user_social_media = \'"""+ user_social_signup+ """\',
                        social_timestamp  =  DATE_ADD(now() , INTERVAL 14 DAY)
                        WHERE customer_uid = \'"""+ cust_id+ """\';
                    """
                ]

            else:

                # check if there is a same customer_id existing
                query = (
                    """
                        SELECT customer_email FROM io.customers
                        WHERE customer_email = \'"""
                    + email
                    + "';"
                )
                print("email---------")
                items = execute(query, "get", conn)
                if items["result"]:

                    items["result"] = ""
                    items["code"] = 409
                    items["message"] = "Email address has already been taken."

                    return items

                if items["code"] == 480:

                    items["result"] = ""
                    items["code"] = 480
                    items["message"] = "Internal Server Error."
                    return items

                print("Before write")
                # write everything to database
                customer_insert_query = [
                    """
                        INSERT INTO io.customers 
                        (
                            customer_uid,
                            customer_created_at,
                            customer_first_name,
                            customer_last_name,
                            customer_phone_num,
                            customer_email,
                            customer_address,
                            customer_unit,
                            customer_city,
                            customer_state,
                            customer_zip,
                            customer_lat,
                            customer_long,
                            password_salt,
                            password_hashed,
                            password_algorithm,
                            referral_source,
                            role,
                            user_social_media,
                            user_access_token,
                            social_timestamp,
                            user_refresh_token,
                            mobile_access_token,
                            mobile_refresh_token,
                            social_id
                        )
                        VALUES
                        (
                        
                            \'"""+ NewUserID+ """\',
                            \'"""+ (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")+ """\',
                            \'"""+ firstName+ """\',
                            \'"""+ lastName+ """\',
                            \'"""+ phone+ """\',
                            \'"""+ email+ """\',
                            \'"""+ address+ """\',
                            \'"""+ unit+ """\',
                            \'"""+ city+ """\',
                            \'"""+ state+ """\',
                            \'"""+ zip_code+ """\',
                            \'"""+ latitude+ """\',
                            \'"""+ longitude+ """\',
                            \'"""+ salt+ """\',
                            \'"""+ password+ """\',
                            \'"""+ algorithm+ """\',
                            \'"""+ referral+ """\',
                            \'"""+ role+ """\',
                            \'"""+ user_social_signup+ """\',
                            \'"""+ user_access_token+ """\',
                            DATE_ADD(now() , INTERVAL 14 DAY),
                            \'"""+ user_refresh_token+ """\',
                            \'"""+ mobile_access_token+ """\',
                            \'"""+ mobile_refresh_token+ """\',
                            \'"""+ social_id+ """\');"""
                        ]
            print(customer_insert_query[0])
            items = execute(customer_insert_query[0], "post", conn)

            if items["code"] != 281:
                items["result"] = ""
                items["code"] = 480
                items["message"] = "Error while inserting values in database"

                return items

            items["result"] = {
                "first_name": firstName,
                "last_name": lastName,
                "customer_uid": NewUserID,
                "access_token": user_access_token,
                "refresh_token": user_refresh_token,
                "access_token": mobile_access_token,
                "refresh_token": mobile_refresh_token,
                "social_id": social_id,
            }
            items["message"] = "Signup successful"
            items["code"] = 200

            print("sss-----", social_signup)

            # generate coupon for new user

            # query = ["CALL io.new_coupons_uid;"]
            # couponIDresponse = execute(query[0], "get", conn)
            # couponID = couponIDresponse["result"][0]["new_id"]
            # EndDate = date.today() + timedelta(days=30)
            # exp_time = str(EndDate) + " 00:00:00"

            # query = (
            #     """
            #         INSERT INTO io.coupons 
            #         (
            #             coupon_uid, 
            #             coupon_id, 
            #             valid, 
            #             discount_percent, 
            #             discount_amount, 
            #             discount_shipping, 
            #             expire_date, 
            #             limits, 
            #             notes, 
            #             num_used, 
            #             recurring, 
            #             email_id, 
            #             cup_business_uid, 
            #             threshold
            #         ) 
            #         VALUES 
            #         ( 
            #             \'"""+ couponID+ """\', 
            #             'NewCustomer', 
            #             'TRUE', 
            #             '0', 
            #             '0', 
            #             '5', 
            #             \'"""+ exp_time+ """\', 
            #             '1', 
            #             'Welcome Coupon', 
            #             '0', 
            #             'F', 
            #             \'"""+ email+ """\', 
            #             'null', 
            #             '0'
            #         );
            #         """
            # )
            # print(query)
            # item = execute(query, "post", conn)
            # if item["code"] != 281:
            #     item["message"] = "check sql query for coupons"
            #     item["code"] = 400
            #     return item
            # return items

        except:
            print("Error happened while Sign Up")
            if "NewUserID" in locals():
                execute(
                    """DELETE FROM customers WHERE customer_uid = '"""
                    + NewUserID
                    + """';""",
                    "post",
                    conn,
                )
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

class AccountSalt(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            query = (
                """
                    SELECT password_algorithm, 
                            password_salt,
                            user_social_media 
                    FROM io.customers cus
                    WHERE customer_email = \'""" + email + """\';
                """
            )
            items = execute(query, "get", conn)
            print(items)
            if not items["result"]:
                items["message"] = "Email doesn't exists"
                items["code"] = 404
                return items
            if items["result"][0]["user_social_media"] != "NULL":
                items["message"] = (
                    """Social Signup exists. Use \'"""
                    + items["result"][0]["user_social_media"]
                    + """\' """
                )
                items["code"] = 401
                return items
            items["message"] = "SALT sent successfully"
            items["code"] = 200
            return items
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

class Login(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            password = data.get("password")
            social_id = data.get("social_id")
            signup_platform = data.get("signup_platform")
            query = (
                """
                    # CUSTOMER QUERY 1: LOGIN
                    SELECT customer_uid,
                        customer_last_name,
                        customer_first_name,
                        customer_email,
                        password_hashed,
                        email_verified,
                        user_social_media,
                        user_access_token,
                        user_refresh_token,
                        user_access_token,
                        user_refresh_token,
                        social_id
                    FROM io.customers c
                    WHERE customer_email = \'""" + email + """\';
                """
            )
            items = execute(query, "get", conn)
            print("Password", password)
            print(items)

            if items["code"] != 280:
                response["message"] = "Internal Server Error."
                response["code"] = 500
                return response
            elif not items["result"]:
                items["message"] = "Email Not Found. Please signup"
                items["result"] = ""
                items["code"] = 404
                return items
            else:
                print(items["result"])
                print("sc: ", items["result"][0]["user_social_media"])

                # checks if login was by social media
                if (
                    password
                    and items["result"][0]["user_social_media"] != "NULL"
                    and items["result"][0]["user_social_media"] != None
                ):
                    response["message"] = "Need to login by Social Media"
                    response["code"] = 401
                    return response

                # nothing to check
                elif (password is None and social_id is None) or (
                    password is None
                    and items["result"][0]["user_social_media"] == "NULL"
                ):
                    response["message"] = "Enter password else login from social media"
                    response["code"] = 405
                    return response

                # compare passwords if user_social_media is false
                elif (
                    items["result"][0]["user_social_media"] == "NULL"
                    or items["result"][0]["user_social_media"] == None
                ) and password is not None:

                    if items["result"][0]["password_hashed"] != password:
                        items["message"] = "Wrong password"
                        items["result"] = ""
                        items["code"] = 406
                        return items

                    if ((items["result"][0]["email_verified"]) == "0") or (
                        items["result"][0]["email_verified"] == "FALSE"
                    ):
                        response["message"] = "Account need to be verified by email."
                        response["code"] = 407
                        return response

                # compare the social_id because it never expire.
                elif (items["result"][0]["user_social_media"]) != "NULL":

                    if signup_platform != items["result"][0]["user_social_media"]:
                        items["message"] = (
                            "Wrong social media used for signup. Use '"
                            + items["result"][0]["user_social_media"]
                            + "'."
                        )
                        items["result"] = ""
                        items["code"] = 411
                        return items

                    if items["result"][0]["social_id"] != social_id:
                        print(items["result"][0]["social_id"])

                        items["message"] = "Cannot Authenticated. Social_id is invalid"
                        items["result"] = ""
                        items["code"] = 408
                        return items

                else:
                    string = " Cannot compare the password or social_id while log in. "
                    print("*" * (len(string) + 10))
                    print(string.center(len(string) + 10, "*"))
                    print("*" * (len(string) + 10))
                    response["message"] = string
                    response["code"] = 500
                    return response
                del items["result"][0]["password_hashed"]
                del items["result"][0]["email_verified"]

                query = (
                    "SELECT * from io.customers WHERE customer_email = '" + email + "';"
                )
                items = execute(query, "get", conn)
                items["message"] = "Authenticated successfully."
                items["code"] = 200
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

class stripe_key(Resource):
    
    def get(self, desc):    
        print(desc)      
        if desc == 'IOTEST':
            return {'publicKey': stripe_public_test_key} 
        else:             
            return {'publicKey': stripe_public_live_key} 

# -- DEFINE APIS -------------------------------------------------------------------------------
# Define API routes
api.add_resource(createGame, "/api/v2/createGame")
api.add_resource(checkGame, "/api/v2/checkGame/<string:game_code>")
api.add_resource(createUser, "/api/v2/createUser")
api.add_resource(createNewGame, "/api/v2/createNewGame")
api.add_resource(joinGame, "/api/v2/joinGame")
api.add_resource(getPlayers, "/api/v2/getPlayers/<string:game_code>")
api.add_resource(decks, "/api/v2/decks")
api.add_resource(gameTimer, "/api/v2/gameTimer/<string:game_code>")
api.add_resource(selectDeck, "/api/v2/selectDeck")
api.add_resource(changeRoundsAndDuration, "/api/v2/changeRoundsAndDuration")
api.add_resource(getImageInRound, "/api/v2/getImageInRound/<string:game_code>")
api.add_resource(submitCaption, "/api/v2/submitCaption")
api.add_resource(getPlayersRemainingToSubmitCaption, "/api/v2/getPlayersRemainingToSubmitCaption/<string:game_code>,<string:round_number>")
api.add_resource(getAllSubmittedCaptions, "/api/v2/getAllSubmittedCaptions/<string:game_code>,<string:round_number>")
api.add_resource(voteCaption, "/api/v2/voteCaption")
api.add_resource(getPlayersWhoHaventVoted, "/api/v2/getPlayersWhoHaventVoted/<string:game_code>,<string:round_number>")
api.add_resource(createNextRound, "/api/v2/createNextRound")
api.add_resource(getScoreBoard, "/api/v2/getScoreBoard/<string:game_code>,<string:round_number>")
api.add_resource(startPlaying, "/api/v2/startPlaying/<string:game_code>,<string:round_number>")


# reference APIs
api.add_resource(CreateAppointment, "/api/v2/createAppointment")
api.add_resource(AvailableAppointments, "/api/v2/availableAppointments/<string:date_value>")
api.add_resource(AddContact, "/api/v2/addContact")

api.add_resource(createAccount, "/api/v2/createAccount")
api.add_resource(AccountSalt, "/api/v2/AccountSalt")
api.add_resource(Login, "/api/v2/Login/")
api.add_resource(stripe_key, '/api/v2/stripe_key/<string:desc>')


# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4000)
