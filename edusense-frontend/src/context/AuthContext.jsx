import React, { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../lib/api'

const AuthContext = createContext()

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('edusense_token') || '')
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('edusense_user') || 'null'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      fetchCurrentUser()
    } else {
      setLoading(false)
    }
  }, [token])

  const fetchCurrentUser = async () => {
    try {
      const res = await api.get('/auth/me')
      if (res.data?.user) {
        setUser(res.data.user)
        localStorage.setItem('edusense_user', JSON.stringify(res.data.user))
      }
    } catch (err) {
      console.error('Failed to fetch user session:', err)
      logout()
    } finally {
      setLoading(false)
    }
  }

  const loginWithToken = (newToken, userProfile) => {
    setToken(newToken)
    setUser(userProfile)
    localStorage.setItem('edusense_token', newToken)
    localStorage.setItem('edusense_user', JSON.stringify(userProfile))
  }

  const logout = () => {
    setToken('')
    setUser(null)
    localStorage.removeItem('edusense_token')
    localStorage.removeItem('edusense_user')
  }

  return (
    <AuthContext.Provider value={{ user, token, role: user?.role, status: user?.status, loginWithToken, logout, loading, refreshUser: fetchCurrentUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
