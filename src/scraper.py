import requests # this is to make an api request
import pandas as pd
from datetime import datetime
from tqdm import tqdm
tqdm.pandas()
import time
import json
import os
from thefuzz import process
from processor import validate_and_clean_data, generate_summary_stats, update_readme
import logging
from visualiser import generate_savings_chart


logger = logging.getLogger(__name__)

file_path = "data/epic_games_data_edited_active7.csv"
try:
    # Force read using 'cp1252' (the specific Windows/Latin encoding that uses 0x92)
    # This will correctly interpret that '0x92' as an apostrophe
    df_existing = pd.read_csv(file_path, encoding="cp1252", engine='python')
    
    df_existing.to_csv(file_path, index=False, encoding="utf-8-sig", date_format='%d/%m/%Y')
    
    print("✅ Migration Successful! Your file is now in professional UTF-8 format.")
    print("🚀 You can now run your main scraper.py without errors.")
    
except Exception as e:
    print(f"❌ Migration failed: {e}")


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
        df_updated.to_csv(file_path, index=False, encoding='utf-8-sig')
        logger.info(f"Added {len(df_to_add)} new games!")
        return df_updated
    else:
        logger.info("No new games found.")
        return df_existing

df_existing = pd.read_csv(file_path, encoding="utf-8-sig")
df_existing = update_csv()


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


def get_publisher_from_steam(game_title):
    try:
        search_url = f"https://store.steampowered.com/api/storesearch/?term={game_title}&l=english&cc=US"
        search_res = requests.get(search_url, timeout=10).json()
        
        if search_res and search_res.get('items'):
            # 1. Create a map of {Title: AppID} from Steam's search results
            choices = {item['name']: item['id'] for item in search_res['items']}
            
            # 2. Use Levenshtein distance to find the best match among the results
            best_match, score = process.extractOne(game_title, choices.keys())
            
            # 3. Only proceed if the match is high (e.g., 85% or better)
            if score >= 85:
                appid = choices[best_match]
                details_url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
                details_res = requests.get(details_url, timeout=10).json()
                
                if details_res and details_res.get(str(appid), {}).get('success'):
                    publishers = details_res[str(appid)]['data'].get('publishers', [])
                    return publishers[0] if publishers else "Unknown Publisher"
            else:
                logger.warning(f"Low match score ({score}) for {game_title} on Steam.")
                
    except Exception as e:
        logger.warning(f"Steam API error for {game_title}: {e}")
    
    return "Unknown Publisher"

def get_game_metadata_with_cache(game_title, cache):
    """
    Checks cache for price and publisher. 
    Fetches from APIs only if we haven't tried before.
    """
    # 1. Initialize the entry
    if game_title not in cache or not isinstance(cache[game_title], dict):
        cache[game_title] = {"price": None, "publisher": "Unknown Publisher"}

    # 2. Fetch PRICE (CheapShark)
    # Only fetch if price is exactly None. 
    # If we found it, it's a float. If we tried and failed, it will be 0.0.
    if cache[game_title].get("price") is None:
        logger.info(f"💰 Fetching Price for: {game_title}")
        time.sleep(10) 
        try:
            search_url = f"https://www.cheapshark.com/api/1.0/games?title={game_title}"
            res = requests.get(search_url, timeout=10).json()
            if res:
                choices = {game['external']: game['gameID'] for game in res}
                best_match, score = process.extractOne(game_title, choices.keys())
                if score >= 85:
                    game_id = choices[best_match]
                    detail_url = f"https://www.cheapshark.com/api/1.0/games?id={game_id}"
                    details = requests.get(detail_url, timeout=10).json()
                    cache[game_title]["price"] = float(details['deals'][0]['retailPrice'])
                else:
                    # Score too low? Mark as 0.0 so we don't try again
                    cache[game_title]["price"] = 0.0
            else:
                # No results at all? Mark as 0.0
                cache[game_title]["price"] = 0.0
            
            save_to_cache(cache)
        except Exception as e:
            logger.warning(f"Price API error for {game_title}: {e}")

    # 3. Fetch PUBLISHER (Steam)
    # Only fetch if it is the default "Unknown Publisher".
    if cache[game_title].get("publisher") == "Unknown Publisher":
        logger.info(f"🏢 Fetching Publisher for: {game_title}")
        time.sleep(1.5)
        publisher = get_publisher_from_steam(game_title)
        
        # If the fetch fails to find a real name, mark it as "Publisher Not Found"
        if publisher == "Unknown Publisher":
            cache[game_title]["publisher"] = "Publisher Not Found"
        else:
            cache[game_title]["publisher"] = publisher
            
        save_to_cache(cache)

    return cache[game_title]


# --- EXECUTION ---
# Load data
update_csv() 
price_cache = load_cache()
df_existing = pd.read_csv(file_path, encoding="utf-8-sig")


for col in ["price", "publisher"]:
    if col not in df_existing.columns:
        df_existing[col] = pd.NA

# 2. Identify rows that are missing ANY metadata
needs_enrichment = (
    df_existing["price"].isna() | 
    df_existing["publisher"].isna()
)

if needs_enrichment.any():
    count = int(needs_enrichment.sum())
    logger.info(f"🔍 Found {count} games needing metadata. Starting enrichment...")
    
    for idx in tqdm(df_existing[needs_enrichment].index):
        title = df_existing.at[idx, 'game']
        
        # 1. Attempt to fetch metadata
        metadata = get_game_metadata_with_cache(title, price_cache)
        publisher = metadata.get("publisher", "Unknown Publisher")
        price = metadata.get("price")

        # 2. Update Price 
        # (Usually fine to update even if 0, as it indicates 'checked')
        df_existing.at[idx, 'price'] = price

        # 3. SMART UPDATE for Publisher
        # Only save to the DataFrame if we got a real result back from Steam.
        # This keeps the CSV cell "Empty/Unknown" so the filter finds it again next time.
        if publisher not in ["Unknown Publisher", "Publisher Not Found"]:
            df_existing.at[idx, 'publisher'] = publisher
            # Explicitly sync the cache to ensure the real name is saved
            price_cache[title]['publisher'] = publisher
        else:
            logger.warning(f"⚠️ Metadata for '{title}' incomplete. Will retry in next run.")
        
        # 4. Frequent Cache Saving
        # During a 600-game backfill, save the cache every loop so you don't 
        # lose progress if the script is interrupted.
        save_to_cache(price_cache)

    # 5. Final Save of the CSV
    df_existing.to_csv(file_path, index=False, encoding="utf-8-sig", date_format='%d/%m/%Y')
    logger.info("✅ Metadata enrichment session complete.")


df_existing = validate_and_clean_data(df_existing)

# 6. SAVE the final, validated version
df_existing.to_csv(file_path, index=False, encoding="utf-8-sig", date_format='%d/%m/%Y')
logger.info("✅ Update complete: Data scraped, enriched, and validated.")
summary = generate_summary_stats(df_existing)
logger.info(summary)
update_readme(summary)

try:
    generate_savings_chart(file_path)
    logger.info("📈 Savings chart generated successfully.")
except Exception as e:
    logger.error(f"❌ Failed to generate chart: {e}")