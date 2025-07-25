import json
import logging
from typing import Optional, Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options


class HeaderExtractor:
    """
    Utility class for extracting HTTP response headers from WebDriver sessions.

    Specifically designed to capture the X-SCYTHE-TARGET-VERSION header
    that indicates the version of the web application being tested.
    """

    SCYTHE_VERSION_HEADER = "X-Scythe-Target-Version"

    def __init__(self):
        self.logger = logging.getLogger("HeaderExtractor")

    @staticmethod
    def enable_logging_for_driver(chrome_options: Options) -> None:
        """
        Enable performance logging capabilities for Chrome WebDriver.

        This must be called during WebDriver setup to capture network logs.

        Args:
            chrome_options: Chrome options object to modify
        """
        # Enable performance logging to capture network events
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--log-level=0")
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    def extract_target_version(self, driver: WebDriver, target_url: Optional[str] = None) -> Optional[str]:
        """
        Extract the X-SCYTHE-TARGET-VERSION header from the most recent HTTP response.

        Args:
            driver: WebDriver instance with performance logging enabled
            target_url: Optional URL to filter responses for (if None, uses any response)

        Returns:
            Version string if header found, None otherwise
        """
        try:
            # Get performance logs - using getattr to handle type checking
            if not hasattr(driver, 'get_log'):
                self.logger.warning("WebDriver does not support get_log method")
                return None

            logs = getattr(driver, 'get_log')('performance')

            # Look for Network.responseReceived events
            for log_entry in reversed(logs):  # Start with most recent
                try:
                    message = log_entry.get('message', {})
                    if isinstance(message, str):
                        message = json.loads(message)

                    method = message.get('message', {}).get('method', '')
                    params = message.get('message', {}).get('params', {})

                    if method == 'Network.responseReceived':
                        response = params.get('response', {})
                        headers = response.get('headers', {})
                        response_url = response.get('url', '')

                        # Filter by target URL if specified
                        if target_url and target_url not in response_url:
                            continue

                        # Look for the version header (case-insensitive)
                        version = self._find_version_header(headers)
                        if version:
                            self.logger.debug(f"Found target version '{version}' in response from {response_url}")
                            return version

                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    self.logger.debug(f"Error parsing log entry: {e}")
                    continue

            self.logger.debug("No X-SCYTHE-TARGET-VERSION header found in network logs")
            return None

        except Exception as e:
            self.logger.warning(f"Failed to extract target version from logs: {e}")
            return None

    def _find_version_header(self, headers: Dict[str, Any]) -> Optional[str]:
        """
        Find the version header in a case-insensitive manner.

        Args:
            headers: Dictionary of HTTP headers

        Returns:
            Version string if found, None otherwise
        """
        # Check for exact case match first
        if self.SCYTHE_VERSION_HEADER in headers:
            return str(headers[self.SCYTHE_VERSION_HEADER]).strip()

        # Check case-insensitive
        header_lower = self.SCYTHE_VERSION_HEADER.lower()
        for header_name, header_value in headers.items():
            if header_name.lower() == header_lower:
                return str(header_value).strip()

        return None

    def extract_all_headers(self, driver: WebDriver, target_url: Optional[str] = None) -> Dict[str, str]:
        """
        Extract all headers from the most recent HTTP response.

        Useful for debugging or when additional headers might be needed.

        Args:
            driver: WebDriver instance with performance logging enabled
            target_url: Optional URL to filter responses for

        Returns:
            Dictionary of headers from the most recent response
        """
        try:
            # Get performance logs - using getattr to handle type checking
            if not hasattr(driver, 'get_log'):
                self.logger.warning("WebDriver does not support get_log method")
                return {}

            logs = getattr(driver, 'get_log')('performance')

            for log_entry in reversed(logs):
                try:
                    message = log_entry.get('message', {})
                    if isinstance(message, str):
                        message = json.loads(message)

                    method = message.get('message', {}).get('method', '')
                    params = message.get('message', {}).get('params', {})

                    if method == 'Network.responseReceived':
                        response = params.get('response', {})
                        headers = response.get('headers', {})
                        response_url = response.get('url', '')

                        # Filter by target URL if specified
                        if target_url and target_url not in response_url:
                            continue

                        # Convert all header values to strings
                        return {k: str(v) for k, v in headers.items()}

                except (json.JSONDecodeError, KeyError, AttributeError):
                    continue

            return {}

        except Exception as e:
            self.logger.warning(f"Failed to extract headers from logs: {e}")
            return {}

    def get_version_summary(self, results: list) -> Dict[str, Any]:
        """
        Analyze version information across multiple test results.

        Args:
            results: List of result dictionaries containing version information

        Returns:
            Dictionary with version analysis summary
        """
        versions = []
        results_with_version = 0

        for result in results:
            version = result.get('target_version')
            if version:
                versions.append(version)
                results_with_version += 1

        summary = {
            'total_results': len(results),
            'results_with_version': results_with_version,
            'unique_versions': list(set(versions)) if versions else [],
            'version_counts': {}
        }

        # Count occurrences of each version
        for version in versions:
            summary['version_counts'][version] = summary['version_counts'].get(version, 0) + 1

        return summary
