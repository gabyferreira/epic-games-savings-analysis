import requests # this is to make an api request
import pandas as pd
from datetime import datetime
from tqdm import tqdm
tqdm.pandas()
import time
import json
import os
from thefuzz import process
from constants import SHARED_UNIVERSES
from processor import validate_and_clean_data, generate_summary_stats, update_readme, calculate_generosity_index, preprocess_for_plotting
import logging
from visualiser import (generate_savings_chart, generate_generosity_chart, 
                        generate_monthly_bar_chart, generate_velocity_chart, 
                        generate_inflation_comparison_chart, generate_market_timing_chart,
                        generate_maturity_histogram, generate_quality_pulse_chart, generate_hype_cycle_chart, generate_hype_heatmap)
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
    
def get_igdb_headers(token):
    """A helper to provide headers to any IGDB function."""
    return {
        'Client-ID': IGDB_CLIENT_ID,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'text/plain'
    }


def fetch_metadata_from_igdb(game_title, token):
    """Queries IGDB with fuzzy matching to find the best metadata match."""
    if not token: return None, None
    url = "https://api.igdb.com/v4/games"
    
    headers = get_igdb_headers(token)
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

def fetch_sequel_metadata(game_title, token):
    """
    Finds the franchise (collection) and retrieves the release date 
    of the next chronological entry.
    """
    if not token: return None
    url = "https://api.igdb.com/v4/games"
    
    headers = get_igdb_headers(token)

    # 1. Get the collection ID for the current game
    # We use a broad search but limit to 1 to find the franchise link
    search_query = f'search "{game_title}"; fields collection; limit 1;'
    
    try:
        search_res = requests.post(url, headers=headers, data=search_query, timeout=10).json()
        
        if search_res and 'collection' in search_res[0]:
            collection_id = search_res[0]['collection']
            
            # 2. Find all games in that franchise
            # We sort by date ascending to find the 'next' game in the series
            sequel_query = f'fields name, first_release_date; where collection = {collection_id}; sort first_release_date asc; limit 10;'
            sequel_res = requests.post(url, headers=headers, data=sequel_query, timeout=10).json()
            
            return sequel_res # Return the list for local processing
            
    except Exception as e:
        logger.warning(f"Failed to fetch franchise data for {game_title}: {e}")
        
    return None

