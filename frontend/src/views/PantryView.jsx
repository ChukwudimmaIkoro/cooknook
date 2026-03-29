import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  ShoppingBasket, Plus, Trash2, Edit2, Check, X,
  ChefHat, AlertTriangle, RefreshCw,
} from 'lucide-react';
import {
  getPantryItems, addPantryItem, updatePantryItem,
  deletePantryItem, searchByPantry,
} from '../services/api';

// ── Expiration badge ─────────────────────────────────────────────────────────
// FIX: thresholds — green until 7d, orange 7-3d, red <3d
const ExpirationBadge = ({ days }) => {
  if (days == null) return null;
  let label, className;
  if (days === 0)      { label = 'Expired';   className = 'expiry-badge expired'; }
  else if (days === 1) { label = 'Tomorrow';  className = 'expiry-badge critical'; }
  else if (days <= 3)  { label = `${days}d`;  className = 'expiry-badge critical'; }
  else if (days <= 7)  { label = `${days}d`;  className = 'expiry-badge warning'; }
  else                 { label = `${days}d`;  className = 'expiry-badge ok'; }
  return <span className={className}>{label}</span>;
};

// ── Pantry item row ──────────────────────────────────────────────────────────
const PantryItemCard = ({ item, onDelete, onUpdate }) => {
  const [editing, setEditing] = useState(false);
  const [qty, setQty]   = useState(item.quantity ?? 1);
  const [unit, setUnit] = useState(item.unit ?? '');

  const handleSave = async () => {
    await onUpdate({ quantity: qty !== '' ? parseFloat(qty) : null, unit: unit || null });
    setEditing(false);
  };

  return (
    <div className="pantry-item-card">
      <div className="pantry-item-info">
        <span className="pantry-item-name">{item.ingredient_name}</span>
        <ExpirationBadge days={item.days_until_expiration} />
        {item.category && <span className="pantry-item-category">{item.category}</span>}
      </div>
      <div className="pantry-item-actions">
        {editing ? (
          <div className="pantry-item-edit">
            <input type="number" value={qty} onChange={e => setQty(e.target.value)}
              placeholder="Qty" className="pantry-edit-input qty" />
            <input value={unit} onChange={e => setUnit(e.target.value)}
              placeholder="Unit" className="pantry-edit-input unit" />
            <button onClick={handleSave} className="icon-btn confirm"><Check size={16}/></button>
            <button onClick={() => setEditing(false)} className="icon-btn cancel"><X size={16}/></button>
          </div>
        ) : (
          <div className="pantry-item-qty">
            {item.quantity != null && (
              <span className="qty-label">{item.quantity} {item.unit || ''}</span>
            )}
            <button onClick={() => setEditing(true)} className="icon-btn edit"><Edit2 size={15}/></button>
            <button onClick={onDelete} className="icon-btn delete"><Trash2 size={15}/></button>
          </div>
        )}
      </div>
    </div>
  );
};

// ── Recipe result card with ingredient matching ──────────────────────────────
// FIX: case-insensitive matching, green checkmark boxes, coverage %
const PantryRecipeCard = ({ recipe, pantrySet }) => {
  const pct = Math.round(recipe.coverage * 100);

  // Re-derive per-ingredient status from live pantrySet (case-insensitive)
  const ingredients = recipe.ingredients || [];
  const matched   = new Set(recipe.matched_ingredients.map(i => i.toLowerCase()));
  const expiring  = new Set(recipe.uses_expiring_soon.map(i => i.toLowerCase()));

  return (
    <div className="pantry-recipe-card">
      <div className="pantry-recipe-header">
        <span className="pantry-recipe-name">{recipe.name}</span>
        <span className="pantry-coverage-badge">{pct}% covered</span>
      </div>

      {recipe.uses_expiring_soon.length > 0 && (
        <p className="pantry-recipe-expiring">
          <AlertTriangle size={13}/>
          Uses expiring: {recipe.uses_expiring_soon.join(', ')}
        </p>
      )}

      {/* Ingredient list with have/need indicators */}
      <div className="pantry-recipe-ingredients">
        {ingredients.slice(0, 10).map((ing, i) => {
          const norm  = ing.toLowerCase().trim();
          const have  = matched.has(norm);
          const soon  = expiring.has(norm);
          return (
            <span key={i} className={`ingredient-chip ${have ? (soon ? 'chip-expiring' : 'chip-have') : 'chip-need'}`}>
              {have
                ? <Check size={11} style={{marginRight:3}}/>
                : <X size={11} style={{marginRight:3}}/>}
              {ing}
            </span>
          );
        })}
        {ingredients.length > 10 && (
          <span className="ingredient-chip chip-need">+{ingredients.length - 10} more</span>
        )}
      </div>

      {recipe.missing_ingredients.length > 0 && (
        <p className="pantry-recipe-missing">
          Still need: {recipe.missing_ingredients.slice(0, 4).join(', ')}
          {recipe.missing_ingredients.length > 4 ? ` +${recipe.missing_ingredients.length - 4} more` : ''}
        </p>
      )}
    </div>
  );
};

