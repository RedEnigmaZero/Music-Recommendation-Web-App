# Written by Navjeet for HW3

from flask import Flask, jsonify, send_from_directory, request, session, redirect, url_for
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
redirect_uri = 'http://127.0.0.1:5173/' # This is == to localhost:5173 
scope = (
    'playlist-read-private '
    'user-read-email '
    'user-top-read '
    'user-library-read '
    'user-library-modify'
)

# Configure Spotipy's OAuth  handler
# Tells Spotipy to store the token in Flask's session
cache_handler = FlaskSessionCacheHandler(session) 
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    # This is where Spotify will redirect after authorization (login)
    redirect_uri=redirect_uri, 
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True
)
# Create a Spotify client instance with the OAuth manager
# It will use sp_oauth to automatically handle getting the token and refreshing it
sp = Spotify(auth_manager=sp_oauth)

def store_token(token_info: dict):
    session["token_info"] = token_info
    session.permanent = True    

def get_spotify_client() -> Spotify | None:
    token = session.get("token_info")
    if not token:
        return None
    if sp_oauth.is_token_expired(token):
        token = sp_oauth.refresh_access_token(token["refresh_token"])
        store_token(token)
    return Spotify(auth=token["access_token"])

# Helper function to check if the user is logged in
def validate_user_token():
    token_info = sp_oauth.get_cached_token()

    # Check if the token exists and is valid
    if not token_info or not sp_oauth.validate_token(token_info):
        # If the token is not valid, try to refresh it
        if token_info and token_info.get('refresh_token'):
            app.logger.info(f"SPOTIPY: Token for {request.path} - Attempting to refresh.")
            try:
                sp_oauth.refresh_access_token(token_info['refresh_token'])
                app.logger.info(f"SPOTIPY: Token for {request.path} - Refreshed successfully.")
                return None # Token refreshed, proceed
            except Exception as e:
                app.logger.error(f"SPOTIPY: Token for {request.path} - Failed to refresh: {str(e)}")
                session.clear() # Clear session if refresh fails
                return jsonify({"error": "Session expired, failed to refresh token. Please log in again."}), 401
        else:
            session.clear() # Clear session if no refresh token or initial validation fails
            app.logger.warn(f"SPOTIPY: Token for {request.path} - No valid token/refresh token. User needs to re-authenticate.")
            return jsonify({"error": "User not authenticated or token expired. Please log in again."}), 401
    
    app.logger.debug(f"SPOTIPY: Token for {request.path} - Token is valid.")
    return None # Token is valid, proceed


# Endpoint to handle Spotify authorization
# This route is used to redirect the user to Spotify's authorization page 
# when they click the "Login with Spotify" button in the frontend.
@app.route("/spotify/authorize")
def home():
    app.logger.debug("SPOTIPY: Entered /spotify/authorize (home route)")
    if not sp_oauth.validate_token(sp_oauth.get_cached_token()):
        app.logger.debug("SPOTIPY: Token not valid or not found, getting auth URL.")
        auth_url = sp_oauth.get_authorize_url()
        app.logger.debug(f"SPOTIPY: Generated Spotify auth_url: {auth_url}")
        # Redirect the user to Spotify's authorization page to have them login
        return redirect(auth_url)
    
    app.logger.debug("SPOTIPY: Token is valid, redirecting to Svelte app frontend.")
    return redirect('http://localhost:5173/')

# Endpoint to handle the token exchange after Spotify redirects back to our app
# This route is called by the frontend after the user has logged in to Spotify and granted permissions.
@app.route("/api/spotify/token", methods=['POST'])
def spotify_token():
    # Get JSON data sent by the frontend (Specifically the 'code')
    data = request.get_json()
    code = data.get('code')
    app.logger.debug(f"SPOTIPY: /api/spotify/token received code: {'YES' if code else 'NO'}")

    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    try:
        # Exchange the code for an access token
        token_info = sp_oauth.get_access_token(code, check_cache=False)

        if not token_info:
            app.logger.error("SPOTIPY: Failed to get token info from Spotify from /api/spotify/token.")
            return jsonify({"error": "Failed to get token info"}), 500
        
        app.logger.debug(f"SPOTIPY: /api/spotify/token - Token info received: {token_info}")
        
        # get the user's Spotify profile
        spotify_user_profile = sp.current_user()
        app.logger.debug(f"SPOTIPY: /api/spotify/token - Fetched Spotify user profile: {spotify_user_profile}")

        # Prepare to store user info in session
        user_info = {
            "name": spotify_user_profile['display_name'],
            "email": spotify_user_profile['email'],
            "id": spotify_user_profile['id'],
            "moderator": False 
        }
        # Store user info in session 
        session["user"] = user_info 
        app.logger.debug(f"SPOTIPY: /api/spotify/token - User info stored in session. Session data: {dict(session)}")
        # Send a response back to the frontend with the user info
        return jsonify({"success": True, "user": user_info})
    except Exception as e:
        app.logger.error(f"SPOTIPY: Error in /api/spotify/token: {str(e)}")
        return jsonify({"error": "An error occurred during Spotify token exchange."}), 500
        

@app.route("/api/playlists")
def api_get_playlists():
    app.logger.debug("APP: Entered /api/playlists route")

    auth_error = validate_user_token()
    if auth_error:
        return auth_error

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


