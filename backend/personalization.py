"""
personalization.py - User Preference Learning and Recipe Personalization

This module analyzes user search history to learn preferences and personalize
recipe recommendations. Uses simple but effective heuristics combined with
search history patterns.

Key Features:
- Analyze search history to extract preferences
- Build user preference profiles
- Score recipes based on learned preferences
- Generate personalized recommendations
"""

from typing import List, Dict, Optional, Tuple
from collections import Counter
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import User, SearchHistory
from models import SearchResponse
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# USER PROFILE DATA STRUCTURES
# ============================================================================

class UserPreferences:
    """
    Represents a user's learned preferences from their search history.
    
    This class aggregates patterns from search history to understand what
    a user typically searches for and prefers.
    """
    
    def __init__(
        self,
        user_id: int,
        favorite_cuisines: List[Tuple[str, int]],
        favorite_ingredients: List[Tuple[str, int]],
        avg_time_preference: Optional[float],
        total_searches: int,
        recent_searches: int
    ):
        """
        Initialize user preferences.
        
        Args:
            user_id: User's database ID
            favorite_cuisines: List of (cuisine, count) tuples, sorted by frequency
            favorite_ingredients: List of (ingredient, count) tuples, sorted by frequency
            avg_time_preference: Average max_time from searches (None if not set)
            total_searches: Total number of searches in history
            recent_searches: Number of searches in last 30 days
        """
        self.user_id = user_id
        self.favorite_cuisines = favorite_cuisines
        self.favorite_ingredients = favorite_ingredients
        self.avg_time_preference = avg_time_preference
        self.total_searches = total_searches
        self.recent_searches = recent_searches
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "user_id": self.user_id,
            "favorite_cuisines": [
                {"cuisine": c, "count": count} 
                for c, count in self.favorite_cuisines[:5]
            ],
            "favorite_ingredients": [
                {"ingredient": ing, "count": count} 
                for ing, count in self.favorite_ingredients[:10]
            ],
            "avg_time_preference": self.avg_time_preference,
            "total_searches": self.total_searches,
            "recent_searches": self.recent_searches
        }


# ============================================================================
# PREFERENCE ANALYSIS
# ============================================================================

def analyze_user_preferences(user_id: int, db: Session) -> UserPreferences:
    """
    Analyze user's search history to extract preferences.
    
    This function looks at all searches a user has made and identifies patterns:
    - Which cuisines they search for most often
    - Which ingredients they commonly look for
    - Their typical time constraints
    - How active they are (recent vs total searches)
    
    Args:
        user_id: User's database ID
        db: Database session
    
    Returns:
        UserPreferences object with learned preferences
    
    Algorithm:
        1. Fetch all user's search history from database
        2. Count frequency of each cuisine searched
        3. Count frequency of each ingredient searched
        4. Calculate average time constraint (if any)
        5. Count recent searches (last 30 days) for activity level
        6. Return aggregated preferences
    """
    # Fetch all search history for this user
    history = db.query(SearchHistory).filter(
        SearchHistory.user_id == user_id
    ).order_by(
        SearchHistory.timestamp.desc()
    ).all()
    
    total_searches = len(history)
    
    if total_searches == 0:
        # New user with no history - return empty preferences
        logger.info(f"No search history for user {user_id}")
        return UserPreferences(
            user_id=user_id,
            favorite_cuisines=[],
            favorite_ingredients=[],
            avg_time_preference=None,
            total_searches=0,
            recent_searches=0
        )
    
    # Count cuisine preferences
    cuisines = [h.cuisine for h in history if h.cuisine]
    cuisine_counter = Counter(cuisines)
    favorite_cuisines = cuisine_counter.most_common(10)  # Top 10 cuisines
    
    # Also analyze query text to find food-related keywords
    # This helps when users don't use cuisine filters
    query_words = []
    for h in history:
        if h.query:
            # Extract words from queries (simple tokenization)
            words = h.query.lower().split()
            # Filter out very common words
            stopwords = {'the', 'a', 'an', 'with', 'for', 'quick', 'easy', 'simple', 'best', 'good'}
            query_words.extend([w for w in words if w not in stopwords and len(w) > 2])
    
    # Count ingredient preferences
    all_ingredients = []
    for h in history:
        if h.ingredients:
            # Split comma-separated ingredients
            ingredients = [ing.strip() for ing in h.ingredients.split(',')]
            all_ingredients.extend(ingredients)
    
    # Add query words to ingredients (they're food-related terms)
    all_ingredients.extend(query_words)
    
    ingredient_counter = Counter(all_ingredients)
    favorite_ingredients = ingredient_counter.most_common(20)  # Top 20 ingredients
    
    # Calculate average time preference
    times = [h.max_time for h in history if h.max_time]
    avg_time = sum(times) / len(times) if times else None
    
    # Count recent searches (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_searches = sum(1 for h in history if h.timestamp >= thirty_days_ago)
    
    logger.info(f"Analyzed preferences for user {user_id}: "
                f"{total_searches} total searches, "
                f"{len(favorite_cuisines)} cuisines, "
                f"{len(favorite_ingredients)} ingredients")
    
    return UserPreferences(
        user_id=user_id,
        favorite_cuisines=favorite_cuisines,
        favorite_ingredients=favorite_ingredients,
        avg_time_preference=avg_time,
        total_searches=total_searches,
        recent_searches=recent_searches
    )


