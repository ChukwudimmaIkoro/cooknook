"""
main.py - CookNook API Server

AI-powered recipe recommendation engine with user authentication.

Version: 1.3.0
Features:
- Semantic recipe search (230k+ recipes)
- User authentication (JWT)
- Search history tracking
- Personalized recommendations (NEW - Step 4)
"""
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os
import random

# Import project modules
from models import SearchRequest, SearchResponse, Recipe
from models import PantryItemCreate, PantryItemUpdate, PantryItemResponse
from models import NotificationResponse, PantrySearchResult, PantrySearchRequest
from search import RecipeSearchEngine
from database import get_db, User, SearchHistory, PantryItem, Notification

from auth import (
    get_current_user,
    create_user,
    authenticate_user,
    require_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from personalization import (
    analyze_user_preferences,
    personalize_search_results,
    generate_recommendations,
    update_user_preferences_manual,
    UserPreferences
)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOTIFICATION_TEMPLATES = {
    "expiration_single": [
        "{ingredient} expires {when}! Try making: {recipe}",
        "Heads up — your {ingredient} is about to expire. Quick recipe: {recipe}",
        "Use your {ingredient} {when} before it goes bad. How about: {recipe}?",
    ],
    "expiration_multiple": [
        "You have {count} items expiring {when}. Perfect time to cook: {recipe}",
        "{count} pantry items expire {when}! This recipe uses them: {recipe}",
    ],
}

# Background scheduler (started in startup_event)
scheduler = BackgroundScheduler()


# ============================================================================
# PANTRY + NOTIFICATION HELPERS
# ============================================================================

def _days_until_expiration(expiration_date: Optional[datetime]) -> Optional[int]:
    """Return days until expiry, 0 if already expired, None if no date set."""
    if expiration_date is None:
        return None
    now = datetime.now(timezone.utc)
    if expiration_date.tzinfo is None:
        expiration_date = expiration_date.replace(tzinfo=timezone.utc)
    return max((expiration_date - now).days, 0)


def _to_pantry_response(item) -> dict:
    """Convert PantryItem ORM object to response dict with computed fields."""
    return {
        "id": item.id,
        "user_id": item.user_id,
        "ingredient_name": item.ingredient_name,
        "quantity": item.quantity,
        "unit": item.unit,
        "added_date": item.added_date,
        "expiration_date": item.expiration_date,
        "category": item.category,
        "notes": item.notes,
        "days_until_expiration": _days_until_expiration(item.expiration_date),
    }


def _get_expiring_soon(pantry_items, days_threshold: int = 3) -> set:
    """Return set of ingredient names (lowercased) expiring within threshold days."""
    now = datetime.now(timezone.utc)
    expiring = set()
    for item in pantry_items:
        if item.expiration_date is None:
            continue
        exp = item.expiration_date
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if (exp - now).days <= days_threshold:
            expiring.add(item.ingredient_name.lower())
    return expiring


def _normalize(name: str) -> str:
    return name.lower().strip()


def _when_label(days: int) -> str:
    if days <= 0:
        return "today (already expired)"
    if days == 1:
        return "tomorrow"
    return f"in {days} days"


def generate_notifications(user_id: int, db: Session) -> list:
    """
    Rule-based notification generation.
    Called by the background scheduler every 6 hours.
    Returns a list of dicts ready to insert as Notification rows.
    """
    pantry_items = db.query(PantryItem).filter(PantryItem.user_id == user_id).all()
    notifications = []
    now = datetime.now(timezone.utc)

    expiring = []
    for item in pantry_items:
        if item.expiration_date is None:
            continue
        exp = item.expiration_date
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days_left = (exp - now).days
        if days_left <= 2:
            expiring.append((item, days_left))

    if not expiring:
        return []

    # Find a recipe that uses expiring ingredients
    expiring_names = [item.ingredient_name for item, _ in expiring]
    search_query = " ".join(expiring_names[:3])
    recipe_results = search_engine.search(query=search_query, max_results=1) if search_engine else []
    recipe_name = recipe_results[0].name if recipe_results else "something delicious"
    recipe_url  = f"/recipes/{recipe_results[0].id}" if recipe_results else None

    if len(expiring) == 1:
        item, days_left = expiring[0]
        template = random.choice(NOTIFICATION_TEMPLATES["expiration_single"])
        message = template.format(
            ingredient=item.ingredient_name,
            when=_when_label(days_left),
            recipe=recipe_name,
        )
        notifications.append({
            "user_id":    user_id,
            "type":       "expiration",
            "title":      f"{item.ingredient_name} expiring soon",
            "message":    message,
            "action_url": recipe_url,
        })
    else:
        soonest_days = min(d for _, d in expiring)
        template = random.choice(NOTIFICATION_TEMPLATES["expiration_multiple"])
        message = template.format(
            count=len(expiring),
            when=_when_label(soonest_days),
            recipe=recipe_name,
        )
        notifications.append({
            "user_id":    user_id,
            "type":       "expiration",
            "title":      f"{len(expiring)} items expiring soon",
            "message":    message,
            "action_url": recipe_url,
        })

    return notifications


def save_notifications(notifications: list, db: Session):
    """Persist notifications, skipping duplicates (same unread title for same user)."""
    for n in notifications:
        exists = (
            db.query(Notification)
            .filter(
                Notification.user_id == n["user_id"],
                Notification.title   == n["title"],
                Notification.read    == False,
            )
            .first()
        )
        if not exists:
            db.add(Notification(**n))
    db.commit()


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="CookNook API",
    description="AI-powered recipe recommendation engine with user authentication",
    version="1.4.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# SEARCH ENGINE INITIALIZATION
# ============================================================================

# Determine recipes path relative to this file
# Assumes structure: backend/main.py and data/recipes.json
RECIPES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "recipes.json")

