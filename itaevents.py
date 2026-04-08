import xml.etree.ElementTree as ET
import random
import uuid
import fetcher
import json
import os
import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote_plus  # Add this import


MFPLINK = "https://scemopalle-easyproxy.hf.space"     # non mettere lo / finale al link
MFPPSW = "Milito22."


# Constants
REFERER = "forcedtoplay.xyz"
ORIGIN = "forcedtoplay.xyz"
PROXY = f"{MFPLINK}/extractor/video?host=dlstreams&url="
PROXY2 = f"&redirect_stream=true&api_password={MFPPSW}"
HEADER = f"&h_user-agent=Mozilla%2F5.0+%28Windows+NT+10.0%3B+Win64%3B+x64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F133.0.0.0+Safari%2F537.36&h_referer=https%3A%2F%2F{REFERER}%2F&h_origin=https%3A%2F%2F{ORIGIN}"
NUM_CHANNELS = 10000
DADDY_JSON_FILE = "daddyliveSchedule.json"
M3U8_OUTPUT_FILE = "itaevents.m3u8"
LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddsport.png"
SKYSTR = "help"
GUARCAL = "online"
DADDY= "top"

# Add a cache for logos to avoid repeated requests
LOGO_CACHE = {}

# Add a cache for logos loaded from the local file
LOCAL_LOGO_CACHE = [] # Changed to a list to store URLs directly
LOCAL_LOGO_FILE = "guardacalcio_image_links.txt"

# Define keywords for filtering channels
EVENT_KEYWORDS = ["italy", "atp", "tennis", "basketball", "formula uno", "f1", "motogp", "moto gp", "volley", "serie a", "serie b", "serie c", "uefa champions", "uefa europa",
                 "conference league", "coppa italia", "premier league", "bundesliga", "la liga", "ligue 1"]

