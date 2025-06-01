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

@app.route('/api/spotify/recommendations', methods=['GET'])
def get_spotify_recommendations():
    """
    Get personalized recommendations based on seed tracks (liked songs)
    """
    # Validate user token
    token_validation = validate_user_token()
    if token_validation:
        return token_validation

    try:
        # Get Spotify client
        spotify_client = get_spotify_client()
        if not spotify_client:
            return jsonify({"error": "Unable to get Spotify client"}), 401
        
        # Get seed tracks from query parameters
        seed_tracks = request.args.get('seed_tracks', '')
        if not seed_tracks:
            return jsonify({"error": "Missing seed_tracks parameter"}), 400
            
        seed_track_list = seed_tracks.split(',')[:5]  # Spotify allows max 5 seed tracks
        
        # Get recommendations based on seed tracks
        recommendations = spotify_client.recommendations(
            seed_tracks=seed_track_list,
            limit=20,  # Get 20 recommendations
            market='US'  # You can make this configurable
        )
        
        app.logger.info(f"Got {len(recommendations['tracks'])} recommendations based on {len(seed_track_list)} seed tracks")
        
        return jsonify({"tracks": recommendations['tracks']}), 200
        
    except Exception as e:
        app.logger.error(f"Error getting recommendations from Spotify: {str(e)}")
        return jsonify({"error": "Failed to get recommendations from Spotify"}), 500


@app.route('/api/spotify/discover-tracks', methods=['GET'])
def discover_spotify_tracks():
    """
    Discover tracks from Spotify using various methods like:
    - User's top tracks
    - Featured playlists
    - New releases
    - Recommendations based on user's taste
    """
    # Validate user token
    token_validation = validate_user_token()
    if token_validation:
        return token_validation

    try:
        # Get Spotify client
        spotify_client = get_spotify_client()
        if not spotify_client:
            return jsonify({"error": "Unable to get Spotify client"}), 401
        
        discovered_tracks = []
        
        try:
            # Method 1: Get user's top tracks (medium term)
            top_tracks = spotify_client.current_user_top_tracks(limit=10, time_range='medium_term')
            discovered_tracks.extend(top_tracks['items'])
            app.logger.info(f"Found {len(top_tracks['items'])} top tracks")
        except Exception as e:
            app.logger.warning(f"Could not fetch top tracks: {str(e)}")
        
        try:
            # Method 2: Get featured playlists and sample tracks from them
            featured_playlists = spotify_client.featured_playlists(limit=5)
            for playlist in featured_playlists['playlists']['items']:
                try:
                    playlist_tracks = spotify_client.playlist_tracks(playlist['id'], limit=3)
                    for item in playlist_tracks['items']:
                        if item['track'] and item['track']['type'] == 'track':
                            discovered_tracks.append(item['track'])
                except Exception as e:
                    app.logger.warning(f"Could not fetch tracks from playlist {playlist['name']}: {str(e)}")
                    continue
            app.logger.info(f"Added tracks from featured playlists")
        except Exception as e:
            app.logger.warning(f"Could not fetch featured playlists: {str(e)}")
        
        try:
            # Method 3: Get new releases
            new_releases = spotify_client.new_releases(limit=10)
            for album in new_releases['albums']['items']:
                try:
                    album_tracks = spotify_client.album_tracks(album['id'], limit=2)
                    for track in album_tracks['items']:
                        # Need to get full track info since album_tracks returns simplified
                        full_track = spotify_client.track(track['id'])
                        discovered_tracks.append(full_track)
                except Exception as e:
                    app.logger.warning(f"Could not fetch tracks from album {album['name']}: {str(e)}")
                    continue
            app.logger.info(f"Added tracks from new releases")
        except Exception as e:
            app.logger.warning(f"Could not fetch new releases: {str(e)}")
        
        # If we have some tracks, try to get recommendations based on them
        if discovered_tracks:
            try:
                # Get a few seed tracks for recommendations
                seed_tracks = [track['id'] for track in discovered_tracks[:5]]
                recommendations = spotify_client.recommendations(seed_tracks=seed_tracks, limit=15)
                discovered_tracks.extend(recommendations['tracks'])
                app.logger.info(f"Added {len(recommendations['tracks'])} recommended tracks")
            except Exception as e:
                app.logger.warning(f"Could not fetch recommendations: {str(e)}")
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_tracks = []
        for track in discovered_tracks:
            if track['id'] not in seen_ids:
                seen_ids.add(track['id'])
                unique_tracks.append(track)
                if len(unique_tracks) >= 25:  # Limit to 25 tracks
                    break
        
        if not unique_tracks:
            # Fallback: Get some popular tracks if nothing else worked
            app.logger.info("No tracks found, using fallback popular tracks")
            # You can implement a fallback here or return an error
            return jsonify({"error": "Could not discover any tracks"}), 404
        
        app.logger.info(f"Returning {len(unique_tracks)} unique tracks")
        return jsonify({"tracks": unique_tracks}), 200
        
    except Exception as e:
        app.logger.error(f"Error discovering tracks from Spotify: {str(e)}")
        return jsonify({"error": "Failed to discover tracks from Spotify"}), 500


