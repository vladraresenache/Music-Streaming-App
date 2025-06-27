import os
from dotenv import load_dotenv
import requests
import _json
import logging
import time
from functools import lru_cache
import threading

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# API Configuration
JAMENDO_API_BASE = "https://api.jamendo.com/v3.0"
JAMENDO_CLIENT_ID = os.getenv('JAMENDO_CLIENT_ID', 'your_client_id_here')  # Replace with your Jamendo client ID

# Rate limiting configuration
_request_lock = threading.Lock()
_last_request_time = 0
_min_request_interval = 0.1  # seconds

# Cache for genre information
_genre_cache = {}

def rate_limited_request(url):
    global _last_request_time
    
    with _request_lock:
        # Calculate time to wait
        current_time = time.time()
        time_since_last_request = current_time - _last_request_time
        if time_since_last_request < _min_request_interval:
            time.sleep(_min_request_interval - time_since_last_request)
        
        # Make request
        response = requests.get(url)
        _last_request_time = time.time()
        return response

@lru_cache(maxsize=1000)
def get_genre_by_song(song_id):
    """Get genres for a song with caching."""
    if song_id in _genre_cache:
        return _genre_cache[song_id]
        
    url = f"{JAMENDO_API_BASE}/tracks/?client_id={JAMENDO_CLIENT_ID}&id={song_id}&include=musicinfo"
    logger.debug(f"Getting genres for song {song_id}")
    
    try:
        response = rate_limited_request(url)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        if results:
            genres = results[0].get("tags", [])
            _genre_cache[song_id] = genres
            logger.debug(f"Found genres for song {song_id}: {genres}")
            return genres
    except Exception as e:
        logger.error(f"Error getting genres for song {song_id}: {e}")
    
    return []

def search_jamendo_tracks_by_name(query, limit = 30):
    url = f'{JAMENDO_API_BASE}/tracks/?client_id={JAMENDO_CLIENT_ID}&name={query}&limit={limit}&include=musicinfo'
    logger.debug(f"Calling Jamendo API: {url}")
    
    try:
        response = rate_limited_request(url)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"API Response: {data.get('headers', {})}")
        
        if not data.get('results'):
            logger.warning(f"No results found for query: {query}")
            return {"error": "No results found", "query": query}
            
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return {"error": f"Failed to fetch data from Jamendo API: {str(e)}"}
    except ValueError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        return {"error": "Invalid response from API"}

def search_song_by_genre(genre, limit=30):
    """Search for songs by genre with optimized genre fetching."""
    url = f"{JAMENDO_API_BASE}/tracks/?client_id={JAMENDO_CLIENT_ID}&limit={limit}&tags={genre}&include=musicinfo"
    logger.debug(f"Searching songs by genre: {genre}")
    
    try:
        response = rate_limited_request(url)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            logger.warning(f"No results found for genre: {genre}")
            return {"error": "No results found for this genre"}
            
        # Cache genres from the search results
        for track in results:
            track_id = str(track.get("id"))
            if track_id:
                _genre_cache[track_id] = track.get("tags", [])
        
        logger.debug(f"Found {len(results)} songs for genre {genre}")
        return results
        
    except Exception as e:
        logger.error(f"Error searching songs by genre: {e}")
        return {"error": "Failed to fetch data from Jamendo API"}

def getSongs(query, limit=30):
    """Search for songs by name."""
    url = f"{JAMENDO_API_BASE}/tracks/?client_id={JAMENDO_CLIENT_ID}&name={query}&limit={limit}&include=musicinfo"
    
    try:
        response = rate_limited_request(url)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        # Cache genres from the search results
        for track in results:
            track_id = str(track.get("id"))
            if track_id:
                _genre_cache[track_id] = track.get("tags", [])
                
        return results
    except Exception as e:
        logger.error(f"Error searching songs: {e}")
        return {"error": "Failed to fetch data from Jamendo API"}

def getSongsbyGenre(query, limit=30):
    """Alias for search_song_by_genre for backward compatibility."""
    return search_song_by_genre(query, limit)

def get_song_info(song_id):
    return {
        "title": f"Song {song_id}",
        "artist": f"Artist {song_id % 10}"  # just a dummy placeholder
    }

def _make_request(endpoint, params=None):
    """Make a request to the Jamendo API"""
    if params is None:
        params = {}
    params['client_id'] = JAMENDO_CLIENT_ID
    
    try:
        response = requests.get(f"{JAMENDO_API_BASE}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"error": str(e)}

