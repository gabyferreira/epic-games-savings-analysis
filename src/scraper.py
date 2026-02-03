import requests # this is to make an api request
import pandas as pd
from datetime import datetime
from tqdm import tqdm
tqdm.pandas()
import time
import json
import os
from thefuzz import process
from processor import validate_and_clean_data, generate_summary_stats, update_readme, calculate_generosity_index, preprocess_for_plotting
import logging
from visualiser import (generate_savings_chart, generate_generosity_chart, 
                        generate_monthly_bar_chart, generate_velocity_chart, 
                        generate_inflation_comparison_chart, generate_market_timing_chart,
                        generate_maturity_histogram, generate_quality_pulse_chart)
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
IGDB_CLIENT_ID = os.getenv('IGDB_CLIENT_ID')
IGDB_CLIENT_SECRET = os.getenv('IGDB_CLIENT_SECRET')


def get_igdb_token():
    """Gets a temporary access token from Twitch."""
    auth_url = f"https://id.twitch.tv/oauth2/token?client_id={IGDB_CLIENT_ID}&client_secret={IGDB_CLIENT_SECRET}&grant_type=client_credentials"
    try:
        res = requests.post(auth_url, timeout=10).json()
        return res.get('access_token')
    except Exception as e:
        logger.error(f"❌ IGDB Auth Failed: {e}")
        return None


def fetch_metadata_from_igdb(game_title, token):
    """Queries IGDB with fuzzy matching to find the best metadata match."""
    if not token: return None, None
    url = "https://api.igdb.com/v4/games"
    headers = {
        'Client-ID': IGDB_CLIENT_ID,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'text/plain'
    }
    
    # We query for the top 5 names to compare them locally
    query = f'search "{game_title}"; fields name, first_release_date, aggregated_rating; limit 5;'
    
    try:
        res = requests.post(url, headers=headers, data=query, timeout=10).json()
        if res:
            # 1. Create a dictionary of {Candidate Name: Candidate Data}
            choices = {game['name']: game for game in res}
            
            # 2. Use Levenshtein to find the best string match
            best_match, score_match = process.extractOne(game_title, choices.keys())
            
            # 3. Validation: Only accept if the match is strong (e.g., > 80%)
            if score_match >= 80:
                logger.info(f"🎯 IGDB Match: '{best_match}' ({score_match}%)")
                game_data = choices[best_match]
                
                # Extract and format date
                ts = game_data.get('first_release_date')
                date_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d') if ts else None
                
                # Extract rating
                rating = game_data.get('aggregated_rating')
                
                return date_str, rating
            else:
                logger.warning(f"⚠️ Poor IGDB match ({score_match}%) for {game_title}")
                
    except Exception as e:
        logger.warning(f"IGDB Error for {game_title}: {e}")
        
    return None, None

file_path = "data/epic_games_data_edited_active8.csv"
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
    df_existing['end_date'] = pd.to_datetime(
        df_existing['end_date'], 
        dayfirst=True, 
        errors='coerce'
    ).dt.strftime('%d-%m-%Y')
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

