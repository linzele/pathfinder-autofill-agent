#!/usr/bin/env python3
"""
Website Analyzer module for PathFinder Autofill Agent

This module helps to analyze the structure of the PathFinder website,
identify form fields, and understand authentication mechanisms.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser

# Set up logging
logger = logging.getLogger("pathfinder-analyzer")

class PathFinderAnalyzer:
    """
    Analyzes the PathFinder website structure to help with autofill functionality
    """
    
    PATHFINDER_URL = "https://pathfinder.xtech-sg.net/add"
    LOGIN_URL = "https://pathfinder.xtech-sg.net/login"
    ANALYSIS_CACHE_PATH = ".pathfinder_analysis.json"
    
    def __init__(self, headless: bool = False):
        """Initialize the analyzer"""
        self.playwright = None
        self.browser = None
        self.page = None
        self.headless = headless
        self.analysis_cache = self._load_analysis_cache()
    
    def _load_analysis_cache(self) -> Dict[str, Any]:
        """Load cached analysis if it exists"""
        try:
            if Path(self.ANALYSIS_CACHE_PATH).exists():
                with open(self.ANALYSIS_CACHE_PATH, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading analysis cache: {str(e)}")
            return {}
    
    def _save_analysis_cache(self, analysis_data: Dict[str, Any]) -> None:
        """Save analysis data to cache"""
        try:
            with open(self.ANALYSIS_CACHE_PATH, 'w') as f:
                json.dump(analysis_data, f, indent=2)
            logger.info("Saved analysis data to cache")
        except Exception as e:
            logger.error(f"Error saving analysis cache: {str(e)}")
    
    def start(self) -> None:
        """Start the Playwright browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        
        # Enable request/response logging
        self.page.on("request", lambda request: logger.debug(f">> {request.method} {request.url}"))
        self.page.on("response", lambda response: logger.debug(f"<< {response.status} {response.url}"))
        
        logger.info("Browser started for analysis")
    
    def close(self) -> None:
        """Close the browser and clean up"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            
        self.browser = None
        self.playwright = None
        self.page = None
    
    def analyze_login_page(self) -> Dict[str, Any]:
        """
        Analyze the login page structure to understand authentication mechanisms
        """
        logger.info("Analyzing login page...")
        
        if not self.page:
            self.start()
            
        # Navigate to login page
        self.page.goto(self.LOGIN_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Extract login form structure
        login_form_data = self.page.evaluate('''() => {
            // Find all form elements
            const forms = Array.from(document.querySelectorAll('form'));
            
            return forms.map(form => {
                const inputs = Array.from(form.querySelectorAll('input, button'));
                return {
                    action: form.action,
                    method: form.method,
                    id: form.id,
                    className: form.className,
                    inputs: inputs.map(input => {
                        return {
                            type: input.type,
                            name: input.name,
                            id: input.id,
                            placeholder: input.placeholder,
                            className: input.className
                        };
                    })
                };
            });
        }''')
        
        # Check for token usage in localStorage
        localStorage_data = self.page.evaluate('''() => {
            const keys = Object.keys(localStorage);
            const data = {};
            for (const key of keys) {
                data[key] = localStorage.getItem(key);
            }
            return data;
        }''')
        
        # Monitor network requests for API calls during login
        network_data = {
            "endpoints": [],
            "headers": {}
        }
        
        def handle_request(request):
            if request.url.startswith("https://pathfinder.xtech-sg.net/api/"):
                network_data["endpoints"].append({
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers)
                })
                network_data["headers"] = dict(request.headers)
        
        # Add request listener
        self.page.on("request", handle_request)
        
        # Try to find sample input values
        login_inputs = self.page.evaluate('''() => {
            // Check for any sample values in code or placeholders
            const codeSnippets = Array.from(document.querySelectorAll('code, pre'));
            let samples = {};
            
            // Extract from code snippets
            for (const snippet of codeSnippets) {
                const text = snippet.textContent;
                // Look for patterns that might be tokens or credentials
                const tokenMatch = text.match(/token["']?\s*[=:]\s*["']([^"']+)["']/i);
                const apiKeyMatch = text.match(/apiKey["']?\s*[=:]\s*["']([^"']+)["']/i);
                const usernameMatch = text.match(/username["']?\s*[=:]\s*["']([^"']+)["']/i);
                const passwordMatch = text.match(/password["']?\s*[=:]\s*["']([^"']+)["']/i);
                
                if (tokenMatch) samples.token = tokenMatch[1];
                if (apiKeyMatch) samples.apiKey = apiKeyMatch[1];
                if (usernameMatch) samples.username = usernameMatch[1];
                if (passwordMatch) samples.password = passwordMatch[1];
            }
            
            // Extract from placeholders
            const inputs = Array.from(document.querySelectorAll('input'));
            for (const input of inputs) {
                if (input.placeholder) {
                    if (input.placeholder.match(/token/i)) samples.tokenPlaceholder = input.placeholder;
                    if (input.placeholder.match(/api\s*key/i)) samples.apiKeyPlaceholder = input.placeholder;
                    if (input.placeholder.match(/username|email/i)) samples.usernamePlaceholder = input.placeholder;
                    if (input.placeholder.match(/password/i)) samples.passwordPlaceholder = input.placeholder;
                }
            }
            
            return samples;
        }''')
        
        # Remove the request listener
        self.page.remove_listener("request", handle_request)
        
        # Combine data
        login_analysis = {
            "forms": login_form_data,
            "localStorage": localStorage_data,
            "networkRequests": network_data,
            "sampleInputs": login_inputs,
            "url": self.page.url
        }
        
        # Cache the analysis
        if self.analysis_cache:
            self.analysis_cache["login"] = login_analysis
            self._save_analysis_cache(self.analysis_cache)
        
        return login_analysis
    
    def analyze_add_asset_form(self) -> Dict[str, Any]:
        """
        Analyze the add asset form structure to understand required fields
        """
        logger.info("Analyzing add asset form...")
        
        if not self.page:
            self.start()
            
        # Navigate to add asset page
        self.page.goto(self.PATHFINDER_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Check if we need to login first
        if "/login" in self.page.url:
            logger.info("Login required to analyze form. Skipping detailed analysis.")
            return {"error": "Login required", "url": self.page.url}
        
        # Extract form structure
        form_data = self.page.evaluate('''() => {
            // Find all form elements
            const forms = Array.from(document.querySelectorAll('form'));
            
            return forms.map(form => {
                const inputs = Array.from(form.querySelectorAll('input, textarea, select, button'));
                return {
                    action: form.action,
                    method: form.method,
                    id: form.id,
                    className: form.className,
                    inputs: inputs.map(input => {
                        const isRequired = input.hasAttribute('required');
                        const labelElement = document.querySelector(`label[for="${input.id}"]`);
                        const label = labelElement ? labelElement.textContent.trim() : null;
                        
                        return {
                            type: input.type,
                            name: input.name,
                            id: input.id,
                            placeholder: input.placeholder,
                            className: input.className,
                            required: isRequired,
                            label: label,
                            value: input.value
                        };
                    })
                };
            });
        }''')
        
        # Check for any dynamically loaded form elements
        dynamic_elements = self.page.evaluate('''() => {
            // Check for React/Angular/Vue.js component structures
            const possibleComponents = [
                // React-like components
                Array.from(document.querySelectorAll('[data-reactid], [data-react-checksum]')),
                // Angular-like components
                Array.from(document.querySelectorAll('[ng-model], [ng-app], [ng-controller]')),
                // Vue-like components
                Array.from(document.querySelectorAll('[v-model], [v-bind]'))
            ].flat();
            
            return possibleComponents.map(el => {
                return {
                    tagName: el.tagName,
                    id: el.id,
                    className: el.className,
                    attributes: Array.from(el.attributes).map(attr => {
                        return { name: attr.name, value: attr.value };
                    })
                };
            });
        }''')
        
        # Extract potential API endpoints used by the form
        api_endpoints = []
        
        def capture_form_requests(request):
            if request.url.startswith("https://pathfinder.xtech-sg.net/api/"):
                api_endpoints.append({
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers)
                })
        
        # Add request listener
        self.page.on("request", capture_form_requests)
        
        # Trigger some interactions to capture API requests
        self.page.evaluate('''() => {
            // Click on form elements to trigger potential API calls
            const clickables = Array.from(document.querySelectorAll('input, button, select'));
            for (const el of clickables) {
                try {
                    el.click();
                } catch (e) {
                    // Ignore errors
                }
            }
        }''')
        
        # Wait a bit for any async requests
        self.page.wait_for_timeout(2000)
        
        # Remove the request listener
        self.page.remove_listener("request", capture_form_requests)
        
        # Check for file upload capabilities
        file_uploads = self.page.evaluate('''() => {
            const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
            return fileInputs.map(input => {
                return {
                    id: input.id,
                    name: input.name,
                    accept: input.accept,
                    multiple: input.multiple
                };
            });
        }''')
        
        # Extract labels and field groups
        field_groups = self.page.evaluate('''() => {
            // Look for common patterns of grouped form fields
            const fieldsets = Array.from(document.querySelectorAll('fieldset, .form-group, .form-section'));
            
            return fieldsets.map(fieldset => {
                const legend = fieldset.querySelector('legend, .section-title, h2, h3');
                const inputs = Array.from(fieldset.querySelectorAll('input, textarea, select'));
                
                return {
                    title: legend ? legend.textContent.trim() : null,
                    id: fieldset.id,
                    className: fieldset.className,
                    inputs: inputs.map(input => {
                        const labelElement = document.querySelector(`label[for="${input.id}"]`);
                        const label = labelElement ? labelElement.textContent.trim() : null;
                        
                        return {
                            name: input.name,
                            id: input.id,
                            type: input.type,
                            label: label
                        };
                    })
                };
            });
        }''')
        
        # Combine data
        form_analysis = {
            "forms": form_data,
            "dynamicElements": dynamic_elements,
            "apiEndpoints": api_endpoints,
            "fileUploads": file_uploads,
            "fieldGroups": field_groups,
            "url": self.page.url
        }
        
        # Cache the analysis
        if self.analysis_cache:
            self.analysis_cache["addAssetForm"] = form_analysis
            self._save_analysis_cache(self.analysis_cache)
        
        return form_analysis
    
    def extract_auth_tokens(self) -> Dict[str, Any]:
        """
        Attempt to extract authentication tokens from the current browser session
        """
        logger.info("Extracting authentication tokens...")
        
        if not self.page:
            logger.error("Browser not started")
            return {}
        
        # Extract localStorage
        localStorage_data = self.page.evaluate('''() => {
            const keys = Object.keys(localStorage);
            const data = {};
            for (const key of keys) {
                if (key.toLowerCase().includes('token') || 
                    key.toLowerCase().includes('auth') || 
                    key.toLowerCase().includes('api')) {
                    data[key] = localStorage.getItem(key);
                }
            }
            return data;
        }''')
        
        # Extract cookies
        cookies = self.page.context.cookies()
        auth_cookies = [cookie for cookie in cookies if 
                        'token' in cookie['name'].lower() or 
                        'auth' in cookie['name'].lower() or
                        'sid' in cookie['name'].lower() or
                        'session' in cookie['name'].lower()]
        
        # Extract from sessionStorage
        sessionStorage_data = self.page.evaluate('''() => {
            try {
                const keys = Object.keys(sessionStorage);
                const data = {};
                for (const key of keys) {
                    if (key.toLowerCase().includes('token') || 
                        key.toLowerCase().includes('auth') || 
                        key.toLowerCase().includes('api')) {
                        data[key] = sessionStorage.getItem(key);
                    }
                }
                return data;
            } catch (e) {
                return {};
            }
        }''')
        
        auth_data = {
            "localStorage": localStorage_data,
            "cookies": auth_cookies,
            "sessionStorage": sessionStorage_data
        }
        
        # Cache the data
        if self.analysis_cache:
            self.analysis_cache["authTokens"] = auth_data
            self._save_analysis_cache(self.analysis_cache)
        
        return auth_data
    
    def generate_selectors_report(self) -> Dict[str, List[str]]:
        """
        Generate a report of potential selectors for common form fields
        """
        logger.info("Generating selectors report...")
        
        if not self.page:
            self.start()
            
        # Navigate to add asset page if not already there
        if self.PATHFINDER_URL not in self.page.url:
            self.page.goto(self.PATHFINDER_URL)
            self.page.wait_for_load_state("networkidle")
        
        # Check if we need to login first
        if "/login" in self.page.url:
            logger.info("Login required to analyze form. Skipping selector report.")
            return {"error": "Login required"}
        
        # Extract selectors for common fields
        selectors = self.page.evaluate('''() => {
            const findSelectors = (searchTerms) => {
                const results = [];
                
                // Search by id, name, placeholder, aria-label, or label text
                for (const term of searchTerms) {
                    // By ID
                    const idElement = document.querySelector(`#${term}`);
                    if (idElement) results.push(`#${term}`);
                    
                    // By Name
                    const nameElements = document.querySelectorAll(`[name="${term}"]`);
                    if (nameElements.length) results.push(`[name="${term}"]`);
                    
                    // By placeholder containing term
                    const placeholderElements = document.querySelectorAll(`[placeholder*="${term}" i]`);
                    if (placeholderElements.length) results.push(`[placeholder*="${term}" i]`);
                    
                    // By aria-label containing term
                    const ariaElements = document.querySelectorAll(`[aria-label*="${term}" i]`);
                    if (ariaElements.length) results.push(`[aria-label*="${term}" i]`);
                    
                    // By class containing term
                    const classElements = document.querySelectorAll(`.${term}`);
                    if (classElements.length) results.push(`.${term}`);
                    
                    // By label text
                    const labels = Array.from(document.querySelectorAll('label'));
                    for (const label of labels) {
                        if (label.textContent.toLowerCase().includes(term.toLowerCase())) {
                            const forAttr = label.getAttribute('for');
                            if (forAttr) results.push(`#${forAttr}`);
                        }
                    }
                }
                
                return [...new Set(results)]; // Remove duplicates
            };
            
            return {
                title: findSelectors(['title', 'name', 'heading']),
                description: findSelectors(['description', 'desc', 'summary', 'about']),
                url: findSelectors(['url', 'link', 'website', 'address']),
                tags: findSelectors(['tags', 'keywords', 'categories', 'labels']),
                image: findSelectors(['image', 'img', 'photo', 'picture', 'thumbnail']),
                fileUpload: Array.from(document.querySelectorAll('input[type="file"]')).map(el => {
                    return el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : 'input[type="file"]');
                }),
                submitButton: Array.from(document.querySelectorAll('button[type="submit"], input[type="submit"], button:not([type])')).map(el => {
                    return el.id ? `#${el.id}` : (
                        el.className ? `.${el.className.split(' ')[0]}` : 
                        el.tagName.toLowerCase() + (el.textContent ? `:contains("${el.textContent.trim()}")` : '')
                    );
                })
            };
        }''')
        
        # Cache the selectors
        if self.analysis_cache:
            self.analysis_cache["selectors"] = selectors
            self._save_analysis_cache(self.analysis_cache)
        
        return selectors

    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run a complete analysis of the PathFinder site
        """
        logger.info("Running full site analysis...")
        
        try:
            if not self.page:
                self.start()
                
            analysis_data = {
                "login": self.analyze_login_page(),
                "authTokens": self.extract_auth_tokens()
            }
            
            # Navigate to the add asset page
            self.page.goto(self.PATHFINDER_URL)
            self.page.wait_for_load_state("networkidle")
            
            # If we're not redirected to login, analyze the form
            if "/login" not in self.page.url:
                analysis_data["addAssetForm"] = self.analyze_add_asset_form()
                analysis_data["selectors"] = self.generate_selectors_report()
            
            # Save the complete analysis
            self._save_analysis_cache(analysis_data)
            
            return analysis_data
            
        except Exception as e:
            logger.exception(f"Error during full analysis: {str(e)}")
            return {"error": str(e)}
        finally:
            self.close()


if __name__ == "__main__":
    # Set up logging for direct execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run a quick analysis with visible browser
    analyzer = PathFinderAnalyzer(headless=False)
    try:
        analysis = analyzer.run_full_analysis()
        print("Analysis complete. Results saved to .pathfinder_analysis.json")
    finally:
        analyzer.close()