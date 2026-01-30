/**
 * App.jsx - Main Application Component (Updated with Authentication)
 * 
 * Root component that manages:
 * - Authentication state via AuthProvider
 * - Tab-based navigation
 * - View routing
 * - Global layout
 */

import React, { useState } from 'react';
import { AuthProvider } from './contexts/AuthContext';
import BottomNav from './components/BottomNav';
import PantryView from './views/PantryView';
import RecipesView from './views/RecipesView';
import SavedView from './views/SavedView';
import AccountView from './views/AccountView';
import { Wifi, WifiOff } from 'lucide-react';
import './App.css';

/**
 * App Component
 * 
 * Top-level component with authentication and navigation
 */
function App() {
  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  /**
   * Active tab state
   * Controls which view is displayed
   */
  const [activeTab, setActiveTab] = useState('recipes');
  
  /**
   * Backend connection status
   * Used to show connection indicator
   */
  const [isBackendConnected, setIsBackendConnected] = useState(true);

  // ============================================================================
  // EFFECTS
  // ============================================================================
  
  /**
   * Check backend connectivity on mount
   */
  React.useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch('http://localhost:8000/');
        setIsBackendConnected(response.ok);
      } catch (error) {
        setIsBackendConnected(false);
        console.error('Backend connection failed:', error);
      }
    };

    checkBackend();
    
    // Check periodically
    const interval = setInterval(checkBackend, 30000); // Every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================
  
  /**
   * Render the appropriate view based on active tab
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
    <AuthProvider>
      <div className="app">
        {/* App Header */}
        <header className="app-header">
          <div className="header-content">
            <h1 className="app-title">
              <span className="logo-icon">🍳</span>
              CookNook
            </h1>
            
            {/* Backend Status Indicator */}
            <div className="header-status">
              {isBackendConnected ? (
                <div className="status-indicator online">
                  <Wifi size={18} />
                  <span className="status-text">Online</span>
                </div>
              ) : (
                <div className="status-indicator offline">
                  <WifiOff size={18} />
                  <span className="status-text">Offline</span>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="app-main">
          {renderActiveView()}
        </main>

        {/* Bottom Navigation */}
        <BottomNav 
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      </div>
    </AuthProvider>
  );
}

export default App;