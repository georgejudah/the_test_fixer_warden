"""Gemini AI-powered healing for Playwright tests."""

import json
import re
import time
from pathlib import Path
from dataclasses import dataclass

from google import genai
from rich.console import Console

console = Console()


GEMINI_HEALING_PROMPT = """You are an expert at fixing broken Playwright test selectors.

## Context
A test failed because it couldn't find an element using this selector:
**Broken selector:** `{broken_selector}`

## Current Page State (Aria Accessibility Tree)
This is what Playwright captured at the moment of failure - it shows all interactive elements currently on the page:

```yaml
{aria_snapshot}
```

## Your Task
1. Analyze what element the test was trying to find based on the selector name
2. Find the matching element in the aria snapshot  
3. Suggest a Playwright locator that will work

## Reasoning Steps (show your work)
- What type of element is the test looking for? (button, input, link, etc.)
- What is the semantic meaning of the selector name?
- Which element in the aria snapshot matches that meaning?
- What's the most reliable locator for that element?

## Response Format
Respond with valid JSON only:
{{
    "found": true,
    "reasoning": "Step-by-step explanation of how you found the match",
    "element_type": "button|textbox|link|heading|other",
    "element_label": "The visible label/text of the matched element",
    "old_selector": "{broken_selector}",
    "new_selector": "Playwright locator code",
    "confidence": 0.0-1.0
}}

If no matching element exists, set found=false and explain why.

## Playwright Locator Best Practices
- For buttons: `page.getByRole('button', {{ name: 'Button Text' }})`
- For textboxes with labels: `page.getByLabel('Label Text')`  
- For links: `page.getByRole('link', {{ name: 'Link Text' }})`
- For headings: `page.getByRole('heading', {{ name: 'Heading Text' }})`
- Avoid data-testid if possible - role-based locators are more resilient
"""


@dataclass
class GeminiHealingSuggestion:
    """A healing suggestion from Gemini."""
    found: bool
    reasoning: str
    old_selector: str
    new_selector: str
    confidence: float
    element_type: str = ""
    element_label: str = ""


async def heal_with_gemini_async(
    broken_selector: str,
    aria_snapshot: str,
    screenshot_path: Path | None = None,
    model: str = "gemini-2.0-flash",
    verbose: bool = False,
) -> GeminiHealingSuggestion:
    """
    Use Gemini AI to analyze the failure and suggest a fix (async version).
    """
    client = genai.Client()
    
    # Build the prompt
    prompt = GEMINI_HEALING_PROMPT.format(
        broken_selector=broken_selector,
        aria_snapshot=aria_snapshot[:6000],
    )
    
    if verbose:
        console.print(f"    [dim]Calling Gemini ({model})...[/]")
    
    start_time = time.time()
    
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
        )
        
        text = response.text
        elapsed_time = time.time() - start_time
        
        if verbose:
            console.print(f"    [dim]Gemini response received ({len(text)} chars, {elapsed_time:.2f}s)[/]")
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            return GeminiHealingSuggestion(
                found=False,
                reasoning="Could not parse Gemini response as JSON",
                old_selector=broken_selector,
                new_selector="",
                confidence=0.0,
            )
        
        data = json.loads(json_match.group())
        
        return GeminiHealingSuggestion(
            found=data.get("found", False),
            reasoning=data.get("reasoning", ""),
            old_selector=data.get("old_selector", broken_selector),
            new_selector=data.get("new_selector", ""),
            confidence=float(data.get("confidence", 0.0)),
            element_type=data.get("element_type", ""),
            element_label=data.get("element_label", ""),
        )
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        if verbose:
            console.print(f"    [red]Gemini error ({elapsed_time:.2f}s): {e}[/]")
        return GeminiHealingSuggestion(
            found=False,
            reasoning=f"Gemini API error: {str(e)}",
            old_selector=broken_selector,
            new_selector="",
            confidence=0.0,
        )


def heal_with_gemini(
    broken_selector: str,
    aria_snapshot: str,
    screenshot_path: Path | None = None,
    model: str = "gemini-2.0-flash",
    verbose: bool = False,
) -> GeminiHealingSuggestion:
    """
    Use Gemini AI to analyze the failure and suggest a fix (sync version).
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    heal_with_gemini_async(broken_selector, aria_snapshot, screenshot_path, model, verbose)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                heal_with_gemini_async(broken_selector, aria_snapshot, screenshot_path, model, verbose)
            )
    except RuntimeError:
        return asyncio.run(
            heal_with_gemini_async(broken_selector, aria_snapshot, screenshot_path, model, verbose)
        )


async def batch_heal_with_gemini(
    selectors: list[str],
    aria_snapshot: str,
    screenshot_path: Path | None = None,
    model: str = "gemini-2.0-flash",
    verbose: bool = False,
) -> list[GeminiHealingSuggestion]:
    """
    Heal multiple broken selectors in a single Gemini call (more efficient).
    """
    client = genai.Client()
    
    prompt = f"""You are an expert at fixing broken Playwright test selectors.

## Broken Selectors
The following selectors failed - the test couldn't find these elements:
{chr(10).join(f'- `{s}`' for s in selectors)}

## Current Page State (Aria Accessibility Tree)
```yaml
{aria_snapshot[:6000]}
```

## Your Task
For EACH broken selector, find the matching element and suggest a fix.

## Response Format
Respond with a JSON array:
[
    {{
        "old_selector": "original broken selector",
        "found": true/false,
        "reasoning": "explanation",
        "new_selector": "playwright locator",
        "confidence": 0.0-1.0
    }},
    ...
]
"""
    
    if verbose:
        console.print(f"    [dim]Batch healing {len(selectors)} selectors with Gemini...[/]")
    
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
        )
        
        text = response.text
        
        # Extract JSON array
        json_match = re.search(r'\[[\s\S]*\]', text)
        if not json_match:
            return []
        
        data = json.loads(json_match.group())
        
        return [
            GeminiHealingSuggestion(
                found=item.get("found", False),
                reasoning=item.get("reasoning", ""),
                old_selector=item.get("old_selector", ""),
                new_selector=item.get("new_selector", ""),
                confidence=float(item.get("confidence", 0.0)),
            )
            for item in data
        ]
        
    except Exception as e:
        if verbose:
            console.print(f"    [red]Gemini batch error: {e}[/]")
        return []
