from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException
from ...core.ttp import TTP
from ...payloads.generators import PayloadGenerator

class InputFieldInjector(TTP):
    def __init__(self,
                 target_url: str,
                 field_selector: str,
                 submit_selector: str,
                 payload_generator: PayloadGenerator):

        super().__init__(
            name="SQL Injection via URL manipulation", 
            description="simulate an sql Injection by manipulation of url queries")

        self.target_url = target_url
        self.field_selector = field_selector
        self.payload_generator = payload_generator
        self.submit_selector = submit_selector

    def get_payloads(self):
        """yields queries from the configured generator"""
        yield from self.payload_generator()

    def execute_step(self, driver: WebDriver, payload: str):
        """fills in a form field with an SQL payload and injects it"""
        try:
            """define the field"""
            field = driver.find_element(By.TAG_NAME, self.field_selector)

            """clear the field"""
            field.clear()

            field.send_keys(payload)

            try:
                submit_button = driver.find_element(By.CSS_SELECTOR, self.submit_selector)

                submit_button.click()
            except NoSuchElementException:
                field.send_keys("\n")

        except NoSuchElementException as e:
            raise Exception(f"could not find input field on page: {e}")


    def verify_result(self, driver: WebDriver) -> bool:
        return "sql" in driver.page_source.lower() or \
               "source" in driver.page_source.lower()


class URLManipulation(TTP):
    def __init__(self,
                 payload_generator: PayloadGenerator,
                 target_url: str):
        super().__init__(
            name="SQL Injection via URL manipulation", 
            description="simulate an sql Injection by manipulation of url queries")
        self.target_url = target_url
        self.payload_generator = payload_generator

    def get_payloads(self):
        yield from self.payload_generator()

    def execute_step(self, driver: WebDriver, payload: str):
        driver.get(f"{self.target_url}?q={payload}")

    def verify_result(self, driver: WebDriver) -> bool:
        return "sql" in driver.page_source.lower() or \
               "source" in driver.page_source.lower()
