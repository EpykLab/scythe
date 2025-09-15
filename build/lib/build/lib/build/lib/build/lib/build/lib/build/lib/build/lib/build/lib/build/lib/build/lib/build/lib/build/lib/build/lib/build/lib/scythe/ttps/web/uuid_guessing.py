from selenium.webdriver.remote.webdriver import WebDriver
from ...core.ttp import TTP
from ...payloads.generators import PayloadGenerator

import requests
from uuid import UUID


class GuessUUIDInURL(TTP):
    def __init__(self,
                 target_url: str,
                 uri_root_path: str,
                 payload_generator: PayloadGenerator,
                 expected_result: bool = True,
                 authentication=None):

        super().__init__(
            name="UUID Guessing",
            description="simulate bruteforcing UUID's in the URL path",
            expected_result=expected_result,
            authentication=authentication)

        self.target_url = target_url
        self.uri_root_path = uri_root_path
        self.payload_generator = payload_generator

    def get_payloads(self):
        yield from self.payload_generator()

    def execute_step(self, driver: WebDriver, payload: UUID):
        driver.get(f"{self.target_url}{self.uri_root_path}{str(payload)}")

    def verify_result(self, driver: WebDriver) -> bool:
        resp = requests.head(driver.current_url, timeout=5)

        if resp.status_code == 404 or 401 or 403:
            return False
        else:
            return True
