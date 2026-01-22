import { useState } from 'react'
import './LoginPage.css'

export function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!email || !password) {
      setError('Please fill in all fields')
      return
    }
    onLogin({ email })
  }

  return (
    <div className="login-page" data-testid="login-page">
      <div className="login-card">
        <h1 data-testid="login-title">Welcome Back</h1>
        <p className="subtitle">Sign in to continue shopping</p>
        
        <form onSubmit={handleSubmit} data-testid="login-form">
          {error && (
            <div className="error-message" data-testid="error-message">
              {error}
            </div>
          )}
          
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              data-testid="user-email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              data-testid="user-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          
          <button type="submit" className="submit-btn" data-testid="login-btn">
            Sign In
          </button>
          
          <a href="/forgot" className="forgot-link" data-testid="forgot-link">
            Forgot Password?
          </a>
        </form>
      </div>
    </div>
  )
}
