"""Capture module for extracting test failure artifacts."""

from .playwright_capture import PlaywrightCapture, PlaywrightFailure, parse_aria_snapshot

__all__ = ["PlaywrightCapture", "PlaywrightFailure", "parse_aria_snapshot"]
