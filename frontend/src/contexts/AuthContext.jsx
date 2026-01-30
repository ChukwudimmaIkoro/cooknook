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
        // Try to load saved token
        const savedToken = localStorage.getItem('authToken');
        const savedUser = localStorage.getItem('authUser');
        
        if (savedToken && savedUser) {
          setToken(savedToken);
          setUser(JSON.parse(savedUser));
          console.log('Restored authentication session');
        }
      } catch (error) {
        console.error('Failed to restore session:', error);
        // Clear corrupted data
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
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      
      // Save to state
      setToken(data.access_token);
      setUser(data.user);
      
      // Persist to localStorage
      localStorage.setItem('authToken', data.access_token);
      localStorage.setItem('authUser', JSON.stringify(data.user));
      
      console.log('Login successful:', data.user.username);
      
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
      const response = await fetch('http://localhost:8000/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
      }

      const data = await response.json();
      
      // Save to state
      setToken(data.access_token);
      setUser(data.user);
      
      // Persist to localStorage
      localStorage.setItem('authToken', data.access_token);
      localStorage.setItem('authUser', JSON.stringify(data.user));
      
      console.log('Registration successful:', data.user.username);
      
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