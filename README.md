# Test Warden

AI-powered auto-healing for Selenium/Playwright test suites.

## Installation

```bash
pip install test-warden
```

## Quick Start

```bash
# Analyze test failures
test-warden analyze --suite tests/e2e

# Preview fixes (dry run)
test-warden heal --suite tests/e2e --dry-run

# Apply fixes
test-warden heal --suite tests/e2e --apply
```

## Configuration

Create `test_warden.yaml` in your project root:

```yaml
test_warden:
  test_command: "pytest tests/e2e"
  gemini:
    model: gemini-2.0-flash
```

## Features

- 🔍 **3-Layer Analysis**: HTML DOM, Gemini Vision, HAR logs
- 🔧 **Auto-Healing**: Fix broken selectors automatically
- 📊 **Observability**: Full tracing with Langfuse
- 🎯 **Multi-Framework**: Supports Selenium & Playwright (Python/Node.js)
