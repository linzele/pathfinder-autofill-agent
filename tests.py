#!/usr/bin/env python3
"""
Unit tests for PathFinder Autofill Agent
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import json
from pathlib import Path

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
from main import PathFinderAutofill
from auth import PathFinderAuth
from extractor import DataExtractor
from analyzer import PathFinderAnalyzer


class TestDataExtractor(unittest.TestCase):
    """Tests for the DataExtractor class"""
    
    def setUp(self):
        """Set up for tests"""
        self.extractor = DataExtractor()
    
    @patch('extractor.requests.get')
    def test_extract_with_requests(self, mock_get):
        """Test extracting data from a website using requests"""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = """
        <html>
            <head>
                <title>Test Title</title>
                <meta name="description" content="Test Description">
                <meta name="keywords" content="tag1,tag2,tag3">
            </head>
            <body>
                <img src="image1.jpg" width="200" height="200">
                <div class="content">This is the main content</div>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test the extraction
        data = self.extractor._extract_with_requests("https://example.com")
        
        # Verify results
        self.assertEqual(data["title"], "Test Title")
        self.assertEqual(data["description"], "Test Description")
        self.assertEqual(data["tags"], ["tag1", "tag2", "tag3"])
        self.assertEqual(data["url"], "https://example.com")
    
    def test_detect_url_type(self):
        """Test URL type detection"""
        # Test SharePoint URL detection
        self.assertEqual(
            self.extractor.extract_from_url.__name__, 
            self.extractor.extract_from_url("https://example.sharepoint.com/sites/test").__name__
        )
        
        # Test regular website URL detection
        with patch.object(self.extractor, '_extract_from_website') as mock_extract:
            mock_extract.return_value = {"title": "Test"}
            result = self.extractor.extract_from_url("https://example.com")
            mock_extract.assert_called_once_with("https://example.com")


class TestPathFinderAuth(unittest.TestCase):
    """Tests for the PathFinderAuth class"""
    
    def setUp(self):
        """Set up for tests"""
        self.mock_page = MagicMock()
        self.mock_config = {
            "access_token": "test_token",
            "api_key": "test_api_key",
            "username": "test_user",
            "password": "test_password"
        }
        self.auth = PathFinderAuth(self.mock_config, self.mock_page)
    
    def test_token_cache_operations(self):
        """Test token cache operations"""
        # Test saving token to cache
        test_token = {"access_token": "test_token"}
        
        # Create a temporary file for token cache
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Replace cache path with temp file
            original_path = self.auth.TOKEN_CACHE_PATH
            self.auth.TOKEN_CACHE_PATH = temp_path
            
            # Save token
            self.auth._save_token_cache(test_token)
            
            # Check if token was saved
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
                self.assertEqual(saved_data["access_token"], "test_token")
                self.assertTrue("expiry" in saved_data)
            
            # Load token
            loaded_data = self.auth._load_token_cache()
            self.assertEqual(loaded_data["access_token"], "test_token")
            
        finally:
            # Restore original path and clean up
            self.auth.TOKEN_CACHE_PATH = original_path
            os.unlink(temp_path)
    
    @patch.object(PathFinderAuth, '_authenticate_with_token')
    def test_authentication_methods(self, mock_auth_with_token):
        """Test authentication method selection"""
        # Mock the token authentication method
        mock_auth_with_token.return_value = True
        
        # Test authentication with token from config
        result = self.auth.authenticate()
        mock_auth_with_token.assert_called_with("test_token")
        self.assertTrue(result)


class TestPathFinderAutofill(unittest.TestCase):
    """Tests for the PathFinderAutofill class"""
    
    def setUp(self):
        """Set up for tests"""
        # Create a temporary config file
        self.config_data = {
            "access_token": "test_token",
            "default_values": {
                "title": "Default Title",
                "description": "Default Description",
                "tags": ["default", "tags"]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            json.dump(self.config_data, temp_file)
            self.config_path = temp_file.name
        
        # Create the autofill agent
        self.agent = PathFinderAutofill(config_path=self.config_path)
    
    def tearDown(self):
        """Clean up after tests"""
        os.unlink(self.config_path)
    
    def test_load_config(self):
        """Test loading configuration"""
        self.assertEqual(self.agent.config["access_token"], "test_token")
        self.assertEqual(self.agent.config["default_values"]["title"], "Default Title")
    
    def test_load_missing_config(self):
        """Test loading a missing configuration file"""
        agent = PathFinderAutofill(config_path="nonexistent.json")
        self.assertEqual(agent.config, {})
        
        # Check that an example config was created
        self.assertTrue(Path("config.example.json").exists())
        
        # Clean up
        os.unlink("config.example.json")
    
    @patch('main.sync_playwright')
    def test_start_browser(self, mock_playwright):
        """Test starting the browser"""
        # Mock the playwright objects
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_chromium = MagicMock()
        mock_chromium.launch.return_value = mock_browser
        mock_pw_instance = MagicMock()
        mock_pw_instance.chromium = mock_chromium
        mock_playwright.return_value.start.return_value = mock_pw_instance
        
        # Test starting the browser
        self.agent.start(headless=True)
        
        # Verify browser was started
        mock_playwright.return_value.start.assert_called_once()
        mock_chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_page.assert_called_once()
        
        # Verify auth and extractor were initialized
        self.assertIsNotNone(self.agent.auth)
        self.assertIsNotNone(self.agent.extractor)
        
        # Test closing the browser
        self.agent.close()
        mock_browser.close.assert_called_once()
        mock_pw_instance.stop.assert_called_once()


class TestAnalyzer(unittest.TestCase):
    """Tests for the PathFinderAnalyzer class"""
    
    def setUp(self):
        """Set up for tests"""
        self.analyzer = PathFinderAnalyzer(headless=True)
    
    def test_analysis_cache_operations(self):
        """Test analysis cache operations"""
        # Test data
        test_data = {"test": "data"}
        
        # Create a temporary file for analysis cache
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Replace cache path with temp file
            original_path = self.analyzer.ANALYSIS_CACHE_PATH
            self.analyzer.ANALYSIS_CACHE_PATH = temp_path
            
            # Save analysis
            self.analyzer._save_analysis_cache(test_data)
            
            # Check if analysis was saved
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
                self.assertEqual(saved_data, test_data)
            
            # Load analysis
            loaded_data = self.analyzer._load_analysis_cache()
            self.assertEqual(loaded_data, test_data)
            
        finally:
            # Restore original path and clean up
            self.analyzer.ANALYSIS_CACHE_PATH = original_path
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()