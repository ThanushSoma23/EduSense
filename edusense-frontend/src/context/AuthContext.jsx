import React, { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../lib/api'
import { login as loginRequest } from '../api/auth'

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('edusense_token') || '')
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('edusense_user') || 'null')
    } catch {
      return null
    }
  })
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

  const login = async (credentials) => {
    setLoading(true)
    try {
      let resData
      if (typeof loginRequest === 'function') {
        resData = await loginRequest(credentials)
      } else {
        const res = await api.post('/auth/login', credentials)
        resData = res.data
      }
      const newToken = resData?.token || resData?.access_token || resData?.data?.token || resData?.data?.access_token
      const u = resData?.user || resData?.data?.user
      if (!newToken) throw new Error('No token returned by backend.')
      loginWithToken(newToken, u)
      return u
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    setToken('')
    setUser(null)
    localStorage.removeItem('edusense_token')
    localStorage.removeItem('token')
    localStorage.removeItem('edusense_user')
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role: user?.role,
        status: user?.status,
        loading,
        login,
        loginWithToken,
        logout,
        refreshUser: fetchCurrentUser,
        fetchCurrentUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
export default AuthContext
