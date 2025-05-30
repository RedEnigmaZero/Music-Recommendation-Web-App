import pytest
from app import app as create_app

# In order to understand how to write the tests, first we looked at the lab slides, then we had to do some reading from pytest documentation and flask documentation. We also read up on documentation in NYT's response fields to help make tests on articles.
# Here are the links of the documentation that we used. 
# https://docs.pytest.org/en/stable/example/simple.html - Pytest documentation
# https://flask.palletsprojects.com/en/latest/testing/#the-test-client - Flask documentation
# https://canvas.ucdavis.edu/courses/993295/files/folder/Lab%20Materials/week%205? - Week 5 Lab Slides
# https://developer.nytimes.com/docs/articlesearch-product/1/overview#response-fields - NYT's API Response Fields

# This is the test client.
@pytest.fixture
def client():
    create_app.config["TESTING"] = True
    with create_app.test_client() as client:
        yield client

# The code down below is to test the API key. Specifically it is to make sure that the API key is returned.
# How the code works is that response sends a get request to the /api/key route. Then the server replies with code 200 which means everything is going ok.
# Next, we convert the JSON response into Python and check if the "data" has the apiKey in it. After we have found the apiKey we check to see that it is a string. 
# Finally, we make sure that the key is real by checking its length, if greater than 25 we deem the key to be real. We chose 25 for the length as the key we used for this project was roughly 30 characters long so a key must be somewhat similar length.
def test_api_key(client):
    response = client.get("/api/key")
    assert response.status_code == 200
    data = response.get_json()
    assert "apiKey" in data
    assert isinstance(data["apiKey"], str)
    assert len(data["apiKey"]) > 25

# The code down below is to test /api/news route and structure and content. Specifically it is to check if it returns articles and that the article contains either "UC Davis" or "Sacramento".
# How the code works is that response sends a get request to the /api/news route. Then the server replies with code 200 which means everything is going ok.
# Next, we convert the JSON response into Python. According to the NYT API Response Field, the docs is the list of article results so we end up checking that. 
# Finally, if there are articles which there should be then we go through each article to check if there is "UC Davis" or "Sacramento" in the article.
def test_news_content(client):
    response = client.get("/api/news")
    assert response.status_code == 200
    data = response.get_json()
    assert "response" in data
    assert "docs" in data["response"]
    articles = data["response"]["docs"]
    assert isinstance(articles,list)
    
    if not articles:
        pytest.skip("Zero articles returned")
        
    for content in articles:
        abstract = (content.get("abstract")).lower()
        if "uc davis" in abstract or "sacramento" in abstract:
            return 
    assert False, "No UC Davis or Sacramento in the articles"

# The code down below is to test the /api/comments/<comment_id>/moderater route.
# First it will create a comment, and then deleting it using the moderator permission. 
# The code works by first making a POST to /api/comments to simulate a comment. THen a POST sent to /api/comments/<comment_id>/moderater to simulate deleting a comment.
# Then it should show that the comment was deleted.          
def test_moderator_delete(client):
    article_id = "pytest-article"
    post = client.post("/api/comments", json={
        "article_id": article_id,
        "text": "Delete me please",
        "parent_id": "root"
    }, headers={"X-User-Email": "pytest@test.com", "X-User-Is-Moderator": "true"})
    comment = post.get_json()
    comment_id = comment["_id"]
    
    res = client.post(f"/api/comments/{comment_id}/moderater", headers={
        "X-User-Email": "pytest@test,com",
        "X-User-Is-Moderator": "true"
    })
    assert res.status_code == 200
    message = res.get_json()
    assert message["message"] == "Comment deleted"  

# The code down below is to test /api/comments route. 
# The code should create a comment and then retrive that comment for the same article.    
def test_get_comments(client):
    article_id = "pytest-article"
    post = client.post("/api/comments", json={
        "article_id": article_id,
        "text": "Comments",
        "parent_id": "root"
    }, headers={"X-User-Email": "pytest@test.com", "X-User-Is-Moderator": "true"})
    
    res = client.get(f"/api/comments?article_id={article_id}")
    assert res.status_code == 200
    comments = res.get_json()
    assert isinstance(comments, list)
    assert any(c["text"] == "Comments" for c in comments)

# The code down below is to test if we can recover a saved article. 
# The code works by saving an article via POST, then fetches it using GET to verify the data inside. 
def test_get_article(client):
    article_id = "https://www.nytimes.com/2023/05/04/us/davis-stabbings-aest-california.html"
    client.post("/api/articles", json={
        "url": article_id,
        "headline": "Article",
        "abstract": "Summary",
        "byline": "Author"
    })

    res = client.get(f"/api/articles/{article_id}")
    assert res.status_code == 200
    article = res.get_json()
    assert article["url"] == article_id
    assert article["headline"] == "Article"
    
# The code down below is to test if a non-moderator cannot delete a comment.
# The code posts a comment and then tries to delete it with a non-moderator, which should not work because only moderators are able to do that.
def test_non_moderator_delete(client):
    post = client.post("/api/comments", json={
        "article_id": "dummy test",
        "text": "No delete",
        "parent_id": "root"
    }, headers={"X-User-Email": "pytest@test.com", "X-User-Is-Moderator": "false"})
    
    comment_id = post.get_json()["_id"]
    res = client.post(f"/api/comments/{comment_id}/moderater", headers={
        "X-User-Is-Moderator": "false"
    })
    assert res.status_code == 400
    assert res.get_json()["error"] == "Unauthorized/Not Moderator"

      
    

