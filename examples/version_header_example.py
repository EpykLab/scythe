#!/usr/bin/env python3
"""
Example demonstrating X-SCYTHE-TARGET-VERSION header extraction in Scythe.

This example shows how Scythe automatically captures the X-SCYTHE-TARGET-VERSION
header from HTTP responses and displays version information in test results.

The target web application should set this header to indicate its version,
for example:
    X-SCYTHE-TARGET-VERSION: 1.3.2

Scythe will then extract this header and include it in test output so you can
see which version of your web application is being tested.
"""

import sys
import os

# Add the parent directory to the path so we can import scythe
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import NavigateAction, AssertAction
from scythe.journeys.executor import JourneyExecutor
from selenium.webdriver.remote.webdriver import WebDriver
from typing import Generator, Any


class VersionTestTTP(TTP):
    """
    Simple TTP that demonstrates version header extraction.
    
    This TTP navigates to different pages to trigger HTTP responses
    that may contain the X-SCYTHE-TARGET-VERSION header.
    """
    
    def __init__(self):
        super().__init__(
            name="Version Header Test",
            description="Tests version header extraction from HTTP responses",
            expected_result=True
        )
    
    def get_payloads(self) -> Generator[Any, None, None]:
        """Generate different URL paths to test."""
        paths = [
            "/",
            "/about",
            "/api/health",
            "/login",
            "/dashboard"
        ]
        
        for path in paths:
            yield path
    
    def execute_step(self, driver: WebDriver, payload: Any) -> None:
        """Navigate to the URL path."""
        current_url = driver.current_url
        base_url = current_url.split('/', 3)[:3]  # Get protocol://domain
        target_url = '/'.join(base_url) + str(payload)
        
        print(f"Navigating to: {target_url}")
        driver.get(target_url)
    
    def verify_result(self, driver: WebDriver) -> bool:
        """Check if the page loaded successfully."""
        try:
            # Simple check: page title exists and page loaded
            title = driver.title
            return len(title) > 0 and "404" not in title.lower()
        except Exception:
            return False


def run_ttp_example(target_url: str) -> bool:
    """
    Run a TTP test that demonstrates version header extraction.
    
    Args:
        target_url: URL of the target web application
        
    Returns:
        True if all test results matched expectations, False otherwise
    """
    print("="*60)
    print("TTP VERSION HEADER EXTRACTION EXAMPLE")
    print("="*60)
    print(f"Target URL: {target_url}")
    print()
    print("This example will:")
    print("1. Navigate to different pages on your web application")
    print("2. Extract X-SCYTHE-TARGET-VERSION headers from responses")
    print("3. Display version information in test results")
    print()
    print("Make sure your web application sets the header like:")
    print("  X-SCYTHE-TARGET-VERSION: 1.3.2")
    print()
    
    # Create and run the TTP
    version_ttp = VersionTestTTP()
    executor = TTPExecutor(
        ttp=version_ttp,
        target_url=target_url,
        headless=True,
        delay=1
    )
    
    executor.run()
    
    # Return whether the test was successful
    return executor.was_successful()


def run_journey_example(target_url: str) -> bool:
    """
    Run a Journey test that demonstrates version header extraction.
    
    Args:
        target_url: URL of the target web application
        
    Returns:
        True if journey succeeded as expected, False otherwise
    """
    print("\n" + "="*60)
    print("JOURNEY VERSION HEADER EXTRACTION EXAMPLE")
    print("="*60)
    print(f"Target URL: {target_url}")
    print()
    
    # Create a simple journey
    journey = Journey(
        name="Version Detection Journey",
        description="Multi-step journey to detect application version",
        expected_result=True
    )
    
    # Step 1: Home page
    home_step = Step(
        name="Visit Home Page",
        description="Navigate to application home page"
    )
    home_step.add_action(NavigateAction(url=target_url))
    home_step.add_action(AssertAction("element_present", "true", "body"))
    journey.add_step(home_step)
    
    # Step 2: About page
    about_step = Step(
        name="Visit About Page", 
        description="Navigate to about page"
    )
    about_step.add_action(NavigateAction(url=f"{target_url}/about"))
    about_step.add_action(AssertAction("element_present", "true", "body"))
    journey.add_step(about_step)
    
    # Step 3: API endpoint
    api_step = Step(
        name="Check API Endpoint",
        description="Navigate to API health endpoint"
    )
    api_step.add_action(NavigateAction(url=f"{target_url}/api/health"))
    journey.add_step(api_step)
    
    # Execute the journey
    executor = JourneyExecutor(
        journey=journey,
        target_url=target_url,
        headless=True
    )
    
    result = executor.run()
    
    # Display additional version analysis
    if result and result.get('target_versions'):
        print("\nDetailed Version Analysis:")
        versions = result['target_versions']
        unique_versions = list(set(versions))
        
        print(f"Total version detections: {len(versions)}")
        print(f"Unique versions found: {len(unique_versions)}")
        
        for version in unique_versions:
            count = versions.count(version)
            percentage = (count / len(versions)) * 100
            print(f"  Version {version}: {count} times ({percentage:.1f}%)")
    
    # Return whether the journey was successful
    return executor.was_successful()


def main():
    """Main function to run the version header extraction examples."""
    
    # Default target URL - change this to your application
    default_url = "http://localhost:8080"
    
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        target_url = default_url
        print(f"No URL provided, using default: {default_url}")
        print("Usage: python version_header_example.py <target_url>")
        print()
    
    # Track overall success
    all_tests_passed = True
    
    try:
        # Run TTP example
        ttp_success = run_ttp_example(target_url)
        all_tests_passed = all_tests_passed and ttp_success
        
        # Run Journey example
        journey_success = run_journey_example(target_url)
        all_tests_passed = all_tests_passed and journey_success
        
        print("\n" + "="*60)
        print("EXAMPLES COMPLETED")
        print("="*60)
        print()
        print("If you see version information in the results above,")
        print("your application is correctly setting the X-SCYTHE-TARGET-VERSION header!")
        print()
        print("If no version information appears, make sure your web application")
        print("is setting the header in HTTP responses:")
        print()
        print("Example server-side code:")
        print("  # Python/Flask")
        print("  response.headers['X-SCYTHE-TARGET-VERSION'] = '1.3.2'")
        print()
        print("  # Node.js/Express")
        print("  res.set('X-SCYTHE-TARGET-VERSION', '1.3.2')")
        print()
        print("  # Java/Spring")
        print("  response.setHeader('X-SCYTHE-TARGET-VERSION', '1.3.2')")
        print()
        
        # Exit with appropriate code based on test results
        sys.exit(0 if all_tests_passed else 1)
        
    except KeyboardInterrupt:
        print("\nExample interrupted by user.")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"\nError running example: {e}")
        print("Make sure the target URL is accessible and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()