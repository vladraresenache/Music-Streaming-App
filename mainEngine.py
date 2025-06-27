import random
import smtplib
from email.mime.text import MIMEText
import util
from music_api import getSongs, getSongsbyGenre, search_song_by_genre, get_genre_by_song
from datetime import datetime
import json
import os
from util import PlaylistsRepo, Playlist, IntelliMix

USER_DATA_FILE = "user_song_data.json"

#clasa ce contine principalele functii ale aplicatiei
class MainEngine():
    def __init__(self):
        #stocare utilizatori, stocare playlisturi, utilizator curent, dictionar de genuri, clasa IntelliMix - vezi util.py
        self.userRepo = util.UserRepo()
        self.playlistRepos = {}
        self.logged_in_user = None
        self.genres = {0: 'pop', 1: 'rock', 2: 'electronic', 3: 'hiphop', 4: 'jazz', 5: 'indie', 6: 'filmscore', 7: 'classical', 8: 'ambient', 9: 'chillout', 10: 'folk', 11: 'metal', 12: 'latin', 13: 'rnb', 14: 'raggae', 15: 'punk', 16: 'house', 17: 'blues'}
        self.IntelliMix = IntelliMix()

    def set_user_genres(self, selected_genres):
        if self.logged_in_user:
            for genre in selected_genres:
                self.logged_in_user.set_pref(int(genre))
            self.logged_in_user.first_time_login = False
            self.userRepo.save_users()
            return 'homepage'
        return 'login'

    def login(self, username, password):
        #cautam dupa username
        found_user = self.userRepo.get_user(username)
        if found_user:
            #verificam parola
            if found_user.verify_password(password):
                #setam utilizatorul curent si preluam datele despre playlisturi
                self.logged_in_user = found_user
                self.load_songs_user_data()
                #daca e prima logare, redirectionam care selectie de genuri, daca nu, catre pagina principala
                if found_user.first_time_login:
                    return 'select_genre'
                return 'homepage'
        return 'Nume de utilizator sau parolă incorectă.'

        # If user doesn't exist or password doesn't match
        return "Nume de utilizator sau parola gresita. Va rugam incercati din nou."

    def send_password_email(self, recipient_email, password, username):
        #creem o variabila de tip Multipurpose Internet Mail Extensions unde salvam mesajul cu parola, subiectul, expeditorul si destinatarul
        msg = MIMEText(f"Parola asociată contului tău  Harmonia este: {password}. Username-ul este {username}")
        msg['Subject'] = 'Parola contului tău Harmonia'
        msg['From'] = 'no.reply.harmoniaa@gmail.com'
        msg['To'] = recipient_email

        try:
            #creem o conexiune Simple Mail Transfer Protocol securizata cu Secure Socket Layer pe Gmail
            #ne logam pe adresa aplicatiei
            #trimitem mesajul si inchidem conexiunea
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login('no.reply.harmoniaa@gmail.com', 'zeaeoawbakmalskn')
            server.send_message(msg)
            server.quit()
            print(f"Parola a fost trimisă cu succes către {recipient_email}")
            return f"Parola a fost trimisă cu succes către {recipient_email}"
        except Exception as e:
            print(f"Eroare la trimiterea parolei: {e}")
            return f"Eroare la trimiterea parolei: {e}"

    def send_verification_email(self, recipient_email, code):
        #analog send_password_email
        msg = MIMEText(f"Codul tău de verificare Harmonia este: {code}")
        msg['Subject'] = 'Cod de verificare Harmonia'
        msg['From'] = 'no.reply.harmoniaa@gmail.com'
        msg['To'] = recipient_email

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login('no.reply.harmoniaa@gmail.com', 'zeaeoawbakmalskn')
            server.send_message(msg)
            server.quit()
            print(f"Email trimis cu succes către {recipient_email}")
            return True
        except Exception as e:
            print(f"Eroare la trimiterea emailului: {e}")
            return False

    def verif_reg(self, email):
        #generam un cod random, il salvam in engine si trimitem mail
        verification_code = str(random.randint(100000, 999999))
        self._last_verification_code = verification_code
        email_sent = self.send_verification_email(email, verification_code)
        return verification_code if email_sent else None

    def verify_code(self, code_entered):
        return code_entered == self._last_verification_code

    def activate_user(self, username, name, email, password):
        #cautam user-ul, daca nu exita, trecem peste
        existing_user = self.userRepo.get_user(username)
        if existing_user:
            print(f"Utilizatorul {username} este deja activat.")
            return

        #adaugam user si salvam
        self.userRepo.add_user(username, name, email, password)
        self.userRepo.save_users()

    def register(self, username, email):
        if self.userRepo.get_user(username):
            return "Numele de utilizator introdus este deja asociat unui cont."

        if self.userRepo.get_user_by_email(email):
            return "Exista deja un utilizator cu acest email."
        self.verif_reg(email)
        return "User created successfully."

    def save_song_user_data(self):
        data = {}
        for user_id, playlist_repo in self.playlistRepos.items():
            data[user_id] = []
            for playlist in playlist_repo.playlists:
                playlist_data = {
                    "name": playlist.name,
                    "songs": [],
                    "date": playlist.created_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(playlist.created_at, datetime) else playlist.created_at,
                    "enhanced": getattr(playlist, "enhanced", False)
                }
                
                # Process each song to ensure all metadata is saved
                for song in playlist.songs:
                    # Handle both dictionary and string ID cases
                    if isinstance(song, dict):
                        song_data = {
                            "id": str(song.get('id', '')),
                            "title": song.get('title', ''),
                            "artist": song.get('artist', ''),
                            "url": song.get('url', ''),
                            "album_image": song.get('album_image', ''),
                            "genre": song.get('genre', [])
                        }
                    else:
                        # If we only have an ID, fetch the metadata
                        song_meta = self.IntelliMix._fetch_song_metadata(str(song))
                        if song_meta:
                            song_data = {
                                "id": str(song),
                                "title": song_meta.get('title', ''),
                                "artist": song_meta.get('artist', ''),
                                "url": song_meta.get('url', ''),
                                "album_image": song_meta.get('album_image', ''),
                                "genre": song_meta.get('genre', [])
                            }
                        else:
                            # Fallback if metadata fetch fails
                            song_data = {
                                "id": str(song),
                                "title": f"Song {song}",
                                "artist": "",
                                "url": "",
                                "album_image": "",
                                "genre": []
                            }
                    playlist_data["songs"].append(song_data)
                
                data[user_id].append(playlist_data)
        
        # Save with proper encoding and formatting
        with open(USER_DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def load_songs_user_data(self):
        self.playlistRepos = {}

        if not os.path.exists(USER_DATA_FILE):
            return

        # Open file with UTF-8 encoding
        try:
            with open(USER_DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)

            for user_id, playlists_data in data.items():
                playlist_repo = PlaylistsRepo(None)  # setam utilizatorul mai tarziu
                playlist_repo.user_id = user_id  # manual, pentru ca nu avem obiect User aici

                #preluam datele despre playlist
                for playlist_data in playlists_data:
                    playlist = Playlist(None, playlist_data["name"], playlist_data.get("date", ""))
                    # Store songs as-is without fetching metadata
                    playlist.songs = playlist_data["songs"]
                    playlist.enhanced = playlist_data.get("enhanced", False)
                    if playlist.enhanced:
                        playlist.original_songs = playlist_data.get("original_songs", [])
                    playlist_repo.add_playlist(playlist)

                self.playlistRepos[user_id] = playlist_repo
        except UnicodeDecodeError:
            # If UTF-8 fails, try to read with a different encoding and convert to UTF-8
            try:
                with open(USER_DATA_FILE, "r", encoding='latin-1') as f:
                    data = json.load(f)
                # Convert data to UTF-8 and save it back
                with open(USER_DATA_FILE, "w", encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"Error loading user data: {e}")
                self.playlistRepos = {}

    def create_playlist(self, playlist_name, date):
        if not self.logged_in_user:
            print("Trebuie să fi logat pentru a crea un playlist.")
            return None

        user_id = self.logged_in_user.id
        # Încarca repo dacă nu exista deja
        if user_id not in self.playlistRepos:
            self.load_songs_user_data()  # populam totul
            if user_id not in self.playlistRepos:
                self.playlistRepos[user_id] = PlaylistsRepo(self.logged_in_user)

        playlist_repo = self.playlistRepos[user_id]

        #verificam daca exista un playlist cu acelasi nume
        if playlist_name in playlist_repo.get_playlist_names():
            print("Playlistul deja există.")
            return None
            
        #creem obiect de tip playlist si adaugam in repo, apoi salvam
        playlist_obj = Playlist(self.logged_in_user, playlist_name, date)
        playlist_repo.add_playlist(playlist_obj)
        self.save_song_user_data()
        print("Playlist creat cu succes.")
        return playlist_obj

    def delete_playlist(self, playlist_name):
        if not self.logged_in_user:
            return "Trebuie să fi logat pentru a crea un playlist."

        user_id = self.logged_in_user.id
        if user_id not in self.playlistRepos:
            return "Nu au fost găsite playlist-uri."

        repo = self.playlistRepos[user_id]
        playlist = repo.find_by_name(playlist_name)
        if not playlist:
            return "Playlist-ul nu a fost găsit."

        repo.delete_playlist(playlist)
        self.save_song_user_data()
        return f"Playlist '{playlist_name}' a fost șters cu succes."

    def search_music(self, query, by_genre=False, limit=30):
        print(f"[DEBUG] Searching music: query={query}, by_genre={by_genre}, limit={limit}")
        if not query:
            return []
        try:
            if by_genre:
                # Search by genre and get results
                print(f"[DEBUG] Searching by genre: {query}")
                results = getSongsbyGenre(query, int(limit))
                print(f"[DEBUG] Genre search returned: {len(results) if isinstance(results, list) else 'error'}")
                if not isinstance(results, list):
                    return []
                
                # Enhance results with genre information
                enhanced_results = []
                for song in results:
                    song_id = song.get("id", "")
                    print(f"[DEBUG] Getting genres for song {song_id}")
                    genres = get_genre_by_song(song_id) if song_id else []
                    print(f"[DEBUG] Found genres: {genres}")
                    song["genre"] = genres
                    enhanced_results.append(song)
                
                return enhanced_results
            else:
                # Search by title and get results
                print(f"[DEBUG] Searching by title: {query}")
                results = getSongs(query, int(limit))
                print(f"[DEBUG] Title search returned: {len(results) if isinstance(results, list) else 'error'}")
                if not isinstance(results, list):
                    return []
                
                # Enhance results with genre information
                enhanced_results = []
                for song in results:
                    song_id = song.get("id", "")
                    print(f"[DEBUG] Getting genres for song {song_id}")
                    genres = get_genre_by_song(song_id) if song_id else []
                    print(f"[DEBUG] Found genres: {genres}")
                    song["genre"] = genres
                    enhanced_results.append(song)
                
                return enhanced_results
        except Exception as e:
            print(f"[DEBUG] Error in search_music: {str(e)}")
            return []

    def recommend_by_genre(self, genre, limit=15):
        print(f"[DEBUG] Recommending songs for genre: {genre}")
        tracks = search_song_by_genre(genre, limit)
        print(f"[DEBUG] API returned tracks: {len(tracks) if isinstance(tracks, list) else 'error'}")
        
        if isinstance(tracks, dict) and "error" in tracks:
            print(f"[DEBUG] Error in tracks: {tracks['error']}")
            return []

        recommendations = []
        for track in tracks:
            if not isinstance(track, dict):
                continue
                
            song_data = {
                "id": str(track.get("id", "")),
                "title": track.get("name", ""),
                "artist": track.get("artist_name", ""),
                "url": track.get("audio", ""),
                "album_image": track.get("album_image", ""),
                "genre": track.get("tags", [])  # Use cached genres from the search results
            }
            recommendations.append(song_data)
            
        print(f"[DEBUG] Returning {len(recommendations)} recommendations")
        return recommendations

    def logout(self):
        if not self.logged_in_user:
            return "Niciun utilizator nu este logat."

        self.logged_in_user = None
        return "Te-ai delogat."

    def populate_training_data(self, genre='pop', limit=30):
        """Populate user song data with songs from a specific genre for training."""
        if not self.logged_in_user:
            print("[DEBUG] Must be logged in to populate training data")
            return False
            
        print(f"[DEBUG] Fetching {limit} {genre} songs for training data...")
        tracks = search_song_by_genre(genre, limit)
        
        if isinstance(tracks, dict) and "error" in tracks:
            print(f"[DEBUG] Error fetching tracks: {tracks['error']}")
            return False
            
        if not isinstance(tracks, list):
            print(f"[DEBUG] Invalid response from API")
            return False
            
        # Create a new playlist for the genre
        playlist_name = f"{genre.capitalize()} Mix"
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        playlist = self.create_playlist(playlist_name, date)
        
        if playlist is None:
            print(f"[DEBUG] Failed to create playlist")
            return False
            
        # Add songs to the playlist
        songs_added = 0
        for track in tracks:
            if not isinstance(track, dict):
                continue
                
            song_data = {
                "id": str(track.get("id", "")),
                "title": track.get("name", ""),
                "artist": track.get("artist_name", ""),
                "url": track.get("audio", ""),
                "album_image": track.get("album_image", ""),
                "genre": track.get("tags", [])
            }
            
            if playlist.add_song(song_data):
                songs_added += 1
                print(f"[DEBUG] Added song: {song_data['title']} by {song_data['artist']}")
                
        print(f"[DEBUG] Added {songs_added} songs to {playlist_name}")
        
        # Save the updated data
        self.save_song_user_data()
        return True



