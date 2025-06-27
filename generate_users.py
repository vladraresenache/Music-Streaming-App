import json
import random
import string
import sys
from datetime import datetime
from mainEngine import MainEngine

# Ensure requests is installed
try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
    import requests

# API call to get pop songs from Jamendo
API_URL = 'https://api.jamendo.com/v3.0/tracks/'
CLIENT_ID = '9942cee3'  # Use your client_id if different
SONG_LIMIT = 100  # Number of pop songs to fetch

# Fetch pop songs
params = {
    'client_id': CLIENT_ID,
    'limit': SONG_LIMIT,
    'tags': 'pop',
    'include': 'musicinfo',
}
response = requests.get(API_URL, params=params)
data = response.json()
pop_songs = data.get('results', [])

if not pop_songs:
    print('No pop songs found from API!')
    exit(1)

# Use the correct path for user_song_data.json
USER_SONG_DATA_PATH = 'user_song_data.json'

# Load existing user-song data
try:
    with open(USER_SONG_DATA_PATH, 'r', encoding='utf-8') as f:
        user_data = json.load(f)
except FileNotFoundError:
    user_data = {}

# Helper to generate a random user id
def random_user_id():
    return ''.join(random.choices(string.hexdigits, k=32))

# Helper to create a playlist with diverse pop songs
def create_diverse_playlist(song_pool, playlist_size=7):
    # Try to maximize diversity by artist
    artists = list(set(song['artist_name'] for song in song_pool))
    random.shuffle(artists)
    selected_songs = []
    used_artists = set()
    for artist in artists:
        artist_songs = [s for s in song_pool if s['artist_name'] == artist]
        if artist_songs:
            song = random.choice(artist_songs)
            selected_songs.append(song)
            used_artists.add(artist)
        if len(selected_songs) >= playlist_size:
            break
    # If not enough, fill with random songs
    if len(selected_songs) < playlist_size:
        remaining = [s for s in song_pool if s['artist_name'] not in used_artists]
        if len(remaining) >= (playlist_size - len(selected_songs)):
            selected_songs += random.sample(remaining, k=playlist_size - len(selected_songs))
        else:
            selected_songs += remaining
    # Format for user_song_data.json
    return [
        {
            'id': song['id'],
            'title': song['name'],
            'artist': song['artist_name'],
            'url': song['audio'],
            'album_image': song['album_image']
        }
        for song in selected_songs
    ]

# Generate new users and playlists
NUM_USERS = 10
PLAYLISTS_PER_USER = 2
SONGS_PER_PLAYLIST = 7

for _ in range(NUM_USERS):
    uid = random_user_id()
    playlists = []
    for p in range(PLAYLISTS_PER_USER):
        playlist_name = f"pop_playlist_{p+1}"
        playlist_songs = create_diverse_playlist(pop_songs, SONGS_PER_PLAYLIST)
        playlists.append({
            'name': playlist_name,
            'songs': playlist_songs,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'enhanced': False
        })
    user_data[uid] = playlists

# Save back to user_song_data.json
with open(USER_SONG_DATA_PATH, 'w', encoding='utf-8') as f:
    json.dump(user_data, f, indent=4)

print(f"Added {NUM_USERS} users with {PLAYLISTS_PER_USER} pop playlists each.")

def main():
    # Create engine instance
    engine = MainEngine()
    
    # Create test user
    username = "test_user"
    name = "Test User"
    email = "test@example.com"
    password = "test123"
    
    # Register and activate user
    print("Registering test user...")
    result = engine.register(username, email)
    if "successfully" in result:
        engine.activate_user(username, name, email, password)
        print("Test user activated")
        
        # Login
        result = engine.login(username, password)
        if result == 'select_genre':
            # Set some initial genres
            engine.set_user_genres(['0', '2', '4'])  # pop, electronic, jazz
            print("Set initial genres")
            
            # Populate training data
            print("Populating training data...")
            engine.populate_training_data(genre='pop', limit=30)
            print("Done!")
        else:
            print(f"Login failed: {result}")
    else:
        print(f"Registration failed: {result}")

if __name__ == "__main__":
    main() 