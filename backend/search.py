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


class RecipeSearchEngine:
    """
    Main search engine class that handles recipe recommendations.
    
    This class loads recipes, generates embeddings, and provides search functionality
    using semantic similarity rather than simple keyword matching.
    """
    
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
        
        # Try to use GPU if available for much faster embedding generation
        # This can speed up processing by 10-50x depending on GPU
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {device}")
        
        self.model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
        
        # Step 3: Generate or load cached embeddings
        # Embeddings are expensive to compute but can be cached to disk
        print("Loading or generating embeddings...")
        self.recipe_embeddings = self._load_or_generate_embeddings(recipes_path)
        print("Search engine ready!")
    
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
        # batch_size can be increased for faster processing on GPU (default: 32)
        embeddings = self.model.encode(
            recipe_texts, 
            show_progress_bar=True,
            batch_size=128  # Increased from default 32 for faster processing
        )
        
        return embeddings
    
    def _get_embeddings_cache_path(self, recipes_path: str) -> str:
        """
        Get the path where embeddings should be cached.
        
        Embeddings are saved alongside the recipes.json file
        with a .npy extension for numpy arrays.
        
        Args:
            recipes_path (str): Path to recipes.json
        
        Returns:
            str: Path to embeddings cache file
        
        Example:
            recipes_path = "../data/recipes.json"
            returns: "../data/recipes_embeddings.npy"
        """
        import os
        base_path = os.path.splitext(recipes_path)[0]
        return f"{base_path}_embeddings.npy"
    
    def _load_or_generate_embeddings(self, recipes_path: str) -> np.ndarray:
        """
        Load embeddings from cache or generate them if cache doesn't exist.
        
        This dramatically speeds up subsequent server startups by avoiding
        re-computation of embeddings. The cache is invalidated if the
        recipes file is newer than the cache file.
        
        Args:
            recipes_path (str): Path to recipes.json file
        
        Returns:
            np.ndarray: Recipe embeddings matrix
        
        Cache Strategy:
            - Check if embeddings cache file exists
            - Check if cache is newer than recipes file (not stale)
            - Check if cache has correct number of embeddings
            - If all checks pass, load from cache
            - Otherwise, generate new embeddings and save to cache
        """
        import os
        
        cache_path = self._get_embeddings_cache_path(recipes_path)
        
        # Check if cache exists and is valid
        if os.path.exists(cache_path):
            print(f"Found embeddings cache at {cache_path}")
            
            # Check if cache is newer than recipes file (not stale)
            cache_mtime = os.path.getmtime(cache_path)
            recipes_mtime = os.path.getmtime(recipes_path)
            
            if cache_mtime > recipes_mtime:
                print("Loading embeddings from cache...")
                try:
                    embeddings = np.load(cache_path)
                    
                    # Verify cache has correct number of embeddings
                    if len(embeddings) == len(self.recipes):
                        print(f"Successfully loaded {len(embeddings)} embeddings from cache")
                        return embeddings
                    else:
                        print(f"Cache size mismatch: {len(embeddings)} vs {len(self.recipes)} recipes")
                        print("Regenerating embeddings...")
                except Exception as e:
                    print(f"Error loading cache: {e}")
                    print("Regenerating embeddings...")
            else:
                print("Cache is outdated (recipes file is newer)")
                print("Regenerating embeddings...")
        else:
            print("No embeddings cache found")
        
        # Generate new embeddings
        print("Generating embeddings for all recipes...")
        embeddings = self._generate_recipe_embeddings()
        
        # Save to cache for next time
        print(f"Saving embeddings to cache: {cache_path}")
        try:
            np.save(cache_path, embeddings)
            print("Embeddings cached successfully!")
        except Exception as e:
            print(f"Warning: Could not save embeddings cache: {e}")
            print("Embeddings will need to be regenerated on next startup")
        
        return embeddings
    
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