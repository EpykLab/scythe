#!/usr/bin/env python3
"""
Test script for verifying header extraction methods.

This script tests both the banner grab method and the Selenium-based method
to help debug header extraction issues.
"""

import logging
import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from scythe.core.headers import HeaderExtractor

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HeaderTest")


def test_banner_grab(url: str) -> None:
    """Test the banner grab method."""
    print(f"\n{'='*60}")
    print("TESTING BANNER GRAB METHOD")
    print(f"{'='*60}")
    
    extractor = HeaderExtractor()
    
    # Test HEAD request
    print(f"\n--- Testing HEAD request to {url} ---")
    version = extractor.banner_grab(url, method="HEAD")
    if version:
        print(f"✅ SUCCESS: Found version '{version}' via HEAD request")
    else:
        print("❌ FAILED: No version found via HEAD request")
    
    # Test GET request
    print(f"\n--- Testing GET request to {url} ---")
    version = extractor.banner_grab(url, method="GET")
    if version:
        print(f"✅ SUCCESS: Found version '{version}' via GET request")
    else:
        print("❌ FAILED: No version found via GET request")
    
    # Get all headers for debugging
    print("\n--- All headers from GET request ---")
    headers = extractor.get_all_headers_via_request(url, method="GET")
    if headers:
        print("Headers found:")
        for name, value in headers.items():
            print(f"  {name}: {value}")
            # Highlight potential version headers
            if "scythe" in name.lower() or "version" in name.lower():
                print("    ^^^ POTENTIAL VERSION HEADER ^^^")
    else:
        print("No headers found")


def test_selenium_method(url: str) -> None:
    """Test the Selenium-based method."""
    print(f"\n{'='*60}")
    print("TESTING SELENIUM METHOD")
    print(f"{'='*60}")
    
    # Set up Chrome driver with performance logging
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run headless for testing
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Enable logging
    HeaderExtractor.enable_logging_for_driver(chrome_options)
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        extractor = HeaderExtractor()
        
        print(f"Navigating to {url}...")
        driver.get(url)
        
        # Wait a moment for logs to populate
        import time
        time.sleep(2)
        
        # Extract version
        version = extractor.extract_target_version(driver, url)
        if version:
            print(f"✅ SUCCESS: Found version '{version}' via Selenium")
        else:
            print("❌ FAILED: No version found via Selenium")
        
        # Get all headers for debugging
        print("\n--- All headers from Selenium ---")
        headers = extractor.extract_all_headers(driver, url)
        if headers:
            print("Headers found:")
            for name, value in headers.items():
                print(f"  {name}: {value}")
                if "scythe" in name.lower() or "version" in name.lower():
                    print("    ^^^ POTENTIAL VERSION HEADER ^^^")
        else:
            print("No headers found")
            
    except Exception as e:
        print(f"❌ ERROR: Selenium test failed: {e}")
    finally:
        if driver:
            driver.quit()


def test_hybrid_method(url: str) -> None:
    """Test the hybrid method."""
    print(f"\n{'='*60}")
    print("TESTING HYBRID METHOD")
    print(f"{'='*60}")
    
    # Set up Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    HeaderExtractor.enable_logging_for_driver(chrome_options)
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        extractor = HeaderExtractor()
        
        # Test hybrid method
        version = extractor.extract_target_version_hybrid(driver, url)
        if version:
            print(f"✅ SUCCESS: Found version '{version}' via hybrid method")
        else:
            print("❌ FAILED: No version found via hybrid method")
            
    except Exception as e:
        print(f"❌ ERROR: Hybrid test failed: {e}")
    finally:
        if driver:
            driver.quit()


def main():
    """Main test function."""
    if len(sys.argv) != 2:
        print("Usage: python test_header_extraction.py <URL>")
        print("Example: python test_header_extraction.py https://example.com")
        sys.exit(1)
    
    url = sys.argv[1]
    print(f"Testing header extraction for: {url}")
    
    try:
        # Test banner grab method (most reliable)
        test_banner_grab(url)
        
        # Test Selenium method
        test_selenium_method(url)
        
        # Test hybrid method
        test_hybrid_method(url)
        
        print(f"\n{'='*60}")
        print("TESTING COMPLETE")
        print(f"{'='*60}")
        print("\nRecommendations:")
        print("1. If banner grab works, use that method for reliability")
        print("2. If only Selenium works, check Chrome logging capabilities")
        print("3. If neither works, verify the server is actually sending the header")
        print("4. Check header name case sensitivity (X-Scythe-Target-Version vs X-SCYTHE-TARGET-VERSION)")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        logger.exception("Test failed with exception")


if __name__ == "__main__":
    main()