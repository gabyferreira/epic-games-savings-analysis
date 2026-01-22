import requests # this is to make an api request
import pandas as pd
from datetime import datetime
from tqdm import tqdm
tqdm.pandas()
import time
import json
import os
from thefuzz import process
from processor import validate_and_clean_data

file_path = "data/epic_games_data_edited_active6.csv"
df_existing = pd.read_csv(file_path, encoding='latin1' )
def update_csv():
    base_url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    response = requests.get(base_url).json()
    elements = response['data']['Catalog']['searchStore']['elements']
    
    new_entries = []
    for game in elements:
        # Epic's API includes 'upcoming' and 'current' free games
        promos = game.get('promotions', {}) #if there is a promotion return the item, if not skip it
        if promos and promos.get('promotionalOffers'):
            offer = promos['promotionalOffers'][0]['promotionalOffers'][0] #promotionalOffers is referenced twice in the request the second item contains the dates of the promotion - also distinguishes it from upcoming promotions
            
            discount = offer.get('discountSetting', {}).get('discountPercentage', 100) #sometimes discounted games, but not free games can appear in the list, this is to check that it is free
        
            if discount == 0:  # 0 means 100% off in Epic's API logic
                new_entries.append({
                    'game': game['title'],
                    'start_date': offer['startDate'],
                    'end_date': offer['endDate']
                })
    
    df_new = pd.DataFrame(new_entries)
    df_existing['start_date'] = pd.to_datetime(
        df_existing['start_date'], 
        dayfirst=True, 
        errors='coerce'
    ).dt.strftime('%d-%m-%Y') #need to do this so that it is read like a date
    df_new['start_date'] = pd.to_datetime(df_new['start_date']).dt.strftime('%d-%m-%Y')
    df_new['end_date'] = pd.to_datetime(df_new['end_date']).dt.strftime('%d-%m-%Y')
    df_to_add = df_new[~df_new['start_date'].isin(df_existing['start_date'])]
    if not df_to_add.empty:
        # safe ID generation
        if df_existing.empty or 'id' not in df_existing.columns or df_existing['id'].isnull().all():
            last_id = 0
        else:
            # We use dropna() to ensure we don't grab a NaN value from the last row
            valid_ids = df_existing['id'].dropna()
            last_id = int(valid_ids.iloc[-1]) if not valid_ids.empty else 0

        start_id = last_id + 1
        new_ids = range(start_id, start_id + len(df_to_add))
        df_to_add.insert(0, 'id', new_ids)

        # 5. Append and Save
        df_updated = pd.concat([df_existing, df_to_add], ignore_index=True)
        
        # IMPORTANT: index=False prevents pandas from adding an extra unnamed column
        df_updated.to_csv(file_path, index=False, encoding='latin1')
        print(f"Added {len(df_to_add)} new games!")
        return df_updated
    else:
        print("No new games found.")
        return df_existing

df_existing = pd.read_csv(file_path, encoding="latin1")
df_existing = update_csv()

def fetch_epic_free_games():
    processed_list = df_existing['game']
    return pd.DataFrame(processed_list)


CACHE_FILE = "game_prices.json"

def load_cache():
    """Loads the local JSON file into a dictionary."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_to_cache(cache):
    """Saves the updated dictionary back to the JSON file."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

def get_release_price_with_cache(game_title, cache):
    # 1. Check if we already have it
    if game_title in cache:
        return cache[game_title]

    # 2. If not in cache, prepare for API call
    print(f"Fetching from API: {game_title}...")
    
    # Stay safe: 1.5 second delay to avoid another 50-minute ban
    time.sleep(5) 
    
    try:
        search_url = f"https://www.cheapshark.com/api/1.0/games?title={game_title}"
        res = requests.get(search_url, timeout=10).json()
        
        if res:
# STEP B: Create a dictionary of {Title: ID} from all search results
            choices = {game['external']: game['gameID'] for game in res}
            
            # STEP C: Use Levenshtein to find the closest match
            best_match, score = process.extractOne(game_title, choices.keys())
# Only proceed if we are 85% sure it's the right game
            if score >= 85:
                game_id = choices[best_match]
                
                # STEP D: Get the specific price details using the best-match ID
                detail_url = f"https://www.cheapshark.com/api/1.0/games?id={game_id}"
                details = requests.get(detail_url, timeout=10).json()
                price = float(details['deals'][0]['retailPrice'])
                
                # 3. Update the cache and save
                cache[game_title] = price
                save_to_cache(cache)
                return price
            else:
                print(f"Low match score ({score}) for {game_title}. Skipping.")
            
    except Exception as e:
        print(f"Error for {game_title}: {e}")
    
    return None

# --- EXECUTION ---
# Load your data
df = update_csv() 
price_cache = load_cache()

if "price" not in df_existing.columns:
    df_existing["price"] = pd.NA

needs_price = df_existing["price"].isna() | (df_existing["price"].astype(str).str.strip() == "")
print(f"Rows missing price: {int(needs_price.sum())}")

if needs_price.any():
    missing_titles = df_existing.loc[needs_price, "game"].dropna().unique()

    title_to_price = {}
    for title in missing_titles:
        title_to_price[title] = get_release_price_with_cache(title, price_cache)

    df_existing.loc[needs_price, "price"] = df_existing.loc[needs_price, "game"].map(title_to_price)

    df_existing.to_csv(file_path, index=False, encoding="latin1")
    print("Saved CSV with newly fetched prices.")
else:
    print("No missing prices — nothing to fetch.")


df_existing = validate_and_clean_data(df_existing)

# 6. SAVE the final, validated version
df_existing.to_csv(file_path, index=False, encoding="latin1")
print("✅ Update complete: Data scraped, enriched, and validated.")