/**
 * RecipesView.jsx - Recipe Search and Discovery Fragment
 * 
 * This is the main recipe search interface - the current functionality
 * Moved into a fragment/view for the tabbed layout
 */

import React, { useState } from 'react';
import SearchForm from '../components/SearchForm';
import RecipeList from '../components/RecipeList';
import { searchRecipes } from '../services/api';

const RecipesView = () => {
  const [recipes, setRecipes] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (searchParams) => {
    setIsLoading(true);
    setError(null);

    try {
      const results = await searchRecipes(searchParams);
      setRecipes(results);
      console.log(`Found ${results.length} recipes`);
    } catch (err) {
      console.error('Search failed:', err);
      setError(err.message || 'Failed to search recipes. Please try again.');
      setRecipes([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Discover Recipes</h1>
        <p className="view-subtitle">AI-powered semantic search</p>
      </div>

      <div className="view-content">
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
      </div>
    </div>
  );
};

export default RecipesView;