"""Pytest plugin to capture HTML snapshots on test failure."""

import os
import pytest
from pathlib import Path
from datetime import datetime


def pytest_runtest_makereport(item, call):
    """Hook to execute after each test phase."""
    if call.when == "call":
        if call.excinfo is not None:
            print(f"DEBUG: Test failed: {item.name}, capturing snapshot...")
            _capture_snapshot(item)


def _capture_snapshot(item):
    """Capture snapshot from the test driver."""
    # Create failures directory
    # Try to put it relative to the test file, or in cwd
    try:
        base_dir = Path(item.fspath).parent
    except Exception:
        base_dir = Path.cwd()
        
    failure_dir = base_dir / "failures"
    failure_dir.mkdir(exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = item.name.replace("::", "_").replace("/", "_")
    filename = failure_dir / f"{clean_name}_{timestamp}.html"
    
    # Try to find driver fixture
    driver = None
    
    # Check fixtures for common driver names
    fixture_names = ["driver", "browser", "web_driver", "selenium"]
    for name in fixture_names:
        if name in item.funcargs:
            driver = item.funcargs[name]
            break
            
    if not driver:
        # Check class attributes (unittest style)
        if item.instance:
            for name in fixture_names:
                if hasattr(item.instance, name):
                    driver = getattr(item.instance, name)
                    break

    # Save snapshot
    if driver:
        content = ""
        try:
            # Selenium / Mock
            if hasattr(driver, "page_source"):
                content = driver.page_source
            # Playwright page
            elif hasattr(driver, "content"):
                content = driver.content()
        except Exception:
            pass
            
        if content:
            try:
                filename.write_text(content, encoding="utf-8")
                # Attach path to the item for reporting if needed
                item.user_properties.append(("snapshot_path", str(filename)))
            except Exception:
                pass
