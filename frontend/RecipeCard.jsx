/**
 * RecipeCard.jsx - Individual Recipe Card Component
 * 
 * Displays a single recipe result with:
 * - Cuisine type
 * - Similarity score (how well it matches the search)
 * - Complete ingredient list
 * - Visual indicators for matching/missing ingredients
 * 
 * Visual Design:
 * - Uses color coding to show ingredient availability
 * - Displays similarity as a percentage
 * - Clean, card-based layout
 */

import React from 'react';
import { ChefHat, Check, X } from 'lucide-react';

/**
 * RecipeCard Component
 * 
 * @param {Object} props
 * @param {Object} props.recipe - Recipe data object
 * @param {number} props.recipe.id - Unique recipe identifier
 * @param {string} props.recipe.name - Recipe name/title
 * @param {string} props.recipe.cuisine - Cuisine type
 * @param {string[]} props.recipe.ingredients - All required ingredients
 * @param {number} props.recipe.similarity_score - Match score (0.0 to 1.0)
 * @param {string[]} props.recipe.matching_ingredients - Ingredients user has
 * @param {string[]} props.recipe.missing_ingredients - Ingredients user needs
 * @param {number} [props.recipe.minutes] - Cooking time in minutes
 * @param {number} [props.recipe.n_steps] - Number of steps
 * @param {string} [props.recipe.description] - Recipe description
 * 
 * @example
 * <RecipeCard recipe={{
 *   id: 137739,
 *   name: "Classic Spaghetti Carbonara",
 *   cuisine: "italian",
 *   ingredients: ["pasta", "eggs", "bacon"],
 *   similarity_score: 0.87,
 *   matching_ingredients: ["eggs"],
 *   missing_ingredients: ["pasta", "bacon"],
 *   minutes: 30,
 *   n_steps: 8
 * }} />
 */
const RecipeCard = ({ recipe }) => {
  // ============================================================================
  // COMPUTED VALUES
  // ============================================================================
  
  /**
   * Convert similarity score to percentage for display
   * 0.87 -> "87%"
   */
  const scorePercentage = Math.round(recipe.similarity_score * 100);
  
  /**
   * Determine score color based on value
   * - High (>80%): Green - excellent match
   * - Medium (60-80%): Yellow - good match
   * - Low (<60%): Orange - weak match
   */
  const getScoreColor = (score) => {
    if (score >= 0.8) return '#22c55e'; // Green
    if (score >= 0.6) return '#eab308'; // Yellow
    return '#f97316'; // Orange
  };

  /**
   * Determine if user has most ingredients
   * Used to show a badge for recipes where user has >70% of ingredients
   */
  const hasMostIngredients = recipe.matching_ingredients.length > 0 &&
    recipe.matching_ingredients.length / recipe.ingredients.length > 0.7;

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================
  
  /**
   * Check if an ingredient is in the user's available list
   * Used to apply different styling to matched vs. missing ingredients
   * 
   * @param {string} ingredient - Ingredient name to check
   * @returns {boolean} True if user has this ingredient
   */
  const isMatching = (ingredient) => {
    return recipe.matching_ingredients.some(
      match => match.toLowerCase() === ingredient.toLowerCase()
    );
  };

  // ============================================================================
  // RENDER
  // ============================================================================
  
  return (
    <div className="recipe-card">
      {/* Card Header - Cuisine and Score */}
      <div className="recipe-header">
        <div className="recipe-cuisine">
          <ChefHat size={20} />
          <span>
            {/* Capitalize cuisine name */}
            {recipe.cuisine.charAt(0).toUpperCase() + recipe.cuisine.slice(1)}
          </span>
        </div>
        
        {/* Similarity Score Badge */}
        <div 
          className="recipe-score"
          style={{ 
            backgroundColor: getScoreColor(recipe.similarity_score),
            color: 'white'
          }}
        >
          {scorePercentage}% Match
        </div>
      </div>

      {/* Recipe ID (useful for debugging/referencing) */}
      <div className="recipe-id">
        Recipe #{recipe.id}
      </div>

      {/* Ingredient Availability Badge (if applicable) */}
      {hasMostIngredients && (
        <div className="recipe-badge">
          <Check size={16} />
          You have most ingredients!
        </div>
      )}

      {/* Ingredients Section */}
      <div className="recipe-section">
        <h4>Ingredients ({recipe.ingredients.length})</h4>
        <ul className="ingredients-list">
          {recipe.ingredients.map((ingredient, index) => (
            <li 
              key={index}
              className={`ingredient ${isMatching(ingredient) ? 'matching' : 'missing'}`}
            >
              {/* Icon indicating if user has this ingredient */}
              {isMatching(ingredient) ? (
                <Check size={16} className="ingredient-icon available" />
              ) : (
                <X size={16} className="ingredient-icon unavailable" />
              )}
              
              {/* Ingredient name */}
              <span>{ingredient}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Summary of Ingredient Availability */}
      {recipe.matching_ingredients.length > 0 && (
        <div className="recipe-summary">
          <div className="summary-item">
            <span className="summary-label">You have:</span>
            <span className="summary-value available">
              {recipe.matching_ingredients.length} ingredients
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">You need:</span>
            <span className="summary-value unavailable">
              {recipe.missing_ingredients.length} ingredients
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default RecipeCard;