# Headers for requests
headers = {
    "Accept": "*/*",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6,ru;q=0.5",
    "Priority": "u=1, i",
    "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    "Sec-Ch-UA-Mobile": "?0",
    "Sec-Ch-UA-Platform": "Windows",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Storage-Access": "active",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

# Remove existing M3U8 file if it exists
if os.path.exists(M3U8_OUTPUT_FILE):
    os.remove(M3U8_OUTPUT_FILE)

def load_local_logos():
    """Loads logo links from the local file into a cache."""
    if not LOCAL_LOGO_CACHE: # Load only once
        try:
            with open(LOCAL_LOGO_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line: # Add non-empty lines to the list
                        LOCAL_LOGO_CACHE.append(line)
            print(f"Caricati {len(LOCAL_LOGO_CACHE)} loghi dal file locale: {LOCAL_LOGO_FILE}")
        except FileNotFoundError:
            print(f"File locale dei loghi non trovato: {LOCAL_LOGO_FILE}. Procedo con lo scraping web.")
        except Exception as e:
            print(f"Errore durante il caricamento del file locale dei loghi {LOCAL_LOGO_FILE}: {e}")

def get_dynamic_logo(event_name):
    """
    Cerca immagini dinamiche per eventi di Serie A, Serie B, Serie C, La Liga, Premier League, Bundesliga e Ligue 1
    """
    # Estrai i nomi delle squadre dall'evento per usarli come chiave di cache
    teams_match = re.search(r':\s*([^:]+?)\s+vs\s+([^:]+?)(?:\s+[-|]|$)', event_name, re.IGNORECASE)

    if not teams_match:
        # Try alternative format "Team1 - Team2"
        teams_match = re.search(r'([^:]+?)\s+-\s+([^:]+?)(?:\s+[-|]|$)', event_name, re.IGNORECASE)

    # Crea una chiave di cache specifica per questa partita
    cache_key = None
    team1 = None
    team2 = None
    if teams_match:
        team1 = teams_match.group(1).strip()
        team2 = teams_match.group(2).strip()
        cache_key = f"{team1} vs {team2}"

        # Check if we already have this specific match in LOGO_CACHE (from web scraping)
        if cache_key in LOGO_CACHE:
            print(f"Logo trovato in cache (web) per: {cache_key}")
            return LOGO_CACHE[cache_key]

        # Check if we have this specific match in LOCAL_LOGO_CACHE (from local file)
        load_local_logos() # Ensure local logos are loaded

        # --- Nuova logica per cercare nomi squadre negli URL locali ---
        if LOCAL_LOGO_CACHE:
            team1_lower = team1.lower() if team1 else ""
            team2_lower = team2.lower() if team2 else ""

            for logo_url in LOCAL_LOGO_CACHE:
                logo_url_lower = logo_url.lower()
                # Check if both team names are in the URL (case-insensitive)
                if team1_lower and team2_lower and team1_lower in logo_url_lower and team2_lower in logo_url_lower:
                     print(f"Logo trovato nel file locale per: {cache_key} -> {logo_url}")
                     # Add to main cache for future use
                     if cache_key:
                         LOGO_CACHE[cache_key] = logo_url
                     return logo_url
                # Check if at least one team name is in the URL (partial match fallback)
                elif (team1_lower and team1_lower in logo_url_lower) or (team2_lower and team2_lower in logo_url_lower):
                     print(f"Logo parziale trovato nel file locale per: {cache_key} -> {logo_url}")
                     # Add to main cache for future use
                     if cache_key:
                         LOGO_CACHE[cache_key] = logo_url
                     return logo_url
        # --- Fine nuova logica ---


    # Verifica se l'evento è di Serie A o altre leghe
    is_serie_a_or_other_leagues = any(league in event_name for league in ["Italy - Serie A :", "La Liga :", "Premier League :", "Bundesliga :", "Ligue 1 :"])
    is_serie_b_or_c = any(league in event_name for league in ["Italy - Serie B :", "Italy - Serie C :"])
    is_uefa_or_coppa = any(league in event_name for league in ["UEFA Champions League :", "UEFA Europa League :", "Conference League :", "Coppa Italia :"])

    if is_serie_a_or_other_leagues:
        print(f"Evento Serie A o altre leghe rilevato: {event_name}")
    elif is_serie_b_or_c:
        print(f"Evento Serie B o Serie C rilevato: {event_name}")
    elif is_uefa_or_coppa:
        print(f"Evento UEFA o Coppa Italia rilevato: {event_name}")
    else:
        print(f"Evento non di Serie A, Serie B, Serie C o altre leghe: {event_name}")
        # If no specific league and not found in local file/web cache, return default
        if cache_key:
            LOGO_CACHE[cache_key] = LOGO
        return LOGO

    # Se non abbiamo ancora estratto i nomi delle squadre, fallo ora (dopo aver controllato cache e file locale)
    if not teams_match:
        print(f"Non sono riuscito a estrarre i nomi delle squadre da: {event_name}")
        return LOGO

    team1 = teams_match.group(1).strip()
    team2 = teams_match.group(2).strip()

    # Normalize team names by removing non-city or non-team names
    def normalize_team_name(team_name):
        # Example normalization logic: remove common non-city/team words
        words_to_remove = ["calcio", "fc", "club", "united", "city", "ac", "sc", "sport", "team"]
        normalized_name = ' '.join(word for word in team_name.split() if word.lower() not in words_to_remove)
        return normalized_name.strip()

    team1_normalized = normalize_team_name(team1)
    team2_normalized = normalize_team_name(team2)

    # Special case for Bayern München and Internazionale
    if "bayern" in team1.lower() or "bayern" in team1_normalized.lower():
        team1_normalized = "Bayern"
    elif "bayern" in team2.lower() or "bayern" in team2_normalized.lower():
        team2_normalized = "Bayern"

    if "internazionale" in team1.lower() or "inter" in team1.lower():
        team1_normalized = "Inter"
    elif "internazionale" in team2.lower() or "inter" in team2.lower():
        team2_normalized = "Inter"

    print(f"Squadre normalizzate: '{team1_normalized}' vs '{team2_normalized}'")

    try:
        # --- Inizio logica di scraping web (originale) ---
        # First try to fetch logos from guardacalcio.{GUARCAL}
        guardacalcio_url = f"https://vod.direttecommunity.{GUARCAL}/partite-streaming.html"
        headers_guardacalcio = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }

        print(f"Cercando logo per {team1_normalized} vs {team2_normalized} su guardacalcio.{GUARCAL}...")

        response = requests.get(guardacalcio_url, headers=headers_guardacalcio, timeout=10)
        html_content = response.text

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Cerca tutte le immagini nella pagina
        img_tags = soup.find_all('img')
        print(f"Trovate {len(img_tags)} immagini su guardacalcio.{GUARCAL}")

        # Cerca immagini che contengono i nomi delle squadre nel src o nell'alt
        for img in img_tags:
            if img.has_attr('src'):
                src = img['src']
                alt = img.get('alt', '')

                # Normalizza src e alt per la ricerca
                src_normalized = src.lower()
                alt_normalized = alt.lower()

                # Verifica se il nome di una delle squadre è presente nel src o nell'alt
                if (team1_normalized.lower() in src_normalized or team1_normalized.lower() in alt_normalized or
                    team2_normalized.lower() in src_normalized or team2_normalized.lower() in alt_normalized):

                    # Assicurati che l'URL sia assoluto
                    if src.startswith('http'):
                        logo_url = src
                    else:
                        # Costruisci URL assoluto
                        base_url = f"https://vod.direttecommunity.{GUARCAL}"
                        if src.startswith('/'):
                            logo_url = base_url + src
                        else:
                            logo_url = base_url + '/' + src

                    print(f"Trovato logo su guardacalcio.{GUARCAL}: {logo_url}")
                    if cache_key:
                        LOGO_CACHE[cache_key] = logo_url
                    return logo_url

        # If no logo found on guardacalcio.{GUARCAL}, try skystreaming.{SKYSTR}
        print(f"Nessun logo trovato su guardacalcio.{GUARCAL}, cercando su skystreaming.{SKYSTR}...")

        # Determina l'URL di skystreaming in base al tipo di evento
        skystreaming_base_url = f"https://skystreaming.{SKYSTR}/"

        # Seleziona l'URL appropriato in base al tipo di evento
        if "Italy - Serie A :" in event_name:
            skystreaming_url = f"{skystreaming_base_url}channel/video/serie-a"
        elif "La Liga :" in event_name:
            skystreaming_url = f"{skystreaming_base_url}channel/video/la-liga"
        elif "Premier League :" in event_name:
            skystreaming_url = f"{skystreaming_base_url}channel/video/english-premier-league"
        elif "Bundesliga :" in event_name:
            skystreaming_url = f"{skystreaming_base_url}channel/video/bundesliga"
        elif "Ligue 1 :" in event_name:
            skystreaming_url = f"{skystreaming_base_url}channel/video/ligue-1"
        elif "Italy - Serie B :" in event_name:
            skystreaming_url = f"{skystreaming_base_url}channel/video/a-serie-b"
        elif "Italy - Serie C :" in event_name:
            skystreaming_url = f"{skystreaming_base_url}channel/video/italia-serie-c"
        else:
            skystreaming_url = skystreaming_base_url

        headers_skystreaming = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }

        print(f"Cercando logo per {team1_normalized} vs {team2_normalized} su skystreaming.{SKYSTR}...")

        response = requests.get(skystreaming_url, headers=headers_skystreaming, timeout=10)
        html_content = response.text

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Cerca span con class="mediabg" e style che contiene l'immagine
        media_spans = soup.find_all('span', class_='mediabg')
        print(f"Trovati {len(media_spans)} span con class='mediabg' su skystreaming.{SKYSTR}")

        # Cerca span che contengono i nomi delle squadre nel testo
        found_match = False
        for span in media_spans:
            span_text = span.text.lower()
            if (team1_normalized.lower() in span_text and team2_normalized.lower() in span_text) or \
               (team1.lower() in span_text and team2.lower() in span_text):
                style = span.get('style', '')
                if 'background-image:url(' in style:
                    # Estrai l'URL dell'immagine
                    match = re.search(r'background-image:url\((.*?)\)', style)
                    if match:
                        logo_url = match.group(1)
                        print(f"Trovato logo specifico su {skystreaming_url}: {logo_url}")
                        if cache_key:
                            LOGO_CACHE[cache_key] = logo_url
                        found_match = True
                        return logo_url

        # Se non abbiamo trovato una corrispondenza esatta, cerchiamo una corrispondenza parziale
        if not found_match:
            for span in media_spans:
                span_text = span.text.lower()
                if (team1_normalized.lower() in span_text or team2_normalized.lower() in span_text) or \
                   (team1.lower() in span_text or team2.lower() in span_text):
                    style = span.get('style', '')
                    if 'background-image:url(' in style:
                        # Estrai l'URL dell'immagine
                        match = re.search(r'background-image:url\((.*?)\)', style)
                        if match:
                            logo_url = match.group(1)
                            print(f"Trovato logo parziale su {skystreaming_url}: {logo_url}")
                            if cache_key:
                                LOGO_CACHE[cache_key] = logo_url
                            return logo_url

        # Se non troviamo nulla nella pagina specifica, proviamo con la homepage come fallback
        if skystreaming_url != skystreaming_base_url:
            print(f"Nessun logo trovato nella pagina specifica, cercando nella homepage di skystreaming.{SKYSTR}...")

            response = requests.get(skystreaming_base_url, headers=headers_skystreaming, timeout=10)
            html_content = response.text

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Cerca span con class="mediabg" e style che contiene l'immagine
            media_spans = soup.find_all('span', class_='mediabg')
            print(f"Trovati {len(media_spans)} span con class='mediabg' nella homepage")

            # Cerca span che contengono i nomi delle squadre nel testo
            for span in media_spans:
                span_text = span.text.lower()
                if (team1_normalized.lower() in span_text and team2_normalized.lower() in span_text) or \
                   (team1.lower() in span_text and team2.lower() in span_text):
                    style = span.get('style', '')
                    if 'background-image:url(' in style:
                        # Estrai l'URL dell'immagine
                        match = re.search(r'background-image:url\((.*?)\)', style)
                        if match:
                            logo_url = match.group(1)
                            print(f"Trovato logo specifico nella homepage: {logo_url}")
                            if cache_key:
                                LOGO_CACHE[cache_key] = logo_url
                            return logo_url

            # Se non abbiamo trovato una corrispondenza esatta, cerchiamo una corrispondenza parziale
            for span in media_spans:
                span_text = span.text.lower()
                if (team1_normalized.lower() in span_text or team2_normalized.lower() in span_text) or \
                   (team1.lower() in span_text or team2.lower() in span_text):
                    style = span.get('style', '')
                    if 'background-image:url(' in style:
                        # Estrai l'URL dell'immagine
                        match = re.search(r'background-image:url\((.*?)\)', style)
                        if match:
                            logo_url = match.group(1)
                            print(f"Trovato logo parziale nella homepage: {logo_url}")
                            if cache_key:
                                LOGO_CACHE[cache_key] = logo_url
                            return logo_url

        # Se non troviamo nulla, usa il logo di default
        print(f"Nessun logo trovato, uso il logo di default")
        if cache_key:
            LOGO_CACHE[cache_key] = LOGO
        return LOGO
        # --- Fine logica di scraping web (originale) ---

    except Exception as e:
        print(f"Error fetching logo for {team1_normalized} vs {team2_normalized}: {e}")
        import traceback
        traceback.print_exc()
        return LOGO

