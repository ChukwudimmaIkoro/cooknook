/**
 * BottomNav.jsx - Bottom Navigation Component
 * 
 * Mobile-style bottom navigation bar with 4 tabs:
 * - Pantry: Virtual pantry/grocery list (future feature)
 * - Recipes: Recipe search and recommendations
 * - Saved: Saved/favorited recipes (future feature)
 * - Account: User profile and settings (future feature)
 * 
 * Similar to Android/iOS bottom navigation patterns
 */

import React from 'react';
import { ShoppingBasket, Search, Bookmark, User } from 'lucide-react';

/**
 * BottomNav Component
 * 
 * @param {Object} props
 * @param {string} props.activeTab - Currently active tab ('pantry', 'recipes', 'saved', 'account')
 * @param {Function} props.onTabChange - Callback when tab is clicked
 */
const BottomNav = ({ activeTab, onTabChange }) => {
  const tabs = [
    {
      id: 'pantry',
      label: 'Pantry',
      icon: ShoppingBasket,
      description: 'Manage your ingredients'
    },
    {
      id: 'recipes',
      label: 'Recipes',
      icon: Search,
      description: 'Search and discover recipes'
    },
    {
      id: 'saved',
      label: 'Saved',
      icon: Bookmark,
      description: 'Your favorite recipes'
    },
    {
      id: 'account',
      label: 'Account',
      icon: User,
      description: 'Profile and settings'
    }
  ];

  return (
    <nav className="bottom-nav">
      <div className="bottom-nav-container">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          
          return (
            <button
              key={tab.id}
              className={`nav-tab ${isActive ? 'active' : ''}`}
              onClick={() => onTabChange(tab.id)}
              aria-label={tab.description}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon 
                size={24} 
                className="nav-icon"
                strokeWidth={isActive ? 2.5 : 2}
              />
              <span className="nav-label">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

export default BottomNav;