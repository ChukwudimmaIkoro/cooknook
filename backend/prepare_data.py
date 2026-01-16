"""
prepare_foodcom_data.py - Food.com Dataset Preparation

This script prepares the Food.com recipe dataset for use with the search engine.
It handles data loading, cleaning, validation, cuisine inference, and standardization.

Key Features:
- Loads RAW_recipes.csv from Food.com
- Infers cuisine from recipe names and tags
- Cleans and validates recipe data
- Standardizes ingredient and cuisine names
- Filters out invalid or incomplete recipes
- Saves processed data in clean JSON format

Run this script once before starting the API server:
    python prepare_foodcom_data.py

Input: RAW_recipes.csv from Food.com dataset
Output: Cleaned recipes.json ready for the search engine
"""

import json
import pandas as pd
import ast
import re
from collections import Counter


def infer_cuisine_from_name_and_tags(name, tags):
    """
    Infer cuisine type from recipe name and tags.
    
    The Food.com dataset doesn't have explicit cuisine labels,
    so we infer them from recipe names and tags using keyword matching.
    
    Args:
        name (str): Recipe name
        tags (list): List of tag strings
    
    Returns:
        str: Inferred cuisine type (lowercase)
    
    Algorithm:
        1. Convert name and tags to lowercase
        2. Check for cuisine keywords in order of specificity
        3. Return first match, or 'american' as default
    
    Examples:
        "Italian Pasta Carbonara", ['italian', 'pasta'] → 'italian'
        "Chicken Curry", ['indian', 'spicy'] → 'indian'
        "Chocolate Chip Cookies", ['dessert', 'baked'] → 'american'
    """
    # Combine name and tags for searching
    text = f"{name} {' '.join(tags)}".lower()
    
    # Cuisine keywords in order of specificity
    # More specific terms first to avoid false matches
    cuisine_keywords = {
        'italian': ['italian', 'tuscany', 'sicilian', 'neapolitan'],
        'mexican': ['mexican', 'tex-mex', 'latin-american'],
        'chinese': ['chinese', 'cantonese', 'szechuan', 'mandarin'],
        'indian': ['indian', 'curry', 'tandoori', 'masala'],
        'japanese': ['japanese', 'sushi', 'teriyaki', 'ramen'],
        'thai': ['thai', 'pad-thai'],
        'french': ['french', 'provencal', 'parisian'],
        'greek': ['greek', 'mediterranean-greek'],
        'spanish': ['spanish', 'tapas', 'paella'],
        'korean': ['korean', 'kimchi', 'bulgogi'],
        'vietnamese': ['vietnamese', 'pho'],
        'middle-eastern': ['middle-eastern', 'lebanese', 'turkish', 'persian'],
        'cajun': ['cajun', 'creole'],
        'southern': ['southern-u-s', 'soul-food'],
        'bbq': ['barbecue', 'grilling'],
        'asian': ['asian'],  # Generic fallback
    }
    
    # Check for each cuisine
    for cuisine, keywords in cuisine_keywords.items():
        for keyword in keywords:
            if keyword in text:
                return cuisine
    
    # Default to American if no match found
    return 'american'


def clean_ingredient(ingredient):
    """
    Clean and standardize ingredient text.
    
    Removes measurements, brand names, and excessive detail
    to focus on the core ingredient.
    
    Args:
        ingredient (str): Raw ingredient text
    
    Returns:
        str: Cleaned ingredient name
    
    Examples:
        "2 cups all-purpose flour" → "all-purpose flour"
        "1 lb ground beef" → "ground beef"
        "salt and pepper to taste" → "salt and pepper"
    """
    # Convert to lowercase
    ingredient = ingredient.lower().strip()
    
    # Remove common measurement patterns
    # Matches: "2 cups", "1 lb", "½ tsp", etc.
    ingredient = re.sub(r'^\d+[\s\-]*(cup|tablespoon|teaspoon|pound|ounce|oz|lb|tsp|tbsp|ml|l|g|kg)s?\s+', '', ingredient)
    ingredient = re.sub(r'^[\d/½¼¾]+\s+', '', ingredient)  # Remove leading numbers and fractions
    
    # Remove parenthetical notes
    ingredient = re.sub(r'\([^)]*\)', '', ingredient)
    
    # Remove common trailing phrases
    remove_phrases = [
        'to taste', 'optional', 'if needed', 'as needed',
        'or more to taste', 'plus more'
    ]
    for phrase in remove_phrases:
        ingredient = ingredient.replace(phrase, '')
    
    # Clean up whitespace
    ingredient = ' '.join(ingredient.split())
    
    return ingredient.strip()


