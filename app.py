from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from io import BytesIO
import requests
from mainEngine import MainEngine
from datetime import datetime
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key
engine = MainEngine()

@app.route('/')
def home():
    return render_template('login_page.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    #elimin vechiul user
    session.pop('username', None)
    session.pop('password', None)
    if request.method == 'POST':
        #iau datele
        username = request.form['username']
        password = request.form['password']

        #rezultat login -> selectie genuri(prima conectare) sau pagina principala
        result = engine.login(username, password)
        if result == 'select_genre':
            return redirect(url_for('select_genre'))
        elif result == 'homepage':
            return redirect(url_for('homepage'))

        #altfel - eroare
        return render_template('login_page.html', error_message=result)
    return render_template('login_page.html')

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        #iau email
        email = request.form.get('email')

        #caut userul in repo
        user = engine.userRepo.get_user_by_email(email)

        #daca nu, eroare
        if not user:
            return render_template('forgot_password.html', error_message="Emailul nu a fost găsit.")

        #iau parola si o trimit pe mail
        password = user.password
        username = user.username
        success = engine.send_password_email(email, password, username)

        if success:
            return render_template('login_page.html', message="Parola a fost trimisă pe email.")
        else:
            return render_template('forgot_password.html', error_message="Eroare la trimiterea emailului.")

    return render_template('forgot_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        #iau datele
        username = request.form.get('username')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        #pastrez datele in sesiune pentru a nu aparea date personale in adresa URL
        session['username'] = username
        session['name'] = name
        session['email'] = email
        session['password'] = password

        #inregistrez utilizatorul
        result = engine.register(username, email)

        if "User created successfully" in result:
            return redirect(url_for('verify_code', username=username, email=email))
        else:
            return render_template('register_page.html', error_message=result)
    return render_template('register_page.html')

@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    #preiau datele
    if request.method == 'GET':
        username = request.args.get('username')
        email = request.args.get('email')
        session['username'] = username
        session['email'] = email
    else:
        username = session.get('username')
        email = session.get('email')

    if request.method == 'POST':
        #iau codul introdus
        user_code = request.form.get('code_to_verif')

        if engine.verify_code(user_code):
            #daca codul e corect, activez contul utilizatorului
            name = session.get('name')
            password = session.get('password')
            engine.activate_user(username, name, email, password)
            return render_template('verification_success.html', message="Contul tău a fost activat cu succes!")
        else:
            return render_template('verify_code.html', email=email, error_message="Cod incorect. Te rugăm să încerci din nou.")

    return render_template('verify_code.html', email=email)

@app.route('/select_genre', methods=['GET', 'POST'])
def select_genre():
    #verificam daca suntem logati
    if not engine.logged_in_user:
        username = session.get('username')
        if username:
            engine.logged_in_user = engine.userRepo.find_by_username(username)
        if not engine.logged_in_user:
            return redirect(url_for('login'))
    if request.method == 'POST':
        #luam preferintele si le setam pe cont
        selected_genres = request.form.getlist('genres')
        result = engine.set_user_genres(selected_genres)
        if result == 'homepage':
            return redirect(url_for('homepage'))
        return 'Eroare la salvarea genurilor.'
    return render_template('select_genre.html', genres=engine.genres)

@app.route('/homepage')
def homepage():
    playlists = []
    genre_recommendations = {}
    name = ""
    if engine.logged_in_user:
        #luam utilizatorul si preluam datele despre el
        user = engine.logged_in_user
        name = user.name
        engine.userRepo.load_users()

        #luam numele playlisturilor
        if user.id in engine.playlistRepos:
            repo = engine.playlistRepos[user.id]
            playlists = repo.get_playlist_names()

        index_to_genre = engine.genres

        #facem lista de preferinte
        preferred_genres = [
            index_to_genre[i]
            for i, val in enumerate(user.preferences)
            if val and i in index_to_genre
        ]

        #creem o lista de liste cu melodii impartite pe genuri
        for genre in preferred_genres:
            genre_recommendations[genre] = engine.recommend_by_genre(genre)

    return render_template("homepage.html", playlists=playlists, recommendations=genre_recommendations, name=name)

@app.route('/search', methods=['GET'])
def search():
    #luam datele de cautare: text, tip de cautare si numarul de rezultate dorite
    query = request.args.get('query')
    by_genre = request.args.get('by_genre') == 'true'
    limit = request.args.get('limit')
    if not query:
        return ''

    #preluam playlisturile in enetualitatea in care dorim sa adaugam melodii
    playlists = []
    name = engine.logged_in_user.name
    if engine.logged_in_user and engine.logged_in_user.id in engine.playlistRepos:
        repo = engine.playlistRepos[engine.logged_in_user.id]
        playlists = repo.get_playlist_names()

    #daca selectam gen, cautarea se face dupa gen, altfel, se face dupa titlu
    if by_genre:
        results = engine.search_music(query, by_genre, limit)
    else:
        results = engine.search_music(query, False, limit)

    return render_template('search_results.html', results=results, playlists=playlists, name=name)

@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    try:
        #luam numele playlistului
        data = request.get_json()
        playlist_name = data.get('name')

        #creem playlistul
        if playlist_name:
            result = engine.create_playlist(playlist_name, datetime.now())
            print(result)
            if "succes" in result:
                return jsonify({"success": True, "message": result}), 200
            else:
                return jsonify({"success": False, "error": result}), 400
        else:
            return jsonify({"success": False, "error": "Numele playlistului este necesar!"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/delete_playlist', methods=['POST'])
def delete_playlist():
    try:
        #luam playlistul si il stergem
        data = request.get_json(force=True)
        playlist_name = data.get('name')
        if not playlist_name:
            return jsonify({"success": False, "error": "Numele playlistului este necesar!"}), 400

        result = engine.delete_playlist(playlist_name)
        if "succes" in result:
            return jsonify({"success": True, "message": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/add_song_to_playlist', methods=['POST'])
def add_song_to_playlist():
    #luam datele melodiei si a playlistului
    data = request.get_json()
    playlist_name = data.get('playlist_name')
    song = data.get('song')

    #luam utilizatorul
    user = engine.logged_in_user
    if not user:
        return jsonify({"success": False, "message": "Utilizatorul nu este logat"}), 401
    if not playlist_name or not song:
        return jsonify({"success": False, "message": "Date lipsă"}), 400

    #luam id-ul
    user_id = user.id
    if user_id not in engine.playlistRepos:
        return jsonify({"success": False, "message": "Nu există repo de playlisturi pentru acest user"}), 400

    #luam repo-ul, cautam playlistul
    repo = engine.playlistRepos[user_id]
    playlist = repo.find_by_name(playlist_name)

    if not playlist:
        return jsonify({"success": False, "message": f"Playlistul '{playlist_name}' nu a fost găsit"}), 404

    #daca e deja in playlist, nu putem adauga
    if any(existing_song['id'] == song['id'] for existing_song in playlist.songs):
        return jsonify({"success": False, "already_exists": True, "message": "Melodia există deja în playlist"}), 200

    #aduagam cantecul si salvam datele
    playlist.add_song(song)
    engine.save_song_user_data()
    return jsonify({"success": True, "message": f"Cântecul a fost adăugat în '{playlist_name}'!"}), 200

@app.route('/playlist_details')
def playlist_details():
    #luam numele playlistului si utilizatorul
    playlist_name = request.args.get('name')
    user = engine.logged_in_user
    if not user or not playlist_name:
        return "Date insuficiente sau utilizatorul nu este autentificat", 400

    user_id = user.id
    if user_id not in engine.playlistRepos:
        return "Nu există repo de playlisturi pentru acest utilizator", 404

    repo = engine.playlistRepos[user_id]
    playlist = repo.find_by_name(playlist_name)

    if not playlist:
        return f"Playlistul '{playlist_name}' nu a fost găsit", 404

    return render_template('playlist_details.html', playlist=playlist)

@app.route('/shuffle_playlist', methods=['POST'])
def shuffle_playlist():
    #luam numele playlistului
    data = request.get_json(force=True)
    playlist_name = data.get('playlist_name')

    user = engine.logged_in_user
    if not user or not playlist_name:
        return jsonify({"success": False, "message": "Date lipsă"}), 400

    user_id = user.id
    repo = engine.playlistRepos.get(user_id)
    if not repo:
        return jsonify({"success": False, "message": "Repo inexistent"}), 404

    playlist = repo.find_by_name(playlist_name)
    if not playlist:
        return jsonify({"success": False, "message": "Playlist negăsit"}), 404

    #amestecam melodiile
    shuffled_songs = playlist.shuffle_playlists()
    return jsonify({"success": True, "songs": shuffled_songs})

@app.route('/delete_song_from_playlist', methods=['POST'])
def delete_song_from_playlist():
    #luam playlistul si melodia
    data = request.get_json()
    playlist_name = data.get('playlist_name')
    song_id = data.get('song_id')

    if not playlist_name or not song_id:
        return jsonify({"success": False, "message": "Date lipsă"}), 400

    user = engine.logged_in_user
    if not user:
        return jsonify({"success": False, "message": "Utilizatorul nu este logat"}), 401

    repo = engine.playlistRepos.get(user.id)
    if not repo:
        return jsonify({"success": False, "message": "Repo inexistent"}), 404

    playlist = repo.find_by_name(playlist_name)
    if not playlist:
        return jsonify({"success": False, "message": "Playlist negăsit"}), 404

    #stergem melodia si actualizam datele
    success = playlist.remove_song(song_id)
    engine.save_song_user_data()

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Melodia nu a fost găsită"}), 404

@app.route('/library_content')
def library_content():
    #preluam playlisturi si le dam mai departe
    user = engine.logged_in_user
    if not user:
        return "Trebuie să fii logat pentru a vedea biblioteca.", 401

    repo = engine.playlistRepos.get(user.id)
    playlists = repo.playlists if repo else []

    return render_template("library_content.html", playlists=playlists)

@app.route('/toggle_enhance_playlist', methods=['POST'])
def toggle_enhance_playlist():
    #luam datele playlistului si daca este activata optiunea sau nu
    data = request.get_json()
    playlist_name = data.get('playlist_name')
    toggle = data.get('toggle')  # True = activate, False = deactivate

    user = engine.logged_in_user
    if not user or not playlist_name:
        return jsonify({"success": False, "error": "User sau numele playlistului lipsesc"}), 400

    repo = engine.playlistRepos.get(user.id)
    playlist = repo.find_by_name(playlist_name)
    if not playlist:
        return jsonify({"success": False, "error": "Playlistul nu a fost găsit"}), 404

    #daca e activ
    if toggle:
        # Use the new hybrid recommender-based enhancement
        enhanced = engine.IntelliMix.enhanced_playlist(playlist, user_id=user.id)
        if enhanced:
            # Update the playlist in the repo with the enhanced version
            playlist.songs = enhanced.songs
            playlist.enhanced = True
            playlist.original_songs = enhanced.original_songs
    else:
        #resetam la original
        playlist.reset_to_original()
        playlist.enhanced = False

    #salvam playlistul
    engine.save_song_user_data()
    return jsonify({"success": True, "songs": playlist.songs})

@app.route('/download_song')
def download_song():
    #luam url-ul si titlus
    url = request.args.get('url')
    title = request.args.get('title', 'melodie').replace(' ', '_')

    if not url or not url.startswith('http'):
        return "URL invalid", 400


    try:
        #cerere GET catre url cu stream True pentru a nu incarca tot continutul odata
        response = requests.get(url, stream=True)
        #verificam statusul
        response.raise_for_status()

        #creem un fisier cu continutul din raspuns, ca atasament browserului WEB, cu un titlu si un tip de date
        return send_file(
            BytesIO(response.content),
            as_attachment=True,
            download_name=f"{title}.mp3",
            mimetype='audio/mpeg'
        )
    except Exception as e:
        return f"Eroare la descărcare: {str(e)}", 500
@app.route('/logout')
def logout():
    user = engine.logged_in_user
    if user:
        repo = engine.playlistRepos.get(user.id)
        if repo:
            #daca avem repo-uri si playlisturi si daca avem, le intoarcem la original si salvam in json
            for playlist in repo.playlists:
                if getattr(playlist, "enhanced", False):
                    playlist.reset_to_original()
                    playlist.enhanced = False
        engine.save_song_user_data()

    #deconectam si curatam datele din sesiune
    engine.logout()
    session.clear()
    return redirect(url_for('home'))



if __name__ == '__main__':
    app.run(debug=True)

