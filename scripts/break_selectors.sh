#!/bin/bash
# break_selectors.sh
# 
# This script simulates a frontend refactor by changing data-testid values.
# After running this, the Playwright tests will fail because they use the old selectors.

set -e

DEMO_APP="demo-app/src"

echo "🔨 Breaking selectors in the demo app..."
echo ""

# LoginPage.jsx changes:
# - email-input → user-email
# - password-input → user-password  
# - submit-button → login-btn
# - forgot-password-link → forgot-link

echo "📝 Modifying LoginPage.jsx..."
sed -i '' 's/data-testid="email-input"/data-testid="user-email"/g' "$DEMO_APP/LoginPage.jsx"
sed -i '' 's/data-testid="password-input"/data-testid="user-password"/g' "$DEMO_APP/LoginPage.jsx"
sed -i '' 's/data-testid="submit-button"/data-testid="login-btn"/g' "$DEMO_APP/LoginPage.jsx"
sed -i '' 's/data-testid="forgot-password-link"/data-testid="forgot-link"/g' "$DEMO_APP/LoginPage.jsx"

# CartPage.jsx changes:
# - cart-summary → cart-overview
# - cart-count → item-count
# - cart-total → total-price
# - checkout-button → checkout-btn
# - continue-shopping → keep-shopping

echo "📝 Modifying CartPage.jsx..."
sed -i '' 's/data-testid="cart-summary"/data-testid="cart-overview"/g' "$DEMO_APP/CartPage.jsx"
sed -i '' 's/data-testid="cart-count"/data-testid="item-count"/g' "$DEMO_APP/CartPage.jsx"
sed -i '' 's/data-testid="cart-total"/data-testid="total-price"/g' "$DEMO_APP/CartPage.jsx"
sed -i '' 's/data-testid="checkout-button"/data-testid="checkout-btn"/g' "$DEMO_APP/CartPage.jsx"
sed -i '' 's/data-testid="continue-shopping"/data-testid="keep-shopping"/g' "$DEMO_APP/CartPage.jsx"

echo ""
echo "✅ Done! The following selectors have been changed:"
echo ""
echo "  LoginPage.jsx:"
echo "    • email-input     → user-email"
echo "    • password-input  → user-password"
echo "    • submit-button   → login-btn"
echo "    • forgot-password-link → forgot-link"
echo ""
echo "  CartPage.jsx:"
echo "    • cart-summary    → cart-overview"
echo "    • cart-count      → item-count"
echo "    • cart-total      → total-price"
echo "    • checkout-button → checkout-btn"
echo "    • continue-shopping → keep-shopping"
echo ""
echo "🧪 Now run 'npx playwright test' to see the tests fail!"
echo ""
