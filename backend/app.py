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
    
    
# Add these routes to your Flask app

@app.route('/api/spotify/discover-tracks')
def discover_tracks():
    """Get initial tracks from popular artists across different genres"""
    error_response = validate_user_token()
    if error_response:
        return error_response
    
    try:
        sp_client = get_spotify_client()
        if not sp_client:
            return jsonify({"error": "Failed to get Spotify client"}), 500
        
        # Get user's saved tracks to understand their taste
        user_tracks = []
        try:
            saved_tracks = sp_client.current_user_saved_tracks(limit=50)
            user_tracks = [track['track'] for track in saved_tracks['items']]
        except Exception as e:
            app.logger.info(f"No saved tracks found or error accessing them: {str(e)}")
        
        # If user has saved tracks, get artists from those
        if user_tracks:
            artist_ids = []
            for track in user_tracks[:20]:  # Use first 20 tracks
                for artist in track['artists']:
                    if artist['id'] not in artist_ids:
                        artist_ids.append(artist['id'])
            
            # Get top tracks from these artists
            all_tracks = []
            for artist_id in artist_ids[:10]:  # Limit to 10 artists to avoid rate limits
                try:
                    top_tracks = sp_client.artist_top_tracks(artist_id, country='US')
                    all_tracks.extend(top_tracks['tracks'][:3])  # Top 3 tracks per artist
                except Exception as e:
                    app.logger.error(f"Error getting top tracks for artist {artist_id}: {str(e)}")
                    continue
            
            if all_tracks:
                return jsonify({"tracks": all_tracks})
        
        # Fallback: Get tracks from popular artists across different genres
        # Define some popular artist IDs across different genres
        popular_artists = [
            "4NHQUGzhtTLFvgF5SZesLK",  # Tame Impala (Psychedelic Rock)
            "06HL4z0CvFAxyc27GXpf02",  # Taylor Swift (Pop)
            "3TVXtAsR1Inumwj472S9r4",  # Drake (Hip Hop)
            "1HY2Jd0NmPuamShAr6KMms",  # Lady Gaga (Pop)
            "4q3ewBCX7sLwd24UFkeCZp",  # Eminem (Hip Hop)
            "1dfeR4HaWDbWqFHLkxsg1d",  # Queen (Rock)
            "7dGJo4pcD2V6oG8kP0tJRR",  # Eminem (Alternative)
            "0du5cEVh5yTK9QJze8zA0C",  # Bruno Mars (Pop/R&B)
            "53XhwfbYqKCa1cC15pYq2q",  # Imagine Dragons (Alternative Rock)
            "1uNFoZAHBGtllmzznpCI3s",  # Justin Bieber (Pop)
        ]
        
        all_tracks = []
        for artist_id in popular_artists:
            try:
                top_tracks = sp_client.artist_top_tracks(artist_id, country='US')
                all_tracks.extend(top_tracks['tracks'][:2])  # Top 2 tracks per artist
            except Exception as e:
                app.logger.error(f"Error getting top tracks for artist {artist_id}: {str(e)}")
                continue
        
        return jsonify({"tracks": all_tracks})
        
    except Exception as e:
        app.logger.error(f"Error in discover_tracks: {str(e)}")
        return jsonify({"error": "Failed to fetch tracks"}), 500

@app.route('/api/spotify/artist-tracks/<artist_id>')
def get_artist_tracks(artist_id):
    """Get more tracks from a specific artist"""
    error_response = validate_user_token()
    if error_response:
        return error_response
    
    try:
        sp_client = get_spotify_client()
        if not sp_client:
            return jsonify({"error": "Failed to get Spotify client"}), 500
        
        # Get artist's top tracks
        top_tracks = sp_client.artist_top_tracks(artist_id, country='US')
        
        # Get artist's albums and more tracks
        albums = sp_client.artist_albums(artist_id, album_type='album,single', limit=10)
        album_tracks = []
        
        for album in albums['items']:
            try:
                tracks = sp_client.album_tracks(album['id'], limit=5)
                for track in tracks['items']:
                    # Add album info to track
                    track['album'] = {
                        'id': album['id'],
                        'name': album['name'],
                        'images': album['images']
                    }
                    album_tracks.append(track)
            except Exception as e:
                app.logger.error(f"Error getting tracks from album {album['id']}: {str(e)}")
                continue
        
        # Combine top tracks and album tracks
        all_tracks = top_tracks['tracks'] + album_tracks
        
        return jsonify({"tracks": all_tracks})
        
    except Exception as e:
        app.logger.error(f"Error getting artist tracks: {str(e)}")
        return jsonify({"error": "Failed to fetch artist tracks"}), 500

@app.route('/api/spotify/genre-tracks/<genre>')
def get_genre_tracks(genre):
    """Get tracks from artists in a specific genre"""
    error_response = validate_user_token()
    if error_response:
        return error_response
    
    try:
        sp_client = get_spotify_client()
        if not sp_client:
            return jsonify({"error": "Failed to get Spotify client"}), 500
        
        # Search for artists in the genre
        search_results = sp_client.search(
            q=f'genre:"{genre}"', 
            type='artist', 
            limit=10
        )
        
        all_tracks = []
        for artist in search_results['artists']['items']:
            try:
                top_tracks = sp_client.artist_top_tracks(artist['id'], country='US')
                all_tracks.extend(top_tracks['tracks'][:3])  # Top 3 tracks per artist
            except Exception as e:
                app.logger.error(f"Error getting top tracks for artist {artist['id']}: {str(e)}")
                continue
        
        return jsonify({"tracks": all_tracks})
        
    except Exception as e:
        app.logger.error(f"Error getting genre tracks: {str(e)}")
        return jsonify({"error": "Failed to fetch genre tracks"}), 500

