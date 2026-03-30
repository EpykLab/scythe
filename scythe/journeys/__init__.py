"""
Journeys module for Scythe framework.

This module provides journey capabilities for complex multi-step test scenarios.
Journeys are composed of steps, and steps contain actions that can include TTPs
or other custom actions like navigation, form filling, etc.
"""

from .base import Journey, Step, Action
from .actions import NavigateAction, ClickAction, FillFormAction, WaitAction, TTPAction, ApiRequestAction
from .executor import JourneyExecutor


def __getattr__(name):
    if name in ("PlaywrightRunAction", "PlaywrightWrapAction"):
        from ..playwright import PlaywrightRunAction, PlaywrightWrapAction
        return PlaywrightRunAction if name == "PlaywrightRunAction" else PlaywrightWrapAction
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'Journey',
    'Step',
    'Action',
    'NavigateAction',
    'ClickAction',
    'FillFormAction',
    'WaitAction',
    'TTPAction',
    'ApiRequestAction',
    'PlaywrightRunAction',
    'PlaywrightWrapAction',
    'JourneyExecutor'
]