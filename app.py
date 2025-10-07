import os
import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Security middleware - manually add security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response

# Rate limiting (commented out for now)
# limiter = Limiter(
#     app,
#     key_func=get_remote_address,
#     default_limits=["100 per 15 minutes"]
# )

# CORS configuration for mobile apps
CORS(app, origins=[
    "http://localhost:3000",  # Web development
    "http://localhost:8081",  # Expo web
    "exp://localhost:19000",  # Expo development
    "exp://192.168.1.100:19000",  # Expo on local network
], supports_credentials=True)

# Store active sessions (in production, use Redis)
active_sessions: Dict[str, Dict] = {}
user_tokens: Dict[str, Dict] = {}

# Configuration
PORT = int(os.getenv('PORT', 3001))
GOOGLE_CLIENT_ID = os.getenv('REACT_APP_GOOGLE_CLIENT_ID_WEB')
GOOGLE_CLIENT_SECRET = os.getenv('REACT_APP_GOOGLE_CLIENT_SECRET_WEB')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:3000')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Utility functions
def base64url_encode(data: bytes) -> str:
    """Base64 URL encode without padding"""
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def generate_code_verifier() -> str:
    """Generate a cryptographically random code verifier"""
    return base64url_encode(secrets.token_bytes(32))

def generate_code_challenge(verifier: str) -> str:
    """Generate code challenge from verifier using SHA256"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64url_encode(digest)

def validate_mobile_request():
    """Middleware to validate mobile app requests"""
    user_agent = request.headers.get('User-Agent', '')
    is_mobile_app = 'Expo' in user_agent or 'ReactNative' in user_agent
    
    if not is_mobile_app and os.getenv('NODE_ENV') == 'production':
        return jsonify({'error': 'This API is for mobile apps only'}), 403
    
    return None

# Routes

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'message': 'Google API Demo Backend is running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/oauth/url', methods=['GET'])
def get_oauth_url():
    """Get OAuth URL for mobile"""
    try:
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        
        # Store code verifier for later use
        session_id = str(uuid.uuid4())
        active_sessions[session_id] = {
            'code_verifier': code_verifier,
            'timestamp': datetime.now().timestamp(),
            'user_agent': request.headers.get('User-Agent', 'unknown')
        }
        
        scopes = [
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/photoslibrary.readonly',
            'https://www.googleapis.com/auth/photospicker.mediaitems.readonly'
        ]
        
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"response_type=code&"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={REDIRECT_URI}&"
            f"scope={' '.join(scopes)}&"
            f"code_challenge={code_challenge}&"
            f"code_challenge_method=S256&"
            f"include_granted_scopes=true&"
            f"access_type=offline&"
            f"prompt=consent&"
            f"state={session_id}"
        )
        
        return jsonify({
            'authUrl': auth_url,
            'sessionId': session_id,
            'message': 'Use this URL for OAuth flow',
            'expiresIn': 600  # 10 minutes
        })
        
    except Exception as e:
        print(f"Error generating OAuth URL: {e}")
        return jsonify({'error': 'Failed to generate OAuth URL'}), 500

@app.route('/api/oauth/token', methods=['POST'])
def exchange_code_for_token():
    """Exchange code for token"""
    try:
        # Handle empty or invalid JSON gracefully
        try:
            data = request.get_json() or {}
        except Exception:
            data = {}
        code = data.get('code')
        state = data.get('state')
        user_id = data.get('userId')
        
        if not code or not state:
            return jsonify({'error': 'Missing code or state parameter'}), 400
        
        # Retrieve code verifier from session
        session = active_sessions.get(state)
        if not session:
            return jsonify({'error': 'Invalid or expired session'}), 400
        
        # Check if session is expired (10 minutes)
        if datetime.now().timestamp() - session['timestamp'] > 600:
            active_sessions.pop(state, None)
            return jsonify({'error': 'Session expired'}), 400
        
        code_verifier = session['code_verifier']
        
        # Exchange code for token
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'code_verifier': code_verifier
        }
        
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Token exchange failed'}), 500
        
        token_response = response.json()
        
        # Clean up session
        active_sessions.pop(state, None)
        
        # Store user token
        user_token_id = user_id or str(uuid.uuid4())
        user_tokens[user_token_id] = {
            'access_token': token_response['access_token'],
            'refresh_token': token_response.get('refresh_token'),
            'expires_at': datetime.now().timestamp() + token_response['expires_in'],
            'user_id': user_token_id
        }
        
        return jsonify({
            'access_token': token_response['access_token'],
            'refresh_token': token_response.get('refresh_token'),
            'expires_in': token_response['expires_in'],
            'scope': token_response.get('scope'),
            'user_id': user_token_id
        })
        
    except Exception as e:
        print(f"Token exchange error: {e}")
        return jsonify({'error': 'Token exchange failed', 'details': str(e)}), 500

@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """Get user profile"""
    try:
        user_id = request.args.get('user_id')
        auth_header = request.headers.get('Authorization')
        
        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
        elif user_id:
            user_token = user_tokens.get(user_id)
            if not user_token or datetime.now().timestamp() > user_token['expires_at']:
                return jsonify({'error': 'Token expired or invalid'}), 401
            access_token = user_token['access_token']
        else:
            return jsonify({'error': 'Missing authorization'}), 401
        
        response = requests.get(
            'https://people.googleapis.com/v1/people/me?personFields=names,emailAddresses,photos',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch profile', 'details': response.text}), 500
        
        return jsonify(response.json())
        
    except Exception as e:
        print(f"Profile fetch error: {e}")
        return jsonify({'error': 'Failed to fetch profile', 'details': str(e)}), 500

@app.route('/api/drive/files', methods=['GET'])
def get_drive_files():
    """Get Drive files"""
    try:
        user_id = request.args.get('user_id')
        page_size = int(request.args.get('pageSize', 20))
        auth_header = request.headers.get('Authorization')
        
        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
        elif user_id:
            user_token = user_tokens.get(user_id)
            if not user_token or datetime.now().timestamp() > user_token['expires_at']:
                return jsonify({'error': 'Token expired or invalid'}), 401
            access_token = user_token['access_token']
        else:
            return jsonify({'error': 'Missing authorization'}), 401
        
        params = {
            'pageSize': page_size,
            'fields': 'files(id,name,mimeType,createdTime,modifiedTime,size,webViewLink,thumbnailLink,imageMediaMetadata)',
            'orderBy': 'modifiedTime desc'
        }
        
        response = requests.get(
            'https://www.googleapis.com/drive/v3/files',
            params=params,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch Drive files', 'details': response.text}), 500
        
        return jsonify(response.json())
        
    except Exception as e:
        print(f"Drive files fetch error: {e}")
        return jsonify({'error': 'Failed to fetch Drive files', 'details': str(e)}), 500

@app.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    """Get Calendar events"""
    try:
        date = request.args.get('date')
        user_id = request.args.get('user_id')
        
        if not date:
            return jsonify({'error': 'Date parameter is required'}), 400
        
        auth_header = request.headers.get('Authorization')
        
        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
        elif user_id:
            user_token = user_tokens.get(user_id)
            if not user_token or datetime.now().timestamp() > user_token['expires_at']:
                return jsonify({'error': 'Token expired or invalid'}), 401
            access_token = user_token['access_token']
        else:
            return jsonify({'error': 'Missing authorization'}), 401
        
        time_min = f"{date}T00:00:00Z"
        time_max = f"{date}T23:59:59Z"
        
        params = {
            'timeMin': time_min,
            'timeMax': time_max,
            'maxResults': 20,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        response = requests.get(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            params=params,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch Calendar events', 'details': response.text}), 500
        
        return jsonify(response.json())
        
    except Exception as e:
        print(f"Calendar events fetch error: {e}")
        return jsonify({'error': 'Failed to fetch Calendar events', 'details': str(e)}), 500

@app.route('/api/drive/photos', methods=['GET'])
def get_drive_photos():
    """Get Drive photos"""
    try:
        user_id = request.args.get('user_id')
        page_size = int(request.args.get('pageSize', 20))
        auth_header = request.headers.get('Authorization')
        
        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
        elif user_id:
            user_token = user_tokens.get(user_id)
            if not user_token or datetime.now().timestamp() > user_token['expires_at']:
                return jsonify({'error': 'Token expired or invalid'}), 401
            access_token = user_token['access_token']
        else:
            return jsonify({'error': 'Missing authorization'}), 401
        
        params = {
            'q': "mimeType contains 'image/'",
            'pageSize': page_size,
            'fields': 'files(id,name,mimeType,createdTime,modifiedTime,size,webViewLink,thumbnailLink,imageMediaMetadata,webContentLink)',
            'orderBy': 'modifiedTime desc'
        }
        
        response = requests.get(
            'https://www.googleapis.com/drive/v3/files',
            params=params,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch Drive photos', 'details': response.text}), 500
        
        # Transform the data for mobile
        files = response.json().get('files', [])
        photos = [
            {
                'id': file['id'],
                'name': file['name'],
                'url': file['webViewLink'],
                'thumbnails': [{'url': file['thumbnailLink']}] if file.get('thumbnailLink') else [],
                'mimeType': file['mimeType'],
                'size': file.get('size'),
                'modifiedTime': file['modifiedTime'],
                'imageMetadata': file.get('imageMediaMetadata')
            }
            for file in files
        ]
        
        return jsonify({'photos': photos, 'totalCount': len(photos)})
        
    except Exception as e:
        print(f"Drive photos fetch error: {e}")
        return jsonify({'error': 'Failed to fetch Drive photos', 'details': str(e)}), 500

@app.route('/api/photos/picker/session', methods=['POST'])
def create_photo_picker_session():
    """Create Photo Picker session"""
    try:
        # Handle empty or invalid JSON gracefully
        try:
            data = request.get_json() or {}
        except Exception:
            data = {}
        user_id = data.get('user_id')
        auth_header = request.headers.get('Authorization')
        
        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
        elif user_id:
            user_token = user_tokens.get(user_id)
            if not user_token or datetime.now().timestamp() > user_token['expires_at']:
                return jsonify({'error': 'Token expired or invalid'}), 401
            access_token = user_token['access_token']
        else:
            return jsonify({'error': 'Missing authorization'}), 401
        
        response = requests.post(
            'https://photospicker.googleapis.com/v1/sessions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to create Photo Picker session', 'details': response.text}), 500
        
        return jsonify(response.json())
        
    except Exception as e:
        print(f"Photo Picker session creation error: {e}")
        return jsonify({'error': 'Failed to create Photo Picker session', 'details': str(e)}), 500

@app.route('/api/photos/picker/media', methods=['GET'])
def get_photo_picker_media():
    """Get selected photos from Photo Picker"""
    try:
        session_id = request.args.get('sessionId')
        user_id = request.args.get('user_id')
        page_size = int(request.args.get('pageSize', 25))
        
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        auth_header = request.headers.get('Authorization')
        
        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
        elif user_id:
            user_token = user_tokens.get(user_id)
            if not user_token or datetime.now().timestamp() > user_token['expires_at']:
                return jsonify({'error': 'Token expired or invalid'}), 401
            access_token = user_token['access_token']
        else:
            return jsonify({'error': 'Missing authorization'}), 401
        
        params = {
            'sessionId': session_id,
            'pageSize': page_size
        }
        
        response = requests.get(
            'https://photospicker.googleapis.com/v1/mediaItems',
            params=params,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch selected photos', 'details': response.text}), 500
        
        return jsonify(response.json())
        
    except Exception as e:
        print(f"Photo Picker media fetch error: {e}")
        return jsonify({'error': 'Failed to fetch selected photos', 'details': str(e)}), 500

@app.route('/api/photos/picker/url', methods=['GET'])
def get_photo_picker_url():
    """Get Photo Picker URL for WebView"""
    try:
        user_id = request.args.get('user_id')
        auth_header = request.headers.get('Authorization')
        
        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
        elif user_id:
            user_token = user_tokens.get(user_id)
            if not user_token or datetime.now().timestamp() > user_token['expires_at']:
                return jsonify({'error': 'Token expired or invalid'}), 401
            access_token = user_token['access_token']
        else:
            return jsonify({'error': 'Missing authorization'}), 401
        
        # Create Photo Picker session
        session_response = requests.post(
            'https://photospicker.googleapis.com/v1/sessions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        if session_response.status_code != 200:
            return jsonify({'error': 'Failed to get Photo Picker URL', 'details': session_response.text}), 500
        
        session_data = session_response.json()
        
        return jsonify({
            'pickerUrl': session_data['pickerUri'],
            'sessionId': session_data['id'],
            'message': 'Use this URL in WebView for Photo Picker'
        })
        
    except Exception as e:
        print(f"Photo Picker URL error: {e}")
        return jsonify({'error': 'Failed to get Photo Picker URL', 'details': str(e)}), 500

@app.route('/api/oauth/callback', methods=['GET'])
def oauth_callback():
    """OAuth callback endpoint"""
    print("🔄 OAUTH CALLBACK ENDPOINT HIT!")
    print(f"🔄 Request from: {request.remote_addr}")
    
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        print(f"🔄 Query params - code: {code}, state: {state}")
        
        if not code or not state:
            print("❌ Missing code or state in query parameters")
            return jsonify({'error': 'Missing code or state'}), 400
        
        # Get stored code verifier for PKCE
        session = active_sessions.get(state)
        if not session:
            print(f"❌ Session not found for state: {state}")
            return jsonify({'error': 'Invalid or expired session'}), 400
        
        code_verifier = session['code_verifier']
        if not code_verifier:
            print(f"❌ Code verifier not found for session: {state}")
            return jsonify({'error': 'Missing code verifier'}), 400
        
        # Exchange code for tokens with Google (using PKCE)
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code',
            'code_verifier': code_verifier
        }
        
        print("🌐 Making request to Google OAuth token endpoint")
        
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code != 200:
            print(f"❌ Google token exchange failed: {response.text}")
            return jsonify({'error': 'Token exchange failed'}), 500
        
        tokens = response.json()
        print("✅ Successfully exchanged code for tokens")
        
        # Store tokens with state for later retrieval
        if state:
            active_sessions[state] = {
                'tokens': tokens,
                'timestamp': datetime.now().timestamp(),
                'code_verifier': code_verifier
            }
            print(f"💾 Tokens stored for state: {state}")
        else:
            print("❌ No state provided, cannot store tokens")
        
        # Redirect to frontend with session ID
        redirect_url = f"{FRONTEND_URL}?sessionId={state}&success=true"
        print(f"🌐 Redirecting to frontend: {redirect_url}")
        
        return redirect(redirect_url)
        
    except Exception as e:
        print(f"❌ Error in OAuth callback: {e}")
        return jsonify({'error': 'OAuth callback failed', 'details': str(e)}), 500

@app.route('/api/oauth/token/<session_id>', methods=['GET'])
def get_tokens_by_session_id(session_id):
    """Get tokens by session ID"""
    try:
        print(f"🔍 Retrieving tokens for session ID: {session_id}")
        
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        # Get session from active_sessions
        session = active_sessions.get(session_id)
        if not session:
            print(f"❌ Session not found for ID: {session_id}")
            return jsonify({'error': 'Session not found or expired'}), 404
        
        # Check if session is expired (10 minutes)
        if datetime.now().timestamp() - session['timestamp'] > 600:
            print(f"❌ Session expired for ID: {session_id}")
            active_sessions.pop(session_id, None)
            return jsonify({'error': 'Session expired'}), 410
        
        # Check if tokens exist
        if 'tokens' not in session:
            print(f"❌ No tokens found for session ID: {session_id}")
            return jsonify({'error': 'No tokens found for this session'}), 404
        
        print(f"✅ Tokens retrieved for session ID: {session_id}")
        
        # Return the tokens (excluding sensitive data like codeVerifier)
        response = {
            'access_token': session['tokens']['access_token'],
            'expires_in': session['tokens']['expires_in'],
            'refresh_token': session['tokens'].get('refresh_token'),
            'scope': session['tokens'].get('scope'),
            'token_type': session['tokens'].get('token_type')
        }
        
        # Optionally include id_token if present
        if 'id_token' in session['tokens']:
            response['id_token'] = session['tokens']['id_token']
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error retrieving tokens for session {session_id}: {e}")
        return jsonify({'error': 'Failed to retrieve tokens', 'details': str(e)}), 500

@app.route('/api/oauth/refresh', methods=['POST'])
def refresh_token():
    """Refresh token endpoint"""
    try:
        # Handle empty or invalid JSON gracefully
        try:
            data = request.get_json() or {}
        except Exception:
            data = {}
        refresh_token = data.get('refresh_token')
        user_id = data.get('user_id')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token is required'}), 400
        
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Token refresh failed', 'details': response.text}), 500
        
        token_data = response.json()
        
        # Update stored token
        if user_id and user_id in user_tokens:
            user_tokens[user_id]['access_token'] = token_data['access_token']
            user_tokens[user_id]['expires_at'] = datetime.now().timestamp() + token_data['expires_in']
        
        return jsonify({
            'access_token': token_data['access_token'],
            'expires_in': token_data['expires_in']
        })
        
    except Exception as e:
        print(f"Token refresh error: {e}")
        return jsonify({'error': 'Token refresh failed', 'details': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print(f"🚀 Google API Demo Backend server running on port {PORT}")
    print("📱 Ready for React Native apps")
    print("🌐 CORS enabled for mobile development")
    app.run(host='0.0.0.0', port=PORT, debug=True)
