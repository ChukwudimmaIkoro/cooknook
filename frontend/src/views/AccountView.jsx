/**
 * AccountView.jsx - User Account and Settings View
 * 
 * Displays:
 * - Login/Register forms (if not authenticated)
 * - User profile information (if authenticated)
 * - Learned preferences
 * - Search history
 * - Account management options
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Login from '../components/Login';
import Register from '../components/Register';
import {
  User, LogOut, TrendingUp, Clock, Heart, Settings,
  ChevronRight, Loader2, RefreshCw
} from 'lucide-react';
import { getPreferences, getHistory, clearHistory as apiClearHistory } from '../services/api';

const AccountView = () => {
  // ============================================================================
  // HOOKS
  // ============================================================================
  
  const { user, isAuthenticated, logout, token } = useAuth();

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  const [showLogin, setShowLogin] = useState(true); // true = login, false = register
  const [preferences, setPreferences] = useState(null);
  const [loadingPreferences, setLoadingPreferences] = useState(false);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // ============================================================================
  // EFFECTS
  // ============================================================================
  
  /**
   * Load user preferences when authenticated
   * Also reload when component becomes visible (user navigates to Account tab)
   */
  useEffect(() => {
    if (isAuthenticated) {
      loadPreferences();
      loadHistory();
    }
  }, [isAuthenticated]);
  
  /**
   * Add visibility change listener to reload when tab becomes active
   * This ensures fresh data when user navigates back to Account tab
   */
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && isAuthenticated) {
        console.log('Account tab became visible - refreshing data');
        loadPreferences();
        loadHistory();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isAuthenticated]);

  // ============================================================================
  // API FUNCTIONS
  // ============================================================================
  
  /**
   * Manually refresh all data
   */
  const handleRefresh = async () => {
    console.log('Manual refresh triggered');
    await Promise.all([loadPreferences(), loadHistory()]);
  };
  
  /**
   * Load user's learned preferences
   */
  const loadPreferences = async () => {
    setLoadingPreferences(true);
    try {
      const data = await getPreferences(token);
      setPreferences(data);
    } catch (error) {
      console.error('Failed to load preferences:', error);
    } finally {
      setLoadingPreferences(false);
    }
  };

  /**
   * Load user's search history (last 10)
   */
  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const data = await getHistory(token, 10);
      setHistory(data);
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  /**
   * Clear all search history
   */
  const handleClearHistory = async () => {
    if (!confirm('Are you sure you want to clear your search history?')) {
      return;
    }

    try {
      await apiClearHistory(token);
      setHistory([]);
      loadPreferences();
      alert('Search history cleared successfully');
    } catch (error) {
      console.error('Failed to clear history:', error);
      alert('Failed to clear history. Please try again.');
    }
  };

  /**
   * Handle logout
   */
  const handleLogout = () => {
    if (confirm('Are you sure you want to log out?')) {
      logout();
      setPreferences(null);
      setHistory([]);
    }
  };

  // ============================================================================
  // RENDER - NOT AUTHENTICATED
  // ============================================================================
  
  if (!isAuthenticated) {
    return (
      <div className="view-container">
        <div className="view-content auth-view">
          {showLogin ? (
            <Login
              onSuccess={() => console.log('Login successful')}
              onSwitchToRegister={() => setShowLogin(false)}
            />
          ) : (
            <Register
              onSuccess={() => console.log('Registration successful')}
              onSwitchToLogin={() => setShowLogin(true)}
            />
          )}
        </div>
      </div>
    );
  }

  // ============================================================================
  // RENDER - AUTHENTICATED
  // ============================================================================
  
  return (
    <div className="view-container">
      <div className="view-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <div>
            <h1 className="view-title">Account</h1>
            <p className="view-subtitle">Manage your profile and preferences</p>
          </div>
          {isAuthenticated && (
            <button
              onClick={handleRefresh}
              className="btn btn-secondary"
              style={{ padding: '0.5rem 1rem' }}
              title="Refresh data"
            >
              <RefreshCw size={18} />
            </button>
          )}
        </div>
      </div>

      <div className="view-content account-view">
        {/* Profile Card */}
        <div className="account-card profile-card">
          <div className="account-card-header">
            <div className="profile-avatar">
              <User size={32} />
            </div>
            <div className="profile-info">
              <h2>{user.full_name || user.username}</h2>
              <p className="profile-email">{user.email}</p>
              <p className="profile-meta">
                Member since {new Date(user.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
          
          <button
            onClick={handleLogout}
            className="btn btn-secondary btn-block"
          >
            <LogOut size={20} />
            Sign Out
          </button>
        </div>

        {/* Preferences Card */}
        <div className="account-card preferences-card">
          <div className="account-card-header">
            <TrendingUp size={24} />
            <h3>Your Preferences</h3>
          </div>

          {loadingPreferences ? (
            <div className="card-loading">
              <Loader2 className="spinner" size={24} />
              <p>Loading preferences...</p>
            </div>
          ) : preferences ? (
            <div className="preferences-content">
              {/* Search Stats */}
              <div className="preference-stats">
                <div className="stat-item">
                  <span className="stat-value">{preferences.total_searches}</span>
                  <span className="stat-label">Total Searches</span>
                </div>
                <div className="stat-item">
                  <span className="stat-value">{preferences.recent_searches}</span>
                  <span className="stat-label">Last 30 Days</span>
                </div>
              </div>

              {/* Favorite Cuisines */}
              {preferences.favorite_cuisines && preferences.favorite_cuisines.length > 0 && (
                <div className="preference-section">
                  <h4>Favorite Cuisines</h4>
                  <div className="preference-list">
                    {preferences.favorite_cuisines.slice(0, 5).map((item, index) => (
                      <div key={index} className="preference-item">
                        <span className="preference-name">
                          {item.cuisine.charAt(0).toUpperCase() + item.cuisine.slice(1)}
                        </span>
                        <span className="preference-count">{item.count} searches</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Favorite Ingredients */}
              {preferences.favorite_ingredients && preferences.favorite_ingredients.length > 0 && (
                <div className="preference-section">
                  <h4>Favorite Ingredients</h4>
                  <div className="preference-tags">
                    {preferences.favorite_ingredients.slice(0, 10).map((item, index) => (
                      <span key={index} className="preference-tag">
                        {item.ingredient}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Time Preference */}
              {preferences.avg_time_preference && (
                <div className="preference-section">
                  <h4>Typical Cooking Time</h4>
                  <div className="preference-item">
                    <Clock size={18} />
                    <span>~{Math.round(preferences.avg_time_preference)} minutes</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card-empty">
              <p>Start searching for recipes to build your preference profile!</p>
            </div>
          )}
        </div>

        {/* Search History Card */}
        <div className="account-card history-card">
          <div className="account-card-header">
            <Clock size={24} />
            <h3>Recent Searches</h3>
          </div>

          {loadingHistory ? (
            <div className="card-loading">
              <Loader2 className="spinner" size={24} />
              <p>Loading history...</p>
            </div>
          ) : history.length > 0 ? (
            <>
              <div className="history-list">
                {history.map((item) => (
                  <div key={item.id} className="history-item">
                    <div className="history-query">
                      <strong>{item.query || 'Search'}</strong>
                      {item.cuisine && (
                        <span className="history-filter">
                          {item.cuisine}
                        </span>
                      )}
                      {item.max_time && (
                        <span className="history-filter">
                          ≤{item.max_time}min
                        </span>
                      )}
                    </div>
                    <div className="history-meta">
                      <span>{item.results_count} results</span>
                      <span>•</span>
                      <span>{new Date(item.timestamp).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
              
              <button
                onClick={handleClearHistory}
                className="btn btn-secondary btn-block"
              >
                Clear History
              </button>
            </>
          ) : (
            <div className="card-empty">
              <p>No search history yet. Start searching to see your history here!</p>
            </div>
          )}
        </div>

        {/* Settings Placeholder */}
        <div className="account-card settings-card">
          <div className="account-card-header">
            <Settings size={24} />
            <h3>Settings</h3>
          </div>
          
          <div className="settings-list">
            <button className="settings-item" disabled>
              <span>Dietary Restrictions</span>
              <ChevronRight size={20} />
            </button>
            <button className="settings-item" disabled>
              <span>Notification Preferences</span>
              <ChevronRight size={20} />
            </button>
            <button className="settings-item" disabled>
              <span>Privacy Settings</span>
              <ChevronRight size={20} />
            </button>
          </div>
          
          <p className="settings-note">Coming soon!</p>
        </div>
      </div>
    </div>
  );
};

export default AccountView;