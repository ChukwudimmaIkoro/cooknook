/**
 * App.jsx - Main Application Component
 * 
 * This is the root component that:
 * 1. Manages application state (search results, loading, errors)
 * 2. Coordinates communication between components
 * 3. Handles API calls via the service layer
 * 4. Provides overall layout and structure
 * 
 * Component Hierarchy:
 * App
 * ├── Header (inline)
 * ├── SearchForm (search input)
 * └── RecipeList (results display)
 *     └── RecipeCard[] (individual recipes)
 */

import React, { useState, useEffect } from 'react';
import SearchForm from './components/SearchForm';
import RecipeList from './components/RecipeList';
import { searchRecipes, checkHealth } from './services/api';
import { Utensils, AlertCircle } from 'lucide-react';
import './App.css';

/**
 * Main App Component
 * 
 * State Management:
 * - recipes: Array of search results
 * - isLoading: Whether a search is in progress
 * - error: Error message (null if no error)
 * - backendStatus: Whether backend is connected
 */
function App() {
  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  /**
   * Search results state
   * Holds array of recipe objects returned from backend
   */
  const [recipes, setRecipes] = useState([]);
  
  /**
   * Loading state
   * True when search is in progress, false otherwise
   * Used to show loading indicators and disable form
   */
  const [isLoading, setIsLoading] = useState(false);
  
  /**
   * Error state
   * Holds error message string when search fails
   * Null when no error
   */
  const [error, setError] = useState(null);
  
  /**
   * Backend connection status
   * Tracks whether the Python backend is reachable
   * Used to show connection warnings
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
   * Check backend health on component mount
   * Verifies the Python API is running and accessible
   * 
   * This runs once when the app loads to:
   * - Verify backend connection
   * - Get dataset size
   * - Show warning if backend is down
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
  }, []); // Empty dependency array = run once on mount

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================
  
  /**
   * Handle search form submission
   * 
   * This function:
   * 1. Sets loading state
   * 2. Calls backend API with search parameters
   * 3. Updates results or error state
   * 4. Clears loading state
   * 
   * @param {Object} searchParams - Search parameters from form
   * @param {string} searchParams.query - Natural language query
   * @param {string[]} searchParams.ingredients - Available ingredients
   * @param {string|null} searchParams.cuisine - Cuisine filter
   * @param {number|null} searchParams.maxTime - Maximum cooking time filter
   * @param {number} searchParams.maxResults - Number of results to return
   */
  const handleSearch = async (searchParams) => {
    // Step 1: Set loading state and clear previous errors
    setIsLoading(true);
    setError(null);

    try {
      // Step 2: Call API with search parameters
      const results = await searchRecipes(searchParams);
      
      // Step 3: Update recipes state with results
      setRecipes(results);
      
      // Log results for debugging
      console.log(`Found ${results.length} recipes`);
      
    } catch (err) {
      // Step 4: Handle errors
      console.error('Search failed:', err);
      
      // Set user-friendly error message
      setError(err.message || 'Failed to search recipes. Please try again.');
      
      // Clear results on error
      setRecipes([]);
      
    } finally {
      // Step 5: Always clear loading state
      setIsLoading(false);
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================
  
  return (
    <div className="app">
      {/* ====================================================================
          HEADER SECTION
          Shows app title and backend connection status
      ==================================================================== */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-title">
            <Utensils size={32} />
            <h1>Recipe Recommendation Engine</h1>
          </div>
          <p className="header-subtitle">
            AI-powered recipe search using semantic similarity
          </p>
          
          {/* Backend Status Indicator */}
          {backendStatus.isChecking ? (
            <div className="status-badge checking">
              Checking backend connection...
            </div>
          ) : backendStatus.isConnected ? (
            <div className="status-badge connected">
              ✓ Connected to backend ({backendStatus.totalRecipes.toLocaleString()} recipes)
            </div>
          ) : (
            <div className="status-badge disconnected">
              <AlertCircle size={16} />
              Backend not connected. Start the Python server on port 8000.
            </div>
          )}
        </div>
      </header>

      {/* ====================================================================
          MAIN CONTENT SECTION
          Contains search form and results
      ==================================================================== */}
      <main className="app-main">
        <div className="app-container">
          {/* Search Form */}
          <section className="search-section">
            <SearchForm 
              onSearch={handleSearch}
              isLoading={isLoading}
            />
          </section>

          {/* Results Section */}
          <section className="results-section">
            <RecipeList 
              recipes={recipes}
              isLoading={isLoading}
              error={error}
            />
          </section>
        </div>
      </main>

      {/* ====================================================================
          FOOTER SECTION
          App information and credits
      ==================================================================== */}
      <footer className="app-footer">
        <p>
          Built with React + FastAPI + Sentence Transformers
        </p>
        <p className="footer-note">
          Search uses semantic similarity to find recipes matching your preferences
        </p>
      </footer>
    </div>
  );
}

export default App;