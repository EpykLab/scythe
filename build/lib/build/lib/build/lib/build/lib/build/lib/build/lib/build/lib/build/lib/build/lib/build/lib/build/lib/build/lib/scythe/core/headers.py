import json
import logging
import requests
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
    def _normalize_url(url: str) -> str:
        """Ensure the URL has a scheme so requests can handle it."""
        if not isinstance(url, str):
            return url
        lower = url.lower().strip()
        if lower.startswith("http://") or lower.startswith("https://"):
            return url
        return f"http://{url}"

    @staticmethod
    def _is_static_asset(url: str, headers: Optional[Dict[str, Any]] = None) -> bool:
        """Heuristically determine if a URL/log entry is a static asset (css/js/image/font/etc.)."""
        try:
            if not isinstance(url, str):
                return False
            u = url.lower()
            # Common static file extensions
            static_exts = (
                '.css', '.js', '.mjs', '.map', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
                '.woff', '.woff2', '.ttf', '.otf', '.eot', '.webp', '.mp4', '.webm', '.mp3', '.wav'
            )
            if any(u.endswith(ext) for ext in static_exts):
                return True
            if '/static/' in u or '/assets/' in u:
                return True
            # Content-Type hint
            if isinstance(headers, dict):
                # case-insensitive lookup
                ctype = None
                for k, v in headers.items():
                    if isinstance(k, str) and k.lower() == 'content-type':
                        ctype = str(v).lower()
                        break
                if ctype and (ctype.startswith('text/css') or
                              ctype.startswith('application/javascript') or
                              ctype.startswith('text/javascript') or
                              ctype.startswith('image/') or
                              ctype.startswith('font/')):
                    return True
        except Exception:
            # Be safe: if unsure, do not classify as static
            return False
        return False

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

    def banner_grab(self, url: str, timeout: int = 10, method: str = "HEAD") -> Optional[str]:
        """
        Perform a simple HTTP request to extract the X-SCYTHE-TARGET-VERSION header.
        
        This is a more reliable alternative to Selenium's performance logging
        for cases where you just need to grab headers.
        
        Args:
            url: URL to make the request to
            timeout: Request timeout in seconds
            method: HTTP method to use ("HEAD" or "GET")
            
        Returns:
            Version string if header found, None otherwise
        """
        try:
            norm_url = self._normalize_url(url)
            self.logger.debug(f"Making {method} request to {norm_url} for header extraction")
            
            # Use HEAD by default for efficiency, fallback to GET if needed
            if method.upper() == "HEAD":
                response = requests.head(norm_url, timeout=timeout, allow_redirects=True)
            else:
                response = requests.get(norm_url, timeout=timeout, allow_redirects=True)
            
            # Check if request was successful
            response.raise_for_status()
            
            # Look for the version header (case-insensitive)
            version = self._find_version_header(dict(response.headers))
            if version:
                self.logger.debug(f"Found target version '{version}' via {method} request to {url}")
                return version
            else:
                self.logger.debug(f"No X-SCYTHE-TARGET-VERSION header found in response from {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            hint = " (tip: include http:// or https://)" if isinstance(url, str) and not url.lower().startswith(("http://","https://")) else ""
            self.logger.warning(f"Failed to make {method} request to {url}: {e}{hint}")
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error during banner grab: {e}")
            return None

    def get_all_headers_via_request(self, url: str, timeout: int = 10, method: str = "HEAD") -> Dict[str, str]:
        """
        Get all headers from a simple HTTP request.
        
        Args:
            url: URL to make the request to
            timeout: Request timeout in seconds
            method: HTTP method to use ("HEAD" or "GET")
            
        Returns:
            Dictionary of all response headers
        """
        try:
            norm_url = self._normalize_url(url)
            self.logger.debug(f"Making {method} request to {norm_url} for all headers")
            
            if method.upper() == "HEAD":
                response = requests.head(norm_url, timeout=timeout, allow_redirects=True)
            else:
                response = requests.get(norm_url, timeout=timeout, allow_redirects=True)
                
            response.raise_for_status()
            
            # Convert headers to regular dict with string values
            return {k: str(v) for k, v in response.headers.items()}
            
        except requests.exceptions.RequestException as e:
            hint = " (tip: include http:// or https://)" if isinstance(url, str) and not url.lower().startswith(("http://","https://")) else ""
            self.logger.warning(f"Failed to get headers from {url}: {e}{hint}")
            return {}
        except Exception as e:
            self.logger.warning(f"Unexpected error getting headers: {e}")
            return {}

    def debug_headers(self, url: str, timeout: int = 10) -> None:
        """
        Debug method to print all headers received from a URL.
        
        This is useful for troubleshooting when headers aren't being detected properly.
        It will show you exactly what headers the server is sending.
        
        Args:
            url: URL to make the request to
            timeout: Request timeout in seconds
        """
        print(f"\n{'='*60}")
        print(f"DEBUG: Header dump for {url}")
        print(f"{'='*60}")
        
        try:
            # Try HEAD request first
            print("\n--- HEAD Request ---")
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            print(f"Status Code: {response.status_code}")
            print(f"Headers ({len(response.headers)} total):")
            
            for name, value in response.headers.items():
                print(f"  {name}: {value}")
                if "scythe" in name.lower() or "version" in name.lower():
                    print("    *** POTENTIAL VERSION HEADER ***")
            
            # Try GET request
            print("\n--- GET Request ---")
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            print(f"Status Code: {response.status_code}")
            print(f"Headers ({len(response.headers)} total):")
            
            for name, value in response.headers.items():
                print(f"  {name}: {value}")
                if "scythe" in name.lower() or "version" in name.lower():
                    print("    *** POTENTIAL VERSION HEADER ***")
            
            # Check specifically for the target header
            version = self._find_version_header(dict(response.headers))
            print(f"\nTarget version extraction result: {version}")
            
        except Exception as e:
            print(f"ERROR: Failed to debug headers: {e}")
        
        print(f"{'='*60}\n")

    def extract_target_version_hybrid(self, driver: WebDriver, target_url: Optional[str] = None) -> Optional[str]:
        """
        Hybrid approach: Try banner grab first, then fall back to Selenium performance logs.
        
        This method attempts to get the version header using a simple HTTP request first,
        which is more reliable than Selenium's performance logging. If that fails or no
        target_url is provided, it falls back to the Selenium-based extraction.
        
        Args:
            driver: WebDriver instance
            target_url: URL to check (required for banner grab method)
            
        Returns:
            Version string if header found, None otherwise
        """
        # Try banner grab first if we have a target URL
        if target_url:
            self.logger.debug("Attempting banner grab method first")
            version = self.banner_grab(target_url)
            if version:
                self.logger.debug(f"Successfully extracted version '{version}' via banner grab")
                return version
            else:
                self.logger.debug("Banner grab failed")
        
        # In API mode (no driver), do not fall back to Selenium to avoid noisy warnings
        if driver is None:
            return None
        
        # Fall back to Selenium performance logs
        self.logger.debug("Using Selenium performance logs method")
        return self.extract_target_version(driver, target_url)

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

                        # Ignore static assets (css/js/images/fonts) to avoid false detections/noise
                        try:
                            if self._is_static_asset(response_url, headers):
                                continue
                        except Exception:
                            pass

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