file_path = "data/epic_games_data_edited_active8.csv"
try:
    # Try reading with utf-8-sig first, fallback to cp1252 if it fails
    try:
        df_existing = pd.read_csv(file_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df_existing = pd.read_csv(file_path, encoding="cp1252")
    
    # Immediately save back as clean UTF-8
    df_existing.to_csv(file_path, index=False, encoding="utf-8-sig")
    logger.info("✅ Migration Successful!")
except Exception as e:
    logger.warning(f"⚠️ Migration note: {e}")


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

def fetch_sequel_from_wikidata(game_title, publisher_name):
    """
    Queries Wikidata using both Title and Publisher for high-precision matching.
    Helps resolve 'shared universes' and prevents name-collision errors.
    """
    endpoint_url = "https://query.wikidata.org/sparql"
    
    # We filter by Publisher (P123) or Developer (P178) to ensure we have the right IP
    query = f"""
    SELECT DISTINCT ?gameLabel ?date WHERE {{
      ?item rdfs:label "{game_title}"@en;
            (wdt:P123|wdt:P178) ?pub.
      ?pub rdfs:label ?pubLabel.
      FILTER(CONTAINS(LCASE(?pubLabel), LCASE("{publisher_name}")))
      
      ?item wdt:P179 ?series.
      ?game wdt:P179 ?series;
            wdt:P577 ?date.
            
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }} ORDER BY ?date
    """
    
    try:
        # User-agent is required for Wikidata's fair use policy
        headers = {'User-Agent': 'EpicGamesProject/1.0 (contact: your-email@example.com)', 'Accept': 'application/sparql-results+json'}
        res = requests.get(endpoint_url, params={'query': query, 'format': 'json'}, headers=headers, timeout=10).json()
        results = res['results']['bindings']
        
        # Format the results into a clean list
        return [{'name': r['gameLabel']['value'], 'date': r['date']['value'][:10]} for r in results]
    except Exception as e:
        logger.warning(f"🌐 Wikidata SPARQL precision lookup failed for {game_title}: {e}")
        return None

def get_game_metadata_with_cache(game_title, cache, igdb_token, promo_start):
    """
    Consolidated metadata fetcher. Handles Price, Publisher, 
    and deep IGDB lookups (Score, Date, Sequels) in one pass.
    """
    # 1. Initialize or get existing entry
    if game_title not in cache:
        cache[game_title] = {
            "price": None, "publisher": "Unknown Publisher", 
            "original_release_date": None, "aggregated_rating": None,
            "next_sequel_date": None, "is_strategic_hype": False
        }
    cache[game_title]["start_date"] = promo_start
    game_entry = cache[game_title]
    has_changed = False

    # 2. Fetch PRICE (CheapShark)
    if game_entry.get("price") is None:
        logger.info(f"💰 Price Search: {game_title}")
        time.sleep(1.0)
        try:
            search_url = f"https://www.cheapshark.com/api/1.0/games?title={game_title}"
            res = requests.get(search_url, timeout=10).json()
            if res:
                choices = {g['external']: g['gameID'] for g in res}
                best_match, score = process.extractOne(game_title, choices.keys())
                if score >= 85:
                    d_url = f"https://www.cheapshark.com/api/1.0/games?id={choices[best_match]}"
                    details = requests.get(d_url, timeout=10).json()
                    game_entry["price"] = float(details['deals'][0]['retailPrice'])
                else:
                    game_entry["price"] = 0.0
            else:
                game_entry["price"] = 0.0
            has_changed = True
        except Exception as e:
            logger.warning(f"Price error for {game_title}: {e}")

    # 3. Fetch PUBLISHER (Steam)
    if game_entry.get("publisher") in ["Unknown Publisher", "Publisher Not Found"]:
        logger.info(f"🏢 Publisher Search: {game_title}")
        time.sleep(1.2)
        pub = get_publisher_from_steam(game_title)
        game_entry["publisher"] = pub if pub != "Unknown Publisher" else "Publisher Not Found"
        has_changed = True

    # 4. DEEP IGDB LOOKUP (Consolidated Date, Score, and Sequel logic)
    # Check if we are missing basic metadata OR franchise info
   # 4. DEEP ENRICHMENT (Decoupled Logic)
    
# ----------------------------
# A) BASIC METADATA FIRST
# ----------------------------
    missing_date = game_entry.get("original_release_date") in [None, "Date Not Found"]
    missing_score = game_entry.get("aggregated_rating") in [None, "Score Not Found"]
    missing_meta = missing_date or missing_score

    if missing_meta and igdb_token:
        logger.info(f"📅 Fetching Basic Metadata: {game_title}")
        rel_date, score = fetch_metadata_from_igdb(game_title, igdb_token)

        # Only set what’s missing (don’t overwrite good values)
        if missing_date:
            game_entry["original_release_date"] = rel_date or "Date Not Found"
            has_changed = True

        if missing_score:
            game_entry["aggregated_rating"] = score or "Score Not Found"
            has_changed = True


    # Refresh the current release date AFTER metadata enrichment
    current_rel_date = game_entry.get("original_release_date")
    current_promotion_date = game_entry.get("start_date")


    # ----------------------------
    # B) FRANCHISE / SEQUEL AFTER
    # ----------------------------

    missing_sequel = game_entry.get("next_sequel_date") is None

    if missing_sequel and current_rel_date not in [None, "Date Not Found"]:
        logger.info(f"🔗 Searching Franchise Context: {game_title}")
        franchise_list = None
        
        # 1. Tier 1: Manual Map
        manual = SHARED_UNIVERSES.get(game_title)
        if manual:
            game_entry.update({
                "next_sequel_name": manual["name"],
                "next_sequel_date": manual["date"],
                "is_strategic_hype": True 
            })
            has_changed = True
        else:
            # 2. Tiers 2 & 3: API Lookups
            publisher = game_entry.get("publisher", "")
            franchise_list = fetch_sequel_from_wikidata(game_title, publisher)

            if not franchise_list and igdb_token:
                logger.info(f"📡 Fallback to IGDB for {game_title}")
                franchise_list = fetch_sequel_metadata(game_title, igdb_token)

        # 3. Process API Results
        if franchise_list:
            try:
                # 🛡️ Force Clean Timestamp conversion
                # dayfirst=True is vital if your CSV is DD-MM-YYYY
                cur_dt = pd.to_datetime(current_promotion_date, dayfirst=True)
                cur_ts = cur_dt.timestamp()
                
                future = []
                for g in franchise_list:
                    g_ts = 0
                    # Standardize API dates to timestamps
                    raw_g_date = g.get("date") or g.get("first_release_date")
                    if raw_g_date:
                        try:
                            # Handle both strings (Wikidata) and integers (IGDB)
                            g_dt = pd.to_datetime(raw_g_date, unit='s' if isinstance(raw_g_date, int) else None)
                            g_ts = g_dt.timestamp()
                        except: continue

                    # 🎯 The Comparison
                    if g_ts > cur_ts:
                        future.append((g, g_ts))

                if future:
                    future.sort(key=lambda x: x[1])
                    next_game, next_ts = future[0]
                    s_name = next_game.get("name") or next_game.get("gameLabel")
                    s_date = datetime.utcfromtimestamp(next_ts).strftime("%Y-%m-%d")

                    # Calculate Lead Time
                    lead_time_days = int((next_ts - cur_ts) / 86400)
                    is_strategic = 0 <= lead_time_days <= 90

                    game_entry.update({
                        "next_sequel_name": s_name,
                        "next_sequel_date": s_date,
                        "is_strategic_hype": is_strategic
                    })
                    logger.info(f"✅ Found Sequel: {s_name} ({lead_time_days} days away)")
                else:
                    # 🔍 This is where you were getting stuck
                    logger.info(f"ℹ️ No release found AFTER {cur_dt.date()} for {game_title}")
                    game_entry.update({
                        "next_sequel_name": "No Future Sequel Found",
                        "next_sequel_date": "N/A",
                        "is_strategic_hype": False
                    })
                has_changed = True

            except Exception as e:
                logger.error(f"❌ Processing Error for {game_title}: {e}")
        
        # 4. Final Fallback (No series found at all)
        elif not game_entry.get("next_sequel_name"):
            game_entry.update({
                "next_sequel_name": "Standalone",
                "next_sequel_date": "N/A", 
                "is_strategic_hype": False
            })
            has_changed = True
    
    if has_changed:
        save_to_cache(cache)

    return game_entry



# --- EXECUTION ---
# Load data
price_cache = load_cache()
igdb_token = get_igdb_token()
df_existing = pd.read_csv(file_path, encoding="utf-8-sig")

# 2. Ensure all columns exist
for col in ["price", "publisher", "original_release_date", "aggregated_rating", "next_sequel_date", "next_sequel_name"]:
    if col not in df_existing.columns:
        df_existing[col] = pd.NA

# 3. Find games needing ANY piece of data
needs_enrichment = (
    df_existing["price"].isna() | 
    df_existing["publisher"].isna() |
    df_existing["original_release_date"].isna() |
    df_existing["aggregated_rating"].isna() |
    df_existing["next_sequel_date"].isna() |
    df_existing["next_sequel_name"].isna()
)

if needs_enrichment.any():
    count = int(needs_enrichment.sum())
    logger.info(f"🔍 Found {count} games needing metadata. Starting IGDB + Steam + CheapShark enrichment...")
    
    for idx in tqdm(df_existing[needs_enrichment].index):
        title = df_existing.at[idx, 'game']
        promo_start = df_existing.at[idx, 'start_date']
        metadata = get_game_metadata_with_cache(title, price_cache, igdb_token, promo_start)
        
        # Apply updates to DataFrame
        df_existing.at[idx, 'price'] = metadata.get("price")
        df_existing.at[idx, 'original_release_date'] = metadata.get("original_release_date")
        rating_val = metadata.get("aggregated_rating")
        if rating_val and rating_val != "Score Not Found":
            # Convert to float to keep Pandas happy and allow math later
            df_existing.at[idx, 'aggregated_rating'] = float(rating_val)
        else:
            # Use pd.NA (the standard for missing data) instead of a string
            df_existing.at[idx, 'aggregated_rating'] = pd.NA
        df_existing.at[idx, 'next_sequel_date'] = metadata.get("next_sequel_date")
        df_existing.at[idx, 'next_sequel_name'] = metadata.get("next_sequel_name")
        

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
    generate_hype_cycle_chart(clean_df)
    generate_hype_heatmap(clean_df)
    logger.info("📈 All charts generated successfully.")
except Exception as e:
    logger.error(f"❌ Failed to generate chart: {e}")