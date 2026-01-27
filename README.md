# CookNook - AI Recipe Recommendation Engine

**Version**: 1.0 (Pre-Personalization)  
**Date**: January 2025  
**Status**: Core search functionality complete, mobile UI implemented

## Overview

CookNook is a (currently) simple AI-powered recipe search application. Users search recipes with natural language queries, ingredients, cuisine filters, and cooking time limits.

## Demo (1/27/2026)
![CookNook Web Demo 1/27/2026](cooknoofgif.gif)

## Tech Stack

### Backend
- **Python 3.8+** with FastAPI
- **Sentence Transformers** (all-MiniLM-L6-v2) - Semantic embeddings
- **PyTorch** - ML framework (under the hood)
- **scikit-learn** - Cosine similarity
- **Pydantic** - Data validation

### Frontend
- **React 18** with Vite
- **Axios** - API client
- **Lucide React** - Icons
- **Mobile-first design** - Bottom navigation, Fragment/Activity pattern

### Data
- **Food.com Dataset** - 230k+ recipes
- **File-based storage** - JSON + NumPy embeddings
- **In-memory search** - 5-20ms response times

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Frontend (React + Vite)                        │
│  ├─ Bottom Navigation (4 tabs)                  │
│  ├─ RecipesView (search UI)                     │
│  └─ Placeholder views (Pantry, Saved, Account) │
└─────────────────────────────────────────────────┘
                     ↓ HTTP/JSON
┌─────────────────────────────────────────────────┐
│  Backend (FastAPI)                              │
│  ├─ /search - Semantic recipe search            │
│  ├─ /cuisines - Available cuisines              │
│  └─ /stats - Dataset statistics                 │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│  Data Layer                                     │
│  ├─ recipes.json (230k recipes)                 │
│  └─ recipes_embeddings.npy (cached vectors)     │
└─────────────────────────────────────────────────┘
```

## Features

### Current (v1.0)
- Semantic search (understands intent, not just keywords)
- Multi-parameter filtering (query + ingredients + cuisine + time)
- Ingredient availability tracking (shows what you have/need)
- Collapsible ingredients list (shows 5 by default)
- Step-by-step cooking instructions
- Mobile-app-style UI with bottom tabs
- Embedding cache (5 second restarts)
- 230k+ recipes from Food.com with names, times, and steps

### Search Parameters
- **Query**: Natural language (e.g., "quick dinner", "healthy lunch")
- **Ingredients**: What you have on hand
- **Cuisine**: Filter by type (Italian, Mexican, Indian, etc.)
- **Max Time**: Cooking time limit in minutes
- **Max Results**: Number of results (1-50)

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
python prepare_foodcom_data.py  # One-time data prep
python main.py                  # Starts on :8000

# Frontend
cd frontend
npm install
npm run dev                     # Opens on :5173
```

## API Endpoints

```
GET  /              Health check
POST /search        Search recipes
GET  /cuisines      Available cuisines
GET  /stats         Dataset statistics
```

**Example Search:**
```json
POST /search
{
  "query": "spicy dinner",
  "ingredients": ["chicken", "rice"],
  "cuisine": "mexican",
  "max_time": 45,
  "max_results": 10
}
```

## Performance

- **Startup**: 5 seconds (with cache)
- **Search**: 5-20ms per query
- **Dataset**: 230k recipes, 800MB RAM
- **Embeddings**: 384-dimensional vectors

## File Structure

```
recipe-recommender/
├── backend/
│   ├── main.py                  # FastAPI server
│   ├── search.py                # Search engine with caching
│   ├── models.py                # Pydantic models
│   └── prepare_foodcom_data.py  # Data processing
├── frontend/
│   ├── src/
│   │   ├── components/          # SearchForm, RecipeCard, etc.
│   │   ├── views/               # Tab views (Recipes, Pantry, etc.)
│   │   └── services/api.js      # Backend API client
│   └── App.jsx                  # Main app with bottom nav
└── data/
    ├── recipes.json             # Recipe data
    └── recipes_embeddings.npy   # Cached embeddings
```

## Limitations (v1.0)

- **Stateless**: No user accounts or memory
- **Single-user**: No personalization
- **Read-only**: Can't save favorites or add recipes
- **No pantry**: Can't track actual ingredients
- **Static**: Must restart to update recipes
- **In-memory only**: Doesn't scale beyond ~1M recipes

## Next Phase: Personalization System

**Planned features** (v2.0):
- User authentication & profiles
- Personalized recommendations (learning system)
- Pantry management with expiration tracking
- Saved recipes & collections
- Cooking pattern learning
- Proactive recipe suggestions
- PyTorch-based neural recommender

**TODO**:
- Add database (SQLite → PostgreSQL)
- Implement user tracking
- Build ML training pipeline
- Add collaborative filtering
- Create recommendation engine
**Use Case**: Recipe search with semantic understanding  
**Scalability**: Up to ~500k recipes, single server  
**Deployment**: Ready for Vercel (frontend) + Render/Railway (backend)
