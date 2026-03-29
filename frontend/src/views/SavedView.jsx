import React, { useState, useEffect } from 'react';
import { Bookmark, Heart, Trash2, ChefHat, Clock, Star, ChevronDown, ChevronUp } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

// Storage helpers — keyed per user so different accounts don't share saves
const storageKey = (userId) => `cooknook_saved_${userId}`;

export const getSavedRecipes = (userId) => {
  try {
    const raw = localStorage.getItem(storageKey(userId));
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
};

export const saveRecipe = (userId, recipe) => {
  const saved = getSavedRecipes(userId);
  if (saved.find(r => r.id === recipe.id)) return; // already saved
  const entry = { ...recipe, saved_at: new Date().toISOString(), hearted: false };
  localStorage.setItem(storageKey(userId), JSON.stringify([...saved, entry]));
};

export const unsaveRecipe = (userId, recipeId) => {
  const saved = getSavedRecipes(userId).filter(r => r.id !== recipeId);
  localStorage.setItem(storageKey(userId), JSON.stringify(saved));
};

export const toggleHeart = (userId, recipeId) => {
  const saved = getSavedRecipes(userId).map(r =>
    r.id === recipeId ? { ...r, hearted: !r.hearted } : r
  );
  localStorage.setItem(storageKey(userId), JSON.stringify(saved));
};

export const isRecipeSaved = (userId, recipeId) =>
  getSavedRecipes(userId).some(r => r.id === recipeId);

// ── Saved recipe card ────────────────────────────────────────────────────────
const SavedRecipeCard = ({ recipe, onUnsave, onToggleHeart }) => {
  const [showSteps, setShowSteps] = useState(false);

  return (
    <div className={`saved-recipe-card ${recipe.hearted ? 'hearted' : ''}`}>
      <div className="saved-recipe-main">
        <div className="saved-recipe-info">
          <div className="saved-recipe-title-row">
            {recipe.hearted && <Heart size={14} className="heart-indicator" fill="currentColor"/>}
            <span className="saved-recipe-name">{recipe.name}</span>
          </div>
          <div className="saved-recipe-meta">
            {recipe.minutes && (
              <span className="meta-chip"><Clock size={12}/> {recipe.minutes}m</span>
            )}
            {recipe.cuisine && (
              <span className="meta-chip"><ChefHat size={12}/> {recipe.cuisine}</span>
            )}
            {recipe.similarity_score && (
              <span className="meta-chip"><Star size={12}/> {Math.round(recipe.similarity_score * 100)}% match</span>
            )}
          </div>
        </div>
        <div className="saved-recipe-actions">
          <button
            className={`icon-btn ${recipe.hearted ? 'hearted-btn' : 'heart-btn'}`}
            onClick={onToggleHeart}
            title={recipe.hearted ? 'Remove from favourites' : 'Add to favourites'}
          >
            <Heart size={18} fill={recipe.hearted ? 'currentColor' : 'none'}/>
          </button>
          <button className="icon-btn delete" onClick={onUnsave} title="Remove">
            <Trash2 size={16}/>
          </button>
        </div>
      </div>

      {recipe.ingredients && recipe.ingredients.length > 0 && (
        <p className="saved-recipe-ingredients">
          {recipe.ingredients.slice(0, 6).join(', ')}
          {recipe.ingredients.length > 6 ? ` +${recipe.ingredients.length - 6} more` : ''}
        </p>
      )}

      {recipe.steps && recipe.steps.length > 0 && (
        <div className="recipe-instructions">
          <button className="instructions-toggle" onClick={() => setShowSteps(v => !v)}>
            <span>Cooking Instructions ({recipe.steps.length} steps)</span>
            {showSteps ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}
          </button>
          {showSteps && (
            <ol className="instructions-list">
              {recipe.steps.map((step, i) => (
                <li key={i} className="instruction-step">
                  <span className="step-number">{i + 1}</span>
                  <span className="step-text">{step}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
};

// ── Main view ────────────────────────────────────────────────────────────────
const SavedView = () => {
  const { isAuthenticated, user } = useAuth();
  const [saved, setSaved] = useState([]);

  const reload = () => {
    if (user) setSaved(getSavedRecipes(user.id));
  };

  useEffect(() => { reload(); }, [user]);

  if (!isAuthenticated) return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Saved Recipes</h1>
        <p className="view-subtitle">Your bookmarked recipes</p>
      </div>
      <div className="placeholder-content">
        <Bookmark size={64} className="placeholder-icon"/>
        <h2>Sign in to save recipes</h2>
        <p className="placeholder-description">
          Bookmark recipes you love and heart your favourites.
        </p>
      </div>
    </div>
  );

  const hearted  = saved.filter(r => r.hearted);
  const rest     = saved.filter(r => !r.hearted);
  const ordered  = [...hearted, ...rest];

  const handleUnsave = (id) => {
    unsaveRecipe(user.id, id);
    reload();
  };

  const handleHeart = (id) => {
    toggleHeart(user.id, id);
    reload();
  };

  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Saved Recipes</h1>
        <p className="view-subtitle">
          {saved.length} saved · {hearted.length} favourited
        </p>
      </div>

      {saved.length === 0 ? (
        <div className="placeholder-content">
          <Bookmark size={64} className="placeholder-icon"/>
          <h2>No saved recipes yet</h2>
          <p className="placeholder-description">
            Hit the bookmark icon on any recipe in the Recipes tab to save it here.
          </p>
        </div>
      ) : (
        <>
          {hearted.length > 0 && (
            <div className="saved-section">
              <h4 className="pantry-category-label">❤ Favourites</h4>
              {hearted.map(r => (
                <SavedRecipeCard key={r.id} recipe={r}
                  onUnsave={() => handleUnsave(r.id)}
                  onToggleHeart={() => handleHeart(r.id)}/>
              ))}
            </div>
          )}
          {rest.length > 0 && (
            <div className="saved-section">
              {hearted.length > 0 && <h4 className="pantry-category-label">Saved</h4>}
              {rest.map(r => (
                <SavedRecipeCard key={r.id} recipe={r}
                  onUnsave={() => handleUnsave(r.id)}
                  onToggleHeart={() => handleHeart(r.id)}/>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SavedView;