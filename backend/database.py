"""
database.py - User Database Setup

This module sets up SQLite database for user data, tracking, and personalization.
Separate from recipe search (which stays in-memory for speed).

Tables:
- users: User accounts and profiles
- search_history: Track all searches
- recipe_interactions: Views, saves, ratings
- pantry_items: User's ingredient inventory
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database file location
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# ============================================================================
# USER MODELS
# ============================================================================

class User(Base):
    """
    User account and profile information
    
    Stores basic user data and preferences for personalization
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Profile information
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Preferences
    favorite_cuisines = Column(String, nullable=True)  # Comma-separated
    dietary_restrictions = Column(String, nullable=True)  # Comma-separated
    
    # Relationships
    search_history = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    interactions = relationship("RecipeInteraction", back_populates="user", cascade="all, delete-orphan")
    pantry_items = relationship("PantryItem", back_populates="user", cascade="all, delete-orphan")


class SearchHistory(Base):
    """
    Track all user searches for learning preferences
    
    Used to understand what users search for and when
    """
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Search parameters
    query = Column(String, nullable=True)
    ingredients = Column(String, nullable=True)  # Comma-separated
    cuisine = Column(String, nullable=True)
    max_time = Column(Integer, nullable=True)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    results_count = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="search_history")


class RecipeInteraction(Base):
    """
    Track user interactions with recipes
    
    Essential for learning what users like and building recommendations
    """
    __tablename__ = "recipe_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipe_id = Column(Integer, nullable=False, index=True)
    
    # Interaction types
    viewed = Column(Boolean, default=False)
    saved = Column(Boolean, default=False)
    cooked = Column(Boolean, default=False)  # User marks as cooked
    
    # Feedback
    rating = Column(Integer, nullable=True)  # 1-5 stars
    notes = Column(Text, nullable=True)  # User's personal notes
    
    # Timestamps
    first_viewed_at = Column(DateTime, default=datetime.utcnow)
    last_interacted_at = Column(DateTime, default=datetime.utcnow)
    saved_at = Column(DateTime, nullable=True)
    cooked_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="interactions")

class PantryItem(Base):
    __tablename__ = "pantry_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    ingredient_name = Column(String, nullable=False, index=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    added_date = Column(DateTime, default=datetime.utcnow)      # ← was added_at
    expiration_date = Column(DateTime, nullable=True)            # ← was expires_at
    category = Column(String, nullable=True)                     # ← missing
    notes = Column(Text, nullable=True)                          # ← missing

    user = relationship("User", back_populates="pantry_items")

# class PantryItem(Base):
#     """
#     User's virtual pantry - ingredients they have
    
#     Used for smart recommendations and expiration tracking
#     """
#     __tablename__ = "pantry_items"
    
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
#     # Item details
#     ingredient_name = Column(String, nullable=False, index=True)
#     quantity = Column(Float, nullable=True)
#     unit = Column(String, nullable=True)  # cups, lbs, etc.
    
#     # Tracking
#     added_at = Column(DateTime, default=datetime.utcnow)
#     expires_at = Column(DateTime, nullable=True)
#     last_used_at = Column(DateTime, nullable=True)
    
#     # Status
#     is_running_low = Column(Boolean, default=False)
    
#     # Relationships
#     user = relationship("User", back_populates="pantry_items")

class Notification(Base):
    __tablename__ = "notifications"
 
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type       = Column(String, nullable=False)   # "expiration" | "shopping" | "recipe_suggestion"
    title      = Column(String, nullable=False)
    message    = Column(Text,   nullable=False)
    action_url = Column(String, nullable=True)    # e.g. "/recipes/12345"
    read       = Column(Boolean, default=False,   nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """
    Initialize database - create all tables
    
    Call this once on first run or when schema changes
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def get_db():
    """
    Dependency for FastAPI routes
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_test_user():
    """
    Create a test user for development
    
    Usage: python -c "from database import create_test_user; create_test_user()"
    """
    db = SessionLocal()
    try:
        # Check if test user exists
        existing = db.query(User).filter(User.username == "testuser").first()
        if existing:
            print("ℹ️  Test user already exists")
            return
        
        # Create test user with pre-hashed password
        # Password: "test123" - using simple bcrypt hash
        import bcrypt
        password = "test123"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hashed.decode('utf-8'),
            full_name="Test User",
            favorite_cuisines="italian,mexican,indian",
            dietary_restrictions=""
        )
        
        db.add(test_user)
        db.commit()
        print("✅ Test user created: username='testuser', password='test123'")
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        print("But database tables were created successfully!")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Run this file directly to initialize database
    print("Initializing database...")
    init_db()
    
    # Optionally create test user
    create_test_user()