/**
 * PantryView.jsx - Pantry/Grocery Management Fragment
 * 
 * Future feature: Allow users to manage their virtual pantry
 * - Add/remove ingredients
 * - Track what's in stock
 * - Get recipe suggestions based on pantry
 * 
 * Currently: Placeholder view
 */

import React from 'react';
import { ShoppingBasket, Plus } from 'lucide-react';

const PantryView = () => {
  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">My Pantry</h1>
        <p className="view-subtitle">Manage your ingredients and groceries</p>
      </div>

      <div className="placeholder-content">
        <ShoppingBasket size={64} className="placeholder-icon" />
        <h2>Virtual Pantry</h2>
        <p>Coming Soon!</p>
        <p className="placeholder-description">
          Keep track of ingredients you have at home. Get recipe suggestions
          based on what's in your pantry.
        </p>
        
        <button className="btn btn-primary" disabled>
          <Plus size={20} />
          Add Ingredient
        </button>
      </div>
    </div>
  );
};

export default PantryView;