# Initialize search engine (will be loaded on startup)
search_engine = None


# ============================================================================
# PYDANTIC MODELS - REQUEST/RESPONSE SCHEMAS
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request schema"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: Optional[str] = Field(None, max_length=100, description="Optional full name")


class UserLoginRequest(BaseModel):
    """User login request schema"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    """User data response schema (no sensitive information)"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    last_active: Optional[datetime]
    favorite_cuisines: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response schema"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    user: UserResponse


class SearchHistoryResponse(BaseModel):
    """Search history entry response schema"""
    id: int
    query: Optional[str]
    ingredients: Optional[str]
    cuisine: Optional[str]
    max_time: Optional[int]
    results_count: int
    timestamp: datetime
    
    class Config:
        from_attributes = True


class UserPreferencesResponse(BaseModel):
    """User preferences response schema"""
    user_id: int
    favorite_cuisines: List[Dict[str, Any]]
    favorite_ingredients: List[Dict[str, Any]]
    avg_time_preference: Optional[float]
    total_searches: int
    recent_searches: int


class ManualPreferencesRequest(BaseModel):
    """Manual preference update request schema"""
    favorite_cuisines: Optional[List[str]] = None
    dietary_restrictions: Optional[List[str]] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def track_search_history(
    db: Session,
    user_id: int,
    request: SearchRequest,
    results: List[SearchResponse]
) -> SearchHistory:
    """
    Track user's search in the database
    
    This function saves search parameters and metadata for later analysis.
    Used to learn user preferences and build personalized recommendations.
    
    Args:
        db: Database session
        user_id: ID of the user performing the search
        request: Search request parameters
        results: Search results returned
    
    Returns:
        SearchHistory: Created search history record
    """
    # Convert ingredients list to comma-separated string for storage
    ingredients_str = None
    if request.ingredients:
        ingredients_str = ",".join(request.ingredients)
    
    # Create search history entry
    history_entry = SearchHistory(
        user_id=user_id,
        query=request.query if request.query else None,
        ingredients=ingredients_str,
        cuisine=request.cuisine,
        max_time=request.max_time,
        results_count=len(results),
        timestamp=datetime.utcnow()
    )
    
    # Save to database
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)
    
    logger.info(f"Tracked search for user {user_id}: '{request.query}' -> {len(results)} results")
    
    return history_entry


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    """
    API health check endpoint
    
    Returns basic API information and status.
    """
    recipe_count = len(search_engine.recipes) if search_engine else 0
    
    return {
        "message": "CookNook API",
        "version": "1.4.0",
        "status": "running",
        "features": ["recipe_search", "user_authentication", "search_history", "personalization", "virtual_pantry", "notifications"],
        "recipe_count": recipe_count
    }


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account
    
    Creates a new user with hashed password and returns JWT token for immediate login.
    
    Args:
        user_data: Registration details (username, email, password, optional full_name)
        db: Database session (injected)
    
    Returns:
        TokenResponse with access token and user information
    
    Raises:
        400: If username or email already exists
        500: If database operation fails
    """
    try:
        # Create user (will raise ValueError if username/email exists)
        new_user = create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
        # Generate access token
        access_token = create_access_token(data={"sub": new_user.username})
        
        logger.info(f"New user registered: {new_user.username} ({new_user.email})")
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.from_orm(new_user)
        )
    
    except ValueError as e:
        # Username or email already exists
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.rollback()  # Rollback any partial changes
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login_user(user_data: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Login with username and password
    
    Authenticates user credentials and returns JWT token.
    
    Args:
        user_data: Login credentials (username, password)
        db: Database session (injected)
    
    Returns:
        TokenResponse with access token and user information
    
    Raises:
        401: If credentials are invalid
    """
    try:
        # Authenticate user
        user = authenticate_user(db, user_data.username, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate access token
        access_token = create_access_token(data={"sub": user.username})
        
        logger.info(f"User logged in: {user.username}")
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user)
        )
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@app.post("/auth/token", response_model=TokenResponse, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint
    
    This endpoint follows the OAuth2 password flow standard.
    Used by Swagger UI for interactive authentication.
    
    Args:
        form_data: OAuth2 form data (username, password)
        db: Database session (injected)
    
    Returns:
        TokenResponse with access token and user information
    
    Raises:
        401: If credentials are invalid
    """
    try:
        # Authenticate user
        user = authenticate_user(db, form_data.username, form_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate access token
        access_token = create_access_token(data={"sub": user.username})
        
        logger.info(f"User logged in (OAuth2): {user.username}")
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth2 login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(current_user: User = Depends(require_user)):
    """
    Get current authenticated user's information
    
    Protected endpoint - requires valid JWT token in Authorization header.
    
    Args:
        current_user: Authenticated user (injected from token)
    
    Returns:
        UserResponse with current user's information
    
    Raises:
        401: If token is missing or invalid
    """
    return UserResponse.from_orm(current_user)


# ============================================================================
# RECIPE SEARCH ENDPOINTS
# ============================================================================

@app.get("/cuisines", response_model=List[str], tags=["Recipes"])
async def get_cuisines():
    """
    Get list of available cuisine types
    
    Returns the list of cuisine categories available for filtering.
    Used to populate the cuisine dropdown in the search form.
    
    Returns:
        List[str]: List of cuisine type strings
    
    Example Response:
        ["italian", "mexican", "chinese", "indian", "american", ...]
    """
    cuisines = [
        "american",
        "asian",
        "cajun_creole",
        "chinese",
        "french",
        "greek",
        "indian",
        "italian",
        "japanese",
        "korean",
        "mediterranean",
        "mexican",
        "middle_eastern",
        "southern_us",
        "thai",
        "vietnamese"
    ]
    return cuisines


@app.post("/search", response_model=List[SearchResponse], tags=["Recipes"])
async def search_recipes(
    request: SearchRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for recipes using semantic AI search
    
    Supports natural language queries, ingredient matching, and filters.
    Authentication is optional - searches are tracked for logged-in users.
    
    Args:
        request: Search parameters (query, ingredients, cuisine, max_time, max_results)
        current_user: Optional authenticated user (injected from token)
        db: Database session (injected)
    
    Returns:
        List[SearchResponse]: List of matching recipes with metadata
    
    Raises:
        500: If search engine fails
    
    Example Request:
        {
            "query": "quick healthy dinner",
            "ingredients": ["chicken", "broccoli"],
            "cuisine": "asian",
            "max_time": 30,
            "max_results": 10
        }
    """
    try:
        # Perform semantic search
        results = search_engine.search(request)
        
        # Log search activity
        user_info = f"user={current_user.username}" if current_user else "anonymous"
        logger.info(f"Search: '{request.query}' ({user_info}) - {len(results)} results")
        
        # Track search history for authenticated users (NEW in Step 3)
        if current_user:
            try:
                track_search_history(
                    db=db,
                    user_id=current_user.id,
                    request=request,
                    results=results
                )
            except Exception as e:
                # Don't fail the search if history tracking fails
                logger.error(f"Failed to track search history: {str(e)}")
        
        return results
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


# ============================================================================
# SEARCH HISTORY ENDPOINTS (NEW - Step 3)
# ============================================================================

@app.get("/history", response_model=List[SearchHistoryResponse], tags=["Search History"])
async def get_search_history(
    limit: int = 20,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get user's search history
    
    Returns recent searches made by the authenticated user.
    Useful for showing "recent searches" in the UI.
    
    Args:
        limit: Maximum number of history entries to return (default: 20)
        current_user: Authenticated user (injected from token)
        db: Database session (injected)
    
    Returns:
        List[SearchHistoryResponse]: List of search history entries
    
    Raises:
        401: If not authenticated
    """
    try:
        # Query search history for this user, ordered by most recent first
        history = db.query(SearchHistory).filter(
            SearchHistory.user_id == current_user.id
        ).order_by(
            SearchHistory.timestamp.desc()
        ).limit(limit).all()
        
        logger.info(f"Retrieved {len(history)} history entries for user {current_user.username}")
        
        return [SearchHistoryResponse.from_orm(entry) for entry in history]
    
    except Exception as e:
        logger.error(f"Error retrieving search history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve search history"
        )


@app.delete("/history/{history_id}", tags=["Search History"])
async def delete_search_history_entry(
    history_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific search history entry
    
    Allows users to remove individual searches from their history.
    
    Args:
        history_id: ID of the history entry to delete
        current_user: Authenticated user (injected from token)
        db: Database session (injected)
    
    Returns:
        Success message
    
    Raises:
        401: If not authenticated
        404: If history entry not found or doesn't belong to user
    """
    try:
        # Find the history entry
        entry = db.query(SearchHistory).filter(
            SearchHistory.id == history_id,
            SearchHistory.user_id == current_user.id  # Ensure user owns this entry
        ).first()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Search history entry not found"
            )
        
        # Delete the entry
        db.delete(entry)
        db.commit()
        
        logger.info(f"Deleted history entry {history_id} for user {current_user.username}")
        
        return {"message": "Search history entry deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting search history: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete search history entry"
        )


@app.delete("/history", tags=["Search History"])
async def clear_search_history(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Clear all search history for the current user
    
    Deletes all search history entries for the authenticated user.
    Useful for privacy or starting fresh.
    
    Args:
        current_user: Authenticated user (injected from token)
        db: Database session (injected)
    
    Returns:
        Success message with count of deleted entries
    
    Raises:
        401: If not authenticated
    """
    try:
        # Delete all history entries for this user
        deleted_count = db.query(SearchHistory).filter(
            SearchHistory.user_id == current_user.id
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleared {deleted_count} history entries for user {current_user.username}")
        
        return {
            "message": "Search history cleared successfully",
            "deleted_count": deleted_count
        }
    
    except Exception as e:
        logger.error(f"Error clearing search history: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear search history"
        )


# ============================================================================
# PERSONALIZATION ENDPOINTS (NEW - Step 4)
# ============================================================================

@app.get("/recommendations", response_model=List[Dict[str, Any]], tags=["Personalization"])
async def get_recommendations(
    limit: int = 10,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized recipe recommendations
    
    Generates a personalized feed of recipes based on the user's search history
    and learned preferences. No search query required - recommendations are
    automatically tailored to the user.
    
    Args:
        limit: Number of recommendations to return (default: 10, max: 50)
        current_user: Authenticated user (injected from token)
        db: Database session (injected)
    
    Returns:
        List[SearchResponse]: Personalized recipe recommendations
    
    Raises:
        401: If not authenticated
        404: If user has no search history yet
    
    Algorithm:
        1. Analyze user's search history to extract preferences
        2. Build synthetic search query from top preferences
        3. Execute semantic search with learned parameters
        4. Apply personalization boost to results
        5. Return top N recommendations
    """
    try:
        # Limit max recommendations
        limit = min(limit, 50)
        
        # Generate recommendations
        recommendations = generate_recommendations(
            user_id=current_user.id,
            db=db,
            search_engine=search_engine,
            limit=limit
        )
        
        if not recommendations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No recommendations available. Try searching for recipes first to build your preference profile."
            )
        
        logger.info(f"Generated {len(recommendations)} recommendations for user {current_user.username}")
        
        return recommendations
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        )