@app.route('/api/spotify/tracks', methods=['GET'])
def get_spotify_tracks():
    """
    Get track details from Spotify API using the "Get Several Tracks" endpoint
    Expects comma-separated track IDs in the 'ids' query parameter
    """
    # Validate user token
    token_validation = validate_user_token()
    if token_validation:
        return token_validation

    try:
        # Get the comma-separated track IDs from query parameters
        track_ids = request.args.get('ids')
        if not track_ids:
            return jsonify({"error": "Missing 'ids' parameter"}), 400
        
        # Validate that we don't exceed the 50 ID limit
        ids_list = track_ids.split(',')
        if len(ids_list) > 50:
            return jsonify({"error": "Maximum 50 track IDs allowed"}), 400
        
        # Get Spotify client
        spotify_client = get_spotify_client()
        if not spotify_client:
            return jsonify({"error": "Unable to get Spotify client"}), 401
        
        # Get market (country code) from request or default to US
        market = request.args.get('market', 'US')
        
        # Make the API call to Spotify
        tracks_data = spotify_client.tracks(tracks=ids_list, market=market)
        
        return jsonify(tracks_data), 200
        
    except Exception as e:
        app.logger.error(f"Error fetching tracks from Spotify: {str(e)}")
        return jsonify({"error": "Failed to fetch tracks from Spotify"}), 500

# This code is so that we can store "likes" and "dislikes" to MongoDB.
# First the code checks if the user has a valid Spotify account/token. If they do, then the code will extract the "like" or the "dislike" from request.
# Then the code gets the user's Spotify ID, where MongoDB will either create or upload a document with their ratings along with the time it was made. 

@app.route("/api/feedback/<track_id>", methods=["PUT"])
def feedback(track_id):
    app.logger.debug(f"APP: Entered /api/feedback/{track_id} route")

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
    app.logger.debug(f"APP: Entered /api/save/{track_id} route")

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

