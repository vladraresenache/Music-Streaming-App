import hashlib
import random
import music_api
import os
import json
from cryptography.fernet import Fernet
from recommender import HybridRecommender, load_user_song_data, load_song_metadata
from music_api import get_genre_by_song, getSongs, getSongsbyGenre
import copy
from collections import defaultdict

def load_or_generate_key(filepath):
    key_path = filepath
    if os.path.exists(key_path):
        with open(key_path, "rb") as key_file:
            return key_file.read()
    else:
        key = Fernet.generate_key()
        with open(key_path, "wb") as key_file:
            key_file.write(key)
        return key

# incarcam cheia o singura dată global
global_key = load_or_generate_key("secret.key")
global_cipher_suite = Fernet(global_key)


class User:
    def __init__(self, username, name, email, password, preferences = None, first_time = None):
        self.username = username
        self.name = name
        self.email = email
        #criptam odata
        self.id = hashlib.md5(email.encode('utf-8')).hexdigest()
        #daca avem preferinte, le initializam, daca nu, le punem toate False
        self.preferences = self.preferences = preferences if preferences is not None else [False] * 18
        self.password = password
        if first_time is None:
            self.first_time_login = True
        else:
            self.first_time_login = first_time

    def set_pref(self, index):
        self.preferences[index] = True

    def verify_password(self, input_password):
        return input_password == self.password


class UserRepo():
    def __init__(self):
        #generam sau incarcam cheia si cifrul apoi incarcam utilizatorii
        self.key = load_or_generate_key("secret.key")
        self.cipher_suite = Fernet(self.key)
        self.users = []
        self.load_users()

    def add_user(self, username, name, email, password):
        #creem obiect de tip User, adaugam in lista, salvam
        user = User(username, name, email, password)
        if user not in self.users:
            self.users.append(user)
            self.save_users()
            return True
        else:
            return False

    def get_user(self, username):
        #cautam in lista dupa username
        for u in self.users:
            if u.username == username:
                return u
        return False

    def get_user_by_email(self, email):
        #cautam in lista dupa email
        for u in self.users:
            if u.email == email:
                return u
        return False

    def delete_user(self, user):
        #cautam in lista apoi stergem
        for u in self.users:
            if u == user:
                self.users.remove(u)
                self.save_users()
                return True
        return False

    def encrypt_data(self):
        users_data = [{'username': u.username, 'name': u.name, 'email': u.email, 'password': u.password, 'preferences': u.preferences, "first_time": u.first_time_login} for u in self.users]
        json_data = json.dumps(users_data, ensure_ascii=False).encode('utf-8')
        encrypted_data = self.cipher_suite.encrypt(json_data)
        return encrypted_data

    def decrypt_data(self, encrypted_data):
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode('utf-8'))

    def save_users(self):
        encrypted_data = self.encrypt_data()
        with open("users.json", "wb") as file:
            file.write(encrypted_data)

    def load_users(self):
        try:
            with open("users.json", "rb") as file:
                encrypted_data = file.read()
                decrypted_data = self.decrypt_data(encrypted_data)
                self.users = [User(**user) for user in decrypted_data]
        except FileNotFoundError:
            self.users = []
        except Exception as e:
            import traceback
            print("[Eroare load_users]:", traceback.format_exc())
            self.users = []