@app.route("/api/spotify/search")
def api_spotify_search():
    app.logger.debug("APP: Entered /api/spotify/search route")

    auth_error = validate_user_token()
    if auth_error:
        return auth_error

    query = request.args.get('q')
    # Default to searching for tracks, artists, and albums if no specific type is given
    # Types should be a comma-separated string, e.g., "track,artist,album"
    search_types_str = request.args.get('type', 'track,artist,album')
    search_types_list = [t.strip() for t in search_types_str.split(',')]
    limit_per_type = int(request.args.get('limit', 10)) # How many results per type

    if not query:
        app.logger.warn("APP: /api/spotify/search - No query provided.")
        return jsonify({"error": "Search query parameter 'q' is required"}), 400

    app.logger.debug(f"APP: /api/spotify/search - Query: '{query}', Types: {search_types_list}, Limit: {limit_per_type}")

    try:
        # The sp.search method can take a list of types
        results = sp.search(q=query, type=search_types_list, limit=limit_per_type)
        app.logger.debug("APP: /api/spotify/search - Search results from Spotify received.")
        
        # Process results to send a cleaner structure if desired, or send as is
        # Spotipy returns a dict with keys like 'tracks', 'artists', 'albums',
        # each containing a Paging Object with an 'items' list.
        
        # Example of structuring the response:
        processed_results = {}
        if results:
            if 'tracks' in results and results['tracks']:
                processed_results['tracks'] = [{
                    "id": item.get('id'),
                    "name": item.get('name'),
                    "artists": [{"name": artist.get('name'), "id": artist.get('id')} for artist in item.get('artists', [])],
                    "album_name": item.get('album', {}).get('name'),
                    "image_url": item.get('album', {}).get('images')[0].get('url') if item.get('album', {}).get('images') else None,
                    "url": item.get('external_urls', {}).get('spotify')
                } for item in results['tracks'].get('items', [])]
            
            if 'artists' in results and results['artists']:
                processed_results['artists'] = [{
                    "id": item.get('id'),
                    "name": item.get('name'),
                    "image_url": item.get('images')[0].get('url') if item.get('images') else None,
                    "genres": item.get('genres', []),
                    "url": item.get('external_urls', {}).get('spotify')
                } for item in results['artists'].get('items', [])]

            if 'albums' in results and results['albums']:
                 processed_results['albums'] = [{
                    "id": item.get('id'),
                    "name": item.get('name'),
                    "artists": [{"name": artist.get('name'), "id": artist.get('id')} for artist in item.get('artists', [])],
                    "image_url": item.get('images')[0].get('url') if item.get('images') else None,
                    "release_date": item.get('release_date'),
                    "total_tracks": item.get('total_tracks'),
                    "url": item.get('external_urls', {}).get('spotify')
                } for item in results['albums'].get('items', [])]

        return jsonify(processed_results)

    except Exception as e:
        app.logger.error(f"APP: /api/spotify/search - Error during Spotify search: {str(e)}")
        if hasattr(e, 'http_status') and e.http_status == 401:
             session.clear()
             return jsonify({"error": "Spotify authorization error during search. Please log in again."}), 401
        return jsonify({"error": "Failed to perform search on Spotify"}), 500

@app.route("/api/recommendations")
def recommendations():
    sp = get_spotify_client()
    if not sp:
        return jsonify({"error": "Spotify login required"}), 401

    user_id = sp.current_user()["id"]
    doc       = db.userprefs.find_one({"_id": user_id}, {"ratings": 1}) or {}
    ratings   = doc.get("ratings", {})
    likes     = [tid for tid, r in ratings.items() if r == "like"][:5]  
    dislikes  = {tid for tid, r in ratings.items() if r == "dislike"}

    if not likes:
        top  = sp.current_user_top_tracks(limit=5, time_range="medium_term")
        likes = [t["id"] for t in top["items"]] or ["4uLU6hMCjMI75M1A2tKUQC"] 

    raw  = sp.recommendations(seed_tracks=likes, limit=50)["tracks"]
    tracks = [t for t in raw if t["id"] not in dislikes][:20]

    return jsonify([{
        "id":       t["id"],
        "name":     t["name"],
        "artists":  ", ".join(a["name"] for a in t["artists"]),
        "albumArt": t["album"]["images"][0]["url"] if t["album"]["images"] else None,
        "preview":  t["preview_url"],
    } for t in tracks])

# This code is so that we can store "likes" and "dislikes" to MongoDB.
# First the code checks if the user has a valid Spotify account/token. If they do, then the code will extract the "like" or the "dislike" from request.
# Then the code gets the user's Spotify ID, where MongoDB will either create or upload a document with their ratings along with the time it was made. 

@app.route("/api/feedback/<track_id>", methods=["PUT"])
def feedback(track_id):
    auth_error = validate_user_token()
    if auth_error:
        return auth_error

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
    return jsonify({"success": True, "message": "Feedback saved"}), 200

# This code is so that the user can save a song to their Spotify account. 
# First the code checks if the user has a valid Spotify account/token. If they do then the code adds the song to their Spotify account.  

@app.route("/api/save/<track_id>", methods=["PUT"])
def save_track(track_id):
    auth_error = validate_user_token()
    if auth_error:
        return auth_error
    
    try:
        sp.current_user_saved_tracks_add([track_id])
        app.logger.debug(f"APP: /api/save - successfully saved track {track_id} for user")
        return jsonify({"success": True, "message": f"Track {track_id} saved successfully"}), 200
    except Exception as e:
        app.logger.error(f"APP: /api/save - Error saving track {track_id}: {str(e)}")

        return jsonify({"error": f"Failed to save track {track_id}"}), 500


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

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)),debug=debug_mode)
