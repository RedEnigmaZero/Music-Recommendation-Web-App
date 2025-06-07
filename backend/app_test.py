import pytest
from app import app
from unittest.mock import patch

# In order to understand how to write the tests, first we looked at the lab slides, then we had to do some reading from pytest documentation and flask documentation. We also read up on documentation in NYT's response fields to help make tests on articles.
# Here are the links of the documentation that we used. 
# https://docs.pytest.org/en/stable/example/simple.html - Pytest documentation
# https://flask.palletsprojects.com/en/latest/testing/#the-test-client - Flask documentation
# https://canvas.ucdavis.edu/courses/993295/files/folder/Lab%20Materials/week%205? - Week 5 Lab Slides

# This is the test client.
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# Test that the /spotify/authorize route redirects to Spotify login
def test_spotify_authorize_redirect(client):
    with patch("app.sp_oauth.get_cached_token", return_value=None), \
         patch("app.sp_oauth.validate_token", return_value=False), \
         patch("app.sp_oauth.get_authorize_url", return_value="https://accounts.spotify.com/auth"):
        res = client.get("/spotify/authorize")
        assert res.status_code == 302
        assert "https://accounts.spotify.com/auth" in res.location

# Test that the /api/spotify/token route returns an error if no token
def test_spotify_token(client):
    res = client.post("/api/spotify/token", json={})
    assert res.status_code == 400
    assert res.json["error"] == "No code provided"

# Test that when logging out the user it clears the user session and redirects to the homepage
def test_logout(client):
    with client.session_transaction() as sess:
        sess["user"] = {"name": "Navjeet"}
    res = client.get("/logout")
    assert res.status_code == 302
    assert res.location.endswith("localhost:5173/")

# Test that /api/me route returns nothing when no user is logged in.
def test_no_user(client):
    res = client.get("/api/me")
    assert res.status_code == 200
    assert res.json is None

# Test that the /test-mongo route returns a list of collections from the database
def test_mongo_endpoint(client):
    with patch("app.db.list_collection_names", return_value=["user_feedback", "tracks"]):
        res = client.get("/test-mongo")
        assert res.status_code == 200
        assert "collections" in res.json


      
    