def prepare_foodcom_dataset(input_path: str, output_path: str, max_recipes: int = None):
    """
    Prepare Food.com recipe dataset for the search engine.
    
    This function performs a complete data preparation pipeline:
    1. Load data from CSV
    2. Parse list-formatted strings (ingredients, tags)
    3. Infer cuisine from recipe names and tags
    4. Clean and validate entries
    5. Standardize names and formats
    6. Save in optimized JSON format
    
    Args:
        input_path (str): Path to RAW_recipes.csv file
        output_path (str): Path where cleaned data will be saved
        max_recipes (int, optional): Limit number of recipes to process
            Useful for testing or creating smaller datasets
            Default: None (process all recipes)
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If required columns are missing
    
    Data Quality Improvements:
        - Removes duplicate recipes (by ID)
        - Filters out recipes with no ingredients
        - Filters out recipes with no name
        - Cleans ingredient text (removes measurements, notes)
        - Standardizes ingredient names (lowercase, trimmed)
        - Infers cuisine from names and tags
        - Validates data types and ranges
        - Provides detailed statistics about cleaning operations
    """
    print(f"Loading Food.com data from {input_path}...")
    
    # Step 1: Load CSV file
    # nrows parameter limits rows for testing (remove for full dataset)
    df = pd.read_csv(input_path, nrows=max_recipes)
    
    print(f"Loaded {len(df)} recipes")
    print(f"Columns: {df.columns.tolist()}")
    
    # Step 2: Parse string representations of lists
    # Food.com stores lists as strings like "['ingredient1', 'ingredient2']"
    print("\nParsing list fields...")
    
    # Parse ingredients from string to actual list
    df['ingredients'] = df['ingredients'].apply(
        lambda x: ast.literal_eval(x) if pd.notna(x) else []
    )
    
    # Parse tags from string to actual list
    df['tags'] = df['tags'].apply(
        lambda x: ast.literal_eval(x) if pd.notna(x) else []
    )
    
    # Parse steps (cooking instructions) from string to actual list
    df['steps'] = df['steps'].apply(
        lambda x: ast.literal_eval(x) if pd.notna(x) else []
    )
    
    # Step 3: Infer cuisine for each recipe
    print("Inferring cuisines from recipe names and tags...")
    df['cuisine'] = df.apply(
        lambda row: infer_cuisine_from_name_and_tags(row['name'], row['tags']),
        axis=1
    )
    
    # Show cuisine distribution
    cuisine_counts = df['cuisine'].value_counts()
    print(f"\nTop 10 cuisines found:")
    for cuisine, count in cuisine_counts.head(10).items():
        print(f"  {cuisine}: {count}")
    
    # Step 4: Clean and validate data
    print("\nCleaning data...")
    
    initial_count = len(df)
    
    # Remove duplicates based on recipe ID
    df = df.drop_duplicates(subset=['id'])
    duplicates_removed = initial_count - len(df)
    if duplicates_removed > 0:
        print(f"  Removed {duplicates_removed} duplicate recipes")
    
    # Remove recipes with no name
    initial_count = len(df)
    df = df[df['name'].notna() & (df['name'] != '')]
    no_name_removed = initial_count - len(df)
    if no_name_removed > 0:
        print(f"  Removed {no_name_removed} recipes with no name")
    
    # Remove recipes with no ingredients
    initial_count = len(df)
    df = df[df['ingredients'].apply(len) > 0]
    empty_removed = initial_count - len(df)
    if empty_removed > 0:
        print(f"  Removed {empty_removed} recipes with no ingredients")
    
    # Remove recipes with unrealistic cooking times (> 24 hours or negative)
    initial_count = len(df)
    df = df[(df['minutes'] > 0) & (df['minutes'] < 1440)]  # 1440 min = 24 hours
    time_removed = initial_count - len(df)
    if time_removed > 0:
        print(f"  Removed {time_removed} recipes with invalid cooking times")
    
    # Step 5: Clean ingredients
    print("\nCleaning ingredient names...")
    df['ingredients'] = df['ingredients'].apply(
        lambda ings: [clean_ingredient(ing) for ing in ings]
    )
    
    # Remove empty ingredients after cleaning
    df['ingredients'] = df['ingredients'].apply(
        lambda ings: [ing for ing in ings if ing and len(ing) > 0]
    )
    
    # Update ingredient count after cleaning
    df['n_ingredients'] = df['ingredients'].apply(len)
    
    # Step 6: Standardize text fields
    print("Standardizing text fields...")
    
    # Clean recipe names (remove excessive whitespace)
    df['name'] = df['name'].str.strip()
    df['name'] = df['name'].apply(lambda x: ' '.join(x.split()))
    
    # Truncate long descriptions
    if 'description' in df.columns:
        df['description'] = df['description'].apply(
            lambda x: str(x)[:500] if pd.notna(x) else None
        )
    
    # Step 7: Select and rename columns
    print("\nSelecting relevant columns...")
    
    # Keep only the columns we need
    columns_to_keep = ['id', 'name', 'ingredients', 'steps', 'minutes', 'n_steps', 'n_ingredients']
    
    # Add optional columns if they exist
    if 'description' in df.columns:
        columns_to_keep.append('description')
    
    columns_to_keep.append('cuisine')
    
    df = df[columns_to_keep]
    
    # Step 8: Print final statistics
    print(f"\n{'='*60}")
    print("FINAL DATASET STATISTICS")
    print(f"{'='*60}")
    print(f"Total recipes: {len(df):,}")
    print(f"Unique cuisines: {df['cuisine'].nunique()}")
    print(f"Average ingredients per recipe: {df['n_ingredients'].mean():.1f}")
    print(f"Average cooking time: {df['minutes'].mean():.1f} minutes")
    print(f"Average steps: {df['n_steps'].mean():.1f}")
    
    # Show time distribution
    print(f"\nCooking time distribution:")
    print(f"  Quick (<30 min): {len(df[df['minutes'] < 30]):,} recipes")
    print(f"  Medium (30-60 min): {len(df[(df['minutes'] >= 30) & (df['minutes'] < 60)]):,} recipes")
    print(f"  Long (60+ min): {len(df[df['minutes'] >= 60]):,} recipes")
    
    # Step 9: Convert to list of dictionaries
    recipes = df.to_dict('records')
    
    # Step 10: Save cleaned data to JSON file
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(recipes, f, indent=2)
    
    print("Done!")
    
    # Step 11: Print sample recipe for verification
    print("\n" + "="*60)
    print("SAMPLE RECIPE")
    print("="*60)
    print(json.dumps(recipes[0], indent=2))
    
    # Additional validation checks
    print("\n" + "="*60)
    print("DATA VALIDATION")
    print("="*60)
    
    # Check for very short ingredient lists (potential data quality issues)
    short_recipes = len(df[df['n_ingredients'] < 3])
    print(f"Recipes with <3 ingredients: {short_recipes} ({short_recipes/len(df)*100:.1f}%)")
    
    # Check for very long ingredient lists (might be parsing errors)
    long_recipes = len(df[df['n_ingredients'] > 30])
    print(f"Recipes with >30 ingredients: {long_recipes} ({long_recipes/len(df)*100:.1f}%)")
    
    # Most common ingredients
    all_ingredients = [ing for recipe in recipes for ing in recipe['ingredients']]
    ingredient_counts = Counter(all_ingredients)
    print(f"\nTop 10 most common ingredients:")
    for ing, count in ingredient_counts.most_common(10):
        print(f"  {ing}: {count:,} recipes")


# Script entry point
if __name__ == "__main__":
    # Configuration
    INPUT_PATH = "../data/RAW_recipes.csv"
    OUTPUT_PATH = "../data/recipes.json"
    
    # Optional: Set max_recipes to a smaller number for testing
    # This dramatically speeds up embedding generation during development
    # Uncomment one of these lines:
    
    # MAX_RECIPES = 1000   # Very fast (~5 seconds) - good for initial testing
    # MAX_RECIPES = 10000  # Fast (~30 seconds) - good for development
    # MAX_RECIPES = 50000  # Medium (~2 minutes) - decent dataset size
    MAX_RECIPES = None     # Slow (~3-5 minutes) - full dataset (230k recipes)
    
    # Ensure the data directory exists
    import os
    os.makedirs("../data", exist_ok=True)
    
    # Run the preparation pipeline
    prepare_foodcom_dataset(INPUT_PATH, OUTPUT_PATH, MAX_RECIPES)
    
    print("\n" + "="*60)
    print("DATA PREPARATION COMPLETE!")
    print("You can now start the API server with: python main.py")
    print("="*60)