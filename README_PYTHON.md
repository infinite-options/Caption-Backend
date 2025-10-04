# Google API Demo - Python Flask Backend

A unified Python Flask backend server that supports both web (React) and mobile (React Native) applications for Google API integration.

## 🚀 Features

- **OAuth 2.0 Authentication** - Secure Google OAuth flow with PKCE
- **Multi-Platform Support** - Works with both web and mobile apps
- **Google APIs Integration**:
  - Google Drive (file listing)
  - Google Calendar (events)
  - Google Photos (library access)
  - Google Photo Picker (web-only)
- **Security Features**:
  - Rate limiting (100 requests per 15 minutes)
  - CORS configuration
  - PKCE for OAuth security
- **Deep Linking Support** - For mobile app callbacks
- **Comprehensive Logging** - Detailed request/response logging

## 📋 Prerequisites

- Python 3.8+
- pip or pipenv
- Google Cloud Console project with OAuth credentials

## 🛠️ Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables:**
   ```env
   # Google OAuth Configuration
   GOOGLE_CLIENT_ID=your_google_client_id_here
   GOOGLE_CLIENT_SECRET=your_google_client_secret_here
   REDIRECT_URI=http://localhost:3001/oauth2/callback
   
   # Server Configuration
   PORT=3001
   NODE_ENV=development
   
   # Frontend Configuration
   FRONTEND_URL=http://localhost:3000
   
   # Optional: Secret key for Flask sessions
   SECRET_KEY=your_secret_key_here
   ```

4. **Start the server:**
   ```bash
   # Development
   python photo-picker.py
   
   # Production (with gunicorn)
   gunicorn -w 4 -b 0.0.0.0:3001 photo-picker:app
   ```

## 🔗 API Endpoints

### Authentication
- `GET /api/oauth/url` - Get OAuth authorization URL
- `GET /oauth2/callback` - OAuth callback (Google redirects here)
- `POST /api/oauth/token` - Exchange code for tokens
- `POST /api/oauth/refresh` - Refresh access token

### User Data
- `GET /api/user/profile` - Get user profile
- `GET /api/drive/files` - Get Google Drive files
- `GET /api/calendar/events` - Get calendar events
- `GET /api/photos/library` - Get Google Photos

### Photo Picker
- `GET /api/photos/picker/url` - Get Photo Picker URL
- `POST /api/picker/selection` - Store selected photos
- `GET /api/picker/result` - Get selected photos

### Utility
- `GET /health` - Health check
- `GET /test` - Test endpoint for debugging

## 🌐 CORS Configuration

The server is configured to accept requests from:
- `http://localhost:3000` (React web app)
- `http://localhost:8081` (Expo web)
- `http://10.0.2.2:8081` (Android emulator)
- Expo development URLs

## 📱 Mobile App Integration

For React Native apps, the backend supports:
- Deep linking callbacks (`capshnz://photos/done?session=xyz`)
- Token exchange via `/api/oauth/token`
- Photo picker result retrieval
- Comprehensive error handling and logging

## 🔒 Security

- **Rate Limiting**: 100 requests per 15 minutes per IP
- **CORS Protection**: Configured for specific origins
- **PKCE**: OAuth security enhancement
- **Input Validation**: Request parameter validation

## 🚀 Production Deployment

1. **Environment Setup:**
   ```bash
   export NODE_ENV=production
   export PORT=3001
   export REDIRECT_URI=https://yourdomain.com/oauth2/callback
   export FRONTEND_URL=https://yourdomain.com
   ```

2. **Database Integration:**
   - Replace in-memory storage with Redis/PostgreSQL
   - Implement proper session management
   - Add database connection pooling

3. **Security Enhancements:**
   - Use HTTPS for all endpoints
   - Implement proper logging and monitoring
   - Add request validation middleware
   - Set up proper CORS for production domains

4. **Scaling:**
   - Use Gunicorn or similar WSGI server
   - Implement load balancing
   - Add health check endpoints
   - Set up monitoring and alerting

## 📝 Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Yes | - |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Yes | - |
| `REDIRECT_URI` | OAuth callback URL | Yes | - |
| `PORT` | Server port | No | 3001 |
| `FRONTEND_URL` | Frontend URL for web redirects | No | http://localhost:3000 |
| `NODE_ENV` | Environment (development/production) | No | development |
| `SECRET_KEY` | Flask secret key | No | Auto-generated |

## 🧪 Testing

1. **Health Check:**
   ```bash
   curl http://localhost:3001/health
   ```

2. **Test Endpoint:**
   ```bash
   curl http://localhost:3001/test
   ```

3. **OAuth Flow:**
   ```bash
   curl http://localhost:3001/api/oauth/url
   ```

## 📊 Key Differences from Node.js Version

### Python-Specific Features:
- **Type Hints**: Full type annotations for better code clarity
- **Exception Handling**: Python-specific error handling patterns
- **Logging**: Python logging module with structured logging
- **Data Structures**: Python dictionaries and lists for data storage

### Equivalent Functionality:
- All API endpoints work identically
- Same OAuth flow and security features
- Same CORS and rate limiting configuration
- Same error handling and response formats

## 🔄 Migration from Node.js

The Python version maintains 100% API compatibility with the Node.js version:

1. **Same Endpoints**: All endpoints work identically
2. **Same Request/Response Format**: JSON responses match exactly
3. **Same OAuth Flow**: Identical OAuth implementation
4. **Same Error Handling**: Consistent error responses

## 📞 Support

If you encounter issues:

1. Check the logs for error messages
2. Verify environment variables
3. Test individual endpoints
4. Check Google Cloud Console configuration
5. Review this README

## 🎉 Success!

Once deployed, you'll have:
- A single, maintainable Python backend
- Better security and performance
- Clean code structure with type hints
- Comprehensive documentation
- Support for both web and mobile apps