# ============================================================================
# PERSONALIZED SCORING
# ============================================================================

def calculate_personalization_boost(
    recipe: SearchResponse,
    preferences: UserPreferences
) -> float:
    """
    Calculate a personalization boost factor for a recipe.
    
    This function determines how much to boost a recipe's score based on
    how well it matches the user's learned preferences.
    
    Args:
        recipe: Recipe to score
        preferences: User's learned preferences
    
    Returns:
        Boost multiplier (1.0 = no boost, >1.0 = boosted, <1.0 = penalized)
    
    Algorithm:
        Base boost = 1.0
        
        If recipe's cuisine matches favorite cuisine:
            boost *= 1.3 (for top favorite)
            boost *= 1.2 (for 2nd-3rd favorites)
            boost *= 1.1 (for 4th-5th favorites)
        
        For each matching ingredient:
            boost *= 1.05 per common ingredient (up to 10 ingredients)
        
        If cooking time matches preference (within 15 minutes):
            boost *= 1.15
        
        Return final boost
    
    Example:
        - Recipe matches favorite cuisine (italian): boost = 1.3
        - Has 3 favorite ingredients (tomatoes, garlic, basil): boost *= 1.05^3 = 1.158
        - Cooking time is 28 min, avg preference is 30 min: boost *= 1.15
        - Final boost = 1.3 * 1.158 * 1.15 = 1.73x
        - If original score was 0.75, personalized score = 0.75 * 1.73 = 1.30
    """
    boost = 1.0
    
    # No preferences yet - no boost
    if preferences.total_searches == 0:
        return boost
    
    # Cuisine preference boost
    if recipe.cuisine and preferences.favorite_cuisines:
        cuisine_ranks = {cuisine: idx for idx, (cuisine, _) in enumerate(preferences.favorite_cuisines)}
        
        if recipe.cuisine in cuisine_ranks:
            rank = cuisine_ranks[recipe.cuisine]
            if rank == 0:
                boost *= 1.3  # Top favorite cuisine
            elif rank <= 2:
                boost *= 1.2  # 2nd-3rd favorite
            elif rank <= 4:
                boost *= 1.1  # 4th-5th favorite
    
    # Ingredient preference boost
    if preferences.favorite_ingredients:
        favorite_ingredient_names = {ing for ing, _ in preferences.favorite_ingredients}
        recipe_ingredients = set(recipe.ingredients)
        
        # Count how many favorite ingredients are in this recipe
        matching_ingredients = recipe_ingredients & favorite_ingredient_names
        
        # Boost by 5% for each matching ingredient (up to 10)
        ingredient_boost = min(len(matching_ingredients), 10)
        boost *= (1.05 ** ingredient_boost)
    
    # Time preference boost
    if preferences.avg_time_preference and recipe.minutes:
        time_diff = abs(recipe.minutes - preferences.avg_time_preference)
        
        # If within 15 minutes of preferred time, boost
        if time_diff <= 15:
            boost *= 1.15
        # If much longer than preferred (>30 min difference), slight penalty
        elif time_diff > 30:
            boost *= 0.95
    
    return boost


def personalize_search_results(
    results: List[SearchResponse],
    preferences: UserPreferences
) -> List[Dict]:
    """
    Apply personalization to search results.
    
    Takes search results and re-ranks them based on user preferences.
    The original semantic similarity scores are multiplied by personalization
    boost factors to create final personalized scores.
    
    Args:
        results: List of search results from semantic search
        preferences: User's learned preferences
    
    Returns:
        List of results as dicts, re-sorted by personalized scores
    
    Process:
        1. For each recipe in results:
           - Keep original similarity_score
           - Calculate personalization_boost
           - Create personalized_score = similarity_score * boost
        2. Sort by personalized_score (highest first)
        3. Return personalized results
    
    Note:
        Returns dict representations with added personalization fields
        since Pydantic models are immutable.
    """
    # Convert to dicts and add personalized scores
    personalized_results = []
    
    for recipe in results:
        boost = calculate_personalization_boost(recipe, preferences)
        
        # Convert to dict
        recipe_dict = recipe.dict()
        
        # Add personalization fields
        recipe_dict['personalized_score'] = recipe.similarity_score * boost
        recipe_dict['personalization_boost'] = boost
        
        personalized_results.append(recipe_dict)
    
    # Re-sort by personalized score
    personalized_results.sort(
        key=lambda r: r['personalized_score'],
        reverse=True
    )
    
    logger.info(f"Personalized {len(results)} results for user {preferences.user_id}")
    
    return personalized_results


