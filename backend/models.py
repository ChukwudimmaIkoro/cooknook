
"""
models.py - Data Models and Schema Definitions

This module defines the Pydantic models used throughout the application.
Pydantic provides data validation, serialization, and clear API contracts.

Key Models:
- Recipe: Represents a single recipe from the dataset
- SearchRequest: Defines the structure of search queries from users
- SearchResponse: Defines the structure of search results returned to users
"""

from pydantic import BaseModel
from typing import List, Optional


#Recipe model for representing a single recipe from the dataset
class Recipe(BaseModel):
    """
    Represents a single recipe from the dataset.
    
    Attributes:
        id (int): Unique identifier for the recipe
        name (str): Recipe name/title (e.g., "Classic Spaghetti Carbonara")
        cuisine (str): Type of cuisine (e.g., 'indian', 'italian', 'mexican')
        ingredients (List[str]): List of ingredient names required for the recipe
        steps (Optional[List[str]]): Step-by-step cooking instructions
        minutes (Optional[int]): Preparation and cooking time in minutes
        n_steps (Optional[int]): Number of steps in the recipe
        n_ingredients (Optional[int]): Number of ingredients (for reference)
        description (Optional[str]): Brief description of the recipe
    
    Example:
        {
            "id": 137739,
            "name": "Arriba Baked Winter Squash Mexican Style",
            "cuisine": "mexican",
            "ingredients": ["winter squash", "mexican seasoning", "mixed spice"],
            "steps": ["Preheat oven to 350°F", "Cut squash in half", "Bake for 45 minutes"],
            "minutes": 55,
            "n_steps": 3,
            "n_ingredients": 7,
            "description": "A delicious Mexican-inspired squash dish"
        }
    """
    id: int
    name: str
    cuisine: str
    ingredients: List[str]
    steps: Optional[List[str]] = None
    minutes: Optional[int] = None
    n_steps: Optional[int] = None
    n_ingredients: Optional[int] = None
    description: Optional[str] = None


#Search request model for searching recipes
class SearchRequest(BaseModel):
    """
    Defines the structure of a search request from the user.
    
    This model validates and structures the search parameters that users
    can provide to find recipes matching their preferences.
    
    Attributes:
        query (Optional[str]): Natural language search query
            Examples: "quick dinner", "spicy food", "healthy lunch"
            Default: empty string
        
        ingredients (Optional[List[str]]): List of ingredients the user has available
            The search engine will prioritize recipes using these ingredients
            Default: empty list
        
        cuisine (Optional[str]): Filter results to a specific cuisine type
            Must match one of the cuisines in the dataset
            Default: None (no filtering)
        
        max_time (Optional[int]): Maximum cooking time in minutes
            Filters recipes that can be made within this time
            Default: None (no time filtering)
        
        max_results (int): Maximum number of recipes to return
            Default: 10
    
    Example:
        {
            "query": "spicy dinner",
            "ingredients": ["chicken", "rice", "tomatoes"],
            "cuisine": "indian",
            "max_time": 60,
            "max_results": 5
        }
    """
    query: Optional[str] = ""
    ingredients: Optional[List[str]] = []
    cuisine: Optional[str] = None
    max_time: Optional[int] = None
    max_results: int = 10


#Search response model for returning search results
class SearchResponse(BaseModel):
    """
    Defines the structure of a single search result returned to the user.
    
    Each search result includes the recipe details plus additional metadata
    about how well it matches the user's query and available ingredients.
    
    Attributes:
        id (int): Unique identifier for the recipe
        
        name (str): Recipe name/title
        
        cuisine (str): Type of cuisine
        
        ingredients (List[str]): Complete list of ingredients needed
        
        similarity_score (float): Semantic similarity score (0.0 to 1.0)
            Higher scores indicate better matches to the user's query
            Calculated using cosine similarity between embeddings
        
        matching_ingredients (List[str]): Ingredients the user has that are in this recipe
            Useful for showing the user what they already have
        
        missing_ingredients (List[str]): Ingredients needed that the user doesn't have
            Helps users understand what they need to buy/obtain
        
        steps (Optional[List[str]]): Step-by-step cooking instructions
        
        minutes (Optional[int]): Preparation and cooking time in minutes
        
        n_steps (Optional[int]): Number of steps in the recipe
        
        description (Optional[str]): Brief description of the recipe
    
    Example:
        {
            "id": 137739,
            "name": "Arriba Baked Winter Squash Mexican Style",
            "cuisine": "mexican",
            "ingredients": ["winter squash", "mexican seasoning", "mixed spice"],
            "similarity_score": 0.87,
            "matching_ingredients": ["winter squash"],
            "missing_ingredients": ["mexican seasoning", "mixed spice"],
            "steps": ["Preheat oven to 350°F", "Cut squash in half", "Bake 45 min"],
            "minutes": 55,
            "n_steps": 3,
            "description": "A delicious Mexican-inspired squash dish"
        }
    """
    id: int
    name: str
    cuisine: str
    ingredients: List[str]
    similarity_score: float
    matching_ingredients: List[str]
    missing_ingredients: List[str]
    steps: Optional[List[str]] = None
    minutes: Optional[int] = None
    n_steps: Optional[int] = None
    description: Optional[str] = None