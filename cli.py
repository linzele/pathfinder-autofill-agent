#!/usr/bin/env python3
"""
Command-line interface for PathFinder Autofill Agent

This module provides a user-friendly command-line interface for interacting with
the PathFinder Autofill Agent, supporting various commands and options.
"""

import os
import sys
import json
import argparse
import logging
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

# Import local modules
from main import PathFinderAutofill
from extractor import DataExtractor
from analyzer import PathFinderAnalyzer


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("pathfinder-cli")


def setup_parser() -> argparse.ArgumentParser:
    """Set up command-line argument parser with subcommands"""
    
    parser = argparse.ArgumentParser(
        description="PathFinder Autofill Agent - Automate filling in demo asset details",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fill a form with data from a website
  python cli.py fill --url https://example.com --config config.json
  
  # Extract data from a URL without submitting
  python cli.py extract --url https://example.com --output extracted_data.json
  
  # Process multiple URLs from a CSV file
  python cli.py batch --input urls.csv --config config.json
  
  # Analyze the PathFinder website structure
  python cli.py analyze --output analysis.json
  
  # Run in interactive mode
  python cli.py interactive
"""
    )
    
    # Global options
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    
    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Fill command
    fill_parser = subparsers.add_parser('fill', help='Fill in PathFinder form with data from a URL')
    fill_parser.add_argument('--url', required=True, help='Website or SharePoint URL to extract data from')
    fill_parser.add_argument('--config', default='config.json', help='Path to configuration file')
    fill_parser.add_argument('--no-submit', action='store_true', help='Fill the form but do not submit it')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract data from a URL without filling a form')
    extract_parser.add_argument('--url', required=True, help='Website or SharePoint URL to extract data from')
    extract_parser.add_argument('--output', default='extracted_data.json', help='Path to output JSON file')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple URLs from a CSV file')
    batch_parser.add_argument('--input', required=True, help='Path to CSV file with URLs')
    batch_parser.add_argument('--config', default='config.json', help='Path to configuration file')
    batch_parser.add_argument('--output', default='batch_results.json', help='Path to output JSON file')
    batch_parser.add_argument('--skip-errors', action='store_true', help='Continue processing on errors')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze PathFinder website structure')
    analyze_parser.add_argument('--output', default='analysis.json', help='Path to output JSON file')
    
    # Interactive command
    subparsers.add_parser('interactive', help='Run in interactive mode')
    
    return parser


def extract_command(args: argparse.Namespace) -> None:
    """Execute the extract command"""
    logger.info(f"Extracting data from URL: {args.url}")
    
    try:
        # Set up the data extractor with a browser for better extraction
        extractor = None
        
        try:
            from playwright.sync_api import sync_playwright
            logger.info("Using Playwright for extraction")
            
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=args.headless)
            page = browser.new_page()
            
            extractor = DataExtractor(page)
            data = extractor.extract_from_url(args.url)
            
            # Clean up
            browser.close()
            playwright.stop()
            
        except ImportError:
            logger.info("Playwright not available, falling back to requests-based extraction")
            extractor = DataExtractor()
            data = extractor.extract_from_url(args.url)
        
        # Save the extracted data
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Extracted data saved to {args.output}")
        
        # Print a summary
        print("\n===== Extraction Summary =====")
        print(f"Title: {data.get('title', 'N/A')}")
        print(f"Description: {data.get('description', 'N/A')[:100]}..." if data.get('description', '') else "Description: N/A")
        print(f"Tags: {', '.join(data.get('tags', []))}" if data.get('tags') else "Tags: None")
        print(f"Images: {len(data.get('images', []))} found" if data.get('images') else "Images: None")
        print(f"Full data saved to: {args.output}")
        
    except Exception as e:
        logger.exception(f"Error extracting data: {str(e)}")
        sys.exit(1)


def fill_command(args: argparse.Namespace) -> None:
    """Execute the fill command"""
    logger.info(f"Filling form with data from URL: {args.url}")
    
    try:
        # Create and run the autofill agent
        agent = PathFinderAutofill(config_path=args.config)
        
        try:
            agent.start(headless=args.headless)
            
            if agent.login():
                data = agent.extract_data_from_url(args.url)
                
                # Print the extracted data
                print("\n===== Extracted Data =====")
                print(f"Title: {data.get('title', 'N/A')}")
                print(f"Description: {data.get('description', 'N/A')[:100]}..." if data.get('description', '') else "Description: N/A")
                print(f"Tags: {', '.join(data.get('tags', []))}" if data.get('tags') else "Tags: None")
                print(f"Images: {len(data.get('images', []))} found" if data.get('images') else "Images: None")
                
                # Fill the form
                agent.fill_form(data)
                
                if not args.no_submit:
                    success = agent.submit_form()
                    if success:
                        logger.info("Form submitted successfully")
                        print("\nForm submitted successfully! ✓")
                    else:
                        logger.error("Form submission failed")
                        print("\nForm submission failed. Check logs for details.")
                        sys.exit(1)
                else:
                    logger.info("Form filled but not submitted (--no-submit flag used)")
                    print("\nForm filled successfully. Not submitted as requested.")
            else:
                logger.error("Authentication failed")
                print("\nAuthentication failed. Please check your credentials.")
                sys.exit(1)
                
        except Exception as e:
            logger.exception(f"Error: {str(e)}")
            sys.exit(1)
        finally:
            agent.close()
            
    except Exception as e:
        logger.exception(f"Error filling form: {str(e)}")
        sys.exit(1)


def batch_command(args: argparse.Namespace) -> None:
    """Execute the batch command"""
    logger.info(f"Processing batch from file: {args.input}")
    
    # Validate input file exists
    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    
    results = {
        "successful": [],
        "failed": []
    }
    
    try:
        # Read URLs from CSV
        urls = []
        with open(args.input, 'r') as f:
            reader = csv.reader(f)
            # Skip header if it exists
            first_row = next(reader, None)
            
            # Check if first row looks like a header
            if first_row and any(header.lower() in ['url', 'link', 'address', 'website'] 
                                for header in first_row):
                # Find the URL column
                url_col_idx = 0
                for idx, header in enumerate(first_row):
                    if header.lower() in ['url', 'link', 'address', 'website']:
                        url_col_idx = idx
                        break
                        
                # Get URLs from the appropriate column
                for row in reader:
                    if len(row) > url_col_idx and row[url_col_idx].strip():
                        urls.append(row[url_col_idx].strip())
            else:
                # No header, assume first row is data
                if first_row and first_row[0].strip():
                    urls.append(first_row[0].strip())
                
                # Get remaining URLs
                for row in reader:
                    if row and row[0].strip():
                        urls.append(row[0].strip())
        
        if not urls:
            logger.error("No URLs found in the input file")
            sys.exit(1)
            
        logger.info(f"Found {len(urls)} URLs to process")
        
        # Create the autofill agent
        agent = PathFinderAutofill(config_path=args.config)
        
        try:
            agent.start(headless=args.headless)
            
            # Authenticate once
            if not agent.login():
                logger.error("Authentication failed")
                print("\nAuthentication failed. Please check your credentials.")
                sys.exit(1)
            
            # Process each URL
            for idx, url in enumerate(urls):
                try:
                    print(f"\n[{idx+1}/{len(urls)}] Processing {url}")
                    logger.info(f"Processing URL {idx+1}/{len(urls)}: {url}")
                    
                    # Extract data
                    data = agent.extract_data_from_url(url)
                    
                    # Print summary
                    print(f"Title: {data.get('title', 'N/A')}")
                    print(f"Description: {data.get('description', 'N/A')[:50]}..." if data.get('description', '') else "Description: N/A")
                    
                    # Fill and submit form
                    agent.fill_form(data)
                    success = agent.submit_form()
                    
                    if success:
                        logger.info(f"Successfully submitted form for {url}")
                        print("✓ Submission successful")
                        results["successful"].append({
                            "url": url,
                            "title": data.get("title", "N/A")
                        })
                    else:
                        logger.error(f"Failed to submit form for {url}")
                        print("✗ Submission failed")
                        results["failed"].append({
                            "url": url,
                            "title": data.get("title", "N/A"),
                            "error": "Form submission failed"
                        })
                        
                        if not args.skip_errors:
                            print("Stopping batch processing due to error.")
                            break
                            
                except Exception as e:
                    logger.exception(f"Error processing URL {url}: {str(e)}")
                    print(f"✗ Error: {str(e)}")
                    results["failed"].append({
                        "url": url,
                        "error": str(e)
                    })
                    
                    if not args.skip_errors:
                        print("Stopping batch processing due to error.")
                        break
            
            # Save results
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
                
            print(f"\nBatch processing complete. Results saved to {args.output}")
            print(f"Successful: {len(results['successful'])}, Failed: {len(results['failed'])}")
            
        except Exception as e:
            logger.exception(f"Error in batch processing: {str(e)}")
            sys.exit(1)
        finally:
            agent.close()
            
    except Exception as e:
        logger.exception(f"Error in batch command: {str(e)}")
        sys.exit(1)


def analyze_command(args: argparse.Namespace) -> None:
    """Execute the analyze command"""
    logger.info("Analyzing PathFinder website structure")
    
    try:
        # Create the analyzer
        analyzer = PathFinderAnalyzer(headless=args.headless)
        
        try:
            # Run the analysis
            print("Analyzing PathFinder website structure...")
            analysis = analyzer.run_full_analysis()
            
            # Save the results
            with open(args.output, 'w') as f:
                json.dump(analysis, f, indent=2)
                
            print(f"\nAnalysis complete! Results saved to {args.output}")
            
            # Print a summary
            print("\n===== Analysis Summary =====")
            
            if "error" in analysis:
                print(f"Error: {analysis['error']}")
            else:
                print("Login page analyzed: Yes")
                
                if "addAssetForm" in analysis:
                    print("Add asset form analyzed: Yes")
                    
                    if "forms" in analysis["addAssetForm"]:
                        form_count = len(analysis["addAssetForm"]["forms"])
                        print(f"Forms found: {form_count}")
                        
                        if form_count > 0:
                            for i, form in enumerate(analysis["addAssetForm"]["forms"]):
                                print(f"  Form {i+1}: {len(form.get('inputs', []))} fields")
                    
                    if "fileUploads" in analysis["addAssetForm"]:
                        upload_count = len(analysis["addAssetForm"]["fileUploads"])
                        print(f"File upload fields: {upload_count}")
                else:
                    print("Add asset form analyzed: No (login required)")
                
                if "selectors" in analysis:
                    print("\nPotential selectors found:")
                    for field, selectors in analysis["selectors"].items():
                        if selectors:
                            print(f"  {field}: {len(selectors)} selectors")
                            for selector in selectors[:3]:
                                print(f"    - {selector}")
                            if len(selectors) > 3:
                                print(f"    - ... and {len(selectors)-3} more")
                
                if "authTokens" in analysis and "localStorage" in analysis["authTokens"]:
                    token_count = len(analysis["authTokens"]["localStorage"])
                    print(f"\nAuth tokens found in localStorage: {token_count}")
                    
        except Exception as e:
            logger.exception(f"Error during analysis: {str(e)}")
            sys.exit(1)
        finally:
            analyzer.close()
            
    except Exception as e:
        logger.exception(f"Error in analyze command: {str(e)}")
        sys.exit(1)


def interactive_command(args: argparse.Namespace) -> None:
    """Execute the interactive command"""
    print("\n=== PathFinder Autofill Agent: Interactive Mode ===")
    print("This mode allows you to interactively extract data and fill forms.")
    
    try:
        # Create agent and extractor
        agent = None
        
        while True:
            print("\nOptions:")
            print("1. Extract data from URL")
            print("2. Fill form with URL")
            print("3. Analyze website structure")
            print("4. Edit configuration")
            print("5. Exit")
            
            choice = input("\nEnter option number: ").strip()
            
            if choice == '1':  # Extract data
                url = input("\nEnter URL to extract from: ").strip()
                if not url:
                    print("URL cannot be empty.")
                    continue
                    
                # Initialize agent if needed
                if not agent:
                    agent = PathFinderAutofill()
                    agent.start(headless=args.headless)
                
                try:
                    print(f"\nExtracting data from {url}...")
                    data = agent.extractor.extract_from_url(url)
                    
                    print("\nExtracted data:")
                    print(f"Title: {data.get('title', 'N/A')}")
                    print(f"Description: {data.get('description', 'N/A')[:100]}..." if data.get('description', '') else "Description: N/A")
                    print(f"Tags: {', '.join(data.get('tags', []))}" if data.get('tags') else "Tags: None")
                    print(f"Images: {len(data.get('images', []))} found" if data.get('images') else "Images: None")
                    
                    save_option = input("\nSave this data to a file? (y/n): ").strip().lower()
                    if save_option == 'y':
                        filename = input("Enter filename (default: extracted_data.json): ").strip()
                        if not filename:
                            filename = "extracted_data.json"
                        
                        with open(filename, 'w') as f:
                            json.dump(data, f, indent=2)
                        print(f"Data saved to {filename}")
                except Exception as e:
                    print(f"Error extracting data: {str(e)}")
                    
            elif choice == '2':  # Fill form
                url = input("\nEnter URL to extract from: ").strip()
                if not url:
                    print("URL cannot be empty.")
                    continue
                
                # Initialize agent if needed
                if not agent:
                    agent = PathFinderAutofill()
                    agent.start(headless=args.headless)
                
                try:
                    # Try to login if not already logged in
                    if agent.login():
                        print(f"\nExtracting data from {url}...")
                        data = agent.extract_data_from_url(url)
                        
                        print("\nExtracted data:")
                        print(f"Title: {data.get('title', 'N/A')}")
                        print(f"Description: {data.get('description', 'N/A')[:100]}..." if data.get('description', '') else "Description: N/A")
                        print(f"Tags: {', '.join(data.get('tags', []))}" if data.get('tags') else "Tags: None")
                        
                        edit_option = input("\nEdit this data before filling form? (y/n): ").strip().lower()
                        if edit_option == 'y':
                            # Edit the title
                            new_title = input(f"Enter title (current: {data.get('title', 'N/A')}): ").strip()
                            if new_title:
                                data['title'] = new_title
                            
                            # Edit the description
                            new_desc = input(f"Enter description (current: {data.get('description', 'N/A')[:50]}...): ").strip()
                            if new_desc:
                                data['description'] = new_desc
                            
                            # Edit tags
                            new_tags = input(f"Enter tags, comma separated (current: {', '.join(data.get('tags', []))}): ").strip()
                            if new_tags:
                                data['tags'] = [tag.strip() for tag in new_tags.split(',') if tag.strip()]
                        
                        print("\nFilling form...")
                        agent.fill_form(data)
                        
                        submit_option = input("\nSubmit the form? (y/n): ").strip().lower()
                        if submit_option == 'y':
                            success = agent.submit_form()
                            if success:
                                print("Form submitted successfully!")
                            else:
                                print("Form submission failed.")
                    else:
                        print("Authentication failed. Please check your credentials.")
                except Exception as e:
                    print(f"Error filling form: {str(e)}")
                    
            elif choice == '3':  # Analyze website
                # Clean up existing agent if any
                if agent:
                    agent.close()
                    agent = None
                
                try:
                    print("\nAnalyzing PathFinder website structure...")
                    analyzer = PathFinderAnalyzer(headless=args.headless)
                    analysis = analyzer.run_full_analysis()
                    analyzer.close()
                    
                    print("\nAnalysis complete!")
                    
                    # Print a summary
                    if "error" in analysis:
                        print(f"Error: {analysis['error']}")
                    else:
                        if "login" in analysis:
                            print("\nLogin page:")
                            if "forms" in analysis["login"]:
                                form_count = len(analysis["login"]["forms"])
                                print(f"  Forms found: {form_count}")
                        
                        if "addAssetForm" in analysis:
                            print("\nAdd asset form:")
                            if "forms" in analysis["addAssetForm"]:
                                form_count = len(analysis["addAssetForm"]["forms"])
                                print(f"  Forms found: {form_count}")
                                
                                if form_count > 0:
                                    for i, form in enumerate(analysis["addAssetForm"]["forms"]):
                                        print(f"  Form {i+1}: {len(form.get('inputs', []))} fields")
                        
                        if "selectors" in analysis:
                            print("\nPotential selectors:")
                            for field, selectors in analysis["selectors"].items():
                                if selectors:
                                    print(f"  {field}: {len(selectors)} selectors")
                                    for selector in selectors[:2]:
                                        print(f"    - {selector}")
                    
                    save_option = input("\nSave this analysis to a file? (y/n): ").strip().lower()
                    if save_option == 'y':
                        filename = input("Enter filename (default: analysis.json): ").strip()
                        if not filename:
                            filename = "analysis.json"
                        
                        with open(filename, 'w') as f:
                            json.dump(analysis, f, indent=2)
                        print(f"Analysis saved to {filename}")
                except Exception as e:
                    print(f"Error analyzing website: {str(e)}")
                    
            elif choice == '4':  # Edit configuration
                config_file = "config.json"
                config = {}
                
                if Path(config_file).exists():
                    try:
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                        print(f"\nLoaded existing configuration from {config_file}")
                    except Exception as e:
                        print(f"Error loading configuration: {str(e)}")
                        config = {}
                else:
                    print("\nCreating new configuration file")
                
                # Edit credentials
                print("\nEnter authentication details (leave empty to keep existing values):")
                
                token = input(f"Access token (current: {config.get('access_token', 'None')}): ").strip()
                if token:
                    config['access_token'] = token
                
                api_key = input(f"API key (current: {config.get('api_key', 'None')}): ").strip()
                if api_key:
                    config['api_key'] = api_key
                
                username = input(f"Username (current: {config.get('username', 'None')}): ").strip()
                if username:
                    config['username'] = username
                
                password = input(f"Password (current: {config.get('password', 'None')}): ").strip()
                if password:
                    config['password'] = password
                
                # Edit default values
                print("\nEnter default values (leave empty to keep existing values):")
                
                if 'default_values' not in config:
                    config['default_values'] = {}
                
                title = input(f"Default title (current: {config.get('default_values', {}).get('title', 'None')}): ").strip()
                if title:
                    config['default_values']['title'] = title
                
                desc = input(f"Default description (current: {config.get('default_values', {}).get('description', 'None')}): ").strip()
                if desc:
                    config['default_values']['description'] = desc
                
                tags = input(f"Default tags, comma separated (current: {', '.join(config.get('default_values', {}).get('tags', []))}): ").strip()
                if tags:
                    config['default_values']['tags'] = [tag.strip() for tag in tags.split(',') if tag.strip()]
                
                # Save configuration
                try:
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"\nConfiguration saved to {config_file}")
                    
                    # Reload agent with new config if it exists
                    if agent:
                        agent.close()
                        agent = None
                except Exception as e:
                    print(f"Error saving configuration: {str(e)}")
                    
            elif choice == '5':  # Exit
                if agent:
                    agent.close()
                print("\nExiting interactive mode. Goodbye!")
                return
                
            else:
                print("Invalid option. Please try again.")
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    finally:
        if agent:
            agent.close()


def main():
    """Main entry point for the CLI"""
    
    # Load environment variables
    load_dotenv()
    
    # Parse arguments
    parser = setup_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Execute command
    if args.command == 'fill':
        fill_command(args)
    elif args.command == 'extract':
        extract_command(args)
    elif args.command == 'batch':
        batch_command(args)
    elif args.command == 'analyze':
        analyze_command(args)
    elif args.command == 'interactive':
        interactive_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()