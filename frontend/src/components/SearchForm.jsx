/**
 * SearchForm.jsx - Recipe Search Form Component
 * 
 * This component provides the main search interface where users can:
 * - Enter natural language queries
 * - Specify available ingredients
 * - Filter by cuisine type
 * - Adjust number of results
 * 
 * The form handles user input and triggers searches via the parent component.
 */

import React, { useState, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { getCuisines } from '../services/api';

/**
 * SearchForm Component
 * 
 * @param {Object} props
 * @param {Function} props.onSearch - Callback function called when search is submitted
 *                                    Receives search parameters object
 * @param {boolean} props.isLoading - Whether a search is currently in progress
 * 
 * @example
 * <SearchForm 
 *   onSearch={(params) => handleSearch(params)}
 *   isLoading={false}
 * />
 */
const SearchForm = ({ onSearch, isLoading }) => {
  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  /**
   * Form field states
   * Each input field has its own state for controlled components
   */
  const [query, setQuery] = useState('');           // Natural language query
  const [ingredients, setIngredients] = useState(''); // Comma-separated ingredients
  const [cuisine, setCuisine] = useState('');       // Selected cuisine filter
  const [maxTime, setMaxTime] = useState('');       // Maximum cooking time
  const [maxResults, setMaxResults] = useState(10); // Number of results
  
  /**
   * Cuisines list loaded from API
   * Used to populate the cuisine dropdown
   */
  const [cuisines, setCuisines] = useState([]);
  
  /**
   * Loading state for cuisine dropdown
   */
  const [cuisinesLoading, setCuisinesLoading] = useState(true);

  // ============================================================================
  // EFFECTS
  // ============================================================================
  
  /**
   * Load available cuisines when component mounts
   * This runs once on component initialization
   */
  useEffect(() => {
    const loadCuisines = async () => {
      try {
        const cuisineList = await getCuisines();
        setCuisines(cuisineList);
      } catch (error) {
        console.error('Failed to load cuisines:', error);
        // Set empty array on error so dropdown still works
        setCuisines([]);
      } finally {
        setCuisinesLoading(false);
      }
    };

    loadCuisines();
  }, []); // Empty dependency array = run once on mount

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================
  
  /**
   * Handle form submission
   * Prevents default form behavior and triggers search via callback
   * 
   * @param {Event} e - Form submit event
   */
  const handleSubmit = (e) => {
    e.preventDefault(); // Prevent page reload
    
    // Parse ingredients string into array
    const ingredientsArray = ingredients
      .split(',')
      .map(ing => ing.trim())
      .filter(ing => ing.length > 0);
    
    // Construct search parameters object
    const searchParams = {
      query: query.trim(),
      ingredients: ingredientsArray,
      cuisine: cuisine || null, // Send null if no cuisine selected
      maxTime: maxTime ? parseInt(maxTime) : null, // Send null if no time limit
      maxResults: parseInt(maxResults),
    };
    
    // Call parent's search handler
    onSearch(searchParams);
  };

  /**
   * Clear all form fields
   * Resets the form to its initial state
   */
  const handleClear = () => {
    setQuery('');
    setIngredients('');
    setCuisine('');
    setMaxTime('');
    setMaxResults(10);
  };

  // ============================================================================
  // RENDER
  // ============================================================================
  
  return (
    <form onSubmit={handleSubmit} className="search-form">
      {/* Form Title */}
      <h2>Find Your Perfect Recipe</h2>
      
      {/* Natural Language Query Input */}
      <div className="form-group">
        <label htmlFor="query">
          What are you in the mood for?
          <span className="label-hint">
            (e.g., "quick dinner", "spicy food", "healthy lunch")
          </span>
        </label>
        <input
          type="text"
          id="query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Describe what you want..."
          className="form-input"
        />
      </div>

      {/* Ingredients Input */}
      <div className="form-group">
        <label htmlFor="ingredients">
          What ingredients do you have?
          <span className="label-hint">
            (comma-separated, e.g., "chicken, rice, tomatoes")
          </span>
        </label>
        <input
          type="text"
          id="ingredients"
          value={ingredients}
          onChange={(e) => setIngredients(e.target.value)}
          placeholder="tomatoes, onions, garlic..."
          className="form-input"
        />
      </div>

      {/* Cuisine Filter Dropdown */}
      <div className="form-group">
        <label htmlFor="cuisine">
          Cuisine Type
          <span className="label-hint">(optional)</span>
        </label>
        <select
          id="cuisine"
          value={cuisine}
          onChange={(e) => setCuisine(e.target.value)}
          className="form-select"
          disabled={cuisinesLoading}
        >
          <option value="">All Cuisines</option>
          {cuisinesLoading ? (
            <option disabled>Loading cuisines...</option>
          ) : (
            // Map cuisines to option elements
            cuisines.map((c) => (
              <option key={c} value={c}>
                {/* Capitalize first letter for display */}
                {c.charAt(0).toUpperCase() + c.slice(1)}
              </option>
            ))
          )}
        </select>
      </div>

      {/* Maximum Cooking Time - NEW */}
      <div className="form-group">
        <label htmlFor="maxTime">
          Maximum Cooking Time (minutes)
          <span className="label-hint">(optional, e.g., 30, 60, 120)</span>
        </label>
        <input
          type="number"
          id="maxTime"
          value={maxTime}
          onChange={(e) => setMaxTime(e.target.value)}
          placeholder="e.g., 60"
          min="1"
          max="1440"
          className="form-input"
        />
      </div>

      {/* Max Results Input */}
      <div className="form-group">
        <label htmlFor="maxResults">
          Number of Results
        </label>
        <input
          type="number"
          id="maxResults"
          value={maxResults}
          onChange={(e) => setMaxResults(e.target.value)}
          min="1"
          max="50"
          className="form-input"
        />
      </div>

      {/* Form Actions */}
      <div className="form-actions">
        {/* Search Button */}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading}
        >
          <Search size={20} />
          {isLoading ? 'Searching...' : 'Search Recipes'}
        </button>

        {/* Clear Button */}
        <button
          type="button"
          onClick={handleClear}
          className="btn btn-secondary"
          disabled={isLoading}
        >
          <X size={20} />
          Clear
        </button>
      </div>
    </form>
  );
};

export default SearchForm;