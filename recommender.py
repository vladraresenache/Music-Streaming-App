import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from music_api import get_genre_by_song, getSongsbyGenre
import random

class HybridRecommender:
    def __init__(self, user_song_data, song_metadata):
        """
        user_song_data: list of dicts with keys 'user_id', 'song_id', 'liked' (1/0 or True/False)
        song_metadata: dict mapping song_id to dict of features (e.g., genre, artist)
        """
        self.user_song_data = user_song_data
        self.song_metadata = song_metadata
        self.user_ids = list({entry['user_id'] for entry in user_song_data})
        self.song_ids = list(song_metadata.keys())
        self.user_index = {uid: i for i, uid in enumerate(self.user_ids)}
        self.song_index = {sid: i for i, sid in enumerate(self.song_ids)}
        self.interaction_matrix = self._build_interaction_matrix()
        self.song_features = self._build_song_features_matrix()
        self.user_profiles = self._build_user_profiles()
        self.user_genre_preferences = self._build_user_genre_preferences()

    def _build_interaction_matrix(self):
        matrix = np.zeros((len(self.user_ids), len(self.song_ids)))
        for entry in self.user_song_data:
            u = self.user_index[entry['user_id']]
            s = self.song_index.get(entry['song_id'])
            if s is not None:
                matrix[u, s] = 1 if entry.get('liked', 1) else 0
        return matrix

    def _build_song_features_matrix(self):
        # Enhanced feature matrix with more metadata
        genres = set()
        artists = set()
        
        # Use cached genres from metadata, don't make API calls
        for meta in self.song_metadata.values():
            genres.update(meta.get('genre', []))
            artists.add(meta.get('artist', ''))
        
        genres = sorted(genres)
        artists = sorted(artists)
        genre_index = {g: i for i, g in enumerate(genres)}
        artist_index = {a: i for i, a in enumerate(artists)}
        
        features = np.zeros((len(self.song_ids), len(genres) + len(artists)))
        
        for i, sid in enumerate(self.song_ids):
            # Use cached metadata only
            meta = self.song_metadata[sid]
            for g in meta.get('genre', []):
                if g in genre_index:
                    features[i, genre_index[g]] = 1
            
            # Artist
            a = meta.get('artist', '')
            if a in artist_index:
                features[i, len(genres) + artist_index[a]] = 1
        
        return features

    def _build_user_profiles(self):
        # Enhanced user profiles with weighted features
        profiles = np.zeros((len(self.user_ids), self.song_features.shape[1]))
        for u, uid in enumerate(self.user_ids):
            liked_songs = [entry for entry in self.user_song_data if entry['user_id'] == uid and entry.get('liked', 1)]
            if liked_songs:
                # Weight recent songs more heavily
                weights = np.linspace(0.5, 1.0, len(liked_songs))
                for song, weight in zip(liked_songs, weights):
                    idx = self.song_index.get(song['song_id'])
                    if idx is not None:
                        profiles[u] += weight * self.song_features[idx]
                profiles[u] /= len(liked_songs)
        return profiles

    def _build_user_genre_preferences(self):
        preferences = defaultdict(lambda: defaultdict(float))
        for entry in self.user_song_data:
            user_id = entry['user_id']
            song_id = entry['song_id']
            if song_id in self.song_metadata:
                # Use cached genres only
                genres = set(self.song_metadata[song_id].get('genre', []))
                for genre in genres:
                    preferences[user_id][genre] += 1
        
        # Normalize preferences
        for user_id in preferences:
            total = sum(preferences[user_id].values())
            if total > 0:
                for genre in preferences[user_id]:
                    preferences[user_id][genre] /= total
        
        return preferences

    def get_similar_users(self, user_id, n=5):
        if user_id not in self.user_index:
            return []
        uidx = self.user_index[user_id]
        user_sim = cosine_similarity(self.interaction_matrix[uidx:uidx+1], self.interaction_matrix)[0]
        similar_users = [(self.user_ids[i], user_sim[i]) for i in range(len(self.user_ids)) if i != uidx]
        return sorted(similar_users, key=lambda x: x[1], reverse=True)[:n]

    def recommend(self, user_id, exclude_song_ids=None, top_n=10):
        """
        Enhanced recommendation system that combines:
        1. Collaborative filtering
        2. Content-based filtering
        3. Genre preferences
        4. Similar users' preferences
        """
        # Ensure exclude_song_ids is a list
        exclude_song_ids = exclude_song_ids or []
        
        # For new users or users without data, use genre-based recommendations
        if not self.user_song_data or user_id not in self.user_index:
            # Get genres from excluded songs
            genres = set()
            for song_id in exclude_song_ids:
                if song_id in self.song_metadata:
                    genres.update(self.song_metadata[song_id].get('genre', []))
            
            # If no genres found, use popular genres
            if not genres:
                genres = {'pop', 'rock', 'electronic'}
            
            # Get recommendations from each genre (make only one API call per genre)
            recommendations = []
            for genre in genres:
                if len(recommendations) >= top_n:
                    break
                    
                songs = getSongsbyGenre(genre, limit=5)
                if isinstance(songs, list):
                    for song in songs:
                        song_id = str(song.get('id'))
                        if song_id and song_id not in exclude_song_ids and song_id not in recommendations:
                            recommendations.append(song_id)
                            # Cache song metadata
                            if song_id not in self.song_metadata:
                                self.song_metadata[song_id] = {
                                    'id': song_id,
                                    'title': song.get('name', ''),
                                    'artist': song.get('artist_name', ''),
                                    'url': song.get('audio', ''),
                                    'album_image': song.get('album_image', ''),
                                    'genre': song.get('tags', [])
                                }
                            if len(recommendations) >= top_n:
                                break
            
            return recommendations[:top_n]

        # For existing users, use hybrid recommendations
        uidx = self.user_index[user_id]
        
        # 1. Collaborative Filtering
        user_sim = cosine_similarity(self.interaction_matrix[uidx:uidx+1], self.interaction_matrix)[0]
        similar_users = np.argsort(-user_sim)[1:6]
        cf_scores = np.zeros(len(self.song_ids))
        for su in similar_users:
            cf_scores += self.interaction_matrix[su]
        
        # 2. Content-Based Filtering
        cbf_scores = cosine_similarity(self.user_profiles[uidx:uidx+1], self.song_features)[0]
        
        # 3. Genre-based scores
        genre_scores = np.zeros(len(self.song_ids))
        user_genres = self.user_genre_preferences[user_id]
        for i, sid in enumerate(self.song_ids):
            meta = self.song_metadata[sid]
            genres = set(meta.get('genre', []))
            for genre in genres:
                genre_scores[i] += user_genres.get(genre, 0)
        
        # Normalize scores
        for scores in [cf_scores, cbf_scores, genre_scores]:
            if scores.max() > 0:
                scores /= scores.max()
        
        # Combine scores with weights
        hybrid_scores = 0.4 * cf_scores + 0.3 * cbf_scores + 0.3 * genre_scores
        
        # Exclude existing songs
        for sid in exclude_song_ids:
            idx = self.song_index.get(sid)
            if idx is not None:
                hybrid_scores[idx] = -np.inf
        
        # Get top recommendations
        top_indices = np.argsort(-hybrid_scores)[:top_n]
        recommended_ids = [self.song_ids[i] for i in top_indices if hybrid_scores[i] > 0]
        
        # If we don't have enough recommendations, fetch additional songs from similar genres
        if len(recommended_ids) < top_n:
            top_genres = sorted(user_genres.items(), key=lambda x: x[1], reverse=True)[:3]
            for genre, _ in top_genres:
                if len(recommended_ids) >= top_n:
                    break
                    
                additional_songs = getSongsbyGenre(genre, limit=5)
                if isinstance(additional_songs, list):
                    for song in additional_songs:
                        song_id = str(song.get('id'))
                        if song_id and song_id not in recommended_ids and song_id not in exclude_song_ids:
                            recommended_ids.append(song_id)
                            # Cache song metadata
                            if song_id not in self.song_metadata:
                                self.song_metadata[song_id] = {
                                    'id': song_id,
                                    'title': song.get('name', ''),
                                    'artist': song.get('artist_name', ''),
                                    'url': song.get('audio', ''),
                                    'album_image': song.get('album_image', ''),
                                    'genre': song.get('tags', [])
                                }
                            if len(recommended_ids) >= top_n:
                                break
        
        return recommended_ids[:top_n]

# Helper to load data from JSON files
import json

def load_user_song_data(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Flatten to list of dicts
    result = []
    for user_id, playlists in data.items():
        for pl in playlists:
            for song in pl.get('songs', []):
                result.append({'user_id': user_id, 'song_id': song.get('id'), 'liked': 1})
    return result

def load_song_metadata(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Assume data is a list of song dicts
    meta = {}
    for song in data:
        meta[song['id']] = {
            'genre': song.get('genre', []),
            'artist': song.get('artist', ''),
            'title': song.get('title', song.get('name', '')),
            'album_image': song.get('album_image', ''),
            'url': song.get('audio', ''),
        }
    return meta 