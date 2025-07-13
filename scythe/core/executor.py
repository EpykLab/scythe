import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .ttp import TTP
from typing import Optional
from ..behaviors.base import Behavior

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

        self.driver = None
        self.results = []

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
                    
                    if success:
                        consecutive_failures = 0
                        self.logger.warning(f"SUCCESS: '{payload}'")
                        current_url = self.driver.current_url if self.driver else "unknown"
                        self.results.append({'payload': payload, 'url': current_url})
                    else:
                        consecutive_failures += 1
                        self.logger.info("Step did not complete successfully")

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
            self.logger.warning(f"Found {len(self.results)} potential vulnerabilities:")
            for result in self.results:
                self.logger.warning(f"  - Payload: {result['payload']} | URL: {result['url']}")
        else:
            self.logger.info("No vulnerabilities detected.")
