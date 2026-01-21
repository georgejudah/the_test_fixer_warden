"""Sample login page tests with intentional selector failures."""

import pytest
from unittest.mock import MagicMock


class MockDriver:
    """Mock Selenium WebDriver for demonstration."""
    
    def __init__(self):
        self.page_source = """
        <html>
        <body>
            <form id="login-form">
                <input data-testid="email-input" type="email" name="email">
                <input data-testid="password-input" type="password" name="password">
                <button data-testid="submit-button" type="submit">Sign In</button>
            </form>
            <a data-testid="forgot-password-link" href="/forgot">Forgot Password?</a>
        </body>
        </html>
        """
    
    def find_element(self, by, value):
        """Simulate element finding - fails for old selectors."""
        # These OLD selectors will fail (simulating a UI refactor)
        failing_selectors = [
            "old-submit-btn",      # Was renamed to submit-button
            "login-button",        # Was renamed to submit-button
            "email-field",         # Was renamed to email-input
            "password-field",      # Was renamed to password-input
        ]
        
        if value in failing_selectors:
            raise Exception(f"NoSuchElementException: Unable to locate element: {value}")
        
        return MagicMock()


@pytest.fixture
def driver():
    """Provide mock driver."""
    return MockDriver()


class TestLoginPage:
    """Tests for the login page."""
    
    def test_submit_button_click(self, driver):
        """Test clicking the submit button - uses OLD selector that will fail."""
        # This selector is WRONG - the button was renamed to 'submit-button'
        # Test Warden should detect this and suggest: data-testid="submit-button"
        element = driver.find_element("id", "old-submit-btn")
        element.click()
    
    def test_email_input(self, driver):
        """Test email input field - uses OLD selector that will fail."""
        # This selector is WRONG - was renamed to 'email-input'
        element = driver.find_element("id", "email-field")
        element.send_keys("test@example.com")
    
    def test_password_input(self, driver):
        """Test password input field - uses OLD selector that will fail."""
        # This selector is WRONG - was renamed to 'password-input'
        element = driver.find_element("id", "password-field")
        element.send_keys("secret123")
    
    def test_forgot_password_link(self, driver):
        """Test forgot password link - this one should PASS."""
        # This selector is CORRECT
        element = driver.find_element("data-testid", "forgot-password-link")
        element.click()