@app.route("/api/browse-categories")
def api_get_browse_categories():
    app.logger.debug("APP: Entered /api/browse-categories route")

    auth_error = validate_user_token()
    if auth_error:
        return auth_error

    # Get query parameters with defaults
    limit = int(request.args.get('limit', 20))  # Default to 20, max 50
    offset = int(request.args.get('offset', 0))  # Default to 0
    locale = request.args.get('locale', None)  # Optional locale parameter
    
    # Ensure limit is within Spotify's bounds
    limit = min(max(limit, 1), 50)

    try:
        # Call Spotify's browse categories endpoint
        # Build parameters dictionary
        params = {
            'limit': limit,
            'offset': offset
        }
        if locale:
            params['locale'] = locale

        categories_result = sp.categories(**params)
        app.logger.debug(f"APP: /api/browse-categories - Categories fetched from Spotify: {'Data received' if categories_result else 'No data'}")

        categories_data = []
        if categories_result and categories_result.get('categories') and categories_result['categories'].get('items'):
            for item in categories_result['categories']['items']:
                # Get the first icon URL if available
                icon_url = None
                if item.get('icons') and len(item['icons']) > 0:
                    icon_url = item['icons'][0].get('url')

                category_info = {
                    "id": item.get('id'),
                    "name": item.get('name'),
                    "href": item.get('href'),
                    "icons": item.get('icons', []),
                    "image": icon_url  # For easier frontend access
                }
                categories_data.append(category_info)

        app.logger.debug(f"APP: /api/browse-categories - Processed {len(categories_data)} categories.")
        
        # Return the data in a format similar to your existing endpoints
        categories_info = categories_result.get('categories', {}) if categories_result else {}
        return jsonify({
            "items": categories_data,
            "total": categories_info.get('total', 0),
            "limit": categories_info.get('limit', limit),
            "offset": categories_info.get('offset', offset),
            "next": categories_info.get('next'),
            "previous": categories_info.get('previous'),
            "href": categories_info.get('href')
        })

    except Exception as e:
        app.logger.error(f"APP: /api/browse-categories - Error fetching browse categories: {str(e)}")
        if hasattr(e, 'http_status') and e.http_status == 401:  # Spotify API returned 401
            session.clear() 
            return jsonify({"error": "Spotify authorization error. Please log in again."}), 401
        return jsonify({"error": "Failed to fetch browse categories from Spotify"}), 500

@app.route("/api/user-tracks")
def api_get_user_tracks():
    app.logger.debug("APP: Entered /api/user-tracks route")

    auth_error = validate_user_token()
    if auth_error:
        return auth_error

    # Get query parameters with defaults
    limit = int(request.args.get('limit', 20))  # Default to 20, max 50
    offset = int(request.args.get('offset', 0))  # Default to 0
    
    # Ensure limit is within Spotify's bounds
    limit = min(max(limit, 1), 50)

    try:
        # First try to get user's saved tracks (using existing scope user-library-read)
        saved_tracks_result = sp.current_user_saved_tracks(limit=limit, offset=offset)
        app.logger.debug(f"APP: /api/user-tracks - User's saved tracks fetched from Spotify: {'Data received' if saved_tracks_result else 'No data'}")

        tracks_data = []
        if saved_tracks_result and saved_tracks_result.get('items'):
            for item in saved_tracks_result['items']:
                track = item.get('track', {})
                album = track.get('album', {})
                
                # Get the first image URL if available
                image_url = None
                if album.get('images') and len(album['images']) > 0:
                    image_url = album['images'][0].get('url')

                track_info = {
                    "id": track.get('id'),
                    "name": track.get('name'),
                    "artists": ", ".join(artist.get('name', '') for artist in track.get('artists', [])),
                    "album_name": album.get('name'),
                    "image": image_url,
                    "added_at": item.get('added_at'),
                    "duration_ms": track.get('duration_ms'),
                    "url": track.get('external_urls', {}).get('spotify'),
                    "preview_url": track.get('preview_url'),
                    "popularity": track.get('popularity', 0)
                }
                tracks_data.append(track_info)

        # If no saved tracks, fall back to top tracks (using existing scope user-top-read)
        if not tracks_data:
            app.logger.debug("APP: /api/user-tracks - No saved tracks found, falling back to top tracks")
            top_tracks_result = sp.current_user_top_tracks(limit=limit, time_range="short_term")
            
            if top_tracks_result and top_tracks_result.get('items'):
                for track in top_tracks_result['items']:
                    album = track.get('album', {})
                    
                    # Get the first image URL if available
                    image_url = None
                    if album.get('images') and len(album['images']) > 0:
                        image_url = album['images'][0].get('url')

                    track_info = {
                        "id": track.get('id'),
                        "name": track.get('name'),
                        "artists": ", ".join(artist.get('name', '') for artist in track.get('artists', [])),
                        "album_name": album.get('name'),
                        "image": image_url,
                        "added_at": None,  # Top tracks don't have added_at
                        "duration_ms": track.get('duration_ms'),
                        "url": track.get('external_urls', {}).get('spotify'),
                        "preview_url": track.get('preview_url'),
                        "popularity": track.get('popularity', 0)
                    }
                    tracks_data.append(track_info)

        app.logger.debug(f"APP: /api/user-tracks - Processed {len(tracks_data)} user tracks.")
        
        # Return the data in a format consistent with your existing endpoints
        return jsonify({
            "items": tracks_data,
            "total": len(tracks_data),
            "limit": limit,
            "offset": offset,
            "source": "saved_tracks" if saved_tracks_result and saved_tracks_result.get('items') else "top_tracks"
        })

    except Exception as e:
        app.logger.error(f"APP: /api/user-tracks - Error fetching user tracks: {str(e)}")
        if hasattr(e, 'http_status') and e.http_status == 401:  # Spotify API returned 401
            session.clear() 
            return jsonify({"error": "Spotify authorization error. Please log in again."}), 401
        return jsonify({"error": "Failed to fetch user tracks from Spotify"}), 500

