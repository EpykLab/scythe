from abc import ABC, abstractmethod
from typing import Generator, Any
from selenium.webdriver.remote.webdriver import WebDriver

class TTP(ABC):
    """
    Abstract Base Class for a single Tactic, Technique, and Procedure (TTP).

    Each TTP implementation must define how to generate payloads, how to
    execute a test step with a given payload, and how to verify the outcome.
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def get_payloads(self) -> Generator[Any, None, None]:
        """Yields payloads for the test execution."""
        pass

    @abstractmethod
    def execute_step(self, driver: WebDriver, payload: Any) -> None:
        """
        Executes a single test action using the provided payload.
        This method should perform the action (e.g., fill form, click button).
        """
        pass

    @abstractmethod
    def verify_result(self, driver: WebDriver) -> bool:
        """
        Verifies the outcome of the executed step.

        Returns:
            True if the test indicates a potential success/vulnerability, False otherwise.
        """
        pass
