import { test, expect } from '@playwright/test';

/**
 * Login Page Tests
 * 
 * These tests verify the login functionality.
 * The selectors match the current app state - if selectors change,
 * Test Warden should be able to heal these tests.
 */

test.describe('Login Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('should display login form', async ({ page }) => {
        // Verify the login page is displayed
        await expect(page.locator('[data-testid="login-page"]')).toBeVisible();
        await expect(page.locator('[data-testid="login-title"]')).toHaveText('Welcome Back');
    });

    test('should have email input field', async ({ page }) => {
        // Find and interact with email input
        const emailInput = page.locator('[data-testid="email-input"]');
        await expect(emailInput).toBeVisible();
        await emailInput.fill('test@example.com');
        await expect(emailInput).toHaveValue('test@example.com');
    });

    test('should have password input field', async ({ page }) => {
        // Find and interact with password input
        const passwordInput = page.locator('[data-testid="password-input"]');
        await expect(passwordInput).toBeVisible();
        await passwordInput.fill('secret123');
        await expect(passwordInput).toHaveValue('secret123');
    });

    test('should have submit button', async ({ page }) => {
        // Find the submit button
        const submitButton = page.locator('[data-testid="submit-button"]');
        await expect(submitButton).toBeVisible();
        await expect(submitButton).toHaveText('Sign In');
    });

    test('should navigate to cart after login', async ({ page }) => {
        // Fill in login form
        await page.locator('[data-testid="email-input"]').fill('user@shop.com');
        await page.locator('[data-testid="password-input"]').fill('password123');

        // Submit the form
        await page.locator('[data-testid="submit-button"]').click();

        // Verify navigation to cart page
        await expect(page.locator('[data-testid="cart-page"]')).toBeVisible();
    });

    test('should have forgot password link', async ({ page }) => {
        const forgotLink = page.locator('[data-testid="forgot-password-link"]');
        await expect(forgotLink).toBeVisible();
        await expect(forgotLink).toHaveText('Forgot Password?');
    });
});
