"""LangGraph workflow for test healing orchestration."""

from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph

from ..models import (
    AnalysisReport,
    FailureCategory,
    HealingResult,
    RiskLevel,
    TestFailure,
    TestFix,
)


class HealingState(TypedDict):
    """State for the healing workflow."""
    
    # Input
    failures: list[TestFailure]
    
    # Processing state
    current_index: int
    current_failure: TestFailure | None
    
    # Layer results
    html_result: HealingResult | None
    vision_result: HealingResult | None
    har_result: dict | None
    
    # Output
    fixes: Annotated[list[TestFix], "append"]
    actual_bugs: Annotated[list[TestFailure], "append"]
    needs_review: Annotated[list[TestFailure], "append"]
    
    # Control
    use_vision: bool
    complete: bool


def collect_failures(state: HealingState) -> HealingState:
    """Initialize processing of failures."""
    if state["failures"]:
        return {
            **state,
            "current_index": 0,
            "current_failure": state["failures"][0],
            "complete": False,
        }
    return {**state, "complete": True}


def analyze_html(state: HealingState) -> HealingState:
    """Layer 1: Analyze failure using HTML DOM."""
    failure = state["current_failure"]
    if not failure or not failure.html_snapshot:
        return {**state, "html_result": None, "use_vision": True}
    
    # Import here to avoid circular imports
    from ..analyzer.selector_finder import SelectorFinder
    
    finder = SelectorFinder(failure.html_snapshot)
    
    if failure.selector:
        # Try to find alternative selectors
        candidates = finder.find_alternatives(
            failure.selector.strategy,
            failure.selector.value,
            {"expected_text": failure.context.get("expected_text")},
        )
        
        if candidates and candidates[0].confidence > 0.7:
            best = candidates[0]
            result = HealingResult(
                success=True,
                category=FailureCategory.HEALABLE_SELECTOR,
                confidence=best.confidence,
                original_selector=failure.selector,
                new_selector=None,  # Will be populated by healer
                suggested_code=best.value,
                evidence=[f"Found similar element with {best.strategy}"],
                risk_level=RiskLevel.LOW,
                requires_review=False,
            )
            return {**state, "html_result": result, "use_vision": False}
    
    # HTML analysis didn't find a match, try vision
    return {**state, "html_result": None, "use_vision": True}


def analyze_vision(state: HealingState) -> HealingState:
    """Layer 2: Analyze failure using Gemini Vision."""
    failure = state["current_failure"]
    
    if not failure or not failure.screenshot_path:
        # No screenshot available, mark for review
        return {**state, "vision_result": None}
    
    # Vision analysis would be async in real implementation
    # For now, return a placeholder that indicates vision is needed
    result = HealingResult(
        success=False,
        category=FailureCategory.HEALABLE_SELECTOR,
        confidence=0.0,
        original_selector=failure.selector if failure else None,
        new_selector=None,
        suggested_code=None,
        evidence=["Vision analysis required"],
        risk_level=RiskLevel.MEDIUM,
        requires_review=True,
    )
    
    return {**state, "vision_result": result}


def analyze_har(state: HealingState) -> HealingState:
    """Layer 3: Check HAR logs for API failures."""
    failure = state["current_failure"]
    
    if not failure or not failure.har_log_path:
        return {**state, "har_result": None}
    
    from ..network.har_parser import HARParser
    
    parser = HARParser(failure.har_log_path)
    result = parser.analyze()
    
    if result.has_api_failures:
        primary = result.primary_failure
        return {
            **state,
            "har_result": {
                "has_failure": True,
                "status": primary.status if primary else 0,
                "url": primary.url if primary else "",
            },
        }
    
    return {**state, "har_result": {"has_failure": False}}


def classify_failure(state: HealingState) -> HealingState:
    """Classify the failure based on all analysis results."""
    # Check HAR first - API errors are actual bugs
    if state.get("har_result", {}).get("has_failure"):
        failure = state["current_failure"]
        if failure:
            return {
                **state,
                "actual_bugs": [failure],
            }
    
    # Check if HTML found a fix
    if state.get("html_result") and state["html_result"].success:
        return state  # Already has healing result
    
    # Check vision result
    if state.get("vision_result"):
        return state
    
    # No analysis succeeded, mark for review
    failure = state["current_failure"]
    if failure:
        return {**state, "needs_review": [failure]}
    
    return state


def generate_fix(state: HealingState) -> HealingState:
    """Generate a fix for healable failures."""
    failure = state["current_failure"]
    result = state.get("html_result") or state.get("vision_result")
    
    if not failure or not result or not result.success:
        return state
    
    fix = TestFix(
        file_path=failure.test_file,
        line_number=0,  # Would be determined by code analysis
        original_code=failure.selector.original_code if failure.selector else "",
        fixed_code=result.suggested_code or "",
        failure=failure,
        healing_result=result,
    )
    
    return {**state, "fixes": [fix]}


def next_failure(state: HealingState) -> HealingState:
    """Move to next failure in the queue."""
    next_idx = state["current_index"] + 1
    
    if next_idx >= len(state["failures"]):
        return {**state, "complete": True, "current_failure": None}
    
    return {
        **state,
        "current_index": next_idx,
        "current_failure": state["failures"][next_idx],
        "html_result": None,
        "vision_result": None,
        "har_result": None,
        "use_vision": False,
    }


def should_use_vision(state: HealingState) -> str:
    """Decide whether to use vision analysis."""
    if state.get("use_vision"):
        return "vision"
    return "classify"


def is_healable(state: HealingState) -> str:
    """Check if failure is healable."""
    result = state.get("html_result") or state.get("vision_result")
    
    if result and result.success:
        return "heal"
    return "next"


def is_complete(state: HealingState) -> str:
    """Check if all failures have been processed."""
    if state.get("complete"):
        return END
    return "html"


def build_healing_graph() -> StateGraph:
    """Build the LangGraph workflow for test healing."""
    graph = StateGraph(HealingState)
    
    # Add nodes
    graph.add_node("collect", collect_failures)
    graph.add_node("html", analyze_html)
    graph.add_node("vision", analyze_vision)
    graph.add_node("har", analyze_har)
    graph.add_node("classify", classify_failure)
    graph.add_node("heal", generate_fix)
    graph.add_node("next", next_failure)
    
    # Add edges
    graph.set_entry_point("collect")
    graph.add_conditional_edges("collect", is_complete)
    graph.add_conditional_edges("html", should_use_vision, {
        "vision": "vision",
        "classify": "classify",
    })
    graph.add_edge("vision", "har")
    graph.add_edge("har", "classify")
    graph.add_conditional_edges("classify", is_healable, {
        "heal": "heal",
        "next": "next",
    })
    graph.add_edge("heal", "next")
    graph.add_conditional_edges("next", is_complete)
    
    return graph.compile()


# Export compiled graph
healing_workflow = build_healing_graph()
