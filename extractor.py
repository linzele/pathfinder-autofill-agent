#!/usr/bin/env python3
"""
Data Extractor module for PathFinder Autofill Agent

Extracts relevant metadata from websites and SharePoint links
"""

import re
import logging
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from playwright.sync_api import Page

# Set up logging
logger = logging.getLogger("pathfinder-extractor")

class DataExtractor:
    """
    Extracts metadata from websites and SharePoint links
    """
    
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
    
    def __init__(self, page: Optional[Page] = None):
        """Initialize the data extractor with an optional browser page"""
        self.page = page
    
    def extract_from_url(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from a URL
        
        The function detects whether it's a SharePoint URL or a regular website
        and uses the appropriate extraction method.
        """
        logger.info(f"Extracting data from URL: {url}")
        
        # Parse the URL
        parsed_url = urlparse(url)
        
        # Check if it's a SharePoint URL
        if "sharepoint.com" in parsed_url.netloc:
            logger.info("Detected SharePoint URL")
            return self._extract_from_sharepoint(url)
        else:
            logger.info("Detected regular website URL")
            return self._extract_from_website(url)
    
    def _extract_from_website(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from a regular website
        
        Uses either Playwright browser (if available) or requests library
        """
        if self.page:
            return self._extract_with_browser(url)
        else:
            return self._extract_with_requests(url)
    
    def _extract_with_browser(self, url: str) -> Dict[str, Any]:
        """Extract metadata using Playwright browser"""
        try:
            # Navigate to the URL
            self.page.goto(url, wait_until="networkidle")
            
            # Extract page title
            title = self.page.title()
            
            # Extract meta description
            description = self.page.evaluate('''() => {
                const metaDesc = document.querySelector('meta[name="description"]');
                return metaDesc ? metaDesc.getAttribute('content') : '';
            }''')
            
            # Extract keywords/tags
            keywords = self.page.evaluate('''() => {
                const metaKeywords = document.querySelector('meta[name="keywords"]');
                return metaKeywords ? metaKeywords.getAttribute('content') : '';
            }''')
            
            # Extract main content text for better description if meta description is empty
            if not description:
                description = self.page.evaluate('''() => {
                    // Try to find main content area
                    const mainContent = document.querySelector('main, article, .content, #content');
                    const textContent = mainContent ? mainContent.textContent : document.body.textContent;
                    // Clean and truncate
                    return textContent.replace(/\\s+/g, ' ').trim().substring(0, 500);
                }''')
            
            # Extract images
            images = self.page.evaluate('''() => {
                const imgs = Array.from(document.querySelectorAll('img'));
                return imgs
                    .filter(img => {
                        const src = img.getAttribute('src');
                        const width = img.naturalWidth || img.width;
                        const height = img.naturalHeight || img.height;
                        // Filter out small icons, spacers, etc.
                        return src && src.trim() && width > 100 && height > 100;
                    })
                    .map(img => {
                        // Convert relative URLs to absolute
                        let src = img.getAttribute('src');
                        if (src && !src.startsWith('http')) {
                            if (src.startsWith('/')) {
                                // Domain-relative URL
                                const origin = window.location.origin;
                                src = `${origin}${src}`;
                            } else {
                                // Path-relative URL
                                const base = window.location.href.substring(
                                    0, window.location.href.lastIndexOf('/') + 1
                                );
                                src = `${base}${src}`;
                            }
                        }
                        return src;
                    })
                    .filter(Boolean)
                    .slice(0, 5); // Limit to first 5 images
            }''')
            
            # Process keywords into tags
            tags = []
            if keywords:
                # Split by comma and remove empty/whitespace tags
                tags = [tag.strip() for tag in keywords.split(',') if tag.strip()]
            
            # Extract additional potential tags from page content
            if len(tags) < 5:
                additional_tags = self.page.evaluate('''() => {
                    // Look for tag-like elements
                    const tagElements = Array.from(document.querySelectorAll('.tag, .tags a, .category, .categories a'));
                    return tagElements
                        .map(el => el.textContent.trim())
                        .filter(tag => tag.length > 0 && tag.length < 20);
                }''')
                
                # Add unique tags
                for tag in additional_tags:
                    if tag not in tags and len(tags) < 10:
                        tags.append(tag)
            
            return {
                "title": title,
                "description": description,
                "tags": tags,
                "url": url,
                "images": images
            }
            
        except Exception as e:
            logger.error(f"Error extracting data with browser: {str(e)}")
            # Fall back to requests-based extraction
            return self._extract_with_requests(url)
    
    def _extract_with_requests(self, url: str) -> Dict[str, Any]:
        """Extract metadata using requests and BeautifulSoup"""
        try:
            # Send request with user agent
            headers = {"User-Agent": self.USER_AGENT}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Extract title
            title = soup.title.string if soup.title else ""
            
            # Extract meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            description = meta_desc.get("content", "") if meta_desc else ""
            
            # Extract keywords/tags
            meta_keywords = soup.find("meta", attrs={"name": "keywords"})
            keywords = meta_keywords.get("content", "") if meta_keywords else ""
            
            # Extract main content text for better description if meta description is empty
            if not description:
                # Try to find main content
                main_content = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
                if main_content:
                    # Get text and clean it up
                    content_text = main_content.get_text(separator=" ", strip=True)
                    # Truncate to reasonable length
                    description = content_text[:500] + "..." if len(content_text) > 500 else content_text
            
            # Process keywords into tags
            tags = []
            if keywords:
                # Split by comma and remove empty/whitespace tags
                tags = [tag.strip() for tag in keywords.split(',') if tag.strip()]
            
            # Extract additional potential tags
            if len(tags) < 5:
                # Look for elements that might be tags
                tag_elements = (
                    soup.select(".tag") + 
                    soup.select(".tags a") + 
                    soup.select(".category") + 
                    soup.select(".categories a")
                )
                
                # Extract text from tag elements
                for element in tag_elements:
                    tag_text = element.get_text(strip=True)
                    if tag_text and len(tag_text) < 20 and tag_text not in tags and len(tags) < 10:
                        tags.append(tag_text)
            
            # Extract images
            images = []
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if not src:
                    continue
                    
                # Convert relative URLs to absolute
                if src and not src.startswith(('http://', 'https://')):
                    if src.startswith('/'):
                        # Domain-relative URL
                        domain = urlparse(url).scheme + "://" + urlparse(url).netloc
                        src = domain + src
                    else:
                        # Path-relative URL
                        base_url = url[:url.rfind('/')+1] if '/' in url[8:] else url + '/'
                        src = base_url + src
                
                # Check if it's a data URL (skip those)
                if src.startswith('data:'):
                    continue
                    
                # Add to images list
                if src not in images:
                    images.append(src)
                    
                # Limit to 5 images
                if len(images) >= 5:
                    break
            
            return {
                "title": title,
                "description": description,
                "tags": tags,
                "url": url,
                "images": images
            }
            
        except Exception as e:
            logger.error(f"Error extracting data with requests: {str(e)}")
            # Return empty data structure with the URL
            return {
                "title": "",
                "description": "",
                "tags": [],
                "url": url,
                "images": []
            }
    
    def _extract_from_sharepoint(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from a SharePoint URL
        
        SharePoint requires authentication, so browser-based extraction is preferred
        """
        if self.page:
            try:
                # Navigate to the URL
                self.page.goto(url, wait_until="networkidle")
                
                # Check if we need to authenticate
                if "login.microsoftonline.com" in self.page.url:
                    logger.error("SharePoint authentication required but credentials not provided")
                    # Return empty data with the URL
                    return {
                        "title": "",
                        "description": "",
                        "tags": [],
                        "url": url,
                        "images": []
                    }
                
                # Extract title - SharePoint often has document title in specific elements
                title = self.page.evaluate('''() => {
                    // Try SharePoint specific selectors first
                    const spTitle = document.querySelector('.SPPageTitle, .ms-webpart-titleText, .od-ItemContent-title');
                    if (spTitle) return spTitle.textContent.trim();
                    
                    // Fall back to regular title
                    return document.title;
                }''')
                
                # Extract description
                description = self.page.evaluate('''() => {
                    // Try SharePoint specific selectors first
                    const spDesc = document.querySelector('.od-ItemContent-secondaryText, .ms-listviewtable td[aria-describedby*="Description"]');
                    if (spDesc) return spDesc.textContent.trim();
                    
                    // Try meta description
                    const metaDesc = document.querySelector('meta[name="description"]');
                    if (metaDesc) return metaDesc.getAttribute('content');
                    
                    // Fall back to main content
                    const content = document.querySelector('#contentBox, .ms-webpartPage-root');
                    if (content) return content.textContent.replace(/\\s+/g, ' ').trim().substring(0, 500);
                    
                    return '';
                }''')
                
                # Extract file metadata if available
                metadata = self.page.evaluate('''() => {
                    const meta = {};
                    
                    // Look for metadata fields in SharePoint UI
                    const metaRows = Array.from(document.querySelectorAll('.ms-metadata-grid-row, .od-DetailPane-propertyRow'));
                    metaRows.forEach(row => {
                        const label = row.querySelector('.ms-metadata-grid-label, .od-DetailPane-propertyLabel');
                        const value = row.querySelector('.ms-metadata-grid-value, .od-DetailPane-propertyValue');
                        if (label && value) {
                            const key = label.textContent.trim();
                            const val = value.textContent.trim();
                            if (key && val) meta[key] = val;
                        }
                    });
                    
                    return meta;
                }''')
                
                # Extract images
                images = self.page.evaluate('''() => {
                    // Get preview image if available
                    const previewImg = document.querySelector('.od-ItemTile-filePreviewImage, .ms-filePreview img');
                    if (previewImg && previewImg.src) return [previewImg.src];
                    
                    // Fall back to other images
                    const imgs = Array.from(document.querySelectorAll('img'));
                    return imgs
                        .filter(img => {
                            const src = img.getAttribute('src');
                            const width = img.naturalWidth || img.width;
                            const height = img.naturalHeight || img.height;
                            return src && src.trim() && width > 100 && height > 100;
                        })
                        .map(img => img.getAttribute('src'))
                        .filter(Boolean)
                        .slice(0, 5);
                }''')
                
                # Try to extract tags
                tags = []
                if metadata and 'Tags' in metadata:
                    tags = [tag.strip() for tag in metadata['Tags'].split(';') if tag.strip()]
                elif metadata and 'Keywords' in metadata:
                    tags = [tag.strip() for tag in metadata['Keywords'].split(';') if tag.strip()]
                
                return {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "url": url,
                    "images": images,
                    "metadata": metadata  # Include full metadata for additional context
                }
                
            except Exception as e:
                logger.error(f"Error extracting SharePoint data with browser: {str(e)}")
                # Return empty data structure with the URL
                return {
                    "title": "",
                    "description": "",
                    "tags": [],
                    "url": url,
                    "images": []
                }
        else:
            # SharePoint typically requires authentication, so without a browser session
            # we likely can't extract much useful information
            logger.error("SharePoint extraction requires browser authentication")
            return {
                "title": "",
                "description": "",
                "tags": [],
                "url": url,
                "images": []
            }