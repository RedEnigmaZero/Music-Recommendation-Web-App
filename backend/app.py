# Written by Navjeet for HW3

from flask import Flask, jsonify, send_from_directory, request, session, redirect, url_for
from flask import Response
import os
from flask_cors import CORS
import requests
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timezone
from jose import jwt
import time

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler


static_path = os.getenv('STATIC_PATH','static')
template_path = os.getenv('TEMPLATE_PATH','templates')
# Mongo connection
mongo_uri = os.getenv("MONGO_URI")
mongo = MongoClient(mongo_uri)
db = mongo.get_default_database()

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "secret-dev-key")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
redirect_uri = 'http://127.0.0.1:5173/'
scope = (
    'playlist-read-private '
    'user-read-email '
    'user-top-read '
    'user-library-read '
    'user-library-modify'
)

cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True
)
sp = Spotify(auth_manager=sp_oauth)

@app.route("/spotify/authorize")
def home():
    app.logger.debug("SPOTIPY: Entered /spotify/authorize (home route)")
    if not sp_oauth.validate_token(sp_oauth.get_cached_token()):
        app.logger.debug("SPOTIPY: Token not valid or not found, getting auth URL.")
        auth_url = sp_oauth.get_authorize_url()
        app.logger.debug(f"SPOTIPY: Generated Spotify auth_url: {auth_url}")
        return redirect(auth_url)
    
    app.logger.debug("SPOTIPY: Token is valid, redirecting to Svelte app frontend.")
    return redirect('http://localhost:5173/')

@app.route("/api/spotify/token", methods=['POST'])
def spotify_token():
    data = request.get_json()
    code = data.get('code')
    app.logger.debug(f"SPOTIPY: /api/spotify/token received code: {'YES' if code else 'NO'}")

    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    try:
        token_info = sp_oauth.get_access_token(code, check_cache=False)

        if not token_info:
            app.logger.error("SPOTIPY: Failed to get token info from Spotify from /api/spotify/token.")
            return jsonify({"error": "Failed to get token info"}), 500
        
        app.logger.debug(f"SPOTIPY: /api/spotify/token - Token info received: {token_info}")
        
        
        spotify_user_profile = sp.current_user()
        app.logger.debug(f"SPOTIPY: /api/spotify/token - Fetched Spotify user profile: {spotify_user_profile}")

        user_info = {
            "name": spotify_user_profile['display_name'],
            "email": spotify_user_profile['email'],
            "id": spotify_user_profile['id'],
            "moderator": False 
        }
        session["user"] = user_info 
        app.logger.debug(f"SPOTIPY: /api/spotify/token - User info stored in session. Session data: {dict(session)}")
        return jsonify({"success": True, "user": user_info})
    except Exception as e:
        app.logger.error(f"SPOTIPY: Error in /api/spotify/token: {str(e)}")
        return jsonify({"error": "An error occurred during Spotify token exchange."}), 500
        

@app.route("/callback")
def callback():
    app.logger.debug("SPOTIPY: Entered /callback route") 
    app.logger.debug(f"SPOTIPY: Request args received: {request.args}")

    token_info = sp_oauth.get_access_token(request.args['code'])

    app.logger.debug(f"SPOTIPY: Token info received: {'YES' if token_info else 'NO'}")

    spotify_user_profile = sp.current_user()
    app.logger.debug(f"SPOTIPY: Fetched Spotify user profile: {spotify_user_profile}")

    user_info = {
        "name": spotify_user_profile['display_name'],
        "email": spotify_user_profile['email'],
        "id": spotify_user_profile['id'],
        "moderator": False
    }
    app.logger.debug(f"SPOTIPY: Prepared user_info for session: {user_info}")
    session["user"] = user_info
    app.logger.debug(f"SPOTIPY: User info stored in session. Session data: {session}")

    app.logger.debug("SPOTIPY: Redirecting to Svelte app frontend from /callback.")
    return redirect("http://localhost:5173/")

@app.route("/api/playlists")
def api_get_playlists():
    app.logger.debug("APP: Entered /api/playlists route")

    token_info = sp_oauth.get_cached_token()
    # Check if the token exists and is valid
    if not token_info or not sp_oauth.validate_token(token_info):
        # If the token is not valid, try to refresh it
        if token_info and token_info.get('refresh_token'):
            try:
                app.logger.info("APP: /api/playlists - Attempting to refresh token.")
                token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
                app.logger.info("APP: /api/playlists - Token refreshed successfully.")
            except Exception as e:
                app.logger.error(f"APP: /api/playlists - Failed to refresh token: {str(e)}")
                session.clear() # Clear session if refresh fails
                return jsonify({"error": "Session expired, failed to refresh token. Please log in again."}), 401
        else:
            session.clear() # Clear session if no refresh token or initial validation fails
            app.logger.warn("APP: /api/playlists - No valid token/refresh token. User needs to re-authenticate.")
            return jsonify({"error": "User not authenticated or token expired. Please log in again."}), 401

    try:
        playlists_result = sp.current_user_playlists(limit=50) # Get up to 50 playlists
        app.logger.debug(f"APP: /api/playlists - Playlists fetched from Spotify: {'Data received' if playlists_result else 'No data'}")

        playlists_data = []
        if playlists_result and playlists_result.get('items'):
            for item in playlists_result['items']:
                image_url = None
                # Get the first image URL if available
                if item.get('images') and len(item['images']) > 0:
                    image_url = item['images'][0].get('url')

                playlist_info = {
                    "id": item.get('id'),
                    "name": item.get('name'),
                    "url": item.get('external_urls', {}).get('spotify'),
                    "imageUrl": image_url,
                    "track_count": item.get('tracks', {}).get('total', 0)
                }
                playlists_data.append(playlist_info)

        app.logger.debug(f"APP: /api/playlists - Processed {len(playlists_data)} playlists.")
        return jsonify(playlists_data)

    except Exception as e:
        app.logger.error(f"APP: /api/playlists - Error fetching playlists: {str(e)}")
        if hasattr(e, 'http_status') and e.http_status == 401: # Spotify API returned 401
             session.clear() 
             return jsonify({"error": "Spotify authorization error. Please log in again."}), 401
        return jsonify({"error": "Failed to fetch playlists from Spotify"}), 500


