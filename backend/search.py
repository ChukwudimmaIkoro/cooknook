"""
search.py - Recipe Search Engine Core Logic

This module implements the main search engine using semantic similarity
via sentence transformers. It converts recipes and user queries into
vector embeddings and finds the most similar recipes.

Key Concepts:
- Embeddings: Dense vector representations that capture semantic meaning
- Cosine Similarity: Measures how similar two vectors are (0 to 1)
- Sentence Transformers: Pre-trained models that convert text to embeddings

Process Flow:
1. Load recipes from JSON file
2. Convert each recipe to text representation
3. Generate embeddings for all recipes (done once at startup)
4. For each search:
   - Convert user query to embedding
   - Calculate similarity with all recipe embeddings
   - Return top matches with additional metadata
"""

import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple
from models import Recipe, SearchRequest, SearchResponse


#Recipe search engine class for searching recipes based on user query and preferences
class RecipeSearchEngine:
    """
    Main search engine class that handles recipe recommendations.
    
    This class loads recipes, generates embeddings, and provides search functionality
    using semantic similarity rather than simple keyword matching.
    """
    #Function to initialize the search engine with recipe data and ML model
    def __init__(self, recipes_path: str):
        """
        Initialize the search engine with recipe data and ML model.
        
        This is called once when the FastAPI server starts up. It performs
        the expensive operations (loading model, generating embeddings) so
        that subsequent searches are fast.
        
        Args:
            recipes_path (str): Path to the JSON file containing recipe data
        
        Raises:
            FileNotFoundError: If recipes file doesn't exist
            json.JSONDecodeError: If recipes file is not valid JSON
        """
        # Step 1: Load recipe data from JSON file
        print("Loading recipes...")
        with open(recipes_path, 'r') as f:
            data = json.load(f)
            # Convert raw JSON data to Recipe objects for type safety and validation
            self.recipes = [Recipe(**recipe) for recipe in data]
        
        print(f"Loaded {len(self.recipes)} recipes")
        
        # Step 2: Load the pre-trained sentence transformer model
        # 'all-MiniLM-L6-v2' is a lightweight model that:
        # - Produces 384-dimensional embeddings
        # - Balances speed and quality
        # - Works well for semantic similarity tasks
        print("Loading sentence transformer model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Step 3: Generate embeddings for all recipes
        # This is done once at startup and stored in memory for fast searches
        print("Generating embeddings for all recipes...")
        self.recipe_embeddings = self._generate_recipe_embeddings()
        print("Search engine ready!")
    
    #Function to convert a recipe object to a text representation for embedding
    def _create_recipe_text(self, recipe: Recipe) -> str:
        """
        Convert a recipe object to a text representation for embedding.
        
        The quality of text representation significantly impacts search quality.
        We combine recipe name, cuisine type, and ingredients into a natural 
        language format that the sentence transformer can process effectively.
        
        Including the recipe name improves semantic matching since it often
        contains descriptive terms about the dish's style, flavor, or origin.
        
        Args:
            recipe (Recipe): Recipe object to convert
        
        Returns:
            str: Text representation of the recipe
        
        Example:
            Input: Recipe(
                name="Classic Spaghetti Carbonara",
                cuisine="italian", 
                ingredients=["pasta", "eggs", "bacon"]
            )
            Output: "Classic Spaghetti Carbonara - italian cuisine with ingredients: pasta, eggs, bacon"
        """
        ingredients_text = ", ".join(recipe.ingredients)
        return f"{recipe.name} - {recipe.cuisine} cuisine with ingredients: {ingredients_text}"
    
    #Function to generate vector embeddings for all recipes in the dataset
    def _generate_recipe_embeddings(self) -> np.ndarray:
        """
        Generate vector embeddings for all recipes in the dataset.
        
        This method:
        1. Converts each recipe to text using _create_recipe_text()
        2. Passes all texts through the sentence transformer model
        3. Returns a matrix where each row is one recipe's embedding
        
        The resulting embeddings capture semantic meaning, so similar recipes
        (by cuisine or ingredients) will have similar vectors.
        
        Returns:
            np.ndarray: Matrix of shape (num_recipes, embedding_dim)
                       where embedding_dim is 384 for our model
        
        Performance Note:
            This can take 30-60 seconds for large datasets but only runs once
        """
        # Convert all recipes to text format
        recipe_texts = [self._create_recipe_text(recipe) for recipe in self.recipes]
        
        # Generate embeddings using the model
        # show_progress_bar=True displays progress during the operation
        embeddings = self.model.encode(recipe_texts, show_progress_bar=True)
        
        return embeddings
    
    #Function to calculate which ingredients match and which are missing
    def _calculate_ingredient_overlap(
        self, 
        user_ingredients: List[str], 
        recipe_ingredients: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Calculate which ingredients match and which are missing.
        
        This helps users understand:
        1. What ingredients they already have (matching)
        2. What they need to obtain (missing)
        
        Args:
            user_ingredients (List[str]): Ingredients the user has available
            recipe_ingredients (List[str]): Ingredients required by the recipe
        
        Returns:
            Tuple[List[str], List[str]]: (matching_ingredients, missing_ingredients)
        
        Example:
            user_ingredients = ["tomatoes", "onions", "garlic"]
            recipe_ingredients = ["tomatoes", "spinach", "onions", "cream"]
            Returns: (["tomatoes", "onions"], ["spinach", "cream"])
        
        Note:
            Comparison is case-insensitive and whitespace is stripped for robustness
        """
        # Convert to sets for efficient intersection/difference operations
        # Normalize to lowercase and strip whitespace for better matching
        user_set = set(ing.lower().strip() for ing in user_ingredients)
        recipe_set = set(ing.lower().strip() for ing in recipe_ingredients)
        
        # Find ingredients that appear in both sets
        matching = list(user_set.intersection(recipe_set))
        
        # Find ingredients in recipe but not available to user
        missing = list(recipe_set.difference(user_set))
        
        return matching, missing
    
    #Function to search for recipes matching the user's preferences
    def search(self, request: SearchRequest) -> List[SearchResponse]:
        """
        Search for recipes matching the user's preferences.
        
        This is the main search method that:
        1. Builds a query from user input
        2. Converts query to an embedding
        3. Finds most similar recipes using cosine similarity
        4. Applies filters (cuisine, time, etc.)
        5. Calculates ingredient overlap
        6. Returns ranked results
        
        Args:
            request (SearchRequest): User's search parameters including:
                - query: Natural language description
                - ingredients: Available ingredients
                - cuisine: Optional cuisine filter
                - max_time: Optional maximum cooking time filter
                - max_results: Number of results to return
        
        Returns:
            List[SearchResponse]: Ranked list of matching recipes with metadata
        
        Algorithm:
            1. Combine all search parameters into a single query text
            2. Generate embedding for the query
            3. Calculate cosine similarity between query and all recipes
            4. Sort by similarity (highest first)
            5. Apply filters (cuisine, time) and calculate ingredient overlap
            6. Return top N results
        """
        # Step 1: Build query text from user input
        # We combine multiple signals into a single text representation
        query_parts = []
        
        # Add natural language query if provided
        if request.query:
            query_parts.append(request.query)
        
        # Add ingredients the user has
        if request.ingredients:
            query_parts.append(f"ingredients: {', '.join(request.ingredients)}")
        
        # Add cuisine preference if specified
        if request.cuisine:
            query_parts.append(f"{request.cuisine} cuisine")
        
        # Add time preference if specified
        if request.max_time:
            query_parts.append(f"quick recipe under {request.max_time} minutes")
        
        # Combine all parts, or use default if nothing provided
        query_text = " ".join(query_parts) if query_parts else "general recipe"
        
        # Step 2: Generate embedding for the query
        # The model expects a list, so we wrap the query in brackets
        query_embedding = self.model.encode([query_text])
        
        # Step 3: Calculate similarity between query and all recipes
        # cosine_similarity returns a matrix; we get the first (and only) row
        # Values range from -1 to 1, but for text are typically 0 to 1
        similarities = cosine_similarity(query_embedding, self.recipe_embeddings)[0]
        
        # Step 4: Get indices of recipes sorted by similarity (highest first)
        # argsort() returns indices that would sort the array
        # [::-1] reverses to get descending order
        top_indices = np.argsort(similarities)[::-1]
        
        # Step 5: Build result list with filtering and metadata
        results = []
        for idx in top_indices:
            recipe = self.recipes[idx]
            
            # Apply cuisine filter if specified
            # Skip this recipe if it doesn't match the requested cuisine
            if request.cuisine and recipe.cuisine.lower() != request.cuisine.lower():
                continue
            
            # Apply time filter if specified
            # Skip recipes that take longer than the requested max time
            if request.max_time and recipe.minutes:
                if recipe.minutes > request.max_time:
                    continue
            
            # Calculate ingredient overlap if user provided ingredients
            # This shows what they have vs. what they need
            matching_ings = []
            missing_ings = []
            if request.ingredients:
                matching_ings, missing_ings = self._calculate_ingredient_overlap(
                    request.ingredients, 
                    recipe.ingredients
                )
            
            # Create response object with all relevant information
            results.append(SearchResponse(
                id=recipe.id,
                name=recipe.name,  # NEW: Include recipe name
                cuisine=recipe.cuisine,
                ingredients=recipe.ingredients,
                similarity_score=float(similarities[idx]),  # Convert numpy float to Python float
                matching_ingredients=matching_ings,
                missing_ingredients=missing_ings,
                steps=recipe.steps,  # NEW: Include cooking instructions
                minutes=recipe.minutes,  # NEW: Include cooking time
                n_steps=recipe.n_steps,  # NEW: Include step count
                description=recipe.description  # NEW: Include description
            ))
            
            # Stop once we have enough results
            if len(results) >= request.max_results:
                break
        
        return results