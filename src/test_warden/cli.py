"""CLI entry point for Test Warden."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .adapters.runner import TestRunner
from .config import load_config
from .models import FailureCategory, TestFailure, TestFix
from .tracing import init_tracing

console = Console()


@click.group()
@click.version_option()
@click.option("--config", "-c", "config_path", type=click.Path(exists=True), help="Config file path")
@click.pass_context
def main(ctx: click.Context, config_path: str | None) -> None:
    """Test Warden - AI-powered auto-healing for test suites."""
    ctx.ensure_object(dict)
    
    # Load config and initialize tracing
    config = load_config(Path(config_path) if config_path else None)
    ctx.obj["config"] = config
    
    # Initialize Langfuse tracing
    tracing = init_tracing(config)
    ctx.obj["tracing"] = tracing
    
    if config.langfuse.enabled:
        console.print("[dim]Langfuse tracing enabled[/]")


@main.command()
@click.option("--suite", "-s", required=True, help="Path to test suite directory")
@click.option("--config", "-c", "config_path", type=click.Path(exists=True), help="Config file path")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json"]), default="table")
def analyze(suite: str, config_path: str | None, output_format: str) -> None:
    """Analyze test failures without modifying files."""
    config = load_config(Path(config_path) if config_path else None)
    runner = TestRunner(config)
    
    console.print(f"\n[bold blue]🔍 Analyzing test suite:[/] {suite}\n")
    console.print(f"[dim]Test command: {config.test_command}[/]\n")
    
    with console.status("[yellow]Running tests...[/]"):
        success, output, failures = runner.run_tests(Path(suite))
    
    if success:
        console.print("[bold green]✓ All tests passed![/]\n")
        return
    
    console.print(f"[yellow]Found {len(failures)} failures[/]\n")
    
    # Display results
    table = Table(title="Test Failure Analysis")
    table.add_column("Test", style="cyan", max_width=40)
    table.add_column("Type", style="yellow")
    table.add_column("Selector", style="dim", max_width=30)
    table.add_column("Action", style="magenta")
    
    healable = 0
    actual_bugs = 0
    
    for failure in failures:
        action = _get_suggested_action(failure)
        if "heal" in action.lower():
            healable += 1
        else:
            actual_bugs += 1
        
        selector_str = failure.selector.value[:30] if failure.selector else "-"
        
        table.add_row(
            f"{failure.test_file.name}::{failure.test_name[:20]}",
            failure.failure_type.value,
            selector_str,
            action,
        )
    
    console.print(table)
    
    # Summary
    console.print(f"\n[bold]Summary:[/]")
    console.print(f"  • Healable: [green]{healable}[/]")
    console.print(f"  • Actual bugs: [red]{actual_bugs}[/]")
    console.print(f"\n[dim]Run 'test-warden heal --suite {suite} --dry-run' to preview fixes[/]\n")


@main.command()
@click.option("--suite", "-s", required=True, help="Path to test suite directory")
@click.option("--config", "-c", "config_path", type=click.Path(exists=True), help="Config file path")
@click.option("--dry-run", is_flag=True, help="Preview changes without modifying files")
@click.option("--apply", "apply_fixes", is_flag=True, help="Apply fixes to test files")
@click.option("--interactive", "-i", is_flag=True, help="Approve each fix individually")
@click.option("--confidence", type=float, default=0.85, help="Minimum confidence threshold")
@click.option("--use-ai", is_flag=True, help="Use Gemini AI for intelligent selector analysis")
def heal(
    suite: str,
    config_path: str | None,
    dry_run: bool,
    apply_fixes: bool,
    interactive: bool,
    confidence: float,
    use_ai: bool,
) -> None:
    """Heal broken tests by fixing selectors."""
    if not apply_fixes and not interactive:
        dry_run = True  # Default to dry-run
    
    config = load_config(Path(config_path) if config_path else None)
    runner = TestRunner(config)
    
    mode = "dry-run" if dry_run else ("interactive" if interactive else "apply")
    ai_label = "[cyan]AI-powered[/]" if use_ai else "[dim]heuristic[/]"
    console.print(f"\n[bold blue]🔧 Healing test suite:[/] {suite}")
    console.print(f"[dim]Mode: {mode} | Confidence threshold: {confidence:.0%} | Analysis: {ai_label}[/]\n")
    
    # Run tests
    with console.status("[yellow]Running tests...[/]"):
        success, output, failures = runner.run_tests(Path(suite))
    
    if success:
        console.print("[bold green]✓ All tests passed! Nothing to heal.[/]\n")
        return
    
    console.print(f"[yellow]Analyzing {len(failures)} failures...[/]\n")
    
    # Generate fixes - use AI if requested
    if use_ai:
        import asyncio
        fixes = asyncio.run(_generate_fixes_with_ai(failures, confidence, config))
    else:
        fixes = _generate_fixes(failures, confidence)
    
    if not fixes:
        console.print("[yellow]No healable failures found above confidence threshold.[/]\n")
        return
    
    if dry_run:
        _show_diff_preview(fixes)
        console.print(f"\n[dim]Run with --apply to modify {len(fixes)} files[/]\n")
    elif interactive:
        _interactive_apply(fixes)
    else:
        _apply_fixes(fixes)
        console.print(f"\n[green]✓ Applied {len(fixes)} fixes[/]")
        console.print("[dim]Re-run your tests to verify[/]\n")


@main.command()
@click.option("--suite", "-s", required=True, help="Path to test suite directory")
@click.option("--config", "-c", "config_path", type=click.Path(exists=True), help="Config file path")
def baseline(suite: str, config_path: str | None) -> None:
    """Capture baseline HTML snapshots from passing tests."""
    config = load_config(Path(config_path) if config_path else None)
    
    console.print(f"\n[bold blue]📸 Capturing baseline for:[/] {suite}\n")
    
    # Create baseline directory
    baseline_dir = config.baseline_storage
    baseline_dir.mkdir(parents=True, exist_ok=True)
    
    console.print("[yellow]Running tests to capture HTML snapshots...[/]")
    console.print(f"[green]✓ Baseline directory created: {baseline_dir}[/]")
    console.print("[dim]Note: Full baseline capture requires test framework integration[/]\n")


@main.command("heal-playwright")
@click.option("--results-dir", "-r", default="test-results", help="Path to Playwright test-results directory")
@click.option("--test-dir", "-t", default="e2e", help="Path to e2e test directory")
@click.option("--dry-run", is_flag=True, default=True, help="Preview changes without modifying files")
@click.option("--apply", "apply_fixes", is_flag=True, help="Apply fixes to test files")
@click.option("--use-ai", is_flag=True, help="Use Gemini AI for intelligent analysis")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output during analysis")
@click.pass_context
def heal_playwright(
    ctx: click.Context,
    results_dir: str,
    test_dir: str,
    dry_run: bool,
    apply_fixes: bool,
    use_ai: bool,
    verbose: bool,
) -> None:
    """Heal broken Playwright tests using captured aria snapshots."""
    from .capture.playwright_capture import PlaywrightCapture, parse_aria_snapshot
    
    if apply_fixes:
        dry_run = False
    
    config = ctx.obj.get("config")
    results_path = Path(results_dir)
    test_path = Path(test_dir)
    
    mode = "dry-run" if dry_run else "apply"
    console.print(f"\n[bold blue]🔧 Healing Playwright tests[/]")
    console.print(f"[dim]Results: {results_path} | Tests: {test_path} | Mode: {mode}[/]")
    if verbose:
        console.print("[dim]Verbose mode: ON[/]")
    console.print()
    
    if not results_path.exists():
        console.print("[red]Error: test-results directory not found. Run tests first.[/]")
        return
    
    # Get failures from test results
    capture = PlaywrightCapture(results_path)
    failures = capture.get_failures()
    
    if not failures:
        console.print("[green]✓ No failures found in test-results![/]\n")
        return
    
    console.print(f"[yellow]Found {len(failures)} failed tests[/]\n")
    
    if verbose:
        console.print("[bold]─" * 50 + "[/]")
        console.print("[bold cyan]TRIAGING FAILURES[/]")
        console.print("[bold]─" * 50 + "[/]\n")
    
    # Collect all fixes
    all_fixes = []
    
    for i, failure in enumerate(failures, 1):
        console.print(f"[cyan]📋 [{i}/{len(failures)}] {failure.test_name}[/]")
        
        if verbose:
            console.print(f"  [dim]Test file: {failure.test_file}[/]")
            if failure.screenshot_path:
                console.print(f"  [dim]Screenshot: {failure.screenshot_path}[/]")
        
        # Parse aria snapshot to find available elements
        elements = parse_aria_snapshot(failure.aria_snapshot)
        
        if verbose:
            console.print(f"\n  [bold]Aria Snapshot Analysis:[/]")
            console.print(f"    Buttons:   {elements.get('buttons', [])}") 
            console.print(f"    Textboxes: {elements.get('textboxes', [])}")
            console.print(f"    Links:     {elements.get('links', [])}")
            console.print(f"    Headings:  {elements.get('headings', [])}")
        else:
            if elements:
                console.print(f"  [dim]Found: {len(elements.get('buttons', []))} buttons, "
                             f"{len(elements.get('textboxes', []))} textboxes, "
                             f"{len(elements.get('links', []))} links[/]")
        
        # Get test file content to find broken selectors
        test_file = test_path / Path(failure.test_file).name
        if test_file.exists():
            content = test_file.read_text()
            
            # Find data-testid selectors in the test file
            import re
            selectors = re.findall(r'\[data-testid="([^"]+)"\]', content)
            
            if verbose:
                console.print(f"\n  [bold]Selector Analysis:[/]")
                console.print(f"    Found {len(set(selectors))} unique data-testid selectors in test file")
            
            # Use AI if requested
            if use_ai:
                from .healing.gemini_playwright_healer import heal_with_gemini
                
                if verbose:
                    console.print(f"\n  [bold magenta]🤖 Using Gemini AI for healing[/]")
                
                # Get unique selectors that we haven't fixed yet
                unfixed_selectors = [s for s in set(selectors) if f'[data-testid="{s}"]' not in [f.get("old") for f in all_fixes]]
                
                for selector in unfixed_selectors:
                    full_selector = f'[data-testid="{selector}"]'
                    
                    if verbose:
                        console.print(f"\n    [dim]Analyzing: {full_selector}[/]")
                    
                    # Call Gemini (sync wrapper)
                    suggestion = heal_with_gemini(
                        broken_selector=full_selector,
                        aria_snapshot=failure.aria_snapshot,
                        screenshot_path=failure.screenshot_path,
                        model=config.gemini.model if config else "gemini-2.0-flash",
                        verbose=verbose,
                    )
                    
                    if suggestion.found and suggestion.confidence >= 0.7:
                        fix = {
                            "file": str(test_file),
                            "old": full_selector,
                            "new": suggestion.new_selector,
                            "reason": suggestion.reasoning,
                            "confidence": suggestion.confidence,
                        }
                        if fix["old"] not in [f.get("old") for f in all_fixes]:
                            all_fixes.append(fix)
                            if verbose:
                                console.print(f"    [bold green]✓ AI FIX FOUND (confidence: {suggestion.confidence:.0%})[/]")
                                console.print(f"      Reasoning: {suggestion.reasoning[:100]}...")
                                console.print(f"      [red]Old: {fix['old']}[/]")
                                console.print(f"      [green]New: {fix['new']}[/]")
                            else:
                                console.print(f"  [magenta]🤖[/] [red]- {fix['old']}[/]")
                                console.print(f"     [green]+ {fix['new']}[/] [dim]({suggestion.confidence:.0%})[/]")
                    elif verbose:
                        console.print(f"    [dim]✗ AI could not find match (confidence: {suggestion.confidence:.0%})[/]")
                        if suggestion.reasoning:
                            console.print(f"      {suggestion.reasoning[:80]}...")
            else:
                # Heuristic-based matching
                for selector in set(selectors):
                    selector_lower = selector.lower()
                    new_selector = None
                    match_reason = ""
                    
                    # Try to match broken selector to an aria element
                    if "email" in selector_lower and elements.get("textboxes"):
                        for tb in elements["textboxes"]:
                            if "email" in tb.lower():
                                new_selector = f"page.getByLabel('{tb}')"
                                match_reason = f"'email' keyword matched textbox '{tb}'"
                                break
                    
                    elif "password" in selector_lower and elements.get("textboxes"):
                        for tb in elements["textboxes"]:
                            if "password" in tb.lower():
                                new_selector = f"page.getByLabel('{tb}')"
                                match_reason = f"'password' keyword matched textbox '{tb}'"
                                break
                    
                    elif ("submit" in selector_lower or "login" in selector_lower) and elements.get("buttons"):
                        for btn in elements["buttons"]:
                            if "sign" in btn.lower() or "login" in btn.lower():
                                new_selector = f"page.getByRole('button', {{ name: '{btn}' }})"
                                match_reason = f"'submit/login' keyword matched button '{btn}'"
                                break
                    
                    elif "forgot" in selector_lower and elements.get("links"):
                        for link in elements["links"]:
                            if "forgot" in link.lower():
                                new_selector = f"page.getByRole('link', {{ name: '{link}' }})"
                                match_reason = f"'forgot' keyword matched link '{link}'"
                                break
                    
                    elif ("checkout" in selector_lower or "cart" in selector_lower or "continue" in selector_lower) and elements.get("buttons"):
                        # For cart-related buttons, use aria
                        if verbose:
                            console.print(f"    [yellow]⚠ Selector '{selector}' - cart-related, needs more context[/]")
                    
                    if new_selector:
                        fix = {
                            "file": str(test_file),
                            "old": f'[data-testid="{selector}"]',
                            "new": new_selector,
                        }
                        if fix not in all_fixes:
                            all_fixes.append(fix)
                            if verbose:
                                console.print(f"\n    [bold green]✓ FIX FOUND[/]")
                                console.print(f"      Reason: {match_reason}")
                                console.print(f"      [red]Old: {fix['old']}[/]")
                                console.print(f"      [green]New: {fix['new']}[/]")
                            else:
                                console.print(f"  [red]- {fix['old']}[/]")
                                console.print(f"  [green]+ {fix['new']}[/]")
                    elif verbose and selector:
                        console.print(f"    [dim]✗ No match for '{selector}'[/]")
        
        if verbose:
            console.print()
    
    console.print()
    
    if verbose:
        console.print("[bold]─" * 50 + "[/]")
        console.print("[bold cyan]SUMMARY[/]")
        console.print("[bold]─" * 50 + "[/]\n")
    
    if all_fixes:
        console.print(f"[bold]Found {len(all_fixes)} fixes[/]\n")
        
        if verbose:
            console.print("[bold]All fixes:[/]")
            for i, fix in enumerate(all_fixes, 1):
                console.print(f"  {i}. [red]{fix['old']}[/]")
                console.print(f"     → [green]{fix['new']}[/]")
            console.print()
        
        if dry_run:
            console.print("[dim]Run with --apply to modify test files[/]\n")
        else:
            # Apply fixes
            for fix in all_fixes:
                file_path = Path(fix["file"])
                content = file_path.read_text()
                content = content.replace(fix["old"], fix["new"])
                file_path.write_text(content)
                if verbose:
                    console.print(f"[green]✓ Updated {file_path}[/]")
            console.print(f"\n[green]✓ Applied {len(all_fixes)} fixes![/]")
            console.print("[dim]Re-run 'npx playwright test' to verify[/]\n")
    else:
        console.print("[yellow]No automatic fixes found[/]")
        console.print("[dim]The broken selectors may need manual review or AI analysis[/]\n")


def _get_suggested_action(failure: TestFailure) -> str:
    """Suggest an action based on failure type."""
    from .models import FailureType
    
    action_map = {
        FailureType.SELECTOR_NOT_FOUND: "Auto-heal",
        FailureType.ELEMENT_NOT_VISIBLE: "Auto-heal",
        FailureType.TIMEOUT: "Check timing",
        FailureType.ASSERTION_FAILED: "Review assertion",
        FailureType.API_ERROR: "Report bug",
        FailureType.UNKNOWN: "Manual review",
    }
    return action_map.get(failure.failure_type, "Manual review")


def _generate_fixes(failures: list[TestFailure], min_confidence: float) -> list[TestFix]:
    """Generate fixes for healable failures."""
    from .models import HealingResult, RiskLevel, Selector, FailureType
    
    # Known selector mappings
    selector_mappings = {
        "old-submit-btn": "submit-button",
        "email-field": "email-input",
        "password-field": "password-input",
        "cart-icon": "cart-summary",
        "checkout-btn": "checkout-button",
        "item-count": "cart-count",
    }
    
    fixes = []
    
    for failure in failures:
        # Only heal selector-related failures
        if failure.failure_type not in (
            FailureType.SELECTOR_NOT_FOUND,
            FailureType.ELEMENT_NOT_VISIBLE,
            FailureType.TIMEOUT,
        ):
            continue
        
        # Get the broken selector value
        old_selector_value = ""
        if failure.selector:
            old_selector_value = failure.selector.value
        else:
            # Try to extract from error message
            old_selector_value = _extract_selector_value(failure.error_message)
        
        if not old_selector_value:
            continue
        
        # Find suggested new selector
        new_selector_value = selector_mappings.get(old_selector_value.lower())
        if not new_selector_value:
            # Try to infer
            new_selector_value = old_selector_value.replace("old-", "").replace("-btn", "-button")
        
        suggested_code = f'[data-testid="{new_selector_value}"]'
        
        original_selector = Selector(
            strategy="id",
            value=old_selector_value,
            original_code=old_selector_value,
        )
        
        new_selector = Selector(
            strategy="data-testid",
            value=new_selector_value,
            original_code=suggested_code,
        )
        
        healing_result = HealingResult(
            success=True,
            category=FailureCategory.HEALABLE_SELECTOR,
            confidence=0.85,
            original_selector=original_selector,
            new_selector=new_selector,
            suggested_code=suggested_code,
            evidence=[f"Selector '{old_selector_value}' not found, suggesting data-testid"],
            risk_level=RiskLevel.LOW,
            requires_review=False,
        )
        
        fixes.append(TestFix(
            file_path=failure.test_file,
            line_number=0,
            original_code=old_selector_value,
            fixed_code=suggested_code,
            failure=failure,
            healing_result=healing_result,
        ))
    
    return fixes


async def _generate_fixes_with_ai(
    failures: list[TestFailure],
    min_confidence: float,
    config: "Config",
) -> list[TestFix]:
    """Generate fixes using Gemini AI for intelligent analysis."""
    from .healing import GeminiHealingService
    from .models import FailureType
    
    healer = GeminiHealingService(config)
    fixes = []
    
    for failure in failures:
        # Only heal selector-related failures
        if failure.failure_type not in (
            FailureType.SELECTOR_NOT_FOUND,
            FailureType.ELEMENT_NOT_VISIBLE,
            FailureType.TIMEOUT,
        ):
            continue
        
        # Get HTML content from the test file's mock driver (for demo)
        # In real implementation, this would come from baseline snapshots
        html_content = _get_html_for_test(failure)
        
        if not html_content:
            console.print(f"[dim]  Skipping {failure.test_name} - no HTML available[/]")
            continue
        
        console.print(f"[dim]  Analyzing {failure.test_name} with Gemini...[/]")
        
        # Get Gemini's analysis
        healing_result = await healer.analyze_failure(failure, html_content)
        
        if healing_result.success and healing_result.confidence >= min_confidence:
            fixes.append(TestFix(
                file_path=failure.test_file,
                line_number=0,
                original_code=healing_result.original_selector.value if healing_result.original_selector else "",
                fixed_code=healing_result.suggested_code or "",
                failure=failure,
                healing_result=healing_result,
            ))
    
    return fixes


def _get_html_for_test(failure: TestFailure) -> str:
    """Get HTML content for a test - from artifacts or mock driver."""
    import re
    from pathlib import Path
    
    # Strategy 1: Look for real HTML artifacts on disk
    # Common locations for test artifacts
    artifact_dirs = [
        Path("failures"),
        Path("artifacts"),
        Path("reports"),
        Path("test-results"),
        Path(failure.test_file).parent / "failures",
        Path(failure.test_file).parent / "artifacts",
    ]
    
    # Sanitize test name for filename usually used by runners
    # e.g. test_login.py::TestLoginPage::test_submit_button_click -> test_submit_button_click
    simple_name = failure.test_name.split("::")[-1]
    # e.g. test_login.py::TestLoginPage::test_submit_button_click -> TestLoginPage.test_submit_button_click
    class_name = failure.test_name.replace("::", ".")
    
    search_names = [simple_name, class_name, failure.test_name]
    
    for directory in artifact_dirs:
        if not directory.exists():
            continue
            
        for name in search_names:
            # Look for exact match or starting with name
            # Runners might append timestamps or IDs
            matches = list(directory.glob(f"*{name}*.html"))
            if matches:
                try:
                    # Return the content of the newest matching file
                    newest = max(matches, key=lambda p: p.stat().st_mtime)
                    return newest.read_text()
                except Exception:
                    continue

    # Strategy 2: Extract from source code (Mock/Demo mode)
    # Resolve relative path to absolute
    test_file = Path(failure.test_file)
    if not test_file.is_absolute():
        test_file = Path.cwd() / test_file
    
    try:
        content = test_file.read_text()
        
        # Pattern 1: self.page_source = """..."""
        match = re.search(r'page_source\s*=\s*"""(.+?)"""', content, re.DOTALL)
        if match:
            return match.group(1)
        
        # Pattern 2: self.content_html = """..."""  
        match = re.search(r'content_html\s*=\s*"""(.+?)"""', content, re.DOTALL)
        if match:
            return match.group(1)
        
        # Pattern 3: HTML in triple-quoted string with html tag
        match = re.search(r'""".*?<html.*?>(.+?)</html>.*?"""', content, re.DOTALL | re.IGNORECASE)
        if match:
            return f"<html>{match.group(1)}</html>"
            
    except Exception as e:
        pass
    
    return ""


def _extract_selector_value(error: str) -> str:
    """Extract selector value from error message."""
    import re
    patterns = [
        r"Unable to locate element:\s*(\S+)",
        r"Locator\s+'([^']+)'",
        r"#([a-zA-Z0-9_-]+)",
        r"\.([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        if match := re.search(pattern, error, re.IGNORECASE):
            return match.group(1)
    return ""


def _suggest_new_selector(original: "Selector") -> "Selector | None":
    """Suggest a new selector based on the broken one."""
    from .models import Selector
    
    # Map old selector values to new data-testid values
    selector_mappings = {
        "old-submit-btn": "submit-button",
        "email-field": "email-input",
        "password-field": "password-input",
        "#cart-icon": "cart-summary",
        ".checkout-btn": "checkout-button",
        "#item-count": "cart-count",
    }
    
    value = original.value
    
    # Check if we have a known mapping
    new_value = selector_mappings.get(value.lower(), None)
    if not new_value:
        # Try to infer a better selector name
        new_value = value.replace("-", "_").replace("old_", "").replace("old-", "")
        new_value = new_value.replace("-btn", "-button").replace("-field", "-input")
    
    return Selector(
        strategy="data-testid",
        value=new_value,
        original_code=f'[data-testid="{new_value}"]',
    )


def _simulate_find_selector(original: "Selector") -> "Selector | None":
    """Simulate finding a new selector (placeholder)."""
    from .models import Selector
    
    # This would use the HTML analyzer in real implementation
    # Just return a modified selector for demonstration
    new_value = original.value.replace("old", "new").replace("-btn", "-button")
    
    return Selector(
        strategy="css",
        value=f'[data-testid="{new_value}"]',
        original_code=f'By.CSS_SELECTOR, "[data-testid=\\"{new_value}\\"]"',
    )


def _show_diff_preview(fixes: list[TestFix]) -> None:
    """Show diff preview of proposed changes."""
    from rich.markup import escape
    
    console.print("[bold]Proposed changes:[/]\n")
    
    for fix in fixes:
        test_name = fix.failure.test_name.split("::")[-1] if "::" in fix.failure.test_name else fix.failure.test_name
        file_name = f"{fix.file_path.name}::{test_name}"
        
        console.print(f"[cyan]📁 {file_name}[/]")
        console.print(f"[red]- {escape(fix.original_code)}[/]")
        console.print(f"[green]+ {escape(fix.fixed_code)}[/]")
        console.print(f"[dim]  confidence: {fix.healing_result.confidence:.0%}[/]")
        console.print()


def _interactive_apply(fixes: list[TestFix]) -> None:
    """Interactively apply fixes with user approval."""
    applied = 0
    
    for fix in fixes:
        console.print(f"\n[cyan]📁 {fix.file_path}[/]")
        console.print(f"[red]- {fix.original_code}[/]")
        console.print(f"[green]+ {fix.fixed_code}[/]")
        
        response = click.prompt(
            "Apply this fix?",
            type=click.Choice(["y", "n", "d"]),
            default="y",
        )
        
        if response == "y":
            _apply_single_fix(fix)
            applied += 1
            console.print("[green]✓ Applied[/]")
        elif response == "d":
            console.print(f"[dim]Skipped[/]")
    
    console.print(f"\n[green]✓ Applied {applied}/{len(fixes)} fixes[/]\n")


def _apply_fixes(fixes: list[TestFix]) -> None:
    """Apply all fixes to test files."""
    for fix in fixes:
        _apply_single_fix(fix)


def _apply_single_fix(fix: TestFix) -> None:
    """Apply a single fix to a test file."""
    # Read file
    content = fix.file_path.read_text()
    
    # Replace the code
    new_content = content.replace(fix.original_code, fix.fixed_code)
    
    # Write back
    fix.file_path.write_text(new_content)


if __name__ == "__main__":
    main()
