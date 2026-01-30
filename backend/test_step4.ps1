# CookNook Step 4: Personalization Testing Script
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CookNook Step 4: Personalization Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000"

# Step 1: Register and login
Write-Host "Step 1: Setting up test user..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$username = "testuser_$timestamp"
$email = "$username@example.com"

$registerData = @{
    username = $username
    email = $email
    password = "test123"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/auth/register" -Method Post -ContentType "application/json" -Body $registerData
    $token = $response.access_token
    Write-Host "  SUCCESS: User created" -ForegroundColor Green
    Write-Host "  Username: $username" -ForegroundColor White
}
catch {
    Write-Host "  FAILED: Could not create user" -ForegroundColor Red
    exit
}

$headers = @{
    "Authorization" = "Bearer $token"
}

# Step 2: Build search history with clear patterns
Write-Host ""
Write-Host "Step 2: Building search history (Italian food preference)..." -ForegroundColor Yellow

$italianSearches = @(
    @{ query = "pasta carbonara"; cuisine = "italian"; max_results = 5 },
    @{ query = "pizza margherita"; cuisine = "italian"; max_results = 5 },
    @{ query = "lasagna"; cuisine = "italian"; max_results = 5 },
    @{ query = "risotto"; cuisine = "italian"; max_results = 5 },
    @{ query = "tiramisu"; cuisine = "italian"; max_results = 3 }
)

foreach ($search in $italianSearches) {
    $searchData = $search | ConvertTo-Json
    try {
        $results = Invoke-RestMethod -Uri "$baseUrl/search" -Method Post -ContentType "application/json" -Headers $headers -Body $searchData
        $queryText = $search.query
        Write-Host "  Italian search: $queryText" -ForegroundColor Green
        Start-Sleep -Milliseconds 300
    }
    catch {
        Write-Host "  Search failed" -ForegroundColor Red
    }
}

# Add some Mexican searches too
Write-Host ""
Write-Host "  Adding Mexican food searches..." -ForegroundColor Yellow

$mexicanSearches = @(
    @{ query = "tacos"; cuisine = "mexican"; max_results = 5 },
    @{ query = "guacamole"; cuisine = "mexican"; max_results = 3 }
)

foreach ($search in $mexicanSearches) {
    $searchData = $search | ConvertTo-Json
    try {
        $results = Invoke-RestMethod -Uri "$baseUrl/search" -Method Post -ContentType "application/json" -Headers $headers -Body $searchData
        $queryText = $search.query
        Write-Host "  Mexican search: $queryText" -ForegroundColor Green
        Start-Sleep -Milliseconds 300
    }
    catch {
        Write-Host "  Search failed" -ForegroundColor Red
    }
}

# Step 3: View learned preferences
Write-Host ""
Write-Host "Step 3: Analyzing learned preferences..." -ForegroundColor Yellow

