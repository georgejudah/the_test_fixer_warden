import { test, expect } from '@playwright/test';

/**
 * Cart Page Tests
 * 
 * These tests verify the cart/checkout functionality.
 * First login, then test cart features.
 */

test.describe('Cart Page', () => {
    // Login before each test to access cart
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.locator('[data-testid="email-input"]').fill('user@shop.com');
        await page.locator('[data-testid="password-input"]').fill('password123');
        await page.locator('[data-testid="submit-button"]').click();
        await expect(page.locator('[data-testid="cart-page"]')).toBeVisible();
    });

    test('should display cart summary', async ({ page }) => {
        // Verify cart summary is visible
        const cartSummary = page.locator('[data-testid="cart-summary"]');
        await expect(cartSummary).toBeVisible();
    });

    test('should show item count', async ({ page }) => {
        // Check the cart count displays items
        const cartCount = page.locator('[data-testid="cart-count"]');
        await expect(cartCount).toBeVisible();
        await expect(cartCount).toContainText('items');
    });

    test('should show cart total', async ({ page }) => {
        // Check the total price is displayed
        const cartTotal = page.locator('[data-testid="cart-total"]');
        await expect(cartTotal).toBeVisible();
        await expect(cartTotal).toContainText('$');
    });

    test('should have checkout button', async ({ page }) => {
        // Verify checkout button exists
        const checkoutButton = page.locator('[data-testid="checkout-button"]');
        await expect(checkoutButton).toBeVisible();
        await expect(checkoutButton).toHaveText('Proceed to Checkout');
    });

    test('should have continue shopping button', async ({ page }) => {
        // Verify continue shopping button
        const continueButton = page.locator('[data-testid="continue-shopping"]');
        await expect(continueButton).toBeVisible();
        await expect(continueButton).toHaveText('Continue Shopping');
    });

    test('should show checkout success on button click', async ({ page }) => {
        // Click checkout
        await page.locator('[data-testid="checkout-button"]').click();

        // Verify success modal appears
        await expect(page.locator('[data-testid="checkout-success"]')).toBeVisible();
    });

    test('should display cart items', async ({ page }) => {
        // Verify cart items are visible
        const cartItems = page.locator('[data-testid="cart-items"]');
        await expect(cartItems).toBeVisible();

        // Should have at least one item
        const firstItem = page.locator('[data-testid="cart-item-1"]');
        await expect(firstItem).toBeVisible();
    });

    test('should allow logging out', async ({ page }) => {
        // Click logout
        const logoutButton = page.locator('[data-testid="logout-button"]');
        await expect(logoutButton).toBeVisible();
        await logoutButton.click();

        // Should return to login page
        await expect(page.locator('[data-testid="login-page"]')).toBeVisible();
    });
});
