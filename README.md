# PathFinder Autofill Agent

An automated tool that extracts information from websites and SharePoint links to fill in demo asset details on the PathFinder platform.

![PathFinder Autofill Agent](https://via.placeholder.com/800x400?text=PathFinder+Autofill+Agent)

## Features

- **Automatic Data Extraction**: Extract relevant information from websites and SharePoint links
- **Intelligent Form Filling**: Automatically fill in PathFinder forms with extracted data
- **Multiple Authentication Methods**: Support for token-based, API key, and username/password authentication
- **Batch Processing**: Process multiple URLs from a CSV file
- **Website Structure Analysis**: Analyze the PathFinder website structure to help with form filling
- **Interactive Mode**: User-friendly interactive mode for ad-hoc operations
- **Command-line Interface**: Comprehensive CLI for automation and scripting

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Steps

1. Clone this repository:
   ```
   git clone https://github.com/linzele/pathfinder-autofill-agent.git
   cd pathfinder-autofill-agent
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install Playwright browsers:
   ```
   python -m playwright install
   ```

4. Create a configuration file:
   ```
   cp config.example.json config.json
   ```

5. Edit the configuration file with your credentials:
   ```
   {
     "access_token": "YOUR_ACCESS_TOKEN",
     "api_key": "YOUR_API_KEY",
     "username": "YOUR_USERNAME",
     "password": "YOUR_PASSWORD",
     "default_values": {
       "title": "Demo Asset",
       "description": "This is a demo asset for testing purposes",
       "tags": ["demo", "test", "automation"]
     }
   }
   ```

## Usage

### Basic Command Structure

```
python cli.py [command] [options]
```

### Commands

#### Fill Form

Extract data from a URL and fill in the PathFinder form:

```
python cli.py fill --url https://example.com --config config.json
```

Options:
- `--url`: Website or SharePoint URL to extract data from (required)
- `--config`: Path to configuration file (default: config.json)
- `--no-submit`: Fill the form but do not submit it
- `--headless`: Run browser in headless mode
- `--verbose`: Enable verbose logging

#### Extract Data

Extract data from a URL without filling a form:

```
python cli.py extract --url https://example.com --output extracted_data.json
```

Options:
- `--url`: Website or SharePoint URL to extract data from (required)
- `--output`: Path to output JSON file (default: extracted_data.json)
- `--headless`: Run browser in headless mode
- `--verbose`: Enable verbose logging

#### Batch Processing

Process multiple URLs from a CSV file:

```
python cli.py batch --input urls.csv --config config.json --output batch_results.json
```

Options:
- `--input`: Path to CSV file with URLs (required)
- `--config`: Path to configuration file (default: config.json)
- `--output`: Path to output JSON file (default: batch_results.json)
- `--skip-errors`: Continue processing on errors
- `--headless`: Run browser in headless mode
- `--verbose`: Enable verbose logging

#### Website Analysis

Analyze the PathFinder website structure:

```
python cli.py analyze --output analysis.json
```

Options:
- `--output`: Path to output JSON file (default: analysis.json)
- `--headless`: Run browser in headless mode
- `--verbose`: Enable verbose logging

#### Interactive Mode

Launch the interactive mode for ad-hoc operations:

```
python cli.py interactive
```

Options:
- `--headless`: Run browser in headless mode
- `--verbose`: Enable verbose logging

### Environment Variables

Instead of using a configuration file, you can set the following environment variables:

- `PATHFINDER_ACCESS_TOKEN`: Access token for authentication
- `PATHFINDER_API_KEY`: API key for authentication
- `PATHFINDER_USERNAME`: Username for authentication
- `PATHFINDER_PASSWORD`: Password for authentication

## Module Structure

- `main.py`: Core functionality for form automation
- `auth.py`: Authentication handling with PathFinder website
- `extractor.py`: Data extraction from websites and SharePoint
- `analyzer.py`: Analysis tool for inspecting PathFinder website structure
- `cli.py`: Command-line interface for the agent
- `tests.py`: Unit tests for the agent

## CSV File Format

For batch processing, the CSV file should have one URL per line. If the first row contains headers, the tool will try to find a column with "url", "link", "address", or "website" in the header name.

Example:
```
url,name
https://example.com,Example Site
https://example.org,Example Organization
```

## Configuration File

The configuration file is in JSON format and has the following structure:

```json
{
  "access_token": "YOUR_ACCESS_TOKEN",
  "api_key": "YOUR_API_KEY",
  "username": "YOUR_USERNAME",
  "password": "YOUR_PASSWORD",
  "default_values": {
    "title": "Demo Asset",
    "description": "This is a demo asset for testing purposes",
    "tags": ["demo", "test", "automation"]
  }
}
```

## Authentication

The agent supports three methods of authentication:

1. **Access Token**: The most secure and preferred method
2. **API Key**: Alternative method if access token is not available
3. **Username/Password**: Traditional login method

The agent will try each method in the order listed above, using values from environment variables first, then from the configuration file.

## Running Tests

To run the unit tests:

```
python -m unittest tests.py
```

## Development

### Setting Up Development Environment

1. Clone the repository
2. Install development dependencies:
   ```
   pip install -r requirements.txt
   pip install pytest pytest-cov black
   ```
3. Install Playwright browsers:
   ```
   python -m playwright install
   ```

### Running Tests

```
python -m pytest tests.py -v
```

### Code Formatting

```
black *.py
```

## Contributing

1. Fork the repository
2. Create a new branch: `git checkout -b feature-branch`
3. Make your changes and commit: `git commit -m "Add feature"`
4. Push to your fork: `git push origin feature-branch`
5. Create a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Browser Automation Issues

If you encounter issues with browser automation:

1. Ensure you have installed Playwright browsers:
   ```
   python -m playwright install
   ```

2. Try running without headless mode to see what's happening:
   ```
   python cli.py fill --url https://example.com --config config.json
   ```

### Authentication Issues

If you're having trouble authenticating:

1. Use the analyze command to understand the authentication methods:
   ```
   python cli.py analyze
   ```

2. Check the authentication tokens in your configuration file and ensure they're not expired.

3. If using username/password authentication, ensure your credentials are correct.

## Example Workflow

1. Extract data from a website:
   ```
   python cli.py extract --url https://example.com --output data.json
   ```

2. Edit the extracted data if needed.

3. Fill in the PathFinder form with the edited data:
   ```
   python cli.py fill --url https://example.com --config config.json
   ```

## Credits

Developed by Lincoln Zele for the PathFinder project.