@app.route('/api/spotify/similar-artists/<artist_id>')
def get_similar_artists_tracks(artist_id):
    """Get tracks from artists similar to the given artist"""
    error_response = validate_user_token()
    if error_response:
        return error_response
    
    try:
        sp_client = get_spotify_client()
        if not sp_client:
            return jsonify({"error": "Failed to get Spotify client"}), 500
        
        # Get related artists
        related_artists = sp_client.artist_related_artists(artist_id)
        
        all_tracks = []
        for artist in related_artists['artists'][:10]:  # Limit to 10 related artists
            try:
                top_tracks = sp_client.artist_top_tracks(artist['id'], country='US')
                all_tracks.extend(top_tracks['tracks'][:2])  # Top 2 tracks per artist
            except Exception as e:
                app.logger.error(f"Error getting top tracks for related artist {artist['id']}: {str(e)}")
                continue
        
        return jsonify({"tracks": all_tracks})
        
    except Exception as e:
        app.logger.error(f"Error getting similar artists tracks: {str(e)}")
        return jsonify({"error": "Failed to fetch similar artists tracks"}), 500

# Store user preferences for better recommendations
@app.route('/api/feedback/<track_id>', methods=['PUT'])
def store_feedback(track_id):
    """Store user feedback (like/dislike) for a track"""
    error_response = validate_user_token()
    if error_response:
        return error_response
    
    try:
        sp_client = get_spotify_client()
        if not sp_client:
            return jsonify({"error": "Failed to get Spotify client"}), 500
        
        # Get user info
        user_info = sp_client.current_user()
        user_id = user_info['id']
        
        data = request.get_json()
        rating = data.get('rating')  # 'like' or 'dislike'
        
        if rating not in ['like', 'dislike']:
            return jsonify({"error": "Invalid rating"}), 400
        
        # Get track info to store artist and genre data
        track_info = sp_client.track(track_id)
        
        # Store feedback in database
        feedback_data = {
            "user_id": user_id,
            "track_id": track_id,
            "rating": rating,
            "track_name": track_info['name'],
            "artists": [{"id": artist['id'], "name": artist['name']} for artist in track_info['artists']],
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Upsert feedback (update if exists, insert if doesn't)
        db.user_feedback.update_one(
            {"user_id": user_id, "track_id": track_id},
            {"$set": feedback_data},
            upsert=True
        )
        
        return jsonify({"message": "Feedback stored successfully"})
        
    except Exception as e:
        app.logger.error(f"Error storing feedback: {str(e)}")
        return jsonify({"error": "Failed to store feedback"}), 500

@app.route('/api/spotify/personalized-tracks')
def get_personalized_tracks():
    """Get tracks based on user's previous likes"""
    error_response = validate_user_token()
    if error_response:
        return error_response
    
    try:
        sp_client = get_spotify_client()
        if not sp_client:
            return jsonify({"error": "Failed to get Spotify client"}), 500
        
        # Get user info
        user_info = sp_client.current_user()
        user_id = user_info['id']
        
        # Get user's liked tracks from database
        liked_feedback = list(db.user_feedback.find({
            "user_id": user_id,
            "rating": "like"
        }).sort("timestamp", -1).limit(20))
        
        if not liked_feedback:
            # If no likes yet, fall back to discover_tracks
            return discover_tracks()
        
        # Extract artist IDs from liked tracks
        artist_ids = []
        for feedback in liked_feedback:
            for artist in feedback['artists']:
                if artist['id'] not in artist_ids:
                    artist_ids.append(artist['id'])
        
        all_tracks = []
        
        # Get more tracks from liked artists
        for artist_id in artist_ids[:10]:  # Limit to prevent rate limits
            try:
                top_tracks = sp_client.artist_top_tracks(artist_id, country='US')
                all_tracks.extend(top_tracks['tracks'][:3])
                
                # Also get tracks from related artists
                related_artists = sp_client.artist_related_artists(artist_id)
                for related_artist in related_artists['artists'][:3]:  # 3 related artists
                    related_top_tracks = sp_client.artist_top_tracks(related_artist['id'], country='US')
                    all_tracks.extend(related_top_tracks['tracks'][:2])  # 2 tracks each
                    
            except Exception as e:
                app.logger.error(f"Error getting personalized tracks for artist {artist_id}: {str(e)}")
                continue
        
        # Remove duplicates based on track ID
        seen_tracks = set()
        unique_tracks = []
        for track in all_tracks:
            if track['id'] not in seen_tracks:
                seen_tracks.add(track['id'])
                unique_tracks.append(track)
        
        return jsonify({"tracks": unique_tracks})
        
    except Exception as e:
        app.logger.error(f"Error getting personalized tracks: {str(e)}")
        return jsonify({"error": "Failed to fetch personalized tracks"}), 500
    
	
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
