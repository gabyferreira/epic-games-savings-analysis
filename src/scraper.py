import requests # this is to make an api request
import pandas as pd
from datetime import datetime



def update_csv():
    base_url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    file_path = "data/epic_games_data_edited_active.csv"
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
    df_existing = pd.read_csv(file_path, encoding='latin1' )
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
        # --- SAFE ID GENERATION ---
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
    else:
        print("No new games found.")
update_csv()