@app.route("/api/new-releases")
def api_get_new_releases():
    app.logger.debug("APP: Entered /api/new-releases route")

    auth_error = validate_user_token()
    if auth_error:
        return auth_error

    # Get query parameters with defaults
    limit = int(request.args.get('limit', 20))  # Default to 20, max 50
    offset = int(request.args.get('offset', 0))  # Default to 0
    
    # Ensure limit is within Spotify's bounds
    limit = min(max(limit, 1), 50)

    try:
        # Call Spotify's browse new releases endpoint
        new_releases_result = sp.new_releases(limit=limit, offset=offset)
        app.logger.debug(f"APP: /api/new-releases - New releases fetched from Spotify: {'Data received' if new_releases_result else 'No data'}")

        releases_data = []
        if new_releases_result and new_releases_result.get('albums') and new_releases_result['albums'].get('items'):
            for item in new_releases_result['albums']['items']:
                image_url = None
                # Get the first image URL if available
                if item.get('images') and len(item['images']) > 0:
                    image_url = item['images'][0].get('url')

                release_info = {
                    "id": item.get('id'),
                    "name": item.get('name'),
                    "artists": ", ".join(artist.get('name', '') for artist in item.get('artists', [])),
                    "album_type": item.get('album_type'),
                    "release_date": item.get('release_date'),
                    "total_tracks": item.get('total_tracks'),
                    "url": item.get('external_urls', {}).get('spotify'),
                    "image": image_url,
                    "available_markets": item.get('available_markets', [])
                }
                releases_data.append(release_info)

        app.logger.debug(f"APP: /api/new-releases - Processed {len(releases_data)} new releases.")
        
        # Return the data in a format similar to your existing endpoints
        return jsonify({
            "items": releases_data,
            "total": new_releases_result.get('albums', {}).get('total', 0),
            "limit": limit,
            "offset": offset,
            "next": new_releases_result.get('albums', {}).get('next'),
            "previous": new_releases_result.get('albums', {}).get('previous')
        })

    except Exception as e:
        app.logger.error(f"APP: /api/new-releases - Error fetching new releases: {str(e)}")
        if hasattr(e, 'http_status') and e.http_status == 401:  # Spotify API returned 401
            session.clear() 
            return jsonify({"error": "Spotify authorization error. Please log in again."}), 401
        return jsonify({"error": "Failed to fetch new releases from Spotify"}), 500

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)),debug=debug_mode)
