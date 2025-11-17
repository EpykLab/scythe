"""
CSRF (Cross-Site Request Forgery) protection support for API requests.

This module provides configurable CSRF token extraction, storage, and injection
to support testing web applications with CSRF protection enabled.
"""

import logging
from typing import Optional, Dict, Any, Literal
import requests


logger = logging.getLogger(__name__)


class CSRFProtection:
    """
    Handles CSRF token lifecycle for API requests.

    Different web frameworks use different CSRF patterns. This class supports
    the most common patterns and can be configured for custom implementations.

    Common framework configurations:

    Django:
        CSRFProtection(cookie_name='csrftoken', header_name='X-CSRFToken')

    Laravel/Spring Security:
        CSRFProtection(cookie_name='XSRF-TOKEN', header_name='X-XSRF-TOKEN')

    Rails:
        CSRFProtection(extract_from='header', header_name='X-CSRF-Token')

    Express.js (csurf):
        CSRFProtection(cookie_name='_csrf', header_name='CSRF-Token')

    Custom:
        CSRFProtection(
            cookie_name='__Host-csrf_',
            header_name='X-Custom-CSRF',
            extract_from='cookie'
        )

    Args:
        extract_from: Where to extract the token from: 'cookie', 'header', or 'body'
        cookie_name: Name of the CSRF cookie (used when extract_from='cookie')
        header_name: Name of the CSRF header to send with requests
        body_field: JSON field name containing token (when extract_from='body')
        inject_into: Where to inject token: 'header' or 'body'
        refresh_endpoint: Optional endpoint to call to get a fresh CSRF token.
                         If not specified, will use base URL on retry.
                         Many APIs automatically update CSRF cookies with every response.
        auto_extract: Automatically extract token from every response (default: True)
        required_for_methods: HTTP methods that require CSRF token (default: POST, PUT, PATCH, DELETE)
        retry_on_failure: Automatically retry on 403/419 errors after refreshing token (default: True)
    """

    def __init__(
        self,
        extract_from: Literal['cookie', 'header', 'body'] = 'cookie',
        cookie_name: str = 'csrftoken',
        header_name: str = 'X-CSRF-Token',
        body_field: str = 'csrfToken',
        inject_into: Literal['header', 'body'] = 'header',
        refresh_endpoint: Optional[str] = None,
        auto_extract: bool = True,
        required_for_methods: Optional[list] = None,
        retry_on_failure: bool = True
    ):
        """Initialize CSRF protection with configuration."""
        self.extract_from = extract_from
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.body_field = body_field
        self.inject_into = inject_into
        self.refresh_endpoint = refresh_endpoint
        self.auto_extract = auto_extract
        self.required_for_methods = required_for_methods or ['POST', 'PUT', 'PATCH', 'DELETE']
        self.retry_on_failure = retry_on_failure

        # Runtime state
        self._current_token: Optional[str] = None

        logger.debug(
            f"Initialized CSRF protection: extract_from={extract_from}, "
            f"cookie_name={cookie_name}, header_name={header_name}"
        )

    def extract_token(
        self,
        response: Optional[requests.Response] = None,
        session: Optional[requests.Session] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Extract CSRF token from response or session.

        Args:
            response: HTTP response object to extract from
            session: requests.Session object to extract cookies from
            context: Context dictionary (for accessing stored state)

        Returns:
            Extracted CSRF token or None if not found
        """
        token = None

        if self.extract_from == 'cookie':
            # Extract from cookie in session or response
            if session:
                token = session.cookies.get(self.cookie_name)
                if token:
                    logger.debug(f"Extracted CSRF token from session cookie '{self.cookie_name}'")
            elif response:
                token = response.cookies.get(self.cookie_name)
                if token:
                    logger.debug(f"Extracted CSRF token from response cookie '{self.cookie_name}'")

        elif self.extract_from == 'header':
            # Extract from response header
            if response:
                token = response.headers.get(self.header_name)
                if token:
                    logger.debug(f"Extracted CSRF token from response header '{self.header_name}'")

        elif self.extract_from == 'body':
            # Extract from JSON response body
            if response:
                try:
                    body = response.json()
                    token = body.get(self.body_field)
                    if token:
                        logger.debug(f"Extracted CSRF token from response body field '{self.body_field}'")
                except (ValueError, AttributeError):
                    logger.debug("Could not parse response body as JSON for CSRF extraction")

        if token:
            self._current_token = token
            if context is not None:
                context['csrf_token'] = token
        elif self.auto_extract:
            logger.debug(f"No CSRF token found (extract_from={self.extract_from})")

        return token

    def get_token(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Get the current CSRF token.

        Args:
            context: Context dictionary to check for stored token

        Returns:
            Current CSRF token or None
        """
        # Check context first, then fall back to internal state
        if context and 'csrf_token' in context:
            return context['csrf_token']
        return self._current_token

    def inject_token(
        self,
        token: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        method: str = 'GET',
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """
        Inject CSRF token into request headers or body.

        Args:
            token: CSRF token to inject (if None, uses current token)
            headers: Request headers dict to update
            data: Request body data dict to update
            method: HTTP method (token only injected for methods in required_for_methods)
            context: Context dictionary to get token from

        Returns:
            Tuple of (updated_headers, updated_data)
        """
        # Check if CSRF is needed for this method
        if method.upper() not in self.required_for_methods:
            return headers, data

        # Get token
        if token is None:
            token = self.get_token(context)

        if not token:
            logger.debug(f"No CSRF token available to inject for {method} request")
            return headers, data

        # Inject into appropriate location
        if self.inject_into == 'header':
            if headers is None:
                headers = {}
            headers[self.header_name] = token
            logger.debug(f"Injected CSRF token into header '{self.header_name}'")

        elif self.inject_into == 'body':
            if data is None:
                data = {}
            data[self.body_field] = token
            logger.debug(f"Injected CSRF token into body field '{self.body_field}'")

        return headers, data

    def refresh_token(
        self,
        session: requests.Session,
        base_url: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Refresh the CSRF token by making a request to get a new token.

        If refresh_endpoint is configured, uses that specific endpoint.
        Otherwise, makes a GET request to the base URL to get a fresh CSRF cookie.

        This supports APIs that automatically update the CSRF cookie with every response.

        Args:
            session: requests.Session to use for the request
            base_url: Base URL of the target application
            context: Context dictionary to store refreshed token

        Returns:
            New CSRF token or None if refresh failed
        """
        # Determine URL to use for refresh
        if self.refresh_endpoint:
            # Use dedicated refresh endpoint if configured
            if self.refresh_endpoint.startswith('http'):
                url = self.refresh_endpoint
            else:
                url = base_url.rstrip('/') + '/' + self.refresh_endpoint.lstrip('/')
            logger.debug(f"Refreshing CSRF token from dedicated endpoint: {url}")
        else:
            # Fallback: make a simple GET request to base URL
            # Many APIs automatically update CSRF cookies with any response
            url = base_url
            logger.debug(f"Refreshing CSRF token by requesting base URL: {url}")

        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()

            # Extract token from refresh response
            token = self.extract_token(response=response, session=session, context=context)

            if token:
                logger.info("Successfully refreshed CSRF token")
            else:
                logger.warning("CSRF refresh request succeeded but no token found")

            return token

        except Exception as e:
            logger.error(f"Failed to refresh CSRF token: {e}")
            return None

    def handle_csrf_failure(
        self,
        response: requests.Response,
        session: requests.Session,
        base_url: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Handle a potential CSRF failure by attempting to refresh the token.

        Common CSRF failure status codes:
        - 403 Forbidden (Django, Rails)
        - 419 Page Expired (Laravel)

        Args:
            response: Failed response object
            session: requests.Session to use for refresh
            base_url: Base URL for refresh request
            context: Context dictionary

        Returns:
            True if token was refreshed, False otherwise
        """
        status_code = response.status_code

        # Check if this looks like a CSRF failure
        if status_code not in [403, 419]:
            return False

        logger.warning(
            f"Possible CSRF failure detected (status {status_code}), "
            f"attempting to refresh token"
        )

        # Try to refresh
        new_token = self.refresh_token(session, base_url, context)
        return new_token is not None

    def should_retry(self, response: requests.Response) -> bool:
        """
        Determine if a request should be retried due to CSRF failure.

        Args:
            response: Response object to check

        Returns:
            True if the response indicates a CSRF failure that should be retried
        """
        return response.status_code in [403, 419]

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"CSRFProtection(extract_from='{self.extract_from}', "
            f"cookie_name='{self.cookie_name}', header_name='{self.header_name}')"
        )
