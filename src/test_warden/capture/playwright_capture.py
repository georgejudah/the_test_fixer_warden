"""Playwright capture module - extracts failure artifacts from Playwright test runs."""

from pathlib import Path
from dataclasses import dataclass
import re


@dataclass
class PlaywrightFailure:
    """Represents a Playwright test failure with captured artifacts."""
    
    test_name: str
    test_file: str
    failed_selector: str
    error_message: str
    aria_snapshot: str  # Playwright's accessibility tree snapshot
    screenshot_path: Path | None


class PlaywrightCapture:
    """Extract failure information from Playwright test results."""
    
    def __init__(self, test_results_dir: Path = Path("test-results")):
        self.results_dir = test_results_dir
    
    def get_failures(self) -> list[PlaywrightFailure]:
        """Parse all failure directories and extract failure information."""
        failures = []
        
        if not self.results_dir.exists():
            return failures
        
        for folder in self.results_dir.iterdir():
            if not folder.is_dir():
                continue
            
            # Parse test name from folder name
            # Format: test-file-Test-Suite-test-name-browser
            test_info = self._parse_folder_name(folder.name)
            if not test_info:
                continue
            
            # Read error context
            error_context = folder / "error-context.md"
            aria_snapshot = ""
            if error_context.exists():
                aria_snapshot = error_context.read_text()
            
            # Find screenshot
            screenshot = None
            screenshots = list(folder.glob("*.png"))
            if screenshots:
                screenshot = screenshots[0]
            
            # Extract failed selector from aria snapshot context
            failed_selector = self._extract_failed_selector_from_folder(folder)
            
            failures.append(PlaywrightFailure(
                test_name=test_info["test_name"],
                test_file=test_info["test_file"],
                failed_selector=failed_selector,
                error_message=self._get_error_message(folder),
                aria_snapshot=aria_snapshot,
                screenshot_path=screenshot,
            ))
        
        return failures
    
    def _parse_folder_name(self, folder_name: str) -> dict | None:
        """Parse the Playwright test result folder name."""
        # Format: login-Login-Page-should-have-email-input-field-chromium
        parts = folder_name.split("-")
        if len(parts) < 3:
            return None
        
        # First part is the test file name (without .spec.ts)
        test_file = parts[0]
        # Last part is the browser
        browser = parts[-1]
        # Middle parts form the test suite and name
        test_name = "-".join(parts[1:-1])
        
        return {
            "test_file": f"e2e/{test_file}.spec.ts",
            "test_name": test_name,
            "browser": browser,
        }
    
    def _extract_failed_selector_from_folder(self, folder: Path) -> str:
        """Try to extract the failed selector from test artifacts."""
        # Check if there's a trace or additional error info
        # For now, return empty - we'll get this from the test output
        return ""
    
    def _get_error_message(self, folder: Path) -> str:
        """Get the error message from the folder name/context."""
        return f"Test failed: {folder.name}"


def parse_aria_snapshot(aria_content: str) -> dict:
    """
    Parse Playwright's aria snapshot to extract available elements.
    
    Returns a dict with element info that can be used for healing.
    """
    elements = {
        "buttons": [],
        "textboxes": [],
        "links": [],
        "headings": [],
    }
    
    lines = aria_content.split("\n")
    for line in lines:
        line = line.strip()
        
        # Parse button elements
        if match := re.search(r'button "([^"]+)"', line):
            elements["buttons"].append(match.group(1))
        
        # Parse textbox elements
        if match := re.search(r'textbox "([^"]+)"', line):
            elements["textboxes"].append(match.group(1))
        
        # Parse link elements
        if match := re.search(r'link "([^"]+)"', line):
            elements["links"].append(match.group(1))
        
        # Parse heading elements
        if match := re.search(r'heading "([^"]+)"', line):
            elements["headings"].append(match.group(1))
    
    return elements
