import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .ttp import TTP

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
    def __init__(self, ttp: TTP, target_url: str, headless: bool = True, delay: int = 1):
        self.ttp = ttp
        self.target_url = target_url
        self.delay = delay
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

        self._setup_driver()

        try:
            for i, payload in enumerate(self.ttp.get_payloads(), 1):
                self.logger.info(f"Attempt {i}: Executing with payload -> '{payload}'")

                self.driver.get(self.target_url)
                self.ttp.execute_step(self.driver, payload)

                time.sleep(self.delay) # Wait for page reaction

                if self.ttp.verify_result(self.driver):
                    self.logger.warning(f"SUCCESS: Vulnerability detected with payload: '{payload}'")
                    self.results.append({'payload': payload, 'url': self.driver.current_url})
                else:
                    self.logger.info("Step failed as expected for a secure system.")

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