def get_game_metadata_with_cache(game_title, cache, igdb_token):
    """
    Checks cache for price, publisher, release date, and quality score.
    Fetches from APIs only if data is missing.
    """
    # Initialize entry if new (added aggregated_rating to the template)
    if game_title not in cache:
        cache[game_title] = {
            "price": None, 
            "publisher": "Unknown Publisher", 
            "original_release_date": None,
            "aggregated_rating": None  # <--- Ensure this exists
        }

    # 1. Fetch PRICE (CheapShark)
    if cache[game_title].get("price") is None:
        logger.info(f"💰 Fetching Price for: {game_title}")
        time.sleep(1.0) # Reduced from 10 to 1.0 (10s is very long for CheapShark!)
        try:
            search_url = f"https://www.cheapshark.com/api/1.0/games?title={game_title}"
            res = requests.get(search_url, timeout=10).json()
            if res:
                choices = {game['external']: game['gameID'] for game in res}
                best_match, score_match = process.extractOne(game_title, choices.keys())
                if score_match >= 85:
                    game_id = choices[best_match]
                    detail_url = f"https://www.cheapshark.com/api/1.0/games?id={game_id}"
                    details = requests.get(detail_url, timeout=10).json()
                    cache[game_title]["price"] = float(details['deals'][0]['retailPrice'])
                else:
                    cache[game_title]["price"] = 0.0
            else:
                cache[game_title]["price"] = 0.0          
            save_to_cache(cache)
        except Exception as e:
            logger.warning(f"Price API error for {game_title}: {e}")

    # 2. Fetch PUBLISHER (Steam)
    if cache[game_title].get("publisher") in ["Unknown Publisher", "Publisher Not Found"]:
        logger.info(f"🏢 Fetching Publisher for: {game_title}")
        time.sleep(1.5) 
        publisher = get_publisher_from_steam(game_title)
        cache[game_title]["publisher"] = publisher if publisher != "Unknown Publisher" else "Publisher Not Found"
        save_to_cache(cache)

    # 3. Fetch RELEASE DATE & SCORE (IGDB)
    # Note: Using 'igdb_token' to match your function arguments
    current_date = cache[game_title].get("original_release_date")
    current_score = cache[game_title].get("aggregated_rating")

    # 2. Determine if we REALLY need to hit the API
    # We skip if the date is found OR if we've already tried and failed ("Date Not Found")
    date_is_done = current_date is not None and current_date != "" 
    
    # We skip if the score is a number OR if we've explicitly marked it as failed
    score_is_done = isinstance(current_score, (int, float)) or current_score == "Score Not Found"

    # --- THE "SKIP" GATE ---
    if date_is_done and score_is_done:
        # We have everything (or have already tried everything), skip the API
        return cache[game_title]

    # 3. If we got here, we need to fetch
    if igdb_token:
        logger.info(f"🔍 Fetching Metadata (Date & Score) for: {game_title}")
        time.sleep(0.25) 
        
        release_date, score = fetch_metadata_from_igdb(game_title, igdb_token)

        # Update Date if it was missing or "Date Not Found"
        if not date_is_done:
            cache[game_title]["original_release_date"] = release_date or "Date Not Found"

        # Update Score if it was missing or "Score Not Found"
        if not score_is_done:
            cache[game_title]["aggregated_rating"] = score if score is not None else "Score Not Found"

        save_to_cache(cache)

    return cache[game_title]



# --- EXECUTION ---
# Load data
price_cache = load_cache()
igdb_token = get_igdb_token()
df_existing = pd.read_csv(file_path, encoding="utf-8-sig")

# 2. Ensure all columns exist
for col in ["price", "publisher", "original_release_date", "aggregated_rating"]:
    if col not in df_existing.columns:
        df_existing[col] = pd.NA

# 3. Find games needing ANY piece of data
needs_enrichment = (
    df_existing["price"].isna() | 
    df_existing["publisher"].isna() |
    df_existing["original_release_date"].isna() |
    df_existing["aggregated_rating"].isna()
)

if needs_enrichment.any():
    count = int(needs_enrichment.sum())
    logger.info(f"🔍 Found {count} games needing metadata. Starting IGDB + Steam + CheapShark enrichment...")
    
    for idx in tqdm(df_existing[needs_enrichment].index):
        title = df_existing.at[idx, 'game']
        metadata = get_game_metadata_with_cache(title, price_cache, igdb_token)
        
        # Apply updates to DataFrame
        df_existing.at[idx, 'price'] = metadata.get("price")
        df_existing.at[idx, 'original_release_date'] = metadata.get("original_release_date")
        df_existing.at[idx, 'aggregated_rating'] = metadata.get("aggregated_rating")
        
        pub = metadata.get("publisher")
        if pub not in ["Unknown Publisher", "Publisher Not Found"]:
            df_existing.at[idx, 'publisher'] = pub

    df_existing.to_csv(file_path, index=False, encoding="utf-8-sig", date_format='%d/%m/%Y')

# --- 4. ANALYTICS & CHARTS ---
df_existing = validate_and_clean_data(df_existing)
generosity_df = calculate_generosity_index(df_existing)

# Save the final validated CSV
df_existing.to_csv(file_path, index=False, encoding="utf-8-sig", date_format='%d/%m/%Y')

summary = generate_summary_stats(df_existing, generosity_df)
logger.info(summary)
update_readme(summary)
clean_df = preprocess_for_plotting(df_existing)

try:
    generate_monthly_bar_chart(clean_df)
    generate_savings_chart(clean_df) 
    generate_generosity_chart(generosity_df)
    generate_velocity_chart(clean_df)
    generate_inflation_comparison_chart(clean_df)
    generate_market_timing_chart(clean_df)
    generate_maturity_histogram(clean_df)
    generate_quality_pulse_chart(clean_df)
    logger.info("📈 All charts generated successfully.")
except Exception as e:
    logger.error(f"❌ Failed to generate chart: {e}")