#This file contains the main FastAPI application for the Recipe Recommendation API.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import SearchRequest, SearchResponse
from search import RecipeSearchEngine
from typing import List
import os

app = FastAPI(title="Recipe Recommendation API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize search engine
RECIPES_PATH = os.getenv("RECIPES_PATH", "../data/recipes.json")
search_engine = None

@app.on_event("startup")
async def startup_event():
    """Initialize the search engine on startup."""
    global search_engine
    try:
        search_engine = RecipeSearchEngine(RECIPES_PATH)
    except Exception as e:
        print(f"Error initializing search engine: {e}")
        raise

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Recipe Recommendation API is running",
        "total_recipes": len(search_engine.recipes) if search_engine else 0
    }

@app.post("/search", response_model=List[SearchResponse])
async def search_recipes(request: SearchRequest):
    """
    Search for recipes based on user preferences.
    
    Parameters:
    - query: Natural language query (e.g., "quick dinner", "spicy food")
    - ingredients: List of ingredients the user has
    - cuisine: Filter by specific cuisine type
    - max_results: Maximum number of results to return (default: 10)
    """
    if not search_engine:
        raise HTTPException(status_code=503, message="Search engine not initialized")
    
    try:
        results = search_engine.search(request)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/cuisines")
async def get_cuisines():
    """Get list of available cuisines."""
    if not search_engine:
        raise HTTPException(status_code=503, message="Search engine not initialized")
    
    cuisines = list(set(recipe.cuisine for recipe in search_engine.recipes))
    return {"cuisines": sorted(cuisines)}

@app.get("/stats")
async def get_stats():
    """Get dataset statistics."""
    if not search_engine:
        raise HTTPException(status_code=503, message="Search engine not initialized")
    
    cuisines = {}
    all_ingredients = set()
    
    for recipe in search_engine.recipes:
        cuisines[recipe.cuisine] = cuisines.get(recipe.cuisine, 0) + 1
        all_ingredients.update(recipe.ingredients)
    
    return {
        "total_recipes": len(search_engine.recipes),
        "total_cuisines": len(cuisines),
        "cuisine_distribution": cuisines,
        "unique_ingredients": len(all_ingredients)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)