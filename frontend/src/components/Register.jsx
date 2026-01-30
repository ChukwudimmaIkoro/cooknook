/**
 * Register.jsx - User Registration Component
 * 
 * Provides registration interface for new users
 * Features:
 * - Username, email, password input
 * - Password confirmation
 * - Input validation
 * - Error handling
 * - Link to login for existing users
 */

import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { UserPlus, User, Mail, Lock, AlertCircle, CheckCircle } from 'lucide-react';

/**
 * Register Component
 * 
 * @param {Object} props
 * @param {Function} props.onSuccess - Callback after successful registration
 * @param {Function} props.onSwitchToLogin - Callback to switch to login
 */
const Register = ({ onSuccess, onSwitchToLogin }) => {
  // ============================================================================
  // HOOKS
  // ============================================================================
  
  const { register } = useAuth();

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  });
  
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState({});

  // ============================================================================
  // VALIDATION HELPERS
  // ============================================================================
  
  /**
   * Validate email format
   */
  const isValidEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  /**
   * Validate password strength
   * Requirements: At least 6 characters
   */
  const isValidPassword = (password) => {
    return password.length >= 6;
  };

  /**
   * Validate form fields
   * Returns object with field errors or empty object if valid
   */
  const validateForm = () => {
    const errors = {};

    // Username validation
    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    } else if (formData.username.trim().length < 3) {
      errors.username = 'Username must be at least 3 characters';
    }

    // Email validation
    if (!formData.email.trim()) {
      errors.email = 'Email is required';
    } else if (!isValidEmail(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }

    // Password validation
    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (!isValidPassword(formData.password)) {
      errors.password = 'Password must be at least 6 characters';
    }

    // Confirm password validation
    if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }

    return errors;
  };

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================
  
  /**
   * Handle input field changes
   */
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear validation error for this field
    if (validationErrors[name]) {
      setValidationErrors(prev => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Validate form
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    setIsLoading(true);

    try {
      // Register user (without confirmPassword)
      const { confirmPassword, ...userData } = formData;
      await register(userData);
      
      // Success - call parent callback
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
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
          <UserPlus size={32} />
        </div>
        <h2>Create Account</h2>
        <p>Join CookNook to get personalized recipe recommendations</p>
      </div>

      <form onSubmit={handleSubmit} className="auth-form">
        {/* General Error Message */}
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
            Username *
          </label>
          <input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleChange}
            placeholder="Choose a username"
            className={`form-input ${validationErrors.username ? 'error' : ''}`}
            disabled={isLoading}
            autoComplete="username"
            autoFocus
          />
          {validationErrors.username && (
            <span className="field-error">{validationErrors.username}</span>
          )}
        </div>

        {/* Email Input */}
        <div className="form-group">
          <label htmlFor="email">
            <Mail size={18} />
            Email *
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="your.email@example.com"
            className={`form-input ${validationErrors.email ? 'error' : ''}`}
            disabled={isLoading}
            autoComplete="email"
          />
          {validationErrors.email && (
            <span className="field-error">{validationErrors.email}</span>
          )}
        </div>

        {/* Full Name Input (Optional) */}
        <div className="form-group">
          <label htmlFor="full_name">
            <User size={18} />
            Full Name (optional)
          </label>
          <input
            type="text"
            id="full_name"
            name="full_name"
            value={formData.full_name}
            onChange={handleChange}
            placeholder="John Doe"
            className="form-input"
            disabled={isLoading}
            autoComplete="name"
          />
        </div>

        {/* Password Input */}
        <div className="form-group">
          <label htmlFor="password">
            <Lock size={18} />
            Password *
          </label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="At least 6 characters"
            className={`form-input ${validationErrors.password ? 'error' : ''}`}
            disabled={isLoading}
            autoComplete="new-password"
          />
          {validationErrors.password && (
            <span className="field-error">{validationErrors.password}</span>
          )}
        </div>

        {/* Confirm Password Input */}
        <div className="form-group">
          <label htmlFor="confirmPassword">
            <CheckCircle size={18} />
            Confirm Password *
          </label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            placeholder="Re-enter your password"
            className={`form-input ${validationErrors.confirmPassword ? 'error' : ''}`}
            disabled={isLoading}
            autoComplete="new-password"
          />
          {validationErrors.confirmPassword && (
            <span className="field-error">{validationErrors.confirmPassword}</span>
          )}
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
              Creating account...
            </>
          ) : (
            <>
              <UserPlus size={20} />
              Create Account
            </>
          )}
        </button>

        {/* Switch to Login */}
        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <button
              type="button"
              onClick={onSwitchToLogin}
              className="auth-link"
              disabled={isLoading}
            >
              Sign in
            </button>
          </p>
        </div>
      </form>
    </div>
  );
};

export default Register;