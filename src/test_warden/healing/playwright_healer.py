"""Playwright-specific healer that uses aria snapshots for DOM analysis."""

import json
import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..capture.playwright_capture import PlaywrightCapture, parse_aria_snapshot
from ..healing.gemini_healer import GeminiHealingService
from ..config import Config

console = Console()


PLAYWRIGHT_HEALING_PROMPT = """You are an expert at fixing broken Playwright test selectors.

## Context
A test was looking for an element using this selector: `{broken_selector}`
The test failed because the element was not found.

## Page Aria Snapshot (Accessibility Tree)
This is what Playwright captured at the moment of failure:
```yaml
{aria_snapshot}
```

## Task
1. Find which element in the aria snapshot matches what the test was looking for
2. Suggest a working Playwright locator

The old selector uses `data-testid` but the element may have been renamed.
Look for elements with similar purpose (e.g., if looking for "email-input", find textboxes related to email).

## Response Format
Respond with valid JSON only:
{{
    "found": true/false,
    "reasoning": "Explanation of why this fix works",
    "old_selector": "The original broken selector",
    "new_selector": "The suggested working selector using getByRole, getByLabel, etc.",
    "confidence": 0.0-1.0
}}

Example suggestions:
- For a button with text "Sign In": `page.getByRole('button', {{ name: 'Sign In' }})`
- For a textbox with label "Email": `page.getByLabel('Email')`
- For a link with text "Forgot Password?": `page.getByRole('link', {{ name: 'Forgot Password?' }})`
"""


async def analyze_playwright_failure(
    test_file: str,
    broken_selector: str,
    aria_snapshot: str,
    config: Config,
) -> dict:
    """Analyze a Playwright failure and suggest a fix using Gemini."""
    from google import genai
    
    client = genai.Client()
    
    prompt = PLAYWRIGHT_HEALING_PROMPT.format(
        broken_selector=broken_selector,
        aria_snapshot=aria_snapshot,
    )
    
    try:
        response = await client.aio.models.generate_content(
            model=config.gemini.model,
            contents=prompt,
        )
        
        # Parse JSON from response
        text = response.text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        return {"found": False, "reasoning": "Could not parse response"}
    except Exception as e:
        return {"found": False, "reasoning": f"Error: {str(e)}"}


def extract_selectors_from_test_file(test_file: Path) -> list[str]:
    """Extract all data-testid selectors from a Playwright test file."""
    selectors = []
    
    if not test_file.exists():
        return selectors
    
    content = test_file.read_text()
    
    # Find all data-testid patterns
    patterns = [
        r'\[data-testid="([^"]+)"\]',
        r"data-testid='([^']+)'",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content)
        selectors.extend(matches)
    
    return list(set(selectors))


def suggest_fixes_from_aria(broken_selectors: list[str], aria_snapshot: str) -> list[dict]:
    """
    Suggest fixes by matching broken selectors to elements in aria snapshot.
    
    This is a heuristic approach that doesn't require Gemini.
    """
    elements = parse_aria_snapshot(aria_snapshot)
    fixes = []
    
    # Mapping of common selector patterns to aria roles
    selector_to_role = {
        "email": ("textbox", "Email"),
        "password": ("textbox", "Password"),
        "submit": ("button", "Sign In"),
        "login": ("button", "Sign In"),
        "forgot": ("link", "Forgot Password?"),
        "checkout": ("button", None),
        "cart": ("button", None),
        "continue": ("button", None),
    }
    
    for selector in broken_selectors:
        selector_lower = selector.lower()
        
        for keyword, (role, expected_name) in selector_to_role.items():
            if keyword in selector_lower:
                # Find matching element in aria snapshot
                if role == "textbox" and elements.get("textboxes"):
                    for textbox in elements["textboxes"]:
                        if keyword in textbox.lower():
                            fixes.append({
                                "old_selector": f'[data-testid="{selector}"]',
                                "new_selector": f'page.getByLabel(\'{textbox}\')',
                                "reasoning": f"Changed from data-testid to getByLabel for '{textbox}'",
                                "confidence": 0.9,
                            })
                            break
                
                elif role == "button" and elements.get("buttons"):
                    for button in elements["buttons"]:
                        if expected_name and button == expected_name:
                            fixes.append({
                                "old_selector": f'[data-testid="{selector}"]',
                                "new_selector": f'page.getByRole(\'button\', {{ name: \'{button}\' }})',
                                "reasoning": f"Changed from data-testid to getByRole button for '{button}'",
                                "confidence": 0.9,
                            })
                            break
                
                elif role == "link" and elements.get("links"):
                    for link in elements["links"]:
                        if expected_name and link == expected_name:
                            fixes.append({
                                "old_selector": f'[data-testid="{selector}"]',
                                "new_selector": f'page.getByRole(\'link\', {{ name: \'{link}\' }})',
                                "reasoning": f"Changed from data-testid to getByRole link for '{link}'",
                                "confidence": 0.9,
                            })
                            break
    
    return fixes


def heal_playwright_tests(results_dir: Path, dry_run: bool = True):
    """Main function to heal Playwright tests from test-results artifacts."""
    capture = PlaywrightCapture(results_dir)
    failures = capture.get_failures()
    
    if not failures:
        console.print("[yellow]No failures found in test-results directory[/]")
        return
    
    console.print(f"[blue]Found {len(failures)} failed tests[/]\n")
    
    all_fixes = []
    
    for failure in failures:
        console.print(f"[cyan]Analyzing:[/] {failure.test_name}")
        
        # Get broken selectors from the test file
        test_file = Path(failure.test_file)
        broken_selectors = extract_selectors_from_test_file(test_file)
        
        if not broken_selectors:
            console.print("  [dim]No data-testid selectors found[/]")
            continue
        
        # Suggest fixes using aria snapshot
        fixes = suggest_fixes_from_aria(broken_selectors, failure.aria_snapshot)
        
        if fixes:
            all_fixes.extend(fixes)
            for fix in fixes:
                console.print(f"  [green]✓[/] {fix['old_selector']}")
                console.print(f"    → {fix['new_selector']}")
    
    if all_fixes:
        console.print(f"\n[bold green]Found {len(all_fixes)} potential fixes[/]")
        if dry_run:
            console.print("[dim]Run with --apply to modify test files[/]")
    else:
        console.print("\n[yellow]No automatic fixes found - may require manual review or AI analysis[/]")
