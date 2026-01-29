"""
main.py - CookNook API Server

AI-powered recipe recommendation engine with user authentication.

Version: 1.2.0
Features:
- Semantic recipe search (230k+ recipes)
- User authentication (JWT)
- Search history tracking (NEW - Step 3)
- Personalized recommendations (coming in Step 4)
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging
import os

# Import project modules
from models import SearchRequest, SearchResponse, Recipe
from search import RecipeSearchEngine
from database import get_db, User, SearchHistory
from auth import (
    create_user,
    authenticate_user,
    get_current_user,
    require_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="CookNook API",
    description="AI-powered recipe recommendation engine with user authentication",
    version="1.2.0",
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
        "version": "1.2.0",
        "status": "running",
        "features": ["recipe_search", "user_authentication", "search_history"],
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
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize services on application startup
    
    - Loads search engine and recipe embeddings
    - Verifies database connection
    """
    global search_engine
    
    logger.info("=" * 60)
    logger.info("Starting CookNook API v1.2.0")
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
    
    # Verify database
    try:
        from database import engine
        logger.info(f"✓ Database: SQLite (users.db)")
        logger.info(f"✓ Authentication: JWT (7-day tokens)")
        logger.info(f"✓ Search History: Enabled")
    except Exception as e:
        logger.warning(f"⚠️  Database connection issue: {str(e)}")
        logger.warning("Authentication endpoints may not work correctly")
    
    logger.info("=" * 60)
    logger.info("Server ready! Visit http://localhost:8000/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down CookNook API...")


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