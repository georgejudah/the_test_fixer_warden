"""Base adapter interface for test frameworks."""

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import TestFailure


class TestAdapter(ABC):
    """Abstract base class for test framework adapters."""
    
    @abstractmethod
    def run_tests(self, suite_path: Path) -> tuple[bool, str]:
        """
        Run the test suite.
        
        Returns:
            Tuple of (success, output)
        """
        pass
    
    @abstractmethod
    def parse_failures(self, output: str) -> list[TestFailure]:
        """
        Parse test output to extract failures.
        
        Returns:
            List of TestFailure objects
        """
        pass
    
    @abstractmethod
    def run_single_test(self, test_file: Path, test_name: str) -> bool:
        """
        Run a single test for verification.
        
        Returns:
            True if test passed
        """
        pass
