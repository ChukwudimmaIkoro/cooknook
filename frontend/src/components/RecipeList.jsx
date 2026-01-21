import React from 'react';
import RecipeCard from './RecipeCard';
import { Loader2, SearchX } from 'lucide-react';

const RecipeList = ({ recipes, isLoading, error }) => {
  if (isLoading) {
    return (
      <div className="recipe-list-state">
        <Loader2 className="spinner" size={48} />
        <h3>Searching for recipes...</h3>
        <p>Finding the best matches for your preferences</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recipe-list-state error">
        <SearchX size={48} />
        <h3>Oops! Something went wrong</h3>
        <p className="error-message">{error}</p>
        <p className="error-hint">
          Make sure the backend server is running on http://localhost:8000
        </p>
      </div>
    );
  }

  if (recipes.length === 0) {
    return (
      <div className="recipe-list-state">
        <SearchX size={48} />
        <h3>No recipes found</h3>
        <p>Try adjusting your search criteria:</p>
        <ul className="suggestions">
          <li>Remove the cuisine filter for more options</li>
          <li>Use fewer or more general ingredients</li>
          <li>Try a different search query</li>
          <li>Increase the number of results</li>
        </ul>
      </div>
    );
  }

  return (
    <div className="recipe-list-container">
      <div className="results-header">
        <h3>
          Found {recipes.length} {recipes.length === 1 ? 'recipe' : 'recipes'}
        </h3>
        <p className="results-subtitle">
          Sorted by relevance to your search
        </p>
      </div>

      <div className="recipe-grid">
        {recipes.map((recipe) => (
          <RecipeCard 
            key={recipe.id} 
            recipe={recipe} 
          />
        ))}
      </div>
    </div>
  );
};

export default RecipeList;