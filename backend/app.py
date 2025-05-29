# Written by Navjeet for HW3

from flask import Flask, jsonify, send_from_directory, request, session, redirect, url_for
import os
from flask_cors import CORS
import requests
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timezone
from jose import jwt

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
redirect_uri = 'http://localhost:5000/callback'
scope = 'playlist-read-private'

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
    if not sp_oauth.validate_token(sp_oauth.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return redirect(url_for('get_playlists'))

@app.route("/callback")
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('get_playlists'))

@app.route("/get_playlists")
def get_playlists():
    if not sp_oauth.validate_token(sp_oauth.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    playlists = sp.current_user_playlists()
    playlists_info = [(pl['name'], pl['external_urls']['spotify']) for pl in playlists['items']]
    playlists_html = '<br>'.join([f'<a href="{url}">{name}</a>' for name, url in playlists_info])

    return playlists_html

# The code down below should give us the info from the user. It checks if a user is already logged in by looking for their data.
# If the user is found in the session, then it will set the user's name, email, and moderator status.
# We needed to read up on dex documentation and the links from the lab.
# Dex: https://dexidp.io/docs/
# MongoDB in a Flask Application: https://www.digitalocean.com/community/tutorials/how-to-use-mongodb-in-a-flask-application
# Sending Data from a Flask app to MongoDB Database: https://www.geeksforgeeks.org/sending-data-from-a-flask-app-to-mongodb-database/
# Flask documentation: https://flask.palletsprojects.com/en/stable/

@app.before_request
def user():
    if "user" in session:
        request.user = session["user"]
    else:
        request.user = None

# The code down below is a route that is called after the user logs in through Dex.
# The code should work by getting the user's name, email, and moderator status from the token from Dex.
# Then it stores that information in the Flask session so that is is saved. Then it will go back to the homepage and showed that the user is logged in.
# Authorization Code Flow: https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow
# JWT: https://jwt.io/introduction
# Flask-OIDC: https://flask-oidc.readthedocs.io/en/latest/

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

# The code down below is a route that is used when the user wants to logout.
# The code works by clearing out the session data, and then going back to the homepage.

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

# The code down below is a route that the frontend can use to help identify the user's info, email, and moderator role.

@app.route("/api/me")
def get_me():
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
