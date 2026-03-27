/**
 * Handles communication with Python FastAPI backend.
 * Makes API calls without cluttered fetch logic.
 * Error handling, request/response transformation, and type documentation.
 */

import axios from 'axios';

//TODO: Run on different port later?
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

//Create axios instance to handle requests and responses
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // First search slow due to long load, fix?
  timeout: 30000,
});

//Response interceptor for global error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Log error for debugging and display to user
    console.error('API Error:', error.response?.data || error.message);
    
    // Throw a more user-friendly error message to display to user
    const message = error.response?.data?.detail || 
                   error.message || 
                   'An unexpected error occurred';
    throw new Error(message);
  }
);

//Check API status
export const checkHealth = async () => {
  //TODO: Change to cloud server later
  const response = await apiClient.get('/');
  return response.data;
};


//Search for recipes based on user preferences and returns ranked results
export const searchRecipes = async ({
  query = '',
  ingredients = [],
  cuisine = null,
  maxTime = null,
  maxResults = 10,
}) => {
  //Create request body, using snake_case for Python backend compatibility
  const requestBody = {
    query,
    ingredients,
    cuisine,
    max_time: maxTime,
    max_results: maxResults,
  };

  //POST request to /search endpoint
  const response = await apiClient.post('/search', requestBody);
  
  //Return the recipe array from response
  return response.data;
};


//Return list of all available cuisines in the dataset
export const getCuisines = async () => {
  const response = await apiClient.get('/cuisines');
  return response.data;
};

//Returns recipe dataset stats, like total recipes, cuisines, and ingredients
export const getStats = async () => {
  const response = await apiClient.get('/stats');
  return response.data;
};

//Helper function to parse ingredient input
//Split by comma, remove whitespace, and remove empty strings
export const parseIngredients = (ingredientsString) => {
  if (!ingredientsString || ingredientsString.trim() === '') {
    return [];
  }
  
  return ingredientsString.split(',').map(ing => ing.trim()).filter(ing => ing.length > 0); 
};

// ============================================================================
// PANTRY API
// ============================================================================

export const getPantryItems = async (token) => {
  const response = await apiClient.get('/pantry/items', {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const addPantryItem = async (token, itemData) => {
  const response = await apiClient.post('/pantry/items', itemData, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const updatePantryItem = async (token, itemId, updates) => {
  const response = await apiClient.put(`/pantry/items/${itemId}`, updates, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const deletePantryItem = async (token, itemId) => {
  const response = await apiClient.delete(`/pantry/items/${itemId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const searchByPantry = async (token, maxResults = 10) => {
  const response = await apiClient.post(
    '/pantry/search',
    { max_results: maxResults },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.data;
};

// ============================================================================
// NOTIFICATIONS API
// ============================================================================

export const getNotifications = async (token) => {
  const response = await apiClient.get('/notifications', {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const markNotificationRead = async (token, notificationId) => {
  const response = await apiClient.put(`/notifications/${notificationId}/read`, {}, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const markAllNotificationsRead = async (token) => {
  const response = await apiClient.post('/notifications/read-all', {}, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const dismissNotification = async (token, notificationId) => {
  const response = await apiClient.delete(`/notifications/${notificationId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export default apiClient;