import unittest
import sys
import os
import requests
from unittest.mock import patch, MagicMock

# Set environment variable before importing app
os.environ['SPOTIFY_API_KEY'] = 'test_api_key'

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

class TestRoutes(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        
        # Create mock response data
        self.mock_response_data = {
            'response': {
                'docs': [
                    {
                        'headline': {'main': 'Test Article'},
                        'abstract': 'Test abstract',
                        'web_url': 'https://example.com',
                        'pub_date': '2024-05-01T00:00:00Z'
                    }
                ]
            }
        }
        
    def tearDown(self):
        if 'SPOTIFY_API_KEY' in os.environ:
            del os.environ['SPOTIFY_API_KEY']
            
    @patch('requests.get')
    def test_get_articles(self, mock_get):
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_response_data
        mock_get.return_value = mock_response
        
        # Test the /api/articles route
        response = self.app.get('/api/articles?page=0')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('response', data)
        self.assertIn('docs', data['response'])
        self.assertIsInstance(data['response']['docs'], list)

    
if __name__ == '__main__':
    unittest.main()

