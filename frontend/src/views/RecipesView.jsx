/**
 * RecipesView.jsx - Recipe Search and Discovery View (Updated)
 * 
 * Features:
 * - Regular semantic search
 * - Personalized search (if authenticated)
 * - "For You" recommendations feed (if authenticated)
 * - Search history integration
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import SearchForm from '../components/SearchForm';
import RecipeList from '../components/RecipeList';
import { Heart, TrendingUp, Search as SearchIcon, Sparkles } from 'lucide-react';

const RecipesView = () => {
  // ============================================================================
  // HOOKS
  // ============================================================================
  
  const { isAuthenticated, getAuthHeaders } = useAuth();

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  const [recipes, setRecipes] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Recommendations state
  const [recommendations, setRecommendations] = useState([]);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [recommendationsError, setRecommendationsError] = useState(null);
  
  // View mode: 'search' or 'recommendations'
  const [viewMode, setViewMode] = useState('search');
  
  // Search mode: 'regular' or 'personalized'
  const [searchMode, setSearchMode] = useState('regular');

  // ============================================================================
  // EFFECTS
  // ============================================================================
  
  /**
   * Load recommendations when user is authenticated
   */
  useEffect(() => {
    if (isAuthenticated && viewMode === 'recommendations') {
      loadRecommendations();
    }
  }, [isAuthenticated, viewMode]);

  // ============================================================================
  // API FUNCTIONS
  // ============================================================================
  
  /**
   * Load personalized recommendations
   */
  const loadRecommendations = async () => {
    setLoadingRecommendations(true);
    setRecommendationsError(null);

    try {
      const response = await fetch('http://localhost:8000/recommendations?limit=10', {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to load recommendations');
      }

      const data = await response.json();
      setRecommendations(data);
    } catch (err) {
      console.error('Failed to load recommendations:', err);
      setRecommendationsError(err.message);
      setRecommendations([]);
    } finally {
      setLoadingRecommendations(false);
    }
  };

  /**
   * Perform search (regular or personalized)
   */
  const handleSearch = async (searchParams) => {
    setIsLoading(true);
    setError(null);
    setViewMode('search'); // Switch to search view

    try {
      let results;
      
      if (isAuthenticated && searchMode === 'personalized') {
        // Personalized search
        const response = await fetch('http://localhost:8000/search/personalized', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
          },
          body: JSON.stringify({
            query: searchParams.query,
            ingredients: searchParams.ingredients,
            cuisine: searchParams.cuisine,
            max_time: searchParams.maxTime,
            max_results: searchParams.maxResults,
          }),
        });

        if (!response.ok) {
          throw new Error('Personalized search failed');
        }

        results = await response.json();
      } else {
        // Regular search (with auth if logged in)
        const headers = {
          'Content-Type': 'application/json',
        };
        
        // Add auth headers if user is logged in
        if (isAuthenticated) {
          Object.assign(headers, getAuthHeaders());
        }
        
        const response = await fetch('http://localhost:8000/search', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            query: searchParams.query,
            ingredients: searchParams.ingredients,
            cuisine: searchParams.cuisine,
            max_time: searchParams.maxTime,
            max_results: searchParams.maxResults,
          }),
        });

        if (!response.ok) {
          throw new Error('Search failed');
        }

        results = await response.json();
      }

      setRecipes(results);
      console.log(`Found ${results.length} recipes (${searchMode} search)`);
    } catch (err) {
      console.error('Search failed:', err);
      setError(err.message || 'Failed to search recipes. Please try again.');
      setRecipes([]);
    } finally {
      setIsLoading(false);
    }
  };

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================
  
  /**
   * Render view mode selector
   */
  const renderViewModeSelector = () => {
    if (!isAuthenticated) return null;

    return (
      <div className="view-mode-selector">
        <button
          className={`view-mode-btn ${viewMode === 'search' ? 'active' : ''}`}
          onClick={() => setViewMode('search')}
        >
          <SearchIcon size={20} />
          Search
        </button>
        <button
          className={`view-mode-btn ${viewMode === 'recommendations' ? 'active' : ''}`}
          onClick={() => setViewMode('recommendations')}
        >
          <Sparkles size={20} />
          For You
        </button>
      </div>
    );
  };

  /**
   * Render search mode selector
   */
  const renderSearchModeSelector = () => {
    if (!isAuthenticated || viewMode !== 'search') return null;

    return (
      <div className="search-mode-selector">
        <label className="search-mode-option">
          <input
            type="radio"
            name="searchMode"
            value="regular"
            checked={searchMode === 'regular'}
            onChange={(e) => setSearchMode(e.target.value)}
          />
          <span className="search-mode-label">
            <SearchIcon size={18} />
            Regular Search
          </span>
          <span className="search-mode-desc">Pure semantic matching</span>
        </label>
        
        <label className="search-mode-option">
          <input
            type="radio"
            name="searchMode"
            value="personalized"
            checked={searchMode === 'personalized'}
            onChange={(e) => setSearchMode(e.target.value)}
          />
          <span className="search-mode-label">
            <Heart size={18} />
            Personalized Search
          </span>
          <span className="search-mode-desc">Boosted by your preferences</span>
        </label>
      </div>
    );
  };

  /**
   * Render recommendations view
   */
  const renderRecommendations = () => {
    return (
      <div className="recommendations-container">
        <div className="recommendations-header">
          <Sparkles size={32} />
          <h2>Recommended For You</h2>
          <p>Personalized recipes based on your search history</p>
        </div>

        {loadingRecommendations ? (
          <div className="recipe-list-state">
            <div className="spinner"></div>
            <h3>Finding perfect recipes for you...</h3>
          </div>
        ) : recommendationsError ? (
          <div className="recipe-list-state error">
            <TrendingUp size={48} />
            <h3>{recommendationsError}</h3>
            <p>Search for recipes first to build your preference profile!</p>
            <button
              className="btn btn-primary"
              onClick={() => setViewMode('search')}
            >
              <SearchIcon size={20} />
              Start Searching
            </button>
          </div>
        ) : (
          <RecipeList
            recipes={recommendations}
            isLoading={false}
            error={null}
          />
        )}
      </div>
    );
  };

  // ============================================================================
  // RENDER - MAIN
  // ============================================================================
  
  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Discover Recipes</h1>
        <p className="view-subtitle">
          {isAuthenticated 
            ? 'AI-powered search with personalization' 
            : 'AI-powered semantic search'}
        </p>
      </div>

      {/* View Mode Selector */}
      {renderViewModeSelector()}

      <div className="view-content">
        {viewMode === 'recommendations' ? (
          // Recommendations View
          renderRecommendations()
        ) : (
          // Search View
          <>
            {/* Search Mode Selector */}
            {renderSearchModeSelector()}

            <section className="search-section">
              <SearchForm 
                onSearch={handleSearch}
                isLoading={isLoading}
              />
            </section>

            <section className="results-section">
              <RecipeList 
                recipes={recipes}
                isLoading={isLoading}
                error={error}
              />
            </section>
          </>
        )}
      </div>
    </div>
  );
};

export default RecipesView;