/**
 * AccountView.jsx - User Account and Settings Fragment
 * 
 * Future feature: User profile and app settings
 * - User profile information
 * - Dietary preferences
 * - App settings and preferences
 * - Account management
 * 
 * Currently: Placeholder view
 */

import React from 'react';
import { User, Settings, Bell, Lock } from 'lucide-react';

const AccountView = () => {
  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Account</h1>
        <p className="view-subtitle">Settings and preferences</p>
      </div>

      <div className="placeholder-content">
        <div className="account-avatar">
          <User size={48} />
        </div>
        <h2>Guest User</h2>
        <p className="placeholder-description">
          Sign in to save your preferences and sync across devices
        </p>
        
        <div className="settings-preview">
          <div className="setting-item">
            <Settings size={20} />
            <span>Preferences</span>
          </div>
          <div className="setting-item">
            <Bell size={20} />
            <span>Notifications</span>
          </div>
          <div className="setting-item">
            <Lock size={20} />
            <span>Privacy</span>
          </div>
        </div>

        <button className="btn btn-primary" disabled>
          Sign In
        </button>
      </div>
    </div>
  );
};

export default AccountView;