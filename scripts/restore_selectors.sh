#!/bin/bash
# restore_selectors.sh
#
# This script restores the original data-testid values.
# Run this to reset after testing the healing flow.

set -e

DEMO_APP="demo-app/src"

echo "🔧 Restoring original selectors..."
echo ""

# LoginPage.jsx - restore originals
echo "📝 Restoring LoginPage.jsx..."
sed -i '' 's/data-testid="user-email"/data-testid="email-input"/g' "$DEMO_APP/LoginPage.jsx"
sed -i '' 's/data-testid="user-password"/data-testid="password-input"/g' "$DEMO_APP/LoginPage.jsx"
sed -i '' 's/data-testid="login-btn"/data-testid="submit-button"/g' "$DEMO_APP/LoginPage.jsx"
sed -i '' 's/data-testid="forgot-link"/data-testid="forgot-password-link"/g' "$DEMO_APP/LoginPage.jsx"

# CartPage.jsx - restore originals
echo "📝 Restoring CartPage.jsx..."
sed -i '' 's/data-testid="cart-overview"/data-testid="cart-summary"/g' "$DEMO_APP/CartPage.jsx"
sed -i '' 's/data-testid="item-count"/data-testid="cart-count"/g' "$DEMO_APP/CartPage.jsx"
sed -i '' 's/data-testid="total-price"/data-testid="cart-total"/g' "$DEMO_APP/CartPage.jsx"
sed -i '' 's/data-testid="checkout-btn"/data-testid="checkout-button"/g' "$DEMO_APP/CartPage.jsx"
sed -i '' 's/data-testid="keep-shopping"/data-testid="continue-shopping"/g' "$DEMO_APP/CartPage.jsx"

echo ""
echo "✅ Original selectors restored!"
echo ""
echo "🧪 Now run 'npx playwright test' - tests should pass again."
echo ""