# This code is so that we can store "likes" and "dislikes" to MongoDB.
# First the code checks if the user has a valid Spotify account/token. If they do, then the code will extract the "like" or the "dislike" from request.
# Then the code gets the user's Spotify ID, where MongoDB will either create or upload a document with their ratings along with the time it was made. 

@app.route("/api/feedback/<track_id>", methods=["PUT"])
def feedback(track_id):
    if not sp_oauth.validate_token(sp_oauth.get_cached_token()):
        return jsonify({"error": "Spotify login required"}), 500

    rating = (request.json or {}).get("rating")
    if rating not in {"like", "dislike"}:
        return jsonify({"error": "Rating must be 'like' or 'dislike'"}), 400

    user_id = sp.current_user()["id"]
    db.userprefs.update_one(
        {"_id": user_id},
        {
            "$set": {f"ratings.{track_id}": rating},
            "$currentDate": {"updated": True},
            "$setOnInsert": {"created": time.time()}
        },
        upsert=True
    )
    return ""

# This code is so that the user can save a song to their Spotify account. 
# First the code checks if the user has a valid Spotify account/token. If they do then the code adds the song to their Spotify account.  

@app.route("/api/save/<track_id>", methods=["PUT"])
def save_track(track_id):
    if not sp_oauth.validate_token(sp_oauth.get_cached_token()):
        return jsonify({"error": "Spotify login required"}), 500

    sp.current_user_saved_tracks_add([track_id])
    return ""


# The code down below should give us the info from the user. It checks if a user is already logged in by looking for their data.
# If the user is found in the session, then it will set the user's name, email, and moderator status.
# We needed to read up on dex documentation and the links from the lab.
# Dex: https://dexidp.io/docs/
# MongoDB in a Flask Application: https://www.digitalocean.com/community/tutorials/how-to-use-mongodb-in-a-flask-application
# Sending Data from a Flask app to MongoDB Database: https://www.geeksforgeeks.org/sending-data-from-a-flask-app-to-mongodb-database/
# Flask documentation: https://flask.palletsprojects.com/en/stable/

@app.before_request
def user():
    app.logger.debug(f"APP: @before_request triggered for path: {request.path}")
    app.logger.debug(f"APP: @before_request - Incoming request headers: {request.headers}") 
    app.logger.debug(f"APP: @before_request - Full session data at start: {dict(session)}")
    if "user" in session:
        request.user = session["user"]
        app.logger.debug(f"APP: @before_request - User successfully loaded from session: {request.user}")
    else:
        request.user = None
        app.logger.debug("APP: @before_request - No 'user' key found in session for this request.")

# The code down below is a route that is called after the user logs in through Dex.
# The code should work by getting the user's name, email, and moderator status from the token from Dex.
# Then it stores that information in the Flask session so that is is saved. Then it will go back to the homepage and showed that the user is logged in.
# Authorization Code Flow: https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow
# JWT: https://jwt.io/introduction
# Flask-OIDC: https://flask-oidc.readthedocs.io/en/latest/
"""
@app.route("/authorize")
def authorize():
    code = request.args.get("code")
    token_url = os.getenv("OIDC_TOKEN_URL", "http://dex:5556/token")
    client_id = os.getenv("OIDC_CLIENT_ID")
    client_secret = os.getenv("OIDC_CLIENT_SECRET")
    redirect_uri = "http://localhost:8000/authorize"

    token_response = requests.post(token_url, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret
    })

    token_data = token_response.json()
    id_token = token_data["id_token"]
    access_token = token_data["access_token"]
    claims = jwt.decode(id_token, key='', options={"verify_signature": False}, audience=client_id, access_token=access_token)

    user = {
        "name": claims.get("name"),
        "email": claims.get("email"),
        "moderator": claims.get("email") == "moderator@hw3.com" or claims.get("email") == "admin@hw3.com"
    }
    session["user"] = user
    return redirect("http://localhost:5173/")

"""
# The code down below is a route that is used when the user wants to logout.
# The code works by clearing out the session data, and then going back to the homepage.

@app.route("/logout")
def logout():
    session.clear()
    return redirect("http://localhost:5173/")

# The code down below is a route that the frontend can use to help identify the user's info, email, and moderator role.

@app.route("/api/me")
def get_me():
    app.logger.debug(f"APP: Entered /api/me. Current session data: {dict(session)}") 
    app.logger.debug(f"APP: /api/me - request.user (set by @app.before_request) is: {request.user}")
    return jsonify(request.user)

@app.route('/')
@app.route('/<path:path>')
def serve_frontend(path=''):
    if path != '' and os.path.exists(os.path.join(static_path,path)):
        return send_from_directory(static_path, path)
    return send_from_directory(template_path, 'index.html')

@app.route('/login')
def login_frontend():
    return send_from_directory(template_path, 'login.html')

@app.route("/test-mongo")
def test_mongo():
    return jsonify({"collections": db.list_collection_names()})

@app.route("/proxy-image")
def proxy_image():
    url = request.args.get("url")
    if not url:
        return "Missing URL", 400
    try:
        r = requests.get(url)
        return Response(r.content, content_type=r.headers["Content-Type"])
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)),debug=debug_mode)