// ── Main view ────────────────────────────────────────────────────────────────
const CATEGORIES = ['produce','dairy','meat','seafood','pantry','frozen','drinks','other'];

const PantryView = () => {
  const { isAuthenticated, token } = useAuth();

  const [items, setItems]       = useState([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);

  // FIX: default qty = 1
  const [showForm, setShowForm]         = useState(false);
  const [newName, setNewName]           = useState('');
  const [newQty, setNewQty]             = useState('1');
  const [newUnit, setNewUnit]           = useState('');
  const [newCategory, setNewCategory]   = useState('');
  const [newExpiry, setNewExpiry]       = useState('');
  const [adding, setAdding]             = useState(false);
  const [addError, setAddError]         = useState(null);

  const [recipes, setRecipes]       = useState([]);
  const [searching, setSearching]   = useState(false);
  const [recipeError, setRecipeError] = useState(null);
  const [showRecipes, setShowRecipes] = useState(false);

  const loadItems = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true); setError(null);
    try { setItems(await getPantryItems(token)); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [isAuthenticated, token]);

  useEffect(() => { loadItems(); }, [loadItems]);

  const handleAdd = async () => {
    if (!newName.trim()) return;
    setAdding(true); setAddError(null);
    try {
      await addPantryItem(token, {
        ingredient_name: newName.trim(),
        quantity:        newQty !== '' ? parseFloat(newQty) : 1,
        unit:            newUnit || null,
        category:        newCategory || null,
        // FIX: set time to noon UTC to avoid off-by-one from timezone differences
        expiration_date: newExpiry
          ? new Date(newExpiry + 'T12:00:00Z').toISOString()
          : null,
      });
      setNewName(''); setNewQty('1'); setNewUnit('');
      setNewCategory(''); setNewExpiry('');
      setShowForm(false);
      loadItems();
    } catch (e) { setAddError(e.message); }
    finally { setAdding(false); }
  };

  const handleUpdate = async (id, updates) => {
    try { await updatePantryItem(token, id, updates); loadItems(); }
    catch (e) { setError(e.message); }
  };

  const handleDelete = async (id) => {
    try { await deletePantryItem(token, id); loadItems(); }
    catch (e) { setError(e.message); }
  };

  const handlePantrySearch = async () => {
    setSearching(true); setRecipeError(null);
    setRecipes([]); setShowRecipes(true);
    try { setRecipes(await searchByPantry(token, 10)); }
    catch (e) { setRecipeError(e.message); }
    finally { setSearching(false); }
  };

  const grouped = items.reduce((acc, item) => {
    const cat = item.category || 'other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(item);
    return acc;
  }, {});

  // Build pantry set (lowercase) to pass into recipe cards
  const pantrySet = new Set(items.map(i => i.ingredient_name.toLowerCase()));

  const expiringCount = items.filter(
    i => i.days_until_expiration != null && i.days_until_expiration <= 3
  ).length;

  if (!isAuthenticated) return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">My Pantry</h1>
        <p className="view-subtitle">Manage your ingredients and groceries</p>
      </div>
      <div className="placeholder-content">
        <ShoppingBasket size={64} className="placeholder-icon"/>
        <h2>Sign in to use your Pantry</h2>
        <p className="placeholder-description">
          Track ingredients, get expiration reminders, and find recipes based on what you already have.
        </p>
      </div>
    </div>
  );

  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">My Pantry</h1>
        <p className="view-subtitle">
          {items.length} item{items.length !== 1 ? 's' : ''}
          {expiringCount > 0 && (
            <span className="expiring-warning">
              {' '}· <AlertTriangle size={13}/> {expiringCount} expiring soon
            </span>
          )}
        </p>
      </div>

      <div className="pantry-toolbar">
        <button className="btn btn-primary" onClick={() => setShowForm(v => !v)}>
          <Plus size={18}/>{showForm ? 'Cancel' : 'Add Item'}
        </button>
        <button className="btn btn-secondary" onClick={loadItems} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spinning' : ''}/>
        </button>
      </div>

      {showForm && (
        <div className="pantry-add-form">
          <div className="form-row">
            <input value={newName} onChange={e => setNewName(e.target.value)}
              placeholder="Ingredient name *" className="form-input flex-grow"
              onKeyDown={e => e.key === 'Enter' && handleAdd()}/>
            <input type="number" value={newQty} onChange={e => setNewQty(e.target.value)}
              placeholder="Qty" className="form-input qty"/>
            <input value={newUnit} onChange={e => setNewUnit(e.target.value)}
              placeholder="Unit" className="form-input unit"/>
          </div>
          <div className="form-row">
            <select value={newCategory} onChange={e => setNewCategory(e.target.value)}
              className="form-input">
              <option value="">Category (optional)</option>
              {CATEGORIES.map(c => (
                <option key={c} value={c}>{c.charAt(0).toUpperCase()+c.slice(1)}</option>
              ))}
            </select>
            {/* FIX: added label for expiration date */}
            <div className="form-date-wrapper">
              <label className="form-date-label">Expiration date</label>
              <input type="date" value={newExpiry} onChange={e => setNewExpiry(e.target.value)}
                className="form-input"/>
            </div>
          </div>
          {addError && <p className="error-message">{addError}</p>}
          <button className="btn btn-primary full-width" onClick={handleAdd}
            disabled={adding || !newName.trim()}>
            {adding ? 'Adding…' : 'Add to Pantry'}
          </button>
        </div>
      )}

      {error && <p className="error-message">{error}</p>}

      {!loading && items.length === 0 && (
        <div className="placeholder-content">
          <ShoppingBasket size={64} className="placeholder-icon"/>
          <h2>Your pantry is empty</h2>
          <p className="placeholder-description">
            Add ingredients to get recipe suggestions and expiration reminders.
          </p>
        </div>
      )}

      {Object.entries(grouped).map(([cat, catItems]) => (
        <div key={cat} className="pantry-category-group">
          <h4 className="pantry-category-label">
            {cat.charAt(0).toUpperCase()+cat.slice(1)}
          </h4>
          {catItems.map(item => (
            <PantryItemCard key={item.id} item={item}
              onDelete={() => handleDelete(item.id)}
              onUpdate={updates => handleUpdate(item.id, updates)}/>
          ))}
        </div>
      ))}

      {items.length > 0 && (
        <button className="btn btn-find-recipes" onClick={handlePantrySearch} disabled={searching}>
          <ChefHat size={20}/>
          {searching ? 'Finding recipes…' : 'Find Recipes with My Pantry'}
        </button>
      )}

      {showRecipes && (
        <div className="pantry-recipes-section">
          <h3 className="section-title">Recipes You Can Make</h3>
          {searching && <div className="recipe-list-state"><div className="spinner"/><p>Searching…</p></div>}
          {recipeError && <p className="error-message">{recipeError}</p>}
          {!searching && recipes.length === 0 && !recipeError && (
            <p className="muted-text">No matching recipes found.</p>
          )}
          {recipes.map(r => (
            <PantryRecipeCard key={r.id} recipe={r} pantrySet={pantrySet}/>
          ))}
        </div>
      )}
    </div>
  );
};

export default PantryView;