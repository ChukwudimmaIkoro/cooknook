/**
 * api.js - API Service Layer
 * 
 * This module handles all communication with the Python FastAPI backend.
 * It provides a clean interface for making API calls without cluttering
 * component code with fetch logic.
 * 
 * Key Features:
 * - Centralized API configuration
 * - Error handling
 * - Request/response transformation
 * - Type documentation via JSDoc
 */

import axios from 'axios';

/**
 * Base URL for the API backend
 * Update this if your backend runs on a different host/port
 * Default: http://localhost:8000
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Create an axios instance with default configuration
 * This allows us to set common headers and handle errors globally
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Timeout after 30 seconds (first search can be slow due to model warmup)
  timeout: 30000,
});

/**
 * Add a response interceptor for global error handling
 * This catches network errors and API errors in one place
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Log error for debugging
    console.error('API Error:', error.response?.data || error.message);
    
    // Throw a more user-friendly error message
    const message = error.response?.data?.detail || 
                   error.message || 
                   'An unexpected error occurred';
    throw new Error(message);
  }
);

/**
 * Check if the backend API is healthy and responding
 * 
 * This is useful for:
 * - Verifying backend is running
 * - Displaying connection status in UI
 * - Debugging connection issues
 * 
 * @returns {Promise<Object>} Server status information
 * @throws {Error} If server is unreachable or unhealthy
 * 
 * @example
 * const status = await checkHealth();
 * console.log(`Server has ${status.total_recipes} recipes`);
 */
export const checkHealth = async () => {
  const response = await apiClient.get('/');
  return response.data;
};

/**
 * Search for recipes based on user preferences
 * 
 * This is the main API call that powers the recipe recommendation engine.
 * It sends user preferences to the backend and receives ranked recipe results.
 * 
 * @param {Object} searchParams - Search parameters
 * @param {string} [searchParams.query=''] - Natural language query (e.g., "quick dinner")
 * @param {string[]} [searchParams.ingredients=[]] - List of available ingredients
 * @param {string} [searchParams.cuisine=null] - Filter by cuisine type (e.g., "italian")
 * @param {number} [searchParams.maxTime=null] - Maximum cooking time in minutes
 * @param {number} [searchParams.maxResults=10] - Maximum number of results to return
 * 
 * @returns {Promise<Object[]>} Array of recipe results with similarity scores
 * @throws {Error} If search fails or backend is unavailable
 * 
 * @example
 * const results = await searchRecipes({
 *   query: "spicy dinner",
 *   ingredients: ["chicken", "rice"],
 *   cuisine: "indian",
 *   maxTime: 60,
 *   maxResults: 5
 * });
 * 
 * Response format:
 * [
 *   {
 *     id: 137739,
 *     name: "Classic Spaghetti Carbonara",
 *     cuisine: "italian",
 *     ingredients: ["pasta", "eggs", "bacon", "parmesan"],
 *     similarity_score: 0.89,
 *     matching_ingredients: ["eggs"],
 *     missing_ingredients: ["pasta", "bacon", "parmesan"],
 *     minutes: 30,
 *     n_steps: 8,
 *     description: "A classic Italian pasta dish..."
 *   },
 *   ...
 * ]
 */
export const searchRecipes = async ({
  query = '',
  ingredients = [],
  cuisine = null,
  maxTime = null,
  maxResults = 10,
}) => {
  // Construct request body
  // Note: We use snake_case for backend compatibility (Python convention)
  const requestBody = {
    query,
    ingredients,
    cuisine,
    max_time: maxTime,
    max_results: maxResults,
  };

  // Make POST request to search endpoint
  const response = await apiClient.post('/search', requestBody);
  
  // Return the recipe array from response
  return response.data;
};

/**
 * Get list of all available cuisines in the dataset
 * 
 * Useful for:
 * - Populating cuisine filter dropdown
 * - Showing users what options are available
 * - Autocomplete functionality
 * 
 * @returns {Promise<string[]>} Sorted array of cuisine names
 * @throws {Error} If request fails
 * 
 * @example
 * const cuisines = await getCuisines();
 * // ["brazilian", "chinese", "french", "indian", "italian", ...]
 */
export const getCuisines = async () => {
  const response = await apiClient.get('/cuisines');
  return response.data.cuisines;
};

/**
 * Get statistical information about the recipe dataset
 * 
 * Provides insights into:
 * - Total number of recipes
 * - Number of cuisines
 * - Distribution of recipes across cuisines
 * - Unique ingredient count
 * 
 * @returns {Promise<Object>} Dataset statistics
 * @throws {Error} If request fails
 * 
 * @example
 * const stats = await getStats();
 * console.log(`Dataset contains ${stats.total_recipes} recipes`);
 * console.log(`Top cuisine: ${Object.keys(stats.cuisine_distribution)[0]}`);
 * 
 * Response format:
 * {
 *   total_recipes: 39774,
 *   total_cuisines: 20,
 *   cuisine_distribution: { italian: 7838, mexican: 6438, ... },
 *   unique_ingredients: 6714
 * }
 */
export const getStats = async () => {
  const response = await apiClient.get('/stats');
  return response.data;
};

/**
 * Helper function to parse ingredient input
 * Converts comma-separated string to array of trimmed ingredients
 * 
 * @param {string} ingredientsString - Comma-separated ingredients
 * @returns {string[]} Array of ingredient names
 * 
 * @example
 * parseIngredients("tomatoes, onions, garlic")
 * // Returns: ["tomatoes", "onions", "garlic"]
 * 
 * parseIngredients("  chicken  ,  rice  ")
 * // Returns: ["chicken", "rice"]
 */
export const parseIngredients = (ingredientsString) => {
  if (!ingredientsString || ingredientsString.trim() === '') {
    return [];
  }
  
  return ingredientsString
    .split(',')                    // Split by comma
    .map(ing => ing.trim())        // Remove whitespace from each ingredient
    .filter(ing => ing.length > 0); // Remove empty strings
};

// Export the API client for advanced use cases
export default apiClient;