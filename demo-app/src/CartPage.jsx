import { useState } from 'react'
import './CartPage.css'

const INITIAL_CART_ITEMS = [
    { id: 1, name: 'Premium Headphones', price: 49.99, quantity: 1 },
    { id: 2, name: 'Wireless Mouse', price: 29.99, quantity: 1 },
    { id: 3, name: 'USB-C Hub', price: 19.99, quantity: 1 },
]

export function CartPage({ user, onLogout }) {
    const [cartItems, setCartItems] = useState(INITIAL_CART_ITEMS)
    const [checkoutStarted, setCheckoutStarted] = useState(false)

    const totalItems = cartItems.reduce((sum, item) => sum + item.quantity, 0)
    const totalPrice = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0)

    const handleRemoveItem = (id) => {
        setCartItems(cartItems.filter(item => item.id !== id))
    }

    const handleCheckout = () => {
        setCheckoutStarted(true)
    }

    return (
        <div className="cart-page" data-testid="cart-page">
            <header className="cart-header">
                <h1 data-testid="shop-title">TechShop</h1>
                <div className="user-info">
                    <span data-testid="user-email">{user?.email}</span>
                    <button onClick={onLogout} data-testid="logout-button">Logout</button>
                </div>
            </header>

            <main className="cart-content">
                <h2 data-testid="cart-title">Your Cart</h2>

                <div className="cart-summary" data-testid="cart-overview">
                    <span className="cart-count" data-testid="item-count">{totalItems} items</span>
                    <span className="cart-total" data-testid="total-price">${totalPrice.toFixed(2)}</span>
                </div>

                <div className="cart-items" data-testid="cart-items">
                    {cartItems.map(item => (
                        <div key={item.id} className="cart-item" data-testid={`cart-item-${item.id}`}>
                            <div className="item-info">
                                <h3 data-testid={`item-name-${item.id}`}>{item.name}</h3>
                                <p data-testid={`item-price-${item.id}`}>${item.price.toFixed(2)}</p>
                            </div>
                            <button
                                className="remove-btn"
                                onClick={() => handleRemoveItem(item.id)}
                                data-testid={`remove-item-${item.id}`}
                            >
                                Remove
                            </button>
                        </div>
                    ))}
                </div>

                {cartItems.length === 0 && (
                    <p className="empty-cart" data-testid="empty-cart-message">
                        Your cart is empty
                    </p>
                )}

                <div className="cart-actions">
                    <button
                        className="continue-btn"
                        data-testid="keep-shopping"
                        onClick={() => window.history.back()}
                    >
                        Continue Shopping
                    </button>
                    <button
                        className="checkout-btn"
                        data-testid="checkout-btn"
                        onClick={handleCheckout}
                        disabled={cartItems.length === 0}
                    >
                        Proceed to Checkout
                    </button>
                </div>

                {checkoutStarted && (
                    <div className="checkout-modal" data-testid="checkout-success">
                        <div className="modal-content">
                            <h2>🎉 Order Placed!</h2>
                            <p>Thank you for your purchase.</p>
                        </div>
                    </div>
                )}
            </main>
        </div>
    )
}
