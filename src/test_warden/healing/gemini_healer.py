"""Gemini-powered healing service for finding correct selectors."""

import json
import re
from dataclasses import dataclass

from ..config import Config
from ..models import FailureCategory, HealingResult, RiskLevel, Selector, TestFailure
from ..vision.gemini_client import GeminiClient
from ..tracing import get_tracing


HEALING_PROMPT = """You are an expert at analyzing HTML DOM and fixing broken Selenium/Playwright test selectors.

## Context
A test was looking for an element using this selector: `{broken_selector}`
The test failed because the element was not found.

## Current HTML DOM
```html
{html}
```

## Task
Analyze the HTML and find the element that the test was likely trying to interact with.
Consider:
1. Similar data-testid values
2. Similar IDs or class names
3. Similar text content
4. Element type (button, input, link, etc.)

## Response Format
Respond with valid JSON only:
{{
    "found": true/false,
    "confidence": 0.0-1.0,
    "suggested_selector": "[data-testid=\\"example\\"]",
    "element_tag": "button",
    "element_text": "Click Me",
    "reasoning": "Explanation of why this is the correct element",
    "risk_level": "low/medium/high"
}}

If the element appears to have been removed entirely (not just renamed), set found=false.
"""


@dataclass
class HealingSuggestion:
    """A suggestion from Gemini for fixing a broken selector."""
    
    found: bool
    confidence: float
    suggested_selector: str
    element_tag: str
    element_text: str
    reasoning: str
    risk_level: str


class GeminiHealingService:
    """Service that uses Gemini to analyze HTML and suggest selector fixes."""
    
    def __init__(self, config: Config):
        self.config = config
        self.gemini = GeminiClient(config, get_tracing())
    
    async def analyze_failure(
        self,
        failure: TestFailure,
        html_content: str,
    ) -> HealingResult:
        """
        Analyze a test failure and generate a healing suggestion using Gemini.
        
        Args:
            failure: The test failure to analyze
            html_content: The current HTML DOM content
        
        Returns:
            HealingResult with Gemini-generated fix
        """
        broken_selector = ""
        if failure.selector:
            broken_selector = failure.selector.value
        else:
            # Extract from error message
            broken_selector = self._extract_selector_from_error(failure.error_message)
        
        if not broken_selector:
            return self._no_match_result(failure)
        
        # Call Gemini for analysis
        suggestion = await self._get_gemini_suggestion(
            broken_selector=broken_selector,
            html=html_content,
        )
        
        if not suggestion.found:
            return HealingResult(
                success=False,
                category=FailureCategory.REMOVED_FEATURE,
                confidence=suggestion.confidence,
                original_selector=failure.selector,
                new_selector=None,
                suggested_code=None,
                evidence=[suggestion.reasoning],
                risk_level=RiskLevel.HIGH,
                requires_review=True,
            )
        
        # Build the result
        new_selector = Selector(
            strategy=self._get_strategy(suggestion.suggested_selector),
            value=suggestion.suggested_selector,
            original_code=suggestion.suggested_selector,
        )
        
        risk_level = RiskLevel[suggestion.risk_level.upper()]
        
        return HealingResult(
            success=True,
            category=FailureCategory.HEALABLE_SELECTOR,
            confidence=suggestion.confidence,
            original_selector=failure.selector or Selector(
                strategy="unknown",
                value=broken_selector,
                original_code=broken_selector,
            ),
            new_selector=new_selector,
            suggested_code=suggestion.suggested_selector,
            evidence=[
                suggestion.reasoning,
                f"Element: <{suggestion.element_tag}>{suggestion.element_text}</{suggestion.element_tag}>",
            ],
            risk_level=risk_level,
            requires_review=risk_level != RiskLevel.LOW,
        )
    
    async def _get_gemini_suggestion(
        self,
        broken_selector: str,
        html: str,
    ) -> HealingSuggestion:
        """Call Gemini API to get a healing suggestion."""
        # Truncate HTML if too long
        html_truncated = html[:8000] if len(html) > 8000 else html
        
        prompt = HEALING_PROMPT.format(
            broken_selector=broken_selector,
            html=html_truncated,
        )
        
        try:
            response = await self.gemini.model.generate_content_async(prompt)
            result = self._parse_gemini_response(response.text)
            return result
        except Exception as e:
            # Return a fallback suggestion on error
            return HealingSuggestion(
                found=False,
                confidence=0.0,
                suggested_selector="",
                element_tag="",
                element_text="",
                reasoning=f"Gemini API error: {str(e)}",
                risk_level="high",
            )
    
    def _parse_gemini_response(self, response: str) -> HealingSuggestion:
        """Parse Gemini's JSON response."""
        # Extract JSON from response (may be wrapped in markdown)
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            return HealingSuggestion(
                found=False,
                confidence=0.0,
                suggested_selector="",
                element_tag="",
                element_text="",
                reasoning="Could not parse Gemini response",
                risk_level="high",
            )
        
        try:
            data = json.loads(json_match.group())
            return HealingSuggestion(
                found=data.get("found", False),
                confidence=float(data.get("confidence", 0.0)),
                suggested_selector=data.get("suggested_selector", ""),
                element_tag=data.get("element_tag", ""),
                element_text=data.get("element_text", ""),
                reasoning=data.get("reasoning", ""),
                risk_level=data.get("risk_level", "medium"),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return HealingSuggestion(
                found=False,
                confidence=0.0,
                suggested_selector="",
                element_tag="",
                element_text="",
                reasoning="Invalid JSON in Gemini response",
                risk_level="high",
            )
    
    def _extract_selector_from_error(self, error: str) -> str:
        """Extract selector value from error message."""
        patterns = [
            r"Unable to locate element:\s*(\S+)",
            r"Locator\s+'([^']+)'",
            r'#([a-zA-Z0-9_-]+)',
        ]
        for pattern in patterns:
            if match := re.search(pattern, error, re.IGNORECASE):
                return match.group(1)
        return ""
    
    def _get_strategy(self, selector: str) -> str:
        """Determine selector strategy from selector string."""
        if "data-testid" in selector:
            return "data-testid"
        if selector.startswith("#"):
            return "id"
        if selector.startswith("."):
            return "class"
        if selector.startswith("//"):
            return "xpath"
        if "aria-label" in selector:
            return "aria-label"
        return "css"
    
    def _no_match_result(self, failure: TestFailure) -> HealingResult:
        """Return a result for when no selector could be extracted."""
        return HealingResult(
            success=False,
            category=FailureCategory.ACTUAL_BUG,
            confidence=0.0,
            original_selector=None,
            new_selector=None,
            suggested_code=None,
            evidence=["Could not extract selector from failure"],
            risk_level=RiskLevel.HIGH,
            requires_review=True,
        )