@app.get("/preferences", response_model=UserPreferencesResponse, tags=["Personalization"])
async def get_user_preferences(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get user's learned preferences
    
    Returns an analysis of the user's search history showing what they
    typically search for and prefer. Useful for showing users their
    "taste profile" or allowing them to see what the system has learned.
    
    Args:
        current_user: Authenticated user (injected from token)
        db: Database session (injected)
    
    Returns:
        UserPreferencesResponse: User's learned preferences
    
    Raises:
        401: If not authenticated
    
    Example Response:
        {
            "user_id": 1,
            "favorite_cuisines": [
                {"cuisine": "italian", "count": 15},
                {"cuisine": "mexican", "count": 8}
            ],
            "favorite_ingredients": [
                {"ingredient": "tomatoes", "count": 12},
                {"ingredient": "garlic", "count": 10}
            ],
            "avg_time_preference": 35.5,
            "total_searches": 45,
            "recent_searches": 12
        }
    """
    try:
        preferences = analyze_user_preferences(current_user.id, db)
        
        logger.info(f"Retrieved preferences for user {current_user.username}")
        
        return UserPreferencesResponse(**preferences.to_dict())
    
    except Exception as e:
        logger.error(f"Error retrieving preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences"
        )


@app.put("/preferences", tags=["Personalization"])
async def update_preferences(
    preferences: ManualPreferencesRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Manually update user preferences
    
    Allows users to explicitly set their preferences instead of relying
    only on learned preferences from search history. Useful for new users
    or when users want to override learned preferences.
    
    Args:
        preferences: Manual preference settings
        current_user: Authenticated user (injected from token)
        db: Database session (injected)
    
    Returns:
        Success message
    
    Raises:
        401: If not authenticated
        500: If update fails
    
    Example Request:
        {
            "favorite_cuisines": ["italian", "japanese", "mexican"],
            "dietary_restrictions": ["vegetarian", "gluten-free"]
        }
    """
    try:
        success = update_user_preferences_manual(
            user_id=current_user.id,
            db=db,
            favorite_cuisines=preferences.favorite_cuisines,
            dietary_restrictions=preferences.dietary_restrictions
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update preferences"
            )
        
        logger.info(f"Updated manual preferences for user {current_user.username}")
        
        return {
            "message": "Preferences updated successfully",
            "favorite_cuisines": preferences.favorite_cuisines,
            "dietary_restrictions": preferences.dietary_restrictions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@app.post("/search/personalized", response_model=List[Dict[str, Any]], tags=["Recipes"])
async def search_recipes_personalized(
    request: SearchRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Search for recipes with personalization applied
    
    Same as regular search but results are re-ranked based on the user's
    learned preferences. Recipes matching user preferences are boosted higher.
    
    Args:
        request: Search parameters
        current_user: Authenticated user (injected from token)
        db: Database session (injected)
    
    Returns:
        List[SearchResponse]: Personalized search results
    
    Raises:
        401: If not authenticated
        500: If search fails
    
    Note:
        Results include both:
        - similarity_score: Original semantic match score
        - personalized_score: Boosted score based on preferences
        - personalization_boost: Multiplier applied
    """
    try:
        # Get user preferences FIRST
        preferences = analyze_user_preferences(current_user.id, db)
        
        # Modify the search request to include preferences
        enhanced_request = SearchRequest(
            query=request.query,
            ingredients=request.ingredients,
            cuisine=request.cuisine,
            max_time=request.max_time,
            max_results=request.max_results
        )
        
        # If user has preferences, enhance the query
        if preferences.total_searches > 0:
            # Build enhanced query with preferences
            query_parts = []
            
            # Start with original query
            if request.query:
                query_parts.append(request.query)
            
            # Add top cuisine to query if not already filtered by cuisine
            if preferences.favorite_cuisines and not request.cuisine:
                top_cuisine = preferences.favorite_cuisines[0][0]
                query_parts.append(top_cuisine)
                logger.info(f"Enhanced query with cuisine: {top_cuisine}")
            
            # Add top ingredients to query
            if preferences.favorite_ingredients:
                top_ingredients = [ing for ing, _ in preferences.favorite_ingredients[:2]]
                query_parts.extend(top_ingredients)
                logger.info(f"Enhanced query with ingredients: {top_ingredients}")
            
            # Combine enhanced query
            enhanced_query = " ".join(query_parts)
            enhanced_request = SearchRequest(
                query=enhanced_query,
                ingredients=request.ingredients,
                cuisine=request.cuisine or (preferences.favorite_cuisines[0][0] if preferences.favorite_cuisines else None),
                max_time=request.max_time,
                max_results=request.max_results * 2  # Get more results to re-rank
            )
            
            logger.info(f"Personalized search enhanced: '{request.query}' → '{enhanced_query}'")
        
        # Execute search with enhanced query
        results = search_engine.search(enhanced_request)
        
        # Track search history (track ORIGINAL query, not enhanced)
        try:
            track_search_history(
                db=db,
                user_id=current_user.id,
                request=request,  # Track original query
                results=results
            )
        except Exception as e:
            logger.error(f"Failed to track search history: {str(e)}")
        
        # Apply personalization boost to re-rank results
        personalized_results = personalize_search_results(results, preferences)
        
        # Return requested number of results
        personalized_results = personalized_results[:request.max_results]
        
        logger.info(f"Personalized search: '{request.query}' (user={current_user.username}) - {len(personalized_results)} results")
        
        return personalized_results
    
    except Exception as e:
        logger.error(f"Personalized search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Personalized search failed: {str(e)}"
        )
    
def _days_until_expiration(expiration_date: Optional[datetime]) -> Optional[int]:
    """Return the number of days until an item expires, or None if no date set."""
    if expiration_date is None:
        return None
    now = datetime.now(timezone.utc)
    # Ensure expiration_date is timezone-aware for comparison
    if expiration_date.tzinfo is None:
        expiration_date = expiration_date.replace(tzinfo=timezone.utc)
    delta = expiration_date - now
    return max(delta.days, 0)  # Never return negative; 0 means expired today or past


def _to_pantry_response(item) -> dict:
    """Convert a PantryItem ORM object to a response dict with computed fields."""
    return {
        "id": item.id,
        "user_id": item.user_id,
        "ingredient_name": item.ingredient_name,
        "quantity": item.quantity,
        "unit": item.unit,
        "added_date": item.added_date,
        "expiration_date": item.expiration_date,
        "category": item.category,
        "notes": item.notes,
        "days_until_expiration": _days_until_expiration(item.expiration_date),
    }

def _get_expiring_soon(pantry_items, days_threshold: int = 3) -> set[str]:
    """Return a set of ingredient names expiring within `days_threshold` days."""
    now = datetime.now(timezone.utc)
    expiring = set()
    for item in pantry_items:
        if item.expiration_date is None:
            continue
        exp = item.expiration_date
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if (exp - now).days <= days_threshold:
            expiring.add(item.ingredient_name.lower())
    return expiring
 
 
def _normalize(name: str) -> str:
    """Lowercase + strip for loose ingredient matching."""
    return name.lower().strip()
 
 
def _calculate_pantry_score(
    recipe_ingredients: list[str],
    pantry_set: set[str],
    expiring_soon: set[str],
) -> tuple[float, list[str], list[str], list[str]]:
    """
    Score a recipe by how well the user's pantry covers it.
 
    Returns:
        pantry_score       — final ranking score
        matched            — pantry ingredients the recipe uses
        missing            — recipe ingredients not in pantry
        uses_expiring_soon — matched items that are expiring soon
    """
    if not recipe_ingredients:
        return 0.0, [], [], []
 
    normalized_recipe = [_normalize(i) for i in recipe_ingredients]
 
    matched = [i for i in normalized_recipe if i in pantry_set]
    missing = [i for i in normalized_recipe if i not in pantry_set]
    uses_expiring = [i for i in matched if i in expiring_soon]
 
    # Core coverage: what fraction of the recipe do we already have?
    coverage = len(matched) / len(normalized_recipe)
 
    # Urgency bonus: reward recipes that use soon-to-expire items
    # Each expiring ingredient adds +0.2, capped at +0.6 total
    urgency_bonus = min(len(uses_expiring) * 0.2, 0.6)
 
    # Missing penalty: strongly penalise recipes that need lots of items bought
    # (sqrt softens the curve — needing 1 item isn't that bad)
    missing_ratio = len(missing) / len(normalized_recipe)
    missing_penalty = missing_ratio ** 0.5 * 0.3
 
    pantry_score = coverage + urgency_bonus - missing_penalty
 
    return (
        round(max(pantry_score, 0.0), 4),
        matched,
        missing,
        uses_expiring,
    )
 
 
def _when_label(days: int) -> str:
    if days <= 0:
        return "today (already expired)"
    if days == 1:
        return "tomorrow"
    return f"in {days} days"
 
 
def generate_notifications(user_id: int, db: Session) -> list[dict]:
    """
    Rule-based notification generation. Call this from the background scheduler
    or on-demand. Returns a list of notification dicts ready to insert.
 
    Rules:
      1. Single item expiring within 2 days  → expiration_single
      2. Multiple items expiring within 2 days → expiration_multiple
    """
    from datetime import timezone
 
    pantry_items = db.query(PantryItem).filter(PantryItem.user_id == user_id).all()
    notifications = []
 
    now = datetime.now(timezone.utc)
 
    expiring = []
    for item in pantry_items:
        if item.expiration_date is None:
            continue
        exp = item.expiration_date
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days_left = (exp - now).days
        if days_left <= 2:
            expiring.append((item, days_left))
 
    if not expiring:
        return []
 
    # Find a recipe that uses the expiring ingredient(s)
    expiring_names = [item.ingredient_name for item, _ in expiring]
    search_query = " ".join(expiring_names[:3])
    recipe_results = search_engine.search(query=search_query, max_results=1)
    recipe_name = recipe_results[0].name if recipe_results else "something delicious"
    recipe_url  = f"/recipes/{recipe_results[0].id}" if recipe_results else None
 
    if len(expiring) == 1:
        item, days_left = expiring[0]
        template = random.choice(NOTIFICATION_TEMPLATES["expiration_single"])
        message = template.format(
            ingredient=item.ingredient_name,
            when=_when_label(days_left),
            recipe=recipe_name,
        )
        notifications.append({
            "user_id":    user_id,
            "type":       "expiration",
            "title":      f"{item.ingredient_name} expiring soon",
            "message":    message,
            "action_url": recipe_url,
        })
    else:
        # Group all expiring items; use the soonest days_left for the label
        soonest_days = min(d for _, d in expiring)
        template = random.choice(NOTIFICATION_TEMPLATES["expiration_multiple"])
        message = template.format(
            count=len(expiring),
            when=_when_label(soonest_days),
            recipe=recipe_name,
        )
        notifications.append({
            "user_id":    user_id,
            "type":       "expiration",
            "title":      f"{len(expiring)} items expiring soon",
            "message":    message,
            "action_url": recipe_url,
        })
 
    return notifications
 
 
def save_notifications(notifications: list[dict], db: Session):
    """Persist generated notifications, skipping duplicates by title+user."""
    for n in notifications:
        exists = (
            db.query(Notification)
            .filter(
                Notification.user_id == n["user_id"],
                Notification.title   == n["title"],
                Notification.read    == False,
            )
            .first()
        )
        if not exists:
            db.add(Notification(**n))
    db.commit()
 
 
# ---------------------------------------------------------------
# POST /pantry/search  — Find recipes using pantry ingredients
# ---------------------------------------------------------------
@app.post(
    "/pantry/search",
    response_model=list[PantrySearchResult],
    summary="Find recipes you can make from your pantry",
    tags=["pantry"],
)
def search_recipes_by_pantry(
    request: PantrySearchRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Recommends recipes based on what the user already has in their pantry.
 
    **Scoring**:
    - **Coverage**: fraction of recipe ingredients already in pantry (primary signal)
    - **Urgency bonus**: recipes that use soon-to-expire items ranked higher
    - **Missing penalty**: recipes requiring many missing items ranked lower
 
    Results are sorted by `pantry_score` descending.
    Each result includes `matched_ingredients`, `missing_ingredients`,
    and `uses_expiring_soon` so the frontend can render helpful context.
 
    Returns 400 if the pantry is empty.
    """
    # 1. Load user's pantry
    pantry_items = (
        db.query(PantryItem)
        .filter(PantryItem.user_id == current_user.id)
        .all()
    )
 
    if not pantry_items:
        raise HTTPException(
            status_code=400,
            detail="Your pantry is empty. Add some ingredients first.",
        )
 
    pantry_set = {_normalize(item.ingredient_name) for item in pantry_items}
    expiring_soon = _get_expiring_soon(pantry_items)
 
    # 2. Build search query from pantry contents
    # Use up to 6 ingredients — enough signal without blowing up query length.
    # Prioritise expiring items so the semantic search surfaces relevant recipes.
    expiring_names = [i for i in pantry_set if i in expiring_soon]
    other_names = [i for i in pantry_set if i not in expiring_soon]
    query_ingredients = (expiring_names + other_names)[:6]
    search_query = " ".join(query_ingredients)
 
    # 3. Run semantic search with a larger pool so scoring has room to re-rank
    candidate_pool = min(request.max_results * 5, 100)
    raw_results = search_engine.search(
        query=search_query,
        ingredients=list(pantry_set),
        max_results=candidate_pool,
    )
 
    # 4. Score each candidate against the pantry
    scored = []
    for recipe in raw_results:
        recipe_ingredients = recipe.ingredients if hasattr(recipe, "ingredients") else []
 
        pantry_score, matched, missing, uses_expiring = _calculate_pantry_score(
            recipe_ingredients, pantry_set, expiring_soon
        )
 
        scored.append({
            "id": recipe.id,
            "name": recipe.name,
            "ingredients": recipe_ingredients,
            "cuisine": getattr(recipe, "cuisine", None),
            "minutes": getattr(recipe, "minutes", None),
            "similarity_score": round(recipe.similarity_score, 4),
            "pantry_score": pantry_score,
            "coverage": round(len(matched) / len(recipe_ingredients), 4) if recipe_ingredients else 0.0,
            "matched_ingredients": matched,
            "missing_ingredients": missing,
            "uses_expiring_soon": uses_expiring,
        })
 
    # 5. Sort by pantry_score, return top N
    scored.sort(key=lambda r: r["pantry_score"], reverse=True)
    return scored[: request.max_results]


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================

@app.get(
    "/notifications",
    response_model=List[NotificationResponse],
    summary="Get user's notifications",
    tags=["Notifications"],
)
def get_notifications(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Returns all notifications for the current user — unread first, then newest first."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.read.asc(), Notification.created_at.desc())
        .all()
    )


@app.put(
    "/notifications/{notification_id}/read",
    summary="Mark a notification as read",
    tags=["Notifications"],
)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    db.commit()
    return {"message": "Notification marked as read"}


@app.post(
    "/notifications/read-all",
    summary="Mark all notifications as read",
    tags=["Notifications"],
)
def mark_all_notifications_read(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    unread = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.read == False)
        .all()
    )
    count = len(unread)
    for n in unread:
        n.read = True
    db.commit()
    return {"message": "All notifications marked as read", "marked_count": count}


@app.delete(
    "/notifications/{notification_id}",
    summary="Dismiss a notification",
    tags=["Notifications"],
)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notif)
    db.commit()
    return {"message": "Notification dismissed"}


# ============================================================================
# PANTRY ENDPOINTS
# ============================================================================

# ---------------------------------------------------------------
# POST /pantry/items  — Add an item to the user's pantry
# ---------------------------------------------------------------
@app.post(
    "/pantry/items",
    response_model=PantryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an ingredient to the pantry",
    tags=["pantry"],
)
def add_pantry_item(
    item_data: PantryItemCreate,
    current_user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Add a new ingredient to the authenticated user's virtual pantry.

    - **ingredient_name**: Required. Name of the ingredient (e.g. "chicken breast").
    - **quantity**: Optional. How much (e.g. 2.0).
    - **unit**: Optional. Unit of measure (e.g. "lbs", "cups", "pieces").
    - **expiration_date**: Optional. ISO 8601 datetime. If omitted, no expiry tracking.
    - **category**: Optional. E.g. "produce", "dairy", "meat", "pantry".
    - **notes**: Optional. Free-text notes (e.g. "opened", "back of fridge").

    Returns the created item including its generated `id`, `added_date`,
    and the computed `days_until_expiration` field.
    """
    new_item = PantryItem(
        user_id=current_user.id,
        ingredient_name=item_data.ingredient_name.strip(),
        quantity=item_data.quantity,
        unit=item_data.unit,
        added_date=datetime.utcnow(),
        expiration_date=item_data.expiration_date,
        category=item_data.category,
        notes=item_data.notes,
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return _to_pantry_response(new_item)


# ---------------------------------------------------------------
# GET /pantry/items  — List all items in the user's pantry
# ---------------------------------------------------------------
@app.get(
    "/pantry/items",
    response_model=list[PantryItemResponse],
    summary="List all pantry items",
    tags=["pantry"],
)
def list_pantry_items(
    current_user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Return all ingredients in the authenticated user's pantry,
    sorted by expiration date (soonest first, nulls last).

    Each item includes a computed `days_until_expiration` field.
    Items with 0 days are expired but not yet deleted.
    """
    items = (
        db.query(PantryItem)
        .filter(PantryItem.user_id == current_user.id)
        .all()
    )

    # Sort: items with expiration dates first (soonest → latest), then no-date items
    def sort_key(item):
        if item.expiration_date is None:
            return (1, datetime.max)  # No date → end of list
        return (0, item.expiration_date)

    items.sort(key=sort_key)
    return [_to_pantry_response(item) for item in items]


# ---------------------------------------------------------------
# PUT /pantry/items/{id}  — Update quantity, expiration, or notes
# ---------------------------------------------------------------
@app.put(
    "/pantry/items/{item_id}",
    response_model=PantryItemResponse,
    summary="Update a pantry item",
    tags=["pantry"],
)
def update_pantry_item(
    item_id: int,
    updates: PantryItemUpdate,
    current_user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Update quantity, unit, expiration date, or notes for a pantry item.

    Only fields included in the request body are updated (partial update).
    Returns the full updated item.
    """
    item = (
        db.query(PantryItem)
        .filter(PantryItem.id == item_id, PantryItem.user_id == current_user.id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pantry item not found",
        )

    # Apply only the fields that were explicitly provided
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)

    return _to_pantry_response(item)


# ---------------------------------------------------------------
# DELETE /pantry/items/{id}  — Remove an item from the pantry
# ---------------------------------------------------------------
@app.delete(
    "/pantry/items/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a pantry item",
    tags=["pantry"],
)
def delete_pantry_item(
    item_id: int,
    current_user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Permanently remove an ingredient from the user's pantry.
    Returns a confirmation message.
    """
    item = (
        db.query(PantryItem)
        .filter(PantryItem.id == item_id, PantryItem.user_id == current_user.id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pantry item not found",
        )

    db.delete(item)
    db.commit()

    return {"message": f"'{item.ingredient_name}' removed from pantry"}



# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize services on application startup
    
    - Loads search engine and recipe embeddings
    - Verifies database connection
    - Creates any new tables (e.g. notifications)
    - Starts background scheduler for expiration checks
    """
    global search_engine
    
    logger.info("=" * 60)
    logger.info("Starting CookNook API v1.4.0")
    logger.info("=" * 60)
    
    # Initialize search engine
    try:
        logger.info("Initializing search engine...")
        logger.info(f"Loading recipes from: {RECIPES_PATH}")
        
        search_engine = RecipeSearchEngine(recipes_path=RECIPES_PATH)
        
        recipe_count = len(search_engine.recipes)
        logger.info(f"✓ Search engine ready: {recipe_count:,} recipes loaded")
        logger.info(f"✓ Embeddings cached: {search_engine.recipe_embeddings.shape}")
    except FileNotFoundError:
        logger.error(f"❌ Recipe file not found: {RECIPES_PATH}")
        logger.error("Please run prepare_foodcom_data.py first to generate recipes.json")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to initialize search engine: {str(e)}")
        raise
    
    # Verify database and create any new tables
    try:
        from database import engine, Base
        Base.metadata.create_all(bind=engine)  # Creates notifications table if missing
        logger.info(f"✓ Database: SQLite (users.db)")
        logger.info(f"✓ Authentication: JWT (7-day tokens)")
        logger.info(f"✓ Search History: Enabled")
        logger.info(f"✓ Personalization: Enabled")
        logger.info(f"✓ Virtual Pantry: Enabled")
        logger.info(f"✓ Notifications: Enabled")
    except Exception as e:
        logger.warning(f"⚠️  Database connection issue: {str(e)}")
        logger.warning("Authentication endpoints may not work correctly")

    # Start background scheduler for expiration notifications
    @scheduler.scheduled_job("interval", hours=6, id="check_expirations")
    def check_expirations_job():
        """Runs every 6 hours — generates expiration notifications for all users."""
        db = next(get_db())
        try:
            users = db.query(User).all()
            for user in users:
                notifs = generate_notifications(user.id, db)
                save_notifications(notifs, db)
            logger.info(f"Expiration check complete for {len(users)} users")
        except Exception as e:
            logger.error(f"Expiration check failed: {str(e)}")
        finally:
            db.close()

    scheduler.start()
    logger.info("✓ Background scheduler started (expiration checks every 6h)")

    logger.info("=" * 60)
    logger.info("Server ready! Visit http://localhost:8000/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down CookNook API...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting development server...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )