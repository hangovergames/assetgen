#!/usr/bin/env python3

import os
import sys
import re
import time
import argparse
import logging
from pathlib import Path
from typing import Set, Dict, Optional, Tuple, List
from urllib.parse import urlparse, urljoin

try:
    import requests
except ImportError:
    logging.error("The 'requests' package is required. Please install it using: pip install requests")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

MAX_RECURSION_DEPTH = 5
TIMEOUT = 10
# Updated pattern to only match URLs, not HTML tags or example URLs
URL_PATTERN = re.compile(r'<((?:https?://|www\.)[^>]+)>')
HTML_PATTERN = re.compile(r'<!DOCTYPE\s+html|<html|<head|<body', re.IGNORECASE)

def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    try:
        result = urlparse(url)
        # Check if it's a real URL
        is_valid = all([result.scheme, result.netloc])
        logger.debug(f"URL validation for {url}: {'valid' if is_valid else 'invalid'}")
        return is_valid
    except ValueError as e:
        logger.debug(f"URL validation error for {url}: {e}")
        return False

def convert_to_markdown_url(url: str) -> str:
    """Convert URL to Markdown URL.
    
    Handles both .html and extensionless URLs by converting them to .md.
    """
    original_url = url
    if url.endswith('.html'):
        # Replace .html with .md while preserving the URL structure
        base_url = url[:-5]  # Remove .html
        url = base_url + '.md'
    elif not any(url.endswith(ext) for ext in ['.html', '.md', '.txt', '.json', '.xml', '.yaml', '.yml']):
        # If URL has no extension, append .md
        url = url + '.md'
    
    if url != original_url:
        logger.debug(f"Converted URL from {original_url} to {url}")
    return url

def is_html_content(content: str) -> bool:
    """Check if the content appears to be HTML."""
    result = bool(HTML_PATTERN.search(content))
    logger.debug(f"Content type detection: {'HTML' if result else 'not HTML'}")
    return result

def fetch_content(url_or_path: str, is_whitelisted: bool = False) -> Tuple[Optional[str], bool]:
    """Fetch content from URL or local file.
    
    Args:
        url_or_path: The URL or file path to fetch
        is_whitelisted: Whether this URL is whitelisted (affects error handling)
    
    Returns:
        Tuple[Optional[str], bool]: (content, is_html)
    """
    logger.info(f"Fetching content from: {url_or_path} (whitelisted: {is_whitelisted})")
    
    if is_valid_url(url_or_path):
        try:
            # First try the Markdown version if applicable
            markdown_url = convert_to_markdown_url(url_or_path)
            if markdown_url != url_or_path:
                try:
                    logger.debug(f"Attempting to fetch Markdown version: {markdown_url}")
                    md_response = requests.get(markdown_url, timeout=TIMEOUT)
                    md_response.raise_for_status()
                    logger.info(f"Successfully fetched Markdown version from {markdown_url}")
                    return md_response.text, False
                except requests.RequestException as e:
                    logger.debug(f"Failed to fetch Markdown version, falling back to original URL: {e}")
                    pass
            
            # Try the original URL
            logger.debug(f"Fetching original URL: {url_or_path}")
            response = requests.get(url_or_path, timeout=TIMEOUT)
            response.raise_for_status()
            content = response.text
            
            # If we got HTML, try to extract meaningful text
            if is_html_content(content):
                logger.debug("Extracting text content from HTML")
                text_content = ' '.join(re.findall(r'>([^<]+)<', content))
                return text_content, True
            return content, False
            
        except requests.RequestException as e:
            if is_whitelisted:
                logger.error(f"Failed to fetch whitelisted URL {url_or_path}: {e}")
                sys.exit(1)
            else:
                logger.warning(f"Failed to fetch URL {url_or_path}: {e}")
                return None, False
    else:
        try:
            path = Path(url_or_path)
            if not path.exists():
                if is_whitelisted:
                    logger.error(f"File not found: {url_or_path}")
                    sys.exit(1)
                else:
                    logger.warning(f"File not found: {url_or_path}")
                    return None, False
            logger.debug(f"Reading local file: {path}")
            content = path.read_text()
            is_html = is_html_content(content)
            logger.info(f"Successfully read local file: {path} (HTML: {is_html})")
            return content, is_html
        except Exception as e:
            if is_whitelisted:
                logger.error(f"Failed to read file {url_or_path}: {e}")
                sys.exit(1)
            else:
                logger.warning(f"Failed to read file {url_or_path}: {e}")
                return None, False

def is_url_allowed(url: str, whitelist: Optional[List[str]], source_url: Optional[str]) -> bool:
    """Check if a URL is allowed based on whitelist and source URL."""
    # First check if it's a valid URL
    if not is_valid_url(url):
        logger.debug(f"URL {url} is not valid, skipping")
        return False
        
    # Always allow the source URL
    if source_url and url == source_url:
        logger.debug(f"Allowing source URL: {url}")
        return True
    
    # If no whitelist is provided, only allow URLs from the same domain as the source
    if not whitelist:
        if source_url:
            source_domain = urlparse(source_url).netloc
            url_domain = urlparse(url).netloc
            allowed = source_domain == url_domain
            logger.debug(f"No whitelist specified, checking domain match: {url_domain} vs {source_domain}")
            return allowed
        else:
            logger.debug("No whitelist and no source URL, skipping all URLs")
            return False
    
    # Check if URL is in whitelist
    allowed = url in whitelist
    if allowed:
        logger.debug(f"URL {url} found in whitelist")
    else:
        logger.debug(f"URL {url} not in whitelist")
    return allowed

def process_content(content: str, processed_urls: Set[str], depth: int, whitelist: Optional[List[str]], source_url: Optional[str]) -> Dict[str, str]:
    """Process content and recursively fetch referenced URLs."""
    logger.info(f"Processing content at depth {depth}")
    
    if depth >= MAX_RECURSION_DEPTH:
        logger.error(f"Maximum recursion depth reached ({MAX_RECURSION_DEPTH})")
        sys.exit(1)

    results = {}
    urls = URL_PATTERN.findall(content)
    logger.debug(f"Found {len(urls)} URLs in content")
    
    for url in urls:
        if url in processed_urls:
            logger.debug(f"Skipping already processed URL: {url}")
            continue
            
        # Check if URL is allowed before attempting to fetch
        is_whitelisted = is_url_allowed(url, whitelist, source_url)
        if not is_whitelisted:
            logger.debug(f"Skipping non-whitelisted or invalid URL: {url}")
            continue
            
        processed_urls.add(url)
        logger.debug(f"Processing URL {url} at depth {depth}")
        content, is_html = fetch_content(url, is_whitelisted)
        
        if not content:
            if is_whitelisted:
                logger.error(f"Failed to fetch content from whitelisted URL: {url}")
                sys.exit(1)
            continue
            
        # If we got HTML content, try to extract meaningful text
        if is_html:
            logger.debug(f"Extracting text from HTML content for {url}")
            content = ' '.join(re.findall(r'>([^<]+)<', content))
        
        # Add URL header to the content
        results[url] = f"# URL: {url}\n\n{content}"
        
        # Recursively process new content
        logger.debug(f"Starting recursive processing for {url} at depth {depth + 1}")
        nested_results = process_content(content, processed_urls, depth + 1, whitelist, source_url)
        results.update(nested_results)
    
    return results

def process_source(input_source: str, processed_urls: Set[str], whitelist: Optional[List[str]]) -> bool:
    """Process a single input source and its referenced URLs.
    
    Returns:
        bool: True if processing was successful, False otherwise
    """
    logger.info(f"Starting to process source: {input_source}")
    
    # Fetch initial content (command-line URLs are always treated as whitelisted)
    initial_content, is_html = fetch_content(input_source, True)
    if not initial_content:
        logger.error(f"Could not fetch content from {input_source}")
        sys.exit(1)
    
    # If we got HTML content, try to extract meaningful text
    if is_html:
        logger.debug("Extracting text from HTML content for initial source")
        initial_content = ' '.join(re.findall(r'>([^<]+)<', initial_content))
        
    # Process all referenced URLs
    results = process_content(initial_content, processed_urls, 0, whitelist, input_source)
    
    # Output results
    logger.info(f"=== Processing {input_source} ===")
    logger.info("Initial content:")
    print(initial_content)
    logger.info("---")
    
    for url, content in results.items():
        logger.info(f"Content from {url}:")
        print(content)
        logger.info("---")
    
    return True

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Fetch and process prompts from URLs or local files.')
    parser.add_argument('sources', nargs='+', help='URLs or file paths to process')
    parser.add_argument('--whitelist', '-w', nargs='*', help='List of allowed URLs (if not provided, all URLs are allowed)')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug logging')
    return parser.parse_args()

def main() -> None:
    """Main function to process input and generate output."""
    args = parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    processed_urls: Set[str] = set()
    logger.info(f"Starting processing with {len(args.sources)} source(s)")
    
    for source in args.sources:
        process_source(source, processed_urls, args.whitelist)
    
    logger.info("Processing complete: All sources processed successfully")

if __name__ == "__main__":
    main() 