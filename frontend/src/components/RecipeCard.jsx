/**
 * RecipeCard.jsx - Individual Recipe Card Component
 * 
 * Displays a single recipe result with:
 * - Cuisine type
 * - Similarity score (how well it matches the search)
 * - Collapsible ingredient list (shows 5 by default)
 * - Visual indicators for matching/missing ingredients
 * - Collapsible cooking instructions
 * 
 * Visual Design:
 * - Uses color coding to show ingredient availability
 * - Displays similarity as a percentage
 * - Clean, compact card-based layout
 * - Expandable sections to manage card height
 */

import React, { useState } from 'react';
import { ChefHat, Check, X, Clock, List, ChevronDown, ChevronUp } from 'lucide-react';

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
 * @param {string[]} [props.recipe.steps] - Cooking instructions
 * @param {number} [props.recipe.minutes] - Cooking time in minutes
 * @param {number} [props.recipe.n_steps] - Number of steps
 * @param {string} [props.recipe.description] - Recipe description
 */
const RecipeCard = ({ recipe }) => {
  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  /**
   * Track whether cooking instructions are expanded
   * Collapsed by default to keep cards compact
   */
  const [showInstructions, setShowInstructions] = useState(false);
  
  /**
   * Track whether all ingredients are shown
   * Shows only first 5 by default
   */
  const [showAllIngredients, setShowAllIngredients] = useState(false);

  // ============================================================================
  // COMPUTED VALUES
  // ============================================================================
  
  /**
   * Maximum number of ingredients to show when collapsed
   */
  const INGREDIENT_PREVIEW_COUNT = 5;
  
  /**
   * Whether this recipe has more than 5 ingredients
   */
  const hasMoreIngredients = recipe.ingredients.length > INGREDIENT_PREVIEW_COUNT;
  
  /**
   * Ingredients to display (either first 5 or all)
   */
  const displayedIngredients = showAllIngredients 
    ? recipe.ingredients 
    : recipe.ingredients.slice(0, INGREDIENT_PREVIEW_COUNT);
  
  /**
   * Number of hidden ingredients when collapsed
   */
  const hiddenCount = recipe.ingredients.length - INGREDIENT_PREVIEW_COUNT;
  
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

      {/* Recipe Name */}
      <h3 className="recipe-name">{recipe.name}</h3>

      {/* Recipe Metadata (Time and Steps) */}
      <div className="recipe-meta">
        {recipe.minutes && (
          <div className="meta-item">
            <Clock size={16} />
            <span>{recipe.minutes} min</span>
          </div>
        )}
        {recipe.n_steps && (
          <div className="meta-item">
            <List size={16} />
            <span>{recipe.n_steps} steps</span>
          </div>
        )}
      </div>

      {/* Ingredient Availability Badge (if applicable) */}
      {hasMostIngredients && (
        <div className="recipe-badge">
          <Check size={16} />
          You have most ingredients!
        </div>
      )}

      {/* Ingredients Section - COLLAPSIBLE */}
      <div className="recipe-section">
        <h4>Ingredients ({recipe.ingredients.length})</h4>
        <ul className="ingredients-list">
          {displayedIngredients.map((ingredient, index) => (
            <li 
              key={index}
              className={`ingredient ${isMatching(ingredient) ? 'matching' : 'missing'}`}
            >
              {isMatching(ingredient) ? (
                <Check size={16} className="ingredient-icon available" />
              ) : (
                <X size={16} className="ingredient-icon unavailable" />
              )}
              <span>{ingredient}</span>
            </li>
          ))}
        </ul>
        
        {/* Show More/Less Button for Ingredients */}
        {hasMoreIngredients && (
          <button 
            className="show-more-btn"
            onClick={() => setShowAllIngredients(!showAllIngredients)}
          >
            {showAllIngredients ? (
              <>
                <ChevronUp size={16} />
                Show Less
              </>
            ) : (
              <>
                <ChevronDown size={16} />
                Show {hiddenCount} More Ingredient{hiddenCount !== 1 ? 's' : ''}
              </>
            )}
          </button>
        )}
      </div>

      {/* Summary of Ingredient Availability */}
      {recipe.matching_ingredients.length > 0 && (
        <div className="recipe-summary">
          <div className="summary-item">
            <span className="summary-label">You have:</span>
            <span className="summary-value available">
              {recipe.matching_ingredients.length} ingredient{recipe.matching_ingredients.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">You need:</span>
            <span className="summary-value unavailable">
              {recipe.missing_ingredients.length} ingredient{recipe.missing_ingredients.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      )}

      {/* Cooking Instructions Section - COLLAPSIBLE */}
      {recipe.steps && recipe.steps.length > 0 && (
        <div className="recipe-instructions">
          <button 
            className="instructions-toggle"
            onClick={() => setShowInstructions(!showInstructions)}
          >
            <span>Cooking Instructions ({recipe.steps.length} steps)</span>
            {showInstructions ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </button>
          
          {showInstructions && (
            <ol className="instructions-list">
              {recipe.steps.map((step, index) => (
                <li key={index} className="instruction-step">
                  <span className="step-number">{index + 1}</span>
                  <span className="step-text">{step}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
};

export default RecipeCard;