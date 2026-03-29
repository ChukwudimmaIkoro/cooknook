/**
 * AuthContext.jsx - Authentication State Management
 * 
 * Provides global authentication state using React Context API
 * Manages:
 * - User login/logout state
 * - JWT token storage
 * - Automatic token refresh
 * - Protected route authentication
 * 
 * Usage:
 *   import { useAuth } from './contexts/AuthContext';
 *   const { user, login, logout, isAuthenticated } = useAuth();
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { loginUser, registerUser } from '../services/api';

// ============================================================================
// CONTEXT CREATION
// ============================================================================

const AuthContext = createContext(null);

/**
 * Custom hook to access authentication context
 * Must be used within AuthProvider
 * 
 * @returns {Object} Authentication state and methods
 * @throws {Error} If used outside AuthProvider
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// ============================================================================
// PROVIDER COMPONENT
// ============================================================================

/**
 * AuthProvider Component
 * 
 * Wraps the app to provide authentication state to all components
 * 
 * @param {Object} props
 * @param {React.ReactNode} props.children - Child components
 */
export const AuthProvider = ({ children }) => {
  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  /**
   * Current user object (null if not logged in)
   * Contains: id, username, email, full_name, created_at, etc.
   */
  const [user, setUser] = useState(null);
  
  /**
   * JWT access token (null if not logged in)
   */
  const [token, setToken] = useState(null);
  
  /**
   * Loading state for initial authentication check
   */
  const [loading, setLoading] = useState(true);

  // ============================================================================
  // INITIALIZATION
  // ============================================================================
  
  /**
   * Check for existing session on mount
   * Loads token and user from localStorage if available
   */
  useEffect(() => {
    const initAuth = () => {
      try {
        const savedToken = localStorage.getItem('authToken');
        const savedUser = localStorage.getItem('authUser');

        if (savedToken && savedUser) {
          // Decode JWT payload (base64url) to check expiry — no lib needed
          const payload = JSON.parse(atob(savedToken.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
          const isExpired = payload.exp && Date.now() / 1000 > payload.exp;

          if (isExpired) {
            localStorage.removeItem('authToken');
            localStorage.removeItem('authUser');
          } else {
            setToken(savedToken);
            setUser(JSON.parse(savedUser));
          }
        }
      } catch (error) {
        console.error('Failed to restore session:', error);
        localStorage.removeItem('authToken');
        localStorage.removeItem('authUser');
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // ============================================================================
  // AUTHENTICATION METHODS
  // ============================================================================
  
  /**
   * Login user with credentials
   * 
   * @param {string} username - Username
   * @param {string} password - Password
   * @returns {Promise<Object>} User object and token
   * @throws {Error} If login fails
   */
  const login = async (username, password) => {
    try {
      const data = await loginUser(username, password);

      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('authToken', data.access_token);
      localStorage.setItem('authUser', JSON.stringify(data.user));

      return data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  /**
   * Register new user account
   * 
   * @param {Object} userData - User registration data
   * @param {string} userData.username - Username
   * @param {string} userData.email - Email address
   * @param {string} userData.password - Password
   * @param {string} [userData.full_name] - Optional full name
   * @returns {Promise<Object>} User object and token
   * @throws {Error} If registration fails
   */
  const register = async (userData) => {
    try {
      const data = await registerUser(userData);

      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('authToken', data.access_token);
      localStorage.setItem('authUser', JSON.stringify(data.user));

      return data;
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  };

  /**
   * Logout current user
   * Clears all authentication state and localStorage
   */
  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    console.log('Logged out');
  };

  /**
   * Update user profile in state
   * Used after profile updates
   * 
   * @param {Object} updatedUser - Updated user object
   */
  const updateUser = (updatedUser) => {
    setUser(updatedUser);
    localStorage.setItem('authUser', JSON.stringify(updatedUser));
  };

  /**
   * Get authorization header for API requests
   * 
   * @returns {Object} Headers object with Authorization
   */
  const getAuthHeaders = () => {
    if (!token) {
      return {};
    }
    return {
      'Authorization': `Bearer ${token}`,
    };
  };

  // ============================================================================
  // COMPUTED VALUES
  // ============================================================================
  
  /**
   * Whether user is currently authenticated
   */
  const isAuthenticated = !!token && !!user;

  // ============================================================================
  // CONTEXT VALUE
  // ============================================================================
  
  const value = {
    // State
    user,
    token,
    isAuthenticated,
    loading,
    
    // Methods
    login,
    register,
    logout,
    updateUser,
    getAuthHeaders,
  };

  // ============================================================================
  // RENDER
  // ============================================================================
  
  // Don't render children until we've checked for existing session
  if (loading) {
    return (
      <div className="auth-loading">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;