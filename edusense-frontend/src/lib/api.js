import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Attach Bearer token from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('edusense_token') || localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => Promise.reject(error))

export default api
