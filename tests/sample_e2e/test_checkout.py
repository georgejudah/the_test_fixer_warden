"""Sample checkout tests with intentional failures."""

import pytest
from unittest.mock import MagicMock


class MockPage:
    """Mock Playwright Page for demonstration."""
    
    def __init__(self):
        self.content_html = """
        <html>
        <body>
            <div data-testid="cart-summary">
                <span data-testid="cart-count">3 items</span>
                <span data-testid="cart-total">$99.99</span>
            </div>
            <button data-testid="checkout-button">Proceed to Checkout</button>
            <button data-testid="continue-shopping">Continue Shopping</button>
        </body>
        </html>
        """
    
    def locator(self, selector):
        """Simulate locator - fails for old selectors."""
        failing_selectors = [
            "#cart-icon",           # Was changed to data-testid="cart-summary"
            ".checkout-btn",        # Was changed to data-testid="checkout-button"
            "#item-count",          # Was changed to data-testid="cart-count"
        ]
        
        if selector in failing_selectors:
            raise Exception(f"TimeoutError: Locator '{selector}' not found")
        
        return MagicMock()
    
    def content(self):
        return self.content_html


@pytest.fixture
def page():
    """Provide mock page."""
    return MockPage()


class TestCheckoutFlow:
    """Tests for the checkout flow."""
    
    def test_cart_icon_visible(self, page):
        """Test cart icon is visible - uses OLD selector that will fail."""
        # This selector is WRONG - changed to data-testid="cart-summary"
        # Test Warden should suggest: [data-testid="cart-summary"]
        cart = page.locator("#cart-icon")
        assert cart.is_visible()
    
    def test_checkout_button(self, page):
        """Test checkout button - uses OLD selector that will fail."""
        # This selector is WRONG - changed to data-testid="checkout-button"
        btn = page.locator(".checkout-btn")
        btn.click()
    
    def test_item_count_displayed(self, page):
        """Test item count is displayed - uses OLD selector that will fail."""
        # This selector is WRONG - changed to data-testid="cart-count"
        count = page.locator("#item-count")
        assert "3" in count.text_content()
    
    def test_continue_shopping(self, page):
        """Test continue shopping button - this one should PASS."""
        # This selector is CORRECT
        btn = page.locator('[data-testid="continue-shopping"]')
        btn.click()
