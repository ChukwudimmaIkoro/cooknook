/**
 * SavedView.jsx - Saved/Favorited Recipes Fragment
 * 
 * Future feature: Display user's saved/favorited recipes
 * - Save recipes from search
 * - Organize into collections
 * - Quick access to favorites
 * 
 * Currently: Placeholder view
 */

import React from 'react';
import { Bookmark, Heart } from 'lucide-react';

const SavedView = () => {
  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Saved Recipes</h1>
        <p className="view-subtitle">Your favorite recipes in one place</p>
      </div>

      <div className="placeholder-content">
        <Bookmark size={64} className="placeholder-icon" />
        <h2>No Saved Recipes Yet</h2>
        <p className="placeholder-description">
          Recipes you save will appear here. Search for recipes and tap the
          bookmark icon to save them for later.
        </p>
        
        <div className="placeholder-features">
          <div className="feature-item">
            <Heart size={20} />
            <span>Favorite recipes</span>
          </div>
          <div className="feature-item">
            <Bookmark size={20} />
            <span>Organize collections</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SavedView;