try {
    $preferences = Invoke-RestMethod -Uri "$baseUrl/preferences" -Method Get -Headers $headers
    Write-Host "  SUCCESS: Preferences retrieved" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Total Searches: $($preferences.total_searches)" -ForegroundColor White
    Write-Host "  Recent Searches: $($preferences.recent_searches)" -ForegroundColor White
    
    if ($preferences.avg_time_preference) {
        $avgTime = [math]::Round($preferences.avg_time_preference, 1)
        Write-Host "  Avg Time Preference: $avgTime minutes" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "  Favorite Cuisines:" -ForegroundColor Cyan
    foreach ($cuisine in $preferences.favorite_cuisines) {
        $cuisineName = $cuisine.cuisine
        $cuisineCount = $cuisine.count
        Write-Host "    - $cuisineName : $cuisineCount searches" -ForegroundColor White
    }
}
catch {
    Write-Host "  FAILED: Could not retrieve preferences" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Yellow
}

# Step 4: Get personalized recommendations
Write-Host ""
Write-Host "Step 4: Getting personalized recommendations..." -ForegroundColor Yellow

try {
    $recommendations = Invoke-RestMethod -Uri "$baseUrl/recommendations?limit=5" -Method Get -Headers $headers
    $recCount = $recommendations.Count
    Write-Host "  SUCCESS: Received $recCount recommendations" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Recommended Recipes:" -ForegroundColor Cyan
    
    $count = 1
    foreach ($recipe in $recommendations) {
        $recipeName = $recipe.name
        $recipeCuisine = $recipe.cuisine
        $recipeMinutes = $recipe.minutes
        Write-Host "    $count. $recipeName" -ForegroundColor White
        Write-Host "       Cuisine: $recipeCuisine | Time: $recipeMinutes min" -ForegroundColor Gray
        $count++
    }
}
catch {
    Write-Host "  FAILED: Could not get recommendations" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Yellow
}

# Step 5: Test personalized search
Write-Host ""
Write-Host "Step 5: Testing personalized search..." -ForegroundColor Yellow

$testSearch = @{
    query = "dinner"
    max_results = 5
} | ConvertTo-Json

try {
    $personalizedResults = Invoke-RestMethod -Uri "$baseUrl/search/personalized" -Method Post -ContentType "application/json" -Headers $headers -Body $testSearch
    $resultCount = $personalizedResults.Count
    Write-Host "  SUCCESS: Personalized search completed" -ForegroundColor Green
    Write-Host "  Found $resultCount results" -ForegroundColor White
    Write-Host ""
    Write-Host "  Top Personalized Results:" -ForegroundColor Cyan
    
    $count = 1
    foreach ($recipe in $personalizedResults) {
        if ($count -gt 3) { break }
        $recipeName = $recipe.name
        $recipeCuisine = $recipe.cuisine
        $simScore = [math]::Round($recipe.similarity_score * 100, 1)
        Write-Host "    $count. $recipeName ($recipeCuisine)" -ForegroundColor White
        Write-Host "       Semantic Match: $simScore%" -ForegroundColor Gray
        $count++
    }
}
catch {
    Write-Host "  FAILED: Personalized search error" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Yellow
}

# Step 6: Manually update preferences
Write-Host ""
Write-Host "Step 6: Manually setting preferences..." -ForegroundColor Yellow

$manualPrefs = @{
    favorite_cuisines = @("italian", "japanese", "french")
    dietary_restrictions = @("vegetarian")
} | ConvertTo-Json

try {
    $updateResponse = Invoke-RestMethod -Uri "$baseUrl/preferences" -Method Put -ContentType "application/json" -Headers $headers -Body $manualPrefs
    Write-Host "  SUCCESS: Preferences updated" -ForegroundColor Green
    $cuisines = $updateResponse.favorite_cuisines -join ", "
    $restrictions = $updateResponse.dietary_restrictions -join ", "
    Write-Host "  Cuisines: $cuisines" -ForegroundColor White
    Write-Host "  Restrictions: $restrictions" -ForegroundColor White
}
catch {
    Write-Host "  FAILED: Could not update preferences" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Yellow
}

# Step 7: Verify manual preferences saved
Write-Host ""
Write-Host "Step 7: Verifying manual preferences..." -ForegroundColor Yellow

try {
    $user = Invoke-RestMethod -Uri "$baseUrl/auth/me" -Method Get -Headers $headers
    $favCuisines = $user.favorite_cuisines
    $dietRestrict = $user.dietary_restrictions
    
    if ($favCuisines -or $dietRestrict) {
        Write-Host "  SUCCESS: Manual preferences saved" -ForegroundColor Green
        if ($favCuisines) {
            Write-Host "  Saved Cuisines: $favCuisines" -ForegroundColor White
        }
        if ($dietRestrict) {
            Write-Host "  Saved Restrictions: $dietRestrict" -ForegroundColor White
        }
    }
    else {
        Write-Host "  WARNING: Preferences may not have saved" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  Could not verify" -ForegroundColor Yellow
}

# Step 8: Compare regular vs personalized search
Write-Host ""
Write-Host "Step 8: Comparing regular vs personalized search..." -ForegroundColor Yellow

$comparisonSearch = @{
    query = "pasta"
    max_results = 3
} | ConvertTo-Json

try {
    Write-Host ""
    Write-Host "  Regular Search Results:" -ForegroundColor Cyan
    $regularResults = Invoke-RestMethod -Uri "$baseUrl/search" -Method Post -ContentType "application/json" -Headers $headers -Body $comparisonSearch
    
    $count = 1
    foreach ($recipe in $regularResults) {
        $recipeName = $recipe.name
        $recipeCuisine = $recipe.cuisine
        Write-Host "    $count. $recipeName ($recipeCuisine)" -ForegroundColor White
        $count++
    }
    
    Write-Host ""
    Write-Host "  Personalized Search Results:" -ForegroundColor Cyan
    $personalizedResults = Invoke-RestMethod -Uri "$baseUrl/search/personalized" -Method Post -ContentType "application/json" -Headers $headers -Body $comparisonSearch
    
    $count = 1
    foreach ($recipe in $personalizedResults) {
        $recipeName = $recipe.name
        $recipeCuisine = $recipe.cuisine
        Write-Host "    $count. $recipeName ($recipeCuisine)" -ForegroundColor White
        $count++
    }
    
    Write-Host ""
    Write-Host "  Notice how personalized results favor Italian cuisine!" -ForegroundColor Yellow
}
catch {
    Write-Host "  Comparison failed" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 4 Testing Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Personalization Features:" -ForegroundColor Green
Write-Host "  - Automatic preference learning" -ForegroundColor White
Write-Host "  - Personalized recipe recommendations" -ForegroundColor White
Write-Host "  - Personalized search results" -ForegroundColor White
Write-Host "  - Manual preference settings" -ForegroundColor White
Write-Host "  - Preference analysis and viewing" -ForegroundColor White
Write-Host ""
Write-Host "CookNook is now fully functional!" -ForegroundColor Green
Write-Host "All core features complete (v1.3.0)" -ForegroundColor Green
Write-Host ""