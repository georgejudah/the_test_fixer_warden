# Sample E2E Tests

This directory contains sample tests with intentional failures to demonstrate Test Warden.

## Tests

- `test_login.py` - Login page tests with broken selectors
- `test_checkout.py` - Checkout flow tests with element changes

## Running

```bash
# Run tests (they will fail)
pytest tests/sample_e2e/

# Then run Test Warden
test-warden analyze --suite tests/sample_e2e/
test-warden heal --suite tests/sample_e2e/ --dry-run
```
