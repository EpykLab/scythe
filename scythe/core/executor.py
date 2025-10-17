import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .ttp import TTP
from typing import Optional
from ..behaviors.base import Behavior
from .headers import HeaderExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ttp_test.log'),
        logging.StreamHandler()
    ]
)

class TTPExecutor:
    """
    The main engine for running TTP tests.
    """
    def __init__(self, ttp: TTP, target_url: str, headless: bool = True, delay: int = 1, behavior: Optional[Behavior] = None):
        self.ttp = ttp
        self.target_url = target_url
        self.delay = delay
        self.behavior = behavior
        self.logger = logging.getLogger(self.ttp.name)

        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")

        # Enable header extraction capabilities
        HeaderExtractor.enable_logging_for_driver(self.chrome_options)

        self.driver = None
        self.results = []
        self.header_extractor = HeaderExtractor()
        self.has_test_failures = False  # Track if any test had unexpected results

    def _setup_driver(self):
        """Initializes the WebDriver."""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.logger.info("WebDriver initialized.")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    def run(self):
        """Executes the full TTP test flow."""
        self.logger.info(f"Starting TTP: '{self.ttp.name}' on {self.target_url}")
        self.logger.info(f"Description: {self.ttp.description}")
        
        if self.behavior:
            self.logger.info(f"Using behavior: {self.behavior.name}")
            self.logger.info(f"Behavior description: {self.behavior.description}")

        self._setup_driver()

        try:
            # Handle authentication if required
            if self.ttp.requires_authentication():
                auth_name = self.ttp.authentication.name if self.ttp.authentication else "Unknown"
                self.logger.info(f"Authentication required for TTP: {auth_name}")
                if self.driver:
                    auth_success = self.ttp.authenticate(self.driver, self.target_url)
                else:
                    self.logger.error("WebDriver not available for authentication")
                    return
                if not auth_success:
                    self.logger.error("Authentication failed - aborting TTP execution")
                    return
                self.logger.info("Authentication successful")

            # Pre-execution behavior setup
            if self.behavior and self.driver:
                self.behavior.pre_execution(self.driver, self.target_url)

            consecutive_failures = 0
            
            for i, payload in enumerate(self.ttp.get_payloads(), 1):
                # Check if behavior wants to continue
                if self.behavior and not self.behavior.should_continue(i, consecutive_failures):
                    self.logger.info("Behavior requested to stop execution")
                    break
                
                self.logger.info(f"Attempt {i}: Executing with payload -> '{payload}'")

                # Pre-step behavior
                if self.behavior and self.driver:
                    self.behavior.pre_step(self.driver, payload, i)

                try:
                    if self.driver:
                        self.driver.get(self.target_url)
                        self.ttp.execute_step(self.driver, payload)

                    # Use behavior delay if available, otherwise use default
                    if self.behavior:
                        step_delay = self.behavior.get_step_delay(i)
                    else:
                        step_delay = self.delay
                    
                    time.sleep(step_delay)

                    success = self.ttp.verify_result(self.driver) if self.driver else False
                    
                    # Compare actual result with expected result
                    if success:
                        consecutive_failures = 0
                        current_url = self.driver.current_url if self.driver else "unknown"
                        
                        # Extract target version header
                        target_version = None
                        if self.driver:
                            target_version = self.header_extractor.extract_target_version(self.driver, self.target_url)
                        
                        result_entry = {
                            'payload': payload, 
                            'url': current_url, 
                            'expected': self.ttp.expected_result, 
                            'actual': True,
                            'target_version': target_version
                        }
                        self.results.append(result_entry)
                        
                        if self.ttp.expected_result:
                            version_info = f" | Version: {target_version}" if target_version else ""
                            self.logger.info(f"EXPECTED SUCCESS: '{payload}'{version_info}")
                        else:
                            version_info = f" | Version: {target_version}" if target_version else ""
                            self.logger.warning(f"UNEXPECTED SUCCESS: '{payload}' (expected to fail){version_info}")
                            self.has_test_failures = True  # Mark as failure when result differs from expected
                    else:
                        consecutive_failures += 1
                        if self.ttp.expected_result:
                            self.logger.info(f"EXPECTED FAILURE: '{payload}' (security control working)")
                            self.has_test_failures = True  # Mark as failure when result differs from expected
                        else:
                            self.logger.info(f"EXPECTED FAILURE: '{payload}'")

                    # Post-step behavior
                    if self.behavior and self.driver:
                        self.behavior.post_step(self.driver, payload, i, success)

                except Exception as step_error:
                    consecutive_failures += 1
                    self.logger.error(f"Error during step {i}: {step_error}")
                    
                    # Let behavior handle the error
                    if self.behavior:
                        if not self.behavior.on_error(step_error, i):
                            self.logger.info("Behavior requested to stop due to error")
                            break
                    else:
                        # Default behavior: continue on most errors
                        continue

            # Post-execution behavior cleanup
            if self.behavior and self.driver:
                self.behavior.post_execution(self.driver, self.results)

        except KeyboardInterrupt:
            self.logger.info("Test interrupted by user.")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        finally:
            self._cleanup()

    def _cleanup(self):
        """Closes the WebDriver and prints a summary."""
        if self.driver:
            self.driver.quit()

        self.logger.info("\n" + "="*50)
        self.logger.info(f"TTP SUMMARY: {self.ttp.name}")
        self.logger.info("="*50)

        if self.results:
            expected_successes = [r for r in self.results if r['expected'] and r['actual']]
            unexpected_successes = [r for r in self.results if not r['expected'] and r['actual']]
            
            self.logger.info(f"Total results: {len(self.results)}")
            
            if expected_successes:
                self.logger.info(f"Expected successes: {len(expected_successes)}")
                for result in expected_successes:
                    version_info = f" | Version: {result['target_version']}" if result.get('target_version') else ""
                    self.logger.info(f"  ✓ Payload: {result['payload']} | URL: {result['url']}{version_info}")
            
            if unexpected_successes:
                self.logger.warning(f"Unexpected successes: {len(unexpected_successes)}")
                for result in unexpected_successes:
                    version_info = f" | Version: {result['target_version']}" if result.get('target_version') else ""
                    self.logger.warning(f"  ✗ Payload: {result['payload']} | URL: {result['url']}{version_info}")
            
            # Display version summary
            version_summary = self.header_extractor.get_version_summary(self.results)
            if version_summary['results_with_version'] > 0:
                self.logger.info("\nTarget Version Summary:")
                self.logger.info(f"  Results with version info: {version_summary['results_with_version']}/{version_summary['total_results']}")
                if version_summary['unique_versions']:
                    for version in version_summary['unique_versions']:
                        count = version_summary['version_counts'][version]
                        self.logger.info(f"  Version {version}: {count} result(s)")
            else:
                self.logger.info("\nNo X-SCYTHE-TARGET-VERSION headers detected in responses.")
        else:
            if self.ttp.expected_result:
                self.logger.info("No successes detected (expected to find vulnerabilities).")
            else:
                self.logger.info("No successes detected (security controls working as expected).")
        
        # Log overall test status
        if self.has_test_failures:
            self.logger.error("\n✗ TEST FAILED: One or more test results differed from expected")
        else:
            self.logger.info("\n✓ TEST PASSED: All test results matched expectations")
    
    def was_successful(self) -> bool:
        """
        Check if all test results matched expectations.
        
        Returns:
            True if all test results matched expectations, False otherwise
        """
        return not self.has_test_failures
