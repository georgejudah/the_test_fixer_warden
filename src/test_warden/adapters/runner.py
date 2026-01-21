"""Generic test runner that wraps user's test command."""

import json
import re
import subprocess
import os
from pathlib import Path

from ..config import Config
from ..models import FailureType, Selector, TestFailure


class TestRunner:
    """Run tests using the user's configured test command."""
    
    def __init__(self, config: Config):
        self.config = config
        self.test_command = config.test_command
        # Assuming self.context is initialized elsewhere or will be added.
        # For now, providing a dummy context to avoid immediate errors if not present.
        # In a real scenario, this would likely be passed in __init__ or derived.
        self.context = {} # Placeholder for the new line requiring self.context
    
    def run_tests(self, test_file: Path | None = None) -> tuple[bool, str, list[TestFailure]]:
        """Run tests and return success status, output, and failures."""
        output_file = self.context.get("output_file", "test_output.txt")
        
        # Build command
        # Auto-inject our capture plugin
        plugin_path = Path(__file__).parent.parent / "plugins" / "capture.py"
        cmd = f"{self.test_command} -p test_warden.plugins.capture"
        
        if test_file:
            # Handle both file path and directory
            cmd = f"{cmd} {test_file}"
        
        # Add verbosity if needed
        if "-v" not in self.test_command:
            cmd = f"{cmd} -v"
            
        # Run command
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            cwd=Path.cwd(),
            text=True,  # Ensure get string output
            env={**os.environ, "PYTHONPATH": f"{os.getcwd()}:{os.environ.get('PYTHONPATH', '')}"}
        )
        
        output = result.stdout + "\n" + result.stderr
        
        # DEBUG: Check what's happening
        if result.returncode != 0:
            print(f"DEBUG: Pytest output:\n{output[:1000]}")
        
        # Parse failures
        failures = self._parse_failures(output, test_file or Path.cwd())
        
        return result.returncode == 0, output, failures
    
    def run_single_test(self, test_file: Path, test_name: str) -> bool:
        """Run a single test for verification."""
        # Pytest syntax
        cmd = f"{self.test_command} {test_file}::{test_name}"
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            cwd=Path.cwd(),
        )
        
        return result.returncode == 0
    
    def _parse_failures(self, output: str, suite_path: Path) -> list[TestFailure]:
        """Parse test output to extract failures."""
        failures = []
        
        # Try to parse as pytest output first
        failures.extend(self._parse_pytest_output(output, suite_path))
        
        # Try playwright/jest format if no pytest failures found
        if not failures:
            failures.extend(self._parse_playwright_output(output, suite_path))
        
        return failures
    
    def _parse_pytest_output(self, output: str, suite_path: Path) -> list[TestFailure]:
        """Parse pytest output format."""
        failures = []
        
        # Pattern 1: Match short summary lines
        # FAILED tests/file.py::Class::method - Exception: message...
        summary_pattern = r"FAILED\s+(\S+)::(\S+)(?:\s+-\s+(.+))?"
        
        for match in re.finditer(summary_pattern, output, re.MULTILINE):
            file_path = match.group(1)
            test_name = match.group(2)
            error_summary = match.group(3) or ""
            
            # Extract full error from the detailed failure section
            full_error = self._extract_full_error(output, test_name)
            error = full_error if full_error else error_summary
            
            failure_type = self._classify_failure_type(error)
            selector = self._extract_selector(error)
            
            failures.append(TestFailure(
                test_id=f"{file_path}::{test_name}",
                test_file=Path(file_path),
                test_name=test_name,
                failure_type=failure_type,
                selector=selector,
                error_message=error[:500],
                stack_trace=self._extract_stack_trace(output, test_name),
            ))
        
        return failures
    
    def _extract_full_error(self, output: str, test_name: str) -> str:
        """Extract the full error message for a specific test."""
        # Extract just the method name from Class::method format
        method_name = test_name.split("::")[-1] if "::" in test_name else test_name
        
        # Patterns to find in error output - capture the full error
        patterns = [
            r"NoSuchElementException: Unable to locate element: ([a-zA-Z0-9_-]+)",
            r"Unable to locate element: ([a-zA-Z0-9_-]+)",
            r"TimeoutError: Locator '([^']+)' not found",
            r"Locator '([^']+)' not found",
        ]
        
        # Search for patterns in output
        for pattern in patterns:
            if match := re.search(pattern, output, re.IGNORECASE):
                return match.group(0)  # Return full match
        
        return ""
    
    def _parse_playwright_output(self, output: str, suite_path: Path) -> list[TestFailure]:
        """Parse Playwright/Jest output format."""
        failures = []
        
        # Pattern for Playwright: ✘ test name (file:line)
        # Or Jest: ✕ test name
        failed_pattern = r"[✘✕×]\s+(?:\[\d+\]\s+)?(.+?)\s+\((.+?):(\d+):\d+\)"
        
        for match in re.finditer(failed_pattern, output):
            test_name = match.group(1)
            file_path = match.group(2)
            
            failures.append(TestFailure(
                test_id=f"{file_path}::{test_name}",
                test_file=Path(file_path),
                test_name=test_name,
                failure_type=FailureType.UNKNOWN,
                selector=None,
                error_message="",
                stack_trace="",
            ))
        
        return failures
    
    def _classify_failure_type(self, error: str) -> FailureType:
        """Classify the type of failure from error message."""
        error_lower = error.lower()
        
        # Check for selector/element not found
        if any(x in error_lower for x in [
            "nosuchelementexception", "no such element", 
            "element not found", "unable to locate",
            "locator", "not found"
        ]):
            return FailureType.SELECTOR_NOT_FOUND
        elif "not visible" in error_lower or "not displayed" in error_lower:
            return FailureType.ELEMENT_NOT_VISIBLE
        elif "timeout" in error_lower or "timed out" in error_lower:
            return FailureType.TIMEOUT
        elif "assert" in error_lower or "expected" in error_lower:
            return FailureType.ASSERTION_FAILED
        elif "api" in error_lower or "500" in error_lower:
            return FailureType.API_ERROR
        
        return FailureType.UNKNOWN
    
    def _extract_selector(self, error: str) -> Selector | None:
        """Extract selector from error message."""
        # Look for specific selector patterns in error messages
        patterns = [
            # NoSuchElementException: Unable to locate element: old-submit-btn
            (r'Unable to locate element: ([a-zA-Z0-9_-]+)', "id"),
            # TimeoutError: Locator '#cart-icon' not found
            (r"Locator '([^']+)'", "css"),
            # Selenium patterns
            (r'By\.ID,\s*["\']([^"\']+)["\']', "id"),
            (r'By\.CSS_SELECTOR,\s*["\']([^"\']+)["\']', "css"),
        ]
        
        for pattern, strategy in patterns:
            if match := re.search(pattern, error, re.IGNORECASE):
                value = match.group(1)
                # Skip template variables
                if '{' in value or '}' in value:
                    continue
                return Selector(
                    strategy=strategy,
                    value=value,
                    original_code=match.group(0),
                )
        
        return None
    
    def _extract_stack_trace(self, output: str, test_name: str) -> str:
        """Extract stack trace for a specific test."""
        # Find the section for this test
        lines = output.split("\n")
        in_trace = False
        trace_lines = []
        
        for line in lines:
            if test_name in line:
                in_trace = True
            elif in_trace:
                if line.startswith("FAILED") or line.startswith("PASSED"):
                    break
                trace_lines.append(line)
        
        return "\n".join(trace_lines[:20])  # Limit to 20 lines
