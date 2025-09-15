"""
Authentication module for Scythe framework.

This module provides authentication capabilities for TTPs, allowing them to
authenticate before executing their main functionality.
"""

from .base import Authentication
from .bearer import BearerTokenAuth
from .basic import BasicAuth
from .cookie_jwt import CookieJWTAuth

__all__ = [
    'Authentication',
    'BearerTokenAuth', 
    'BasicAuth',
    'CookieJWTAuth',
]