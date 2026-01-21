"""Prompts for Gemini Vision analysis."""

VISUAL_LOCATE_PROMPT = """Look at this screenshot of a web page. I need to find an element that matches this description:

Original selector: {selector}
Expected text/label: {expected_text}
Element type: {element_type}

Please identify:
1. Is this element visible on the page? (yes/no)
2. If yes, describe its location and appearance
3. What unique visual characteristics can identify it?
4. Suggest a new selector strategy based on what you see

If the element is NOT visible, explain why (removed, hidden, different page state).

Respond in JSON format:
{{
    "visible": true/false,
    "location": "description of where it appears",
    "visual_traits": ["list", "of", "traits"],
    "suggested_selector": "new selector",
    "confidence": 0.0-1.0,
    "explanation": "reasoning"
}}
"""

BUG_VS_REFACTOR_PROMPT = """Compare these two screenshots of a web page:
- BASELINE: Last known working state
- CURRENT: Current failing state

The test expected to find: {element_description}
Original selector: {selector}

Analyze and determine:
1. Is this a UI refactor (element moved/restyled) or an actual bug?
2. If refactor: where did the element move to?
3. If bug: what appears to be broken?
4. Confidence score (0-100) for your assessment

Respond in JSON format:
{{
    "classification": "REFACTOR" | "BUG" | "REMOVED" | "UNCERTAIN",
    "confidence": 0-100,
    "element_status": "moved" | "removed" | "hidden" | "broken",
    "new_location": "if moved, describe new location",
    "suggested_selector": "if visible, suggest new selector",
    "reasoning": "detailed explanation"
}}
"""

ELEMENT_FINDER_PROMPT = """Find this UI element in the screenshot:

Description: {description}
Expected behavior: {behavior}
Original selector that failed: {selector}

Look for elements that match the description. Consider:
- Buttons, links, inputs with similar text
- Elements with similar icons or styling
- Elements in similar page locations

Respond in JSON format:
{{
    "found": true/false,
    "elements": [
        {{
            "description": "what the element is",
            "location": "where it appears",
            "suggested_selector": "how to select it"
        }}
    ],
    "best_match": 0,  # index of best match
    "confidence": 0.0-1.0
}}
"""
