/**
 * App.jsx - Main Application Component (Mobile-Style Layout)
 * 
 * Mobile app-style layout with:
 * - Top app bar with status
 * - Fragment/view container (shows different content based on active tab)
 * - Bottom navigation bar (4 tabs)
 * 
 * Architecture similar to Android Activities/Fragments or iOS Tab Bar Controller
 */

import React, { useState, useEffect } from 'react';
import BottomNav from './components/BottomNav';
import PantryView from './views/PantryView';
import RecipesView from './views/RecipesView';
import SavedView from './views/SavedView';
import AccountView from './views/AccountView';
import { checkHealth } from './services/api';
import { Utensils, AlertCircle, Wifi, WifiOff } from 'lucide-react';
import './App.css';

function App() {
  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  /**
   * Currently active tab/view
   * Default: 'recipes' (main feature)
   */
  const [activeTab, setActiveTab] = useState('recipes');
  
  /**
   * Backend connection status
   * Monitors if the Python API is available
   */
  const [backendStatus, setBackendStatus] = useState({
    isConnected: false,
    isChecking: true,
    totalRecipes: 0,
  });

  // ============================================================================
  // EFFECTS
  // ============================================================================
  
  /**
   * Check backend health on app load
   * Verifies the Python API is running and accessible
   */
  useEffect(() => {
    const verifyBackend = async () => {
      try {
        const status = await checkHealth();
        setBackendStatus({
          isConnected: true,
          isChecking: false,
          totalRecipes: status.total_recipes || 0,
        });
      } catch (error) {
        console.error('Backend health check failed:', error);
        setBackendStatus({
          isConnected: false,
          isChecking: false,
          totalRecipes: 0,
        });
      }
    };

    verifyBackend();
  }, []);

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================
  
  /**
   * Render the appropriate view based on active tab
   * Similar to Fragment transaction in Android or view controller in iOS
   */
  const renderActiveView = () => {
    switch (activeTab) {
      case 'pantry':
        return <PantryView />;
      case 'recipes':
        return <RecipesView />;
      case 'saved':
        return <SavedView />;
      case 'account':
        return <AccountView />;
      default:
        return <RecipesView />;
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================
  
  return (
    <div className="app mobile-layout">
      {/* Top App Bar */}
      <header className="app-bar">
        <div className="app-bar-content">
          <div className="app-bar-title">
            <Utensils size={28} />
            <h1>CookNook</h1>
          </div>
          
          {/* Connection Status Indicator */}
          <div className="connection-status">
            {backendStatus.isChecking ? (
              <div className="status-indicator checking">
                <Wifi size={16} className="pulse" />
              </div>
            ) : backendStatus.isConnected ? (
              <div className="status-indicator connected" title={`${backendStatus.totalRecipes.toLocaleString()} recipes`}>
                <Wifi size={16} />
              </div>
            ) : (
              <div className="status-indicator disconnected" title="Backend offline">
                <WifiOff size={16} />
              </div>
            )}
          </div>
        </div>
        
        {/* Connection Warning Banner (only if disconnected) */}
        {!backendStatus.isChecking && !backendStatus.isConnected && (
          <div className="connection-banner">
            <AlertCircle size={16} />
            <span>Backend offline. Start server on port 8000.</span>
          </div>
        )}
      </header>

      {/* Main Content Area - Fragment Container */}
      <main className="app-content">
        {renderActiveView()}
      </main>

      {/* Bottom Navigation */}
      <BottomNav 
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
    </div>
  );
}

export default App;