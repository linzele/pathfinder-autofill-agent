#!/usr/bin/env python3
"""
Authentication module for PathFinder Autofill Agent

Handles various authentication methods for the PathFinder website
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path

from playwright.sync_api import Page
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger("pathfinder-auth")

class PathFinderAuth:
    """
    Handles authentication with the PathFinder website using various methods:
    1. Access token authentication
    2. API key authentication
    3. Username/password authentication
    """
    
    LOGIN_URL = "https://pathfinder.xtech-sg.net/login"
    TOKEN_CACHE_PATH = ".auth_cache.json"
    
    def __init__(self, config: Dict[str, Any], page: Page):
        """Initialize the authentication module with configuration and browser page"""
        self.config = config
        self.page = page
        self.token_cache = self._load_token_cache()
    
    def _load_token_cache(self) -> Dict[str, Any]:
        """Load cached authentication tokens if they exist"""
        try:
            if Path(self.TOKEN_CACHE_PATH).exists():
                with open(self.TOKEN_CACHE_PATH, 'r') as f:
                    cache = json.load(f)
                    # Check if the cached token is expired
                    if 'expiry' in cache and cache['expiry'] > time.time():
                        logger.info("Found valid cached authentication token")
                        return cache
                    logger.info("Cached authentication token expired")
            return {}
        except Exception as e:
            logger.error(f"Error loading token cache: {str(e)}")
            return {}
    
    def _save_token_cache(self, token_data: Dict[str, Any]) -> None:
        """Save authentication tokens to cache"""
        try:
            # Set an expiry time (24 hours from now)
            token_data['expiry'] = time.time() + (24 * 60 * 60)
            with open(self.TOKEN_CACHE_PATH, 'w') as f:
                json.dump(token_data, f)
            logger.info("Saved authentication token to cache")
        except Exception as e:
            logger.error(f"Error saving token cache: {str(e)}")
    
    def authenticate(self) -> bool:
        """
        Authenticate with PathFinder using available methods.
        Returns True if authentication is successful, False otherwise.
        """
        # Try cached token first
        if self.token_cache and 'access_token' in self.token_cache:
            logger.info("Trying cached access token authentication")
            if self._authenticate_with_token(self.token_cache['access_token']):
                return True
        
        # Try environment variables next
        load_dotenv()
        env_token = os.getenv("PATHFINDER_ACCESS_TOKEN")
        env_api_key = os.getenv("PATHFINDER_API_KEY")
        env_username = os.getenv("PATHFINDER_USERNAME")
        env_password = os.getenv("PATHFINDER_PASSWORD")
        
        # Try token from environment
        if env_token:
            logger.info("Trying access token authentication from environment")
            if self._authenticate_with_token(env_token):
                return True
        
        # Try API key from environment
        if env_api_key:
            logger.info("Trying API key authentication from environment")
            if self._authenticate_with_api_key(env_api_key):
                return True
        
        # Try username/password from environment
        if env_username and env_password:
            logger.info("Trying username/password authentication from environment")
            if self._authenticate_with_credentials(env_username, env_password):
                return True
        
        # Now try from config
        if 'access_token' in self.config:
            logger.info("Trying access token authentication from config")
            if self._authenticate_with_token(self.config['access_token']):
                return True
        
        if 'api_key' in self.config:
            logger.info("Trying API key authentication from config")
            if self._authenticate_with_api_key(self.config['api_key']):
                return True
        
        if 'username' in self.config and 'password' in self.config:
            logger.info("Trying username/password authentication from config")
            if self._authenticate_with_credentials(self.config['username'], self.config['password']):
                return True
        
        logger.error("All authentication methods failed")
        return False
    
    def _authenticate_with_token(self, token: str) -> bool:
        """
        Authenticate using an access token
        """
        if not token or token.startswith("YOUR_"):
            return False
            
        try:
            # Navigate to login page
            self.page.goto(self.LOGIN_URL)
            
            # Use localStorage to inject the token
            self.page.evaluate(f"localStorage.setItem('accessToken', '{token}')")
            
            # Reload the page to apply the token
            self.page.reload()
            
            # Check if we're authenticated by looking for login form
            if "/login" not in self.page.url:
                # Cache the successful token
                self._save_token_cache({'access_token': token})
                return True
            
            # Try another approach - look for a token input field
            token_field = self.page.query_selector('input[placeholder*="token"]')
            if token_field:
                token_field.fill(token)
                
                # Find and click submit
                submit_button = self.page.query_selector('button[type="submit"]')
                if submit_button:
                    submit_button.click()
                    
                    # Wait for navigation
                    self.page.wait_for_navigation()
                    
                    # Check if login was successful
                    if "/login" not in self.page.url:
                        self._save_token_cache({'access_token': token})
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Error in token authentication: {str(e)}")
            return False
    
    def _authenticate_with_api_key(self, api_key: str) -> bool:
        """
        Authenticate using an API key
        """
        if not api_key or api_key.startswith("YOUR_"):
            return False
            
        try:
            # Navigate to login page
            self.page.goto(self.LOGIN_URL)
            
            # Look for an API key input
            api_key_field = self.page.query_selector('input[placeholder*="api" i]')
            if not api_key_field:
                # Try finding by name or id
                for selector in ['#apiKey', 'input[name="apiKey"]', 'input[name="api_key"]']:
                    api_key_field = self.page.query_selector(selector)
                    if api_key_field:
                        break
            
            if not api_key_field:
                return False
                
            # Fill in the API key
            api_key_field.fill(api_key)
            
            # Find and click submit
            submit_button = self.page.query_selector('button[type="submit"]')
            if submit_button:
                submit_button.click()
                
                # Wait for navigation
                self.page.wait_for_navigation()
                
                # Check if login was successful
                if "/login" not in self.page.url:
                    # Try to extract token if available
                    try:
                        token = self.page.evaluate("localStorage.getItem('accessToken')")
                        if token:
                            self._save_token_cache({'access_token': token})
                    except:
                        pass
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error in API key authentication: {str(e)}")
            return False
    
    def _authenticate_with_credentials(self, username: str, password: str) -> bool:
        """
        Authenticate using username and password
        """
        if not username or not password or username.startswith("YOUR_"):
            return False
            
        try:
            # Navigate to login page
            self.page.goto(self.LOGIN_URL)
            
            # Look for username and password inputs
            username_field = None
            password_field = None
            
            # Try common selectors for username/email field
            for selector in [
                '#username', 
                '#email', 
                'input[name="username"]', 
                'input[name="email"]',
                'input[type="email"]',
                'input[placeholder*="username" i]',
                'input[placeholder*="email" i]'
            ]:
                username_field = self.page.query_selector(selector)
                if username_field:
                    break
            
            # Try common selectors for password field
            for selector in [
                '#password', 
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="password" i]'
            ]:
                password_field = self.page.query_selector(selector)
                if password_field:
                    break
            
            if not username_field or not password_field:
                logger.error("Could not find username or password fields")
                return False
                
            # Fill in the credentials
            username_field.fill(username)
            password_field.fill(password)
            
            # Find and click submit
            submit_button = self.page.query_selector('button[type="submit"]')
            if submit_button:
                submit_button.click()
                
                # Wait for navigation
                self.page.wait_for_navigation()
                
                # Check if login was successful
                if "/login" not in self.page.url:
                    # Try to extract token if available
                    try:
                        token = self.page.evaluate("localStorage.getItem('accessToken')")
                        if token:
                            self._save_token_cache({'access_token': token})
                    except:
                        pass
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error in credential authentication: {str(e)}")
            return False