def generate_unique_ids(count, seed=42):
    random.seed(seed)
    return [str(uuid.UUID(int=random.getrandbits(128))) for _ in range(count)]

def loadJSON(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_stream_link(dlhd_id, event_name="", channel_name="", max_retries=3):
    print(f"Getting stream link for channel ID: {dlhd_id} - {event_name} on {channel_name}...")
    
    # Verifica se è un canale Tennis Stream
    if channel_name and "Tennis Stream" in channel_name:
        print(f"Canale Tennis Stream rilevato, utilizzo link fisso per: {event_name}")
        return "https://dlstreams.top/watch.php?id=576"
    
    # Restituisci direttamente l'URL senza fare richieste HTTP
    return f"https://dlstreams.top/watch.php?id={dlhd_id}"

    # Verifica se è un canale tennis
    is_tennis_channel = "tennis" in event_name.lower() or "atp" in event_name.lower() or "wta" in event_name.lower()
    
    try:
        # Semplice richiesta all'URL senza elaborazione complessa
        response = requests.get(
            f"https://dlstreams.top/watch.php?id={dlhd_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        # Restituisci direttamente l'URL
        return f"https://dlstreams.top/watch.php?id={dlhd_id}"
        
    except requests.exceptions.RequestException as e:
        # Se è un canale tennis con errore 404, restituisci l'URL placeholder
        if is_tennis_channel and "404" in str(e):
            print(f"Tennis channel with 404 error, returning placeholder URL for: {event_name}")
            return TENNIS_PLACEHOLDER_URL
        
        print(f"Errore durante il recupero del link per il canale {dlhd_id}: {e}")
        return None
    except Exception as e:
        print(f"Errore generale durante il recupero del link per il canale {dlhd_id}: {e}")
        return None
    
    # Imposta il numero di tentativi in base al tipo di canale
    actual_max_retries = 1 if is_tennis_channel else max_retries
    
    base_timeout = 10  # Base timeout in seconds

    for attempt in range(actual_max_retries):
        try:
            # Use timeout for all requests
            response = requests.get(
                f"https://dlstreams.top/watch.php?id={dlhd_id}",
                headers=headers,
                timeout=base_timeout
            )
            response.raise_for_status()
            response.encoding = 'utf-8'

            response_text = response.text
            if not response_text:
                print(f"Warning: Empty response received for channel ID: {dlhd_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    # Calculate exponential backoff with jitter
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                return None

            soup = BeautifulSoup(response_text, 'html.parser')
            iframe = soup.find('iframe', id='thatframe')

            if iframe is None:
                print(f"Debug: iframe with id 'thatframe' NOT FOUND for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                return None

            if iframe and iframe.get('src'):
                real_link = iframe.get('src')
                parent_site_domain = real_link.split('/premiumtv')[0]
                server_key_link = (f'{parent_site_domain}/server_lookup.php?channel_id=premium{dlhd_id}')
                server_key_headers = headers.copy()
                server_key_headers["Referer"] = f"https://newembedplay.xyz/premiumtv/daddylivehd.php?id={dlhd_id}"
                server_key_headers["Origin"] = "https://newembedplay.xyz"
                server_key_headers["Sec-Fetch-Site"] = "same-origin"

                response_key = requests.get(
                    server_key_link,
                    headers=server_key_headers,
                    allow_redirects=False,
                    timeout=base_timeout
                )

                # Add adaptive delay between requests
                time.sleep(random.uniform(1, 3))
                response_key.raise_for_status()

                try:
                    server_key_data = response_key.json()
                except json.JSONDecodeError:
                    print(f"JSON Decode Error for channel ID {dlhd_id}: Invalid JSON response: {response_key.text[:100]}...")
                    if attempt < max_retries - 1:
                        sleep_time = (2 ** attempt) + random.uniform(0, 1)
                        print(f"Retrying in {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)
                        continue
                    return None

                if 'server_key' in server_key_data:
                    server_key = server_key_data['server_key']
                    stream_url = f"https://{server_key}new.newkso.ru/{server_key}/premium{dlhd_id}/mono.m3u8"
                    print(f"Stream URL retrieved for channel ID: {dlhd_id} - {event_name} on {channel_name}")
                    return stream_url
                else:
                    print(f"Error: 'server_key' not found in JSON response from {server_key_link} (attempt {attempt+1}/{max_retries})")
                    if attempt < max_retries - 1:
                        sleep_time = (2 ** attempt) + random.uniform(0, 1)
                        print(f"Retrying in {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)
                        continue
                    return None
            else:
                print(f"Error: iframe with id 'thatframe' found, but 'src' attribute is missing for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                return None

        except requests.exceptions.Timeout:
            print(f"Timeout error for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                continue
            return None

        except requests.exceptions.RequestException as e:
            print(f"Request Exception for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries}): {e}")
            # Se è l'ultimo tentativo e si tratta di un canale tennis con errore 404
            if is_tennis_channel and "404" in str(e):
                print(f"Tennis channel with 404 error, returning placeholder URL for: {event_name}")
                # Restituisci l'URL placeholder per i canali tennis
                return TENNIS_PLACEHOLDER_URL
            
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                return None
    
            return None

        except Exception as e:
            print(f"General Exception for channel ID {dlhd_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                continue
            return None

    return None  # If we get here, all retries failed

def clean_group_title(sport_key):
    """Clean the sport key to create a proper group-title"""
    # More robust HTML tag removal
    import re
    clean_key = re.sub(r'<[^>]+>', '', sport_key).strip()

    # If empty after cleaning, return original key
    if not clean_key:
        clean_key = sport_key.strip()

    # Convert to title case to standardize
    return clean_key.title()

def should_include_channel(channel_name, event_name, sport_key):
    """Check if channel should be included based on keywords"""
    combined_text = (channel_name + " " + event_name + " " + sport_key).lower()

    # Check if any keyword is present in the combined text
    for keyword in EVENT_KEYWORDS:
        if keyword.lower() in combined_text:
            return True

    return False

def process_events():
    # Fetch JSON schedule
    # fetcher.fetchHTML(DADDY_JSON_FILE, "https://daddylive.dad/schedule/schedule-generated.json")

    # Load JSON data
    dadjson = loadJSON(DADDY_JSON_FILE)

    # Counters
    total_events = 0
    skipped_events = 0
    filtered_channels = 0
    processed_channels = 0

    # Define categories to exclude
    excluded_categories = [
        "TV Shows", "Cricket", "Aussie rules", "Snooker", "Baseball",
        "Biathlon", "Cross Country", "Horse Racing", "Ice Hockey",
        "Waterpolo", "Golf", "Darts", "Cycling", "Badminton", "Handball"
    ]

    # First pass to gather category statistics
    category_stats = {}
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
                clean_sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()
                if clean_sport_key not in category_stats:
                    category_stats[clean_sport_key] = 0
                category_stats[clean_sport_key] += len(sport_events)
        except (KeyError, TypeError):
            pass

    # Print category statistics
    print("\n=== Available Categories ===")
    for category, count in sorted(category_stats.items()):
        excluded = "EXCLUDED" if category in excluded_categories else ""
        print(f"{category}: {count} events {excluded}")
    print("===========================\n")

    # Generate unique IDs for channels
    unique_ids = generate_unique_ids(NUM_CHANNELS)

    # Open M3U8 file with header
    with open(M3U8_OUTPUT_FILE, 'w', encoding='utf-8') as file:
        file.write('#EXTM3U\n')

    # Second pass to process events
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
                clean_sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()
                total_events += len(sport_events)

                # Skip only exact category matches
                if clean_sport_key in excluded_categories:
                    skipped_events += len(sport_events)
                    continue

                for game in sport_events:
                    for channel in game.get("channels", []):
                        try:
                            # Clean and format day
                            clean_day = day.replace(" - Schedule Time UK GMT", "")
                            # Rimuovi completamente i suffissi ordinali (st, nd, rd, th)
                            clean_day = clean_day.replace("st ", " ").replace("nd ", " ").replace("rd ", " ").replace("th ", " ")
                            # Rimuovi anche i suffissi attaccati al numero (1st, 2nd, 3rd, etc.)
                            import re
                            clean_day = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', clean_day)

                            print(f"Original day: '{day}'")
                            print(f"Clean day after processing: '{clean_day}'")

                            day_parts = clean_day.split()
                            print(f"Day parts: {day_parts}")  # Debug per vedere i componenti della data

                            # Handle various date formats with better validation
                            day_num = None
                            month_name = None
                            year = None

                            if len(day_parts) >= 4:  # Standard format: Weekday Month Day Year
                                weekday = day_parts[0]
                                # Verifica se il secondo elemento contiene lettere (è il mese) o numeri (è il giorno)
                                if any(c.isalpha() for c in day_parts[1]):
                                    # Formato: Weekday Month Day Year
                                    month_name = day_parts[1]
                                    day_num = day_parts[2]
                                elif any(c.isalpha() for c in day_parts[2]):
                                    # Formato: Weekday Day Month Year
                                    day_num = day_parts[1]
                                    month_name = day_parts[2]
                                else:
                                    # Se non riusciamo a determinare, assumiamo il formato più comune
                                    day_num = day_parts[1]
                                    month_name = day_parts[2]
                                year = day_parts[3]
                                print(f"Parsed date components: weekday={weekday}, day={day_num}, month={month_name}, year={year}")
                            elif len(day_parts) == 3:
                                # Format could be: "Weekday Day Year" (missing month) or "Day Month Year"
                                if day_parts[0].lower() in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                                    # It's "Weekday Day Year" format (missing month)
                                    day_num = day_parts[1]
                                    # Get current month for Rome timezone
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    current_month = datetime.datetime.now(rome_tz).strftime('%B')
                                    month_name = current_month
                                    year = day_parts[2]
                                else:
                                    # Assume Day Month Year
                                    day_num = day_parts[0]
                                    month_name = day_parts[1]
                                    year = day_parts[2]
                            else:
                                # Use current date from Rome timezone
                                rome_tz = pytz.timezone('Europe/Rome')
                                now = datetime.datetime.now(rome_tz)
                                day_num = now.strftime('%d')
                                month_name = now.strftime('%B')
                                year = now.strftime('%Y')
                                print(f"Using current Rome date for: {clean_day}")

                            # Validate day_num - ensure it's a number and extract only digits
                            if day_num:
                                # Extract only digits from day_num
                                day_num_digits = re.sub(r'[^0-9]', '', str(day_num))
                                if day_num_digits:
                                    day_num = day_num_digits
                                else:
                                    # If no digits found, use current day
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    day_num = datetime.datetime.now(rome_tz).strftime('%d')
                                    print(f"Warning: Invalid day number '{day_num}', using current day: {day_num}")
                            else:
                                # If day_num is None, use current day
                                rome_tz = pytz.timezone('Europe/Rome')
                                day_num = datetime.datetime.now(rome_tz).strftime('%d')
                                print(f"Warning: Missing day number, using current day: {day_num}")

                            # Get time from game data
                            time_str = game.get("time", "00:00")

                            # Converti l'orario da UK a CET (aggiungi 2 ore invece di 1)
                            time_parts = time_str.split(":")
                            if len(time_parts) == 2:
                                hour = int(time_parts[0])
                                minute = time_parts[1]
                                # Aggiungi due ore all'orario UK
                                hour_cet = (hour + 2) % 24
                                # Assicura che l'ora abbia due cifre
                                hour_cet_str = f"{hour_cet:02d}"
                                # Nuovo time_str con orario CET
                                time_str_cet = f"{hour_cet_str}:{minute}"
                            else:
                                # Se il formato dell'orario non è corretto, mantieni l'originale
                                time_str_cet = time_str

                            # Convert month name to number
                            month_map = {
                                "January": "01", "February": "02", "March": "03", "April": "04",
                                "May": "05", "June": "06", "July": "07", "August": "08",
                                "September": "09", "October": "10", "November": "11", "December": "12"
                            }

                            # Aggiungi controllo per il mese
                            if not month_name or month_name not in month_map:
                                print(f"Warning: Invalid month name '{month_name}', using current month")
                                rome_tz = pytz.timezone('Europe/Rome')
                                current_month = datetime.datetime.now(rome_tz).strftime('%B')
                                month_name = current_month

                            month_num = month_map.get(month_name, "01")  # Default to January if not found

                            # Ensure day has leading zero if needed
                            if len(str(day_num)) == 1:
                                day_num = f"0{day_num}"

                            # Create formatted date time
                            year_short = str(year)[-2:]  # Extract last two digits of year
                            formatted_date_time = f"{day_num}/{month_num}/{year_short} - {time_str_cet}"

                            # Also create proper datetime objects for EPG
                            # Make sure we're using clean numbers for the date components
                            try:
                                # Ensure all date components are valid
                                if not day_num or day_num == "":
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    day_num = datetime.datetime.now(rome_tz).strftime('%d')
                                    print(f"Using current day as fallback: {day_num}")

                                if not month_num or month_num == "":
                                    month_num = "01"  # Default to January
                                    print(f"Using January as fallback month")

                                if not year or year == "":
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    year = datetime.datetime.now(rome_tz).strftime('%Y')
                                    print(f"Using current year as fallback: {year}")

                                if not time_str or time_str == "":
                                    time_str = "00:00"
                                    print(f"Using 00:00 as fallback time")

                                # Ensure day_num has proper format (1-31)
                                try:
                                    day_int = int(day_num)
                                    if day_int < 1 or day_int > 31:
                                        day_num = "01"  # Default to first day of month
                                        print(f"Day number out of range, using 01 as fallback")
                                except ValueError:
                                    day_num = "01"  # Default to first day of month
                                    print(f"Invalid day number format, using 01 as fallback")

                                # Ensure day has leading zero if needed
                                if len(str(day_num)) == 1:
                                    day_num = f"0{day_num}"

                                date_str = f"{year}-{month_num}-{day_num} {time_str}:00"
                                print(f"Attempting to parse date: '{date_str}'")
                                start_date_utc = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

                                # Convert to Amsterdam timezone
                                amsterdam_timezone = pytz.timezone("Europe/Amsterdam")
                                start_date_amsterdam = start_date_utc.replace(tzinfo=pytz.UTC).astimezone(amsterdam_timezone)

                                # Format for EPG
                                mStartTime = start_date_amsterdam.strftime("%Y%m%d%H%M%S")
                                mStopTime = (start_date_amsterdam + datetime.timedelta(days=2)).strftime("%Y%m%d%H%M%S")
                            except ValueError as e:
                                # Definisci date_str qui se non è già definita
                                error_msg = str(e)
                                if 'date_str' not in locals():
                                    date_str = f"Error with: {year}-{month_num}-{day_num} {time_str}:00"

                                print(f"Date parsing error: {error_msg} for date string '{date_str}'")
                                # Use current time as fallback
                                amsterdam_timezone = pytz.timezone("Europe/Amsterdam")
                                now = datetime.datetime.now(amsterdam_timezone)
                                mStartTime = now.strftime("%Y%m%d%H%M%S")
                                mStopTime = (now + datetime.timedelta(days=2)).strftime("%Y%m%d%H%M%S")

                            # Build channel name with new date format
                            if isinstance(channel, dict) and "channel_name" in channel:
                                channelName = formatted_date_time + "  " + channel["channel_name"]
                            else:
                                channelName = formatted_date_time + "  " + str(channel)

                            # Extract event name for the tvg-id
                            event_name = game["event"].split(":")[0].strip() if ":" in game["event"] else game["event"].strip()
                            event_details = game["event"]  # Keep the full event details for tvg-name

                        except Exception as e:
                            print(f"Error processing date '{day}': {e}")
                            print(f"Game time: {game.get('time', 'No time found')}")
                            continue

                        # Check if channel should be included based on keywords
                        if should_include_channel(channelName, event_name, sport_key):
                            # Process channel information
                            if isinstance(channel, dict) and "channel_id" in channel:
                                channelID = f"{channel['channel_id']}"
                            else:
                                # Generate a fallback ID
                                channelID = str(uuid.uuid4())

                            # Around line 353 where you access channel["channel_name"]
                            if isinstance(channel, dict) and "channel_name" in channel:
                                channel_name_str = channel["channel_name"]
                            else:
                                channel_name_str = str(channel)
                            stream_url_dynamic = get_stream_link(channelID, event_details, channel_name_str)

                            if stream_url_dynamic:
                                # Around line 361 where you access channel["channel_name"] again
                                if isinstance(channel, dict) and "channel_name" in channel:
                                    channel_name_str = channel["channel_name"]
                                else:
                                    channel_name_str = str(channel)

                                with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file:
                                    # Estrai l'orario dal formatted_date_time
                                    time_only = time_str_cet if time_str_cet else "00:00"

                                    # Crea il nuovo formato per tvg-name con l'orario all'inizio e la data alla fine
                                    tvg_name = f"{time_only} {event_details} - {day_num}/{month_num}/{year_short}"

                                    # Get dynamic logo for this event
                                    event_logo = get_dynamic_logo(game["event"])

                                    file.write(f'#EXTINF:-1 tvg-id="{event_name} - {event_details.split(":", 1)[1].strip() if ":" in event_details else event_details}" tvg-name="{tvg_name}" tvg-logo="{event_logo}" group-title="{clean_sport_key}", {channel_name_str}\n')
                                    file.write(f"{PROXY}{stream_url_dynamic}{PROXY2}\n\n")

                                processed_channels += 1
                                filtered_channels += 1
                            else:
                                print(f"Failed to get stream URL for channel ID: {channelID}")
                        else:
                            print(f"Skipping channel (no keyword match): {clean_group_title(sport_key)} - {event_details} - {channelName}")

        except KeyError as e:
            print(f"KeyError: {e} - Key may not exist in JSON structure")

    # Print summary
    print(f"\n=== Processing Summary ===")
    print(f"Total events found: {total_events}")
    print(f"Events skipped due to category filters: {skipped_events}")
    print(f"Channels included due to keyword match: {filtered_channels}")
    print(f"Channels successfully processed: {processed_channels}")
    print(f"Keywords used for filtering: {EVENT_KEYWORDS}")
    print(f"===========================\n")

    return processed_channels

def main():
    # Process events and generate M3U8
    total_processed_channels = process_events()

    # Verify if any valid channels were created
    if total_processed_channels == 0:
        print("No valid channels found matching the keywords.")
    else:
        print(f"M3U8 generated with {total_processed_channels} channels filtered by keywords.")

if __name__ == "__main__":
    main()