class Playlist():
    def __init__(self, user, name, date):
        self.songs = []
        self.name = name
        self.created_at = date
        if user:
            self.id = f"{user.id}" + f"{hashlib.sha256(name.encode()).hexdigest()}"
        else:
            self.id = f"unknownuser_" + f"{hashlib.sha256(name.encode()).hexdigest()}"
        self.enhanced = False
        self.original_songs = []

    def add_song(self, song_id):
        # Check if song already exists by comparing IDs
        song_exists = any(str(song.get('id')) == str(song_id.get('id')) for song in self.songs) if isinstance(song_id, dict) else False
        if not song_exists:
            self.songs.append(song_id)
            # If not enhanced, also add to original songs
            if not self.enhanced and isinstance(song_id, dict):
                self.original_songs.append(copy.deepcopy(song_id))
            return True
        return False

    def get_name(self):
        return self.name

    def remove_song(self, song_id):
        initial_len = len(self.songs)
        self.songs = [song for song in self.songs if str(song.get('id')) != str(song_id)]
        # Also remove from original songs if not enhanced
        if not self.enhanced:
            self.original_songs = [song for song in self.original_songs if str(song.get('id')) != str(song_id)]
        return len(self.songs) < initial_len

    def merge_playlists(self, playlist):
        for song in playlist.songs:
            self.add_song(song)
        return self

    def shuffle_playlists(self):
        shuffled_songs = self.songs[:]
        random.shuffle(shuffled_songs)
        return shuffled_songs

    def IntelliMix_shuffle_playlists(self, additional_playlist):
        merged_playlist = self.merge_playlists(additional_playlist)
        shuffled_songs = merged_playlist.shuffle_playlists()
        return shuffled_songs

    def reset_to_original(self):
        if self.original_songs:
            self.songs = copy.deepcopy(self.original_songs)
        self.enhanced = False



class PlaylistsRepo():
    def __init__(self, user):
        self.playlists = []
        self.user_id = user.id if user else None

    def add_playlist(self, playlist):
        if playlist not in self.playlists:
            self.playlists.append(playlist)
            return True
        return False

    def get_playlist(self, playlist):
        if playlist not in self.playlists:
            return False
        else:
            return self.playlists[playlist]

    def find_by_name(self, playlist_name):
        for playlist in self.playlists:
            if playlist.name == playlist_name:
                return playlist
        return False

    def delete_playlist(self, playlist):
        if playlist in self.playlists:
            self.playlists.remove(playlist)
            return True
        else:
            return False

    def get_playlist_names(self):
        playlist_names = []
        for playlist in self.playlists:
            playlist_names.append(playlist.name)
        return playlist_names



