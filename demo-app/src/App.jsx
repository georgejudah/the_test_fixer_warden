import { useState } from 'react'
import { LoginPage } from './LoginPage'
import { CartPage } from './CartPage'
import './App.css'

function App() {
  const [user, setUser] = useState(null)

  const handleLogin = (userData) => {
    setUser(userData)
  }

  const handleLogout = () => {
    setUser(null)
  }

  if (!user) {
    return <LoginPage onLogin={handleLogin} />
  }

  return <CartPage user={user} onLogout={handleLogout} />
}

export default App
