"""Core data models for Test Warden."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class FailureType(Enum):
    """Types of test failures."""
    
    SELECTOR_NOT_FOUND = "selector_not_found"
    ELEMENT_NOT_VISIBLE = "element_not_visible"
    TIMEOUT = "timeout"
    ASSERTION_FAILED = "assertion_failed"
    API_ERROR = "api_error"
    UNKNOWN = "unknown"


class FailureCategory(Enum):
    """Classification of failures for healing decisions."""
    
    HEALABLE_SELECTOR = "healable_selector"
    HEALABLE_TEXT = "healable_text"
    HEALABLE_STRUCTURE = "healable_structure"
    FLAKY_TIMING = "flaky_timing"
    ACTUAL_BUG = "actual_bug"
    REMOVED_FEATURE = "removed_feature"
    NEW_BLOCKER = "new_blocker"


class RiskLevel(Enum):
    """Risk level for applying fixes."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Selector:
    """Represents a test selector."""
    
    strategy: str  # css, xpath, id, data-testid, etc.
    value: str
    original_code: str  # The actual code line


@dataclass
class TestFailure:
    """Represents a single test failure."""
    
    test_id: str
    test_file: Path
    test_name: str
    failure_type: FailureType
    selector: Selector | None
    error_message: str
    stack_trace: str
    html_snapshot: str | None = None
    screenshot_path: Path | None = None
    har_log_path: Path | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict = field(default_factory=dict)


@dataclass
class HealingResult:
    """Result of attempting to heal a failure."""
    
    success: bool
    category: FailureCategory
    confidence: float  # 0.0 - 1.0
    original_selector: Selector | None
    new_selector: Selector | None
    suggested_code: str | None
    evidence: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    requires_review: bool = False


@dataclass
class TestFix:
    """A fix to be applied to a test file."""
    
    file_path: Path
    line_number: int
    original_code: str
    fixed_code: str
    failure: TestFailure
    healing_result: HealingResult


@dataclass 
class AnalysisReport:
    """Summary report of test analysis."""
    
    total_failures: int
    healable_count: int
    actual_bugs_count: int
    needs_review_count: int
    fixes: list[TestFix]
    actual_bugs: list[TestFailure]
    needs_review: list[TestFailure]
