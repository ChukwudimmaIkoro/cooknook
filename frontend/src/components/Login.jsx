/**
 * Login.jsx - User Login Component
 * 
 * Provides login interface for existing users
 * Features:
 * - Username/password authentication
 * - Error handling and validation
 * - Link to registration for new users
 * - Remember me functionality (via localStorage)
 */

import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { LogIn, User, Lock, AlertCircle } from 'lucide-react';

/**
 * Login Component
 * 
 * @param {Object} props
 * @param {Function} props.onSuccess - Callback after successful login
 * @param {Function} props.onSwitchToRegister - Callback to switch to registration
 */
const Login = ({ onSuccess, onSwitchToRegister }) => {
  // ============================================================================
  // HOOKS
  // ============================================================================
  
  const { login } = useAuth();

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================
  
  /**
   * Handle form submission
   * 
   * @param {Event} e - Form submit event
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Validation
    if (!username.trim()) {
      setError('Please enter your username');
      return;
    }
    
    if (!password) {
      setError('Please enter your password');
      return;
    }

    setIsLoading(true);

    try {
      await login(username.trim(), password);
      
      // Success - call parent callback
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================
  
  return (
    <div className="auth-form-container">
      <div className="auth-form-header">
        <div className="auth-icon">
          <LogIn size={32} />
        </div>
        <h2>Welcome Back</h2>
        <p>Sign in to access personalized recipes</p>
      </div>

      <form onSubmit={handleSubmit} className="auth-form">
        {/* Error Message */}
        {error && (
          <div className="auth-error">
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        {/* Username Input */}
        <div className="form-group">
          <label htmlFor="username">
            <User size={18} />
            Username
          </label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your username"
            className="form-input"
            disabled={isLoading}
            autoComplete="username"
            autoFocus
          />
        </div>

        {/* Password Input */}
        <div className="form-group">
          <label htmlFor="password">
            <Lock size={18} />
            Password
          </label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            className="form-input"
            disabled={isLoading}
            autoComplete="current-password"
          />
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <div className="spinner-small"></div>
              Signing in...
            </>
          ) : (
            <>
              <LogIn size={20} />
              Sign In
            </>
          )}
        </button>

        {/* Switch to Register */}
        <div className="auth-footer">
          <p>
            Don't have an account?{' '}
            <button
              type="button"
              onClick={onSwitchToRegister}
              className="auth-link"
              disabled={isLoading}
            >
              Sign up
            </button>
          </p>
        </div>
      </form>
    </div>
  );
};

export default Login;