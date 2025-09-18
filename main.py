#!/usr/bin/env python3
"""
PathFinder Autofill Agent

This script automates filling in form details on PathFinder's asset submission page
based on the content of a provided website or SharePoint link.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from playwright.sync_api import sync_playwright, Page, Browser
from dotenv import load_dotenv

# Import local modules
from auth import PathFinderAuth
from extractor import DataExtractor


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("pathfinder-autofill")


class PathFinderAutofill:
    """
    Automates form filling on PathFinder's asset submission page.
    """
    
    PATHFINDER_URL = "https://pathfinder.xtech-sg.net/add"
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the autofill agent with configuration"""
        self.config = self._load_config(config_path)
        self.browser = None
        self.page = None
        self.playwright = None
        self.auth = None
        self.extractor = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from a JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found at {config_path}")
            # Create example config if it doesn't exist
            example_config = {
                "access_token": "YOUR_ACCESS_TOKEN",
                "api_key": "YOUR_API_KEY",
                "username": "",
                "password": "",
                "default_values": {
                    "title": "",
                    "description": "",
                    "tags": []
                }
            }
            with open("config.example.json", 'w') as f:
                json.dump(example_config, f, indent=2)
            logger.info("Created example config at config.example.json")
            return {}
    
    def start(self, headless: bool = False) -> None:
        """Start the Playwright browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.page = self.browser.new_page()
        
        # Initialize auth and extractor modules with the browser page
        self.auth = PathFinderAuth(self.config, self.page)
        self.extractor = DataExtractor(self.page)
        
        logger.info("Browser started successfully")
        
    def login(self) -> bool:
        """Authenticate with PathFinder using credentials from config"""
        logger.info("Authenticating with PathFinder...")
        
        # Use the authentication module
        return self.auth.authenticate()
        
    def extract_data_from_url(self, url: str) -> Dict[str, Any]:
        """
        Extract relevant data from the provided website or SharePoint URL
        """
        logger.info(f"Extracting data from {url}...")
        
        # Use the extractor module to get the data
        data = self.extractor.extract_from_url(url)
        
        # Merge with default values from config
        if "default_values" in self.config:
            for key, value in self.config["default_values"].items():
                if key not in data or not data[key]:
                    data[key] = value
        
        return data
    
    def fill_form(self, data: Dict[str, Any]) -> None:
        """
        Fill the PathFinder form with the extracted data
        """
        logger.info("Filling PathFinder form...")
        
        # Navigate to the form page
        self.page.goto(self.PATHFINDER_URL)
        
        # Wait for the page to fully load
        self.page.wait_for_load_state("networkidle")
        
        # Check if we need to authenticate first
        if "/login" in self.page.url:
            logger.info("Login required before filling form")
            if not self.login():
                logger.error("Authentication failed, cannot fill form")
                return
            # Navigate back to the form after login
            self.page.goto(self.PATHFINDER_URL)
            self.page.wait_for_load_state("networkidle")
        
        # Fill in form fields
        # These selectors will need to be updated based on actual page structure
        if "title" in data and data["title"]:
            # Try different potential selectors for the title field
            for selector in ["#title", 'input[name="title"]', 'input[placeholder*="title"]', 'input[placeholder*="name"]']:
                if self.page.query_selector(selector):
                    self.page.fill(selector, data["title"])
                    break
        
        if "description" in data and data["description"]:
            # Try different potential selectors for the description field
            for selector in ["#description", 'textarea[name="description"]', 'textarea[placeholder*="description"]']:
                if self.page.query_selector(selector):
                    self.page.fill(selector, data["description"])
                    break
        
        if "url" in data and data["url"]:
            # Try different potential selectors for the URL field
            for selector in ["#url", 'input[name="url"]', 'input[type="url"]', 'input[placeholder*="url"]', 'input[placeholder*="link"]']:
                if self.page.query_selector(selector):
                    self.page.fill(selector, data["url"])
                    break
        
        # Handle tags if present
        if "tags" in data and data["tags"]:
            # Find a tag input field - this varies widely between sites
            tag_selectors = [
                'input[name="tags"]', 
                'input[placeholder*="tag"]', 
                '.tags-input',
                'div[role="combobox"]'
            ]
            
            for selector in tag_selectors:
                tag_input = self.page.query_selector(selector)
                if tag_input:
                    for tag in data["tags"]:
                        tag_input.fill(tag)
                        self.page.keyboard.press("Enter")
                    break
        
        # Handle images if present
        if "images" in data and data["images"]:
            # Try to find image upload fields
            # This is very site-specific and would need to be customized
            file_inputs = self.page.query_selector_all('input[type="file"]')
            if file_inputs:
                # Try to download the first image and upload it
                try:
                    import requests
                    import tempfile
                    
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                        response = requests.get(data["images"][0], timeout=30)
                        temp_file.write(response.content)
                        temp_file_path = temp_file.name
                    
                    file_inputs[0].set_input_files(temp_file_path)
                    os.unlink(temp_file_path)  # Clean up the temp file
                except Exception as e:
                    logger.error(f"Failed to upload image: {str(e)}")
        
        logger.info("Form filled successfully")
    
    def submit_form(self) -> bool:
        """
        Submit the form and verify success
        """
        logger.info("Submitting form...")
        
        # Look for a submit button
        submit_selectors = [
            "#submit-button", 
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Create")',
            'button:has-text("Add")'
        ]
        
        submit_button = None
        for selector in submit_selectors:
            submit_button = self.page.query_selector(selector)
            if submit_button:
                logger.info(f"Found submit button with selector: {selector}")
                break
        
        if not submit_button:
            logger.error("Could not find submit button")
            return False
        
        # Click the submit button
        submit_button.click()
        
        # Wait for navigation or success indicators
        try:
            # Look for various success indicators
            success_selectors = [
                ".success-message",
                '.alert-success',
                'div:has-text("successfully")',
                'div:has-text("Success")'
            ]
            
            for selector in success_selectors:
                if self.page.wait_for_selector(selector, timeout=5000):
                    logger.info(f"Success indicator found: {selector}")
                    return True
            
            # If no success message but we navigated away from the form page
            if self.PATHFINDER_URL not in self.page.url:
                logger.info("Form submission redirected to a new page")
                return True
            
            logger.error("Could not confirm form submission success")
            return False
        except Exception as e:
            logger.error(f"Error waiting for form submission result: {str(e)}")
            return False
    
    def close(self) -> None:
        """Close the browser and clean up"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='PathFinder Autofill Agent')
    parser.add_argument('--url', required=True, help='Website or SharePoint URL to extract data from')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Create and run the autofill agent
    agent = PathFinderAutofill(config_path=args.config)
    
    try:
        agent.start(headless=args.headless)
        if agent.login():
            data = agent.extract_data_from_url(args.url)
            agent.fill_form(data)
            success = agent.submit_form()
            if success:
                logger.info("Process completed successfully")
                sys.exit(0)
            else:
                logger.error("Process failed")
                sys.exit(1)
        else:
            logger.error("Authentication failed")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        agent.close()


if __name__ == "__main__":
    main()