class IntelliMix():
    def __init__(self):
        self._song_metadata_cache = {}  # Cache for song metadata
        self._load_data()  # Load data first
        self.recommender = HybridRecommender(self.user_song_data, self.song_metadata)  # Initialize with loaded data

    def _load_data(self):
        # Load user song data
        try:
            # Load raw data from file
            with open("user_song_data.json", "r", encoding='utf-8') as f:
                raw_data = json.load(f)
                
            # Format data for recommender system
            self.user_song_data = []
            self.song_metadata = {}
            
            for user_id, playlists in raw_data.items():
                for playlist in playlists:
                    for song in playlist.get("songs", []):
                        # Add to user song data
                        self.user_song_data.append({
                            "user_id": user_id,
                            "song_id": song.get("id"),
                            "rating": 1.0  # Implicit rating - user added song to playlist
                        })
                        
                        # Add to song metadata
                        song_id = song.get("id")
                        if song_id and song_id not in self.song_metadata:
                            self.song_metadata[song_id] = {
                                "id": song_id,
                                "title": song.get("title", ""),
                                "artist": song.get("artist", ""),
                                "url": song.get("url", ""),
                                "album_image": song.get("album_image", ""),
                                "genre": song.get("genre", [])
                            }
                            self._song_metadata_cache[song_id] = self.song_metadata[song_id]
                            
        except Exception as e:
            print(f"Error loading user song data: {e}")
            self.user_song_data = []
            self.song_metadata = {}

    def _fetch_song_metadata(self, song_id):
        # Check cache first
        if song_id in self._song_metadata_cache:
            return self._song_metadata_cache[song_id]
            
        # If it's already a dictionary with metadata, return it
        if isinstance(song_id, dict):
            self._song_metadata_cache[song_id.get('id')] = song_id
            return song_id
            
        # Only fetch from API if absolutely necessary
        try:
            # First check if we have it in the song data
            if song_id in self.song_metadata:
                metadata = self.song_metadata[song_id]
                self._song_metadata_cache[song_id] = metadata
                return metadata
                
            # If not in local data, then fetch from API
            results = getSongs(song_id, limit=1)
            if isinstance(results, list) and results:
                track = results[0]
                metadata = {
                    "id": str(track.get("id", "")),
                    "title": track.get("name", ""),
                    "artist": track.get("artist_name", ""),
                    "url": track.get("audio", ""),
                    "album_image": track.get("album_image", ""),
                    "genre": track.get("tags", [])  # Use cached genres from the search results
                }
                self._song_metadata_cache[song_id] = metadata
                self.song_metadata[song_id] = metadata  # Add to song metadata for recommender
                return metadata
                
            # If we can't get metadata, try getting it from genre search
            for genre in ['pop', 'rock', 'electronic']:  # Try popular genres
                songs = getSongsbyGenre(genre, limit=15)
                if isinstance(songs, list):
                    for song in songs:
                        if str(song.get('id')) == str(song_id):
                            metadata = {
                                "id": str(song.get("id", "")),
                                "title": song.get("name", ""),
                                "artist": song.get("artist_name", ""),
                                "url": song.get("audio", ""),
                                "album_image": song.get("album_image", ""),
                                "genre": song.get("tags", [])
                            }
                            self._song_metadata_cache[song_id] = metadata
                            self.song_metadata[song_id] = metadata
                            return metadata
                            
        except Exception as e:
            print(f"Error fetching metadata for song {song_id}: {e}")
            
        return None

    def enhanced_playlist(self, playlist, user_id=None, top_n=5):
        if not playlist.songs:
            return playlist

        # Extract song IDs from the playlist
        playlist_song_ids = []
        for song in playlist.songs:
            if isinstance(song, dict):
                song_id = song.get('id')
                if song_id:
                    playlist_song_ids.append(song_id)
                    # Add to song metadata if not already there
                    if song_id not in self.song_metadata:
                        self.song_metadata[song_id] = song
            else:
                playlist_song_ids.append(song)

        # Get recommendations
        recommended_ids = self.recommender.recommend(user_id or 'default_user', playlist_song_ids, top_n)
        
        # Create a new playlist with the recommendations
        enhanced = copy.deepcopy(playlist)
        enhanced.enhanced = True
        
        # Store original songs before adding recommendations
        if not enhanced.original_songs:
            enhanced.original_songs = copy.deepcopy(playlist.songs)
            
        # Add recommendations with full metadata
        for song_id in recommended_ids:
            metadata = self._fetch_song_metadata(song_id)
            if metadata:
                enhanced.add_song(metadata)
            
        return enhanced


class MainEngine():
    def __init__(self):
        self.userRepo = UserRepo()
        self.playlistRepos = {}
        self.logged_in_user = None
        self.genres = {0: 'pop', 1: 'rock', 2: 'electronic', 3: 'hiphop', 4: 'jazz', 5: 'indie', 6: 'filmscore', 7: 'classical', 8: 'ambient', 9: 'chillout', 10: 'folk', 11: 'metal', 12: 'latin', 13: 'rnb', 14: 'raggae', 15: 'punk', 16: 'house', 17: 'blues'}
        self.IntelliMix = IntelliMix()

    def save_song_user_data(self):
        data = {}
        for user_id, repo in self.playlistRepos.items():
            playlists_data = []
            for playlist in repo.playlists:
                playlist_data = {
                    "name": playlist.name,
                    "songs": []
                }
                for song in playlist.songs:
                    # Ensure we have all required fields
                    song_data = {
                        "id": str(song.get('id', '')),
                        "title": song.get('title', ''),
                        "artist": song.get('artist', ''),
                        "url": song.get('url', ''),
                        "album_image": song.get('album_image', ''),
                        "genre": song.get('genre', [])
                    }
                    playlist_data["songs"].append(song_data)
                playlists_data.append(playlist_data)
            data[user_id] = playlists_data

        with open("user_song_data.json", "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