# ============================================================================
# RECOMMENDATION GENERATION
# ============================================================================

def generate_recommendations(
    user_id: int,
    db: Session,
    search_engine,
    limit: int = 10
) -> List[Dict]:
    """
    Generate personalized recipe recommendations for a user.
    
    This creates a "Recommended for You" feed based on learned preferences.
    Instead of requiring a search query, it automatically finds recipes
    that match the user's historical preferences.
    
    Args:
        user_id: User's database ID
        db: Database session
        search_engine: RecipeSearchEngine instance
        limit: Number of recommendations to return
    
    Returns:
        List of recommended recipes as dicts with personalization scores
    
    Algorithm:
        1. Analyze user preferences from history
        2. Build a synthetic search query from preferences:
           - Use most common cuisine
           - Use most common ingredients
           - Use average time preference
        3. Execute search with synthetic query
        4. Apply personalization boost
        5. Return top N results
    
    Example:
        User has searched for:
        - Italian food (20 times)
        - Ingredients: tomatoes (15x), basil (12x), garlic (10x)
        - Average time: 35 minutes
        
        Synthetic query:
        - query: "italian cuisine"
        - ingredients: ["tomatoes", "basil", "garlic"]
        - max_time: 40 (slight buffer)
        
        Execute search → Get results → Personalize → Return top 10
    """
    # Get user preferences
    preferences = analyze_user_preferences(user_id, db)
    
    if preferences.total_searches == 0:
        logger.info(f"No history for user {user_id}, cannot generate recommendations")
        return []
    
    # Build synthetic search from preferences
    from models import SearchRequest
    
    # Build a better query from user's search patterns
    query_parts = []
    
    # Use top cuisine if available
    cuisine_filter = None
    if preferences.favorite_cuisines:
        top_cuisine = preferences.favorite_cuisines[0][0]
        cuisine_filter = top_cuisine
        # Don't just say "italian cuisine" - that's too generic
    
    # Use top ingredients as the main query (these are more specific)
    if preferences.favorite_ingredients:
        # Use top 3 ingredients to build a more specific query
        top_3_ingredients = [ing for ing, _ in preferences.favorite_ingredients[:3]]
        query_parts.extend(top_3_ingredients)
    
    # If we have a cuisine but no ingredients, use cuisine
    if cuisine_filter and not query_parts:
        query_parts.append(cuisine_filter)
    
    # Combine into a search query
    # Example: "pasta tomatoes garlic" instead of "italian cuisine"
    query = " ".join(query_parts) if query_parts else ""
    
    # Use top ingredients for filtering
    ingredients = []
    if preferences.favorite_ingredients:
        ingredients = [ing for ing, _ in preferences.favorite_ingredients[:5]]
    
    # Use time preference with small buffer
    max_time = None
    if preferences.avg_time_preference:
        max_time = int(preferences.avg_time_preference * 1.2)  # 20% buffer
    
    logger.info(f"Recommendation query for user {user_id}: '{query}' (cuisine={cuisine_filter}, ingredients={ingredients[:3]})")
    
    # Create search request
    search_request = SearchRequest(
        query=query,
        ingredients=ingredients,
        cuisine=cuisine_filter,
        max_time=max_time,
        max_results=limit * 2  # Get extra results to personalize
    )
    
    # Execute search
    results = search_engine.search(search_request)
    
    if not results:
        logger.warning(f"No results for recommendation query: {query}")
        return []
    
    # Apply personalization
    personalized_results = personalize_search_results(results, preferences)
    
    # Return top N
    recommendations = personalized_results[:limit]
    
    logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
    
    return recommendations


# ============================================================================
# PREFERENCE UPDATES
# ============================================================================

def update_user_preferences_manual(
    user_id: int,
    db: Session,
    favorite_cuisines: Optional[List[str]] = None,
    dietary_restrictions: Optional[List[str]] = None
) -> bool:
    """
    Manually update user preferences in database.
    
    Allows users to explicitly set preferences instead of relying only
    on learned preferences from search history.
    
    Args:
        user_id: User's database ID
        db: Database session
        favorite_cuisines: List of cuisines user likes
        dietary_restrictions: List of dietary restrictions
    
    Returns:
        True if update successful, False otherwise
    """
    from database import User
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Update cuisines
        if favorite_cuisines is not None:
            user.favorite_cuisines = ",".join(favorite_cuisines)
        
        # Update restrictions
        if dietary_restrictions is not None:
            user.dietary_restrictions = ",".join(dietary_restrictions)
        
        db.commit()
        
        logger.info(f"Updated manual preferences for user {user_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating preferences for user {user_id}: {str(e)}")
        db.rollback()
        return False