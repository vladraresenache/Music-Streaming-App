// === Inițializare playere și controale ===
let playPauseButton = document.getElementById('play-pause-button');
const currentSongInfo = document.getElementById('current-song');
const progressBar = document.getElementById('progress-bar');
const volumeBar = document.getElementById('volume-bar');

let playlistQueue = [];
let currentIndex = 0;

let audio = document.getElementById('audio-player');
let audio2 = document.getElementById('audio-player-2');

let currentAudio = audio;
let nextAudio = audio2;

let userVolume = 1.0;

let fadeWatcher = null;
let fadeInterval = null;

// ==================== PLAYLIST ====================
function createPlaylistElement(name) {
    const playlistContainer = document.getElementById('sidebar-playlists');
    const newPlaylist = document.createElement('div');
    newPlaylist.className = 'playlist-item';
    newPlaylist.style.cursor = 'pointer';

    newPlaylist.addEventListener('click', function (event) {
        if (event.target.classList.contains('delete-btn')) return;

        $.get('/playlist_details', { name: name }, function (data) {
            $('.genre-section').remove();
            $('#search-results').html(data);
        }).fail(function () {
            alert("Eroare la încărcarea detaliilor playlistului.");
        });
    });

    const nameDiv = document.createElement('div');
    nameDiv.textContent = name;

    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = '✕';
    deleteBtn.className = 'delete-btn';
    deleteBtn.style.marginLeft = '10px';
    deleteBtn.style.color = 'red';
    deleteBtn.style.cursor = 'pointer';

    deleteBtn.addEventListener('click', function () {
        deletePlaylist(name);
    });

    newPlaylist.appendChild(nameDiv);
    newPlaylist.appendChild(deleteBtn);
    playlistContainer.appendChild(newPlaylist);
}

// ==================== INITIALIZARE CONTROALE ============
document.getElementById('prev-button').addEventListener('click', handlePrev);
document.getElementById('next-button').addEventListener('click', handleNext(true));
document.getElementById('play-pause-button').addEventListener('click', handlePlayPause);
volumeBar.addEventListener('input', handleVolumeChange);
progressBar.addEventListener('input', handleSeek);

function handlePlayPause() {
    if (currentAudio.paused) {
        currentAudio.play();
        playPauseButton.innerHTML = '<i class="fa-solid fa-pause"></i>';
    } else {
        currentAudio.pause();
        playPauseButton.innerHTML = '<i class="fa-solid fa-play"></i>';
    }
}

function handlePrev() {
    const wasAtStart = currentAudio.currentTime < 3;

    // oprim fade și resetăm totul
    stopFade();
    audio.onended = null;
    audio2.onended = null;

    [audio, audio2].forEach(a => {
        a.pause();
        a.currentTime = 0;
        a.src = "";
        a.onended = null;
    });

    if (wasAtStart && currentIndex > 0) {
        currentIndex--;
    }

    currentAudio = audio;
    nextAudio = audio2;

    const currentSong = playlistQueue[currentIndex];
    const nextSong = (currentIndex + 1 < playlistQueue.length) ? playlistQueue[currentIndex + 1] : null;

    playSongWithCrossfade(currentSong, nextSong, true);
}

function handleNext(manual = false) {
    if (currentIndex + 1 < playlistQueue.length) {
        stopFade();

        [audio, audio2].forEach(a => {
            a.pause();
            a.onended = null;
            a.currentTime = 0;
            a.src = ""; // 💡 foarte important: dezactivează complet sursa anterioară
        });

        // Avansează și setează noile referințe
        currentIndex++;
        const currentSong = playlistQueue[currentIndex];
        const nextSong = (currentIndex + 1 < playlistQueue.length) ? playlistQueue[currentIndex + 1] : null;

        currentAudio = audio;
        nextAudio = audio2;

        playSongWithCrossfade(currentSong, nextSong, true);
    } else {
        if (!isNaN(currentAudio.duration)) {
            currentAudio.currentTime = currentAudio.duration;
        }
    }
}

function stopFade() {
    if (fadeWatcher) {
        clearInterval(fadeWatcher);
        fadeWatcher = null;
    }
    if (fadeInterval) {
        clearInterval(fadeInterval);
        fadeInterval = null;
    }
}

function handleVolumeChange() {
    userVolume = parseFloat(volumeBar.value);
    currentAudio.volume = userVolume;
}

function handleSeek() {
    if (!isNaN(currentAudio.duration)) {
        currentAudio.currentTime = (progressBar.value / 100) * currentAudio.duration;
    }
}

// ==================== INITIALIZARE ====================
let crossfadeSeconds = 3;

$(document).ready(function () {
    $('#search-form').on('submit', function (event) {
        event.preventDefault();
        const query = $('#search-input').val();
        const genreToggle = $('#genre-toggle').is(':checked');
        const limit = $('#search-limit').val();
        if (query) {
            $('.genre-section').remove();
            $.get('/search', {
                query: query,
                by_genre: genreToggle,
                limit: limit
            }, function (data) {
                $('#search-results').html(data);
            }).fail(function () {
                $('#search-results').html('<p>A apărut o eroare la căutare.</p>');
            });
        } else {
            alert('Te rog să introduci un termen de căutare!');
        }
    });

    $('#create-playlist-button').on('click', function () {
        const playlistName = prompt("Introdu numele noului playlist:");
        if (playlistName && playlistName.trim() !== "") {
            $.ajax({
                url: '/create_playlist',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ name: playlistName }),
                success: function (response) {
                    if (response.success) {
                        createPlaylistElement(playlistName);
                        alert("Playlistul a fost creat cu succes!");
                    } else {
                        alert("Eroare la creare: " + response.error);
                    }
                },
                error: function () {
                    alert("Eroare de conexiune cu serverul.");
                }
            });
        } else {
            alert("Numele playlistului nu poate fi gol!");
        }
    });

    if (typeof initialPlaylists !== "undefined") {
        initialPlaylists.forEach(name => createPlaylistElement(name));
    }
});

currentAudio.addEventListener('loadedmetadata', () => {
    document.getElementById('duration-time').textContent = formatTime(currentAudio.duration);
});

currentAudio.addEventListener('timeupdate', () => {
    if (!isNaN(currentAudio.duration)) {
        progressBar.value = (currentAudio.currentTime / currentAudio.duration) * 100;
        document.getElementById('current-time').textContent = formatTime(currentAudio.currentTime);
    }
});

document.getElementById("logout-button").addEventListener("click", function () {
    if (confirm("Sigur vrei să te deloghezi?")) {
        window.location.href = "/logout";
    }
});

document.getElementById('download-button').addEventListener('click', () => {
    if (!currentAudio.src) {
        alert("Nicio melodie nu este redată.");
        return;
    }

    const songInfo = currentSongInfo.textContent || "melodie";
    const title = songInfo.replace('Melodie: ', '').split(' - ')[1] || 'melodie';

    const downloadUrl = `/download_song?url=${encodeURIComponent(currentAudio.src)}&title=${encodeURIComponent(title)}`;

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${title}.mp3`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
});

document.getElementById('crossfade-button').addEventListener('click', () => {
    const input = prompt("Introdu numărul de secunde pentru crossfade:", crossfadeSeconds);
    const value = parseInt(input);
    if (!isNaN(value) && value >= 0 && value <= 30) {
        crossfadeSeconds = value;
        alert(`Crossfade setat la ${crossfadeSeconds} secunde.`);
    } else {
        alert("Valoare invalidă. Te rog introdu un număr între 0 și 30.");
    }
});

document.getElementById("home-button").addEventListener("click", () => {
    window.location.href = "/homepage";
});

document.getElementById("library-button").addEventListener("click", function () {
    $('.genre-section').remove();
    $('#search-results').empty();

    $.get('/library_content', function (data) {
        $('#search-results').html(data);
    }).fail(function () {
        alert("Eroare la încărcarea bibliotecii.");
    });
});

// ==================== FUNCȚII AUXILIARE ====================
function addSongToPlaylist(id, title, artist, url, image, buttonElement) {
    const playlistName = buttonElement.previousElementSibling.value;

    if (!playlistName) {
        alert("Te rog selectează un playlist.");
        return;
    }

    $.ajax({
        url: '/add_song_to_playlist',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            playlist_name: playlistName,
            song: { id, title, artist, url, album_image: image }
        }),
        success: function (response) {
            if (response.already_exists) {
                alert("Această melodie există deja în playlist.");
            } else {
                alert(response.message || 'Cântec adăugat!');
            }
        },
        error: function () {
            alert('Eroare la adăugarea cântecului.');
        }
    });
}

function playSongFromPlaylist() {
    const currentSong = playlistQueue[currentIndex];
    const nextSong = (currentIndex + 1 < playlistQueue.length) ? playlistQueue[currentIndex + 1] : null;
    playSongWithCrossfade(currentSong, nextSong);
}

function shufflePlaylist(playlistName) {
    $.ajax({
        url: '/shuffle_playlist',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ playlist_name: playlistName }),
        success: function (res) {
            if (res.success) {
                playPlaylist(res.songs);
            } else {
                alert(res.message || "Eroare la redare.");
            }
        },
        error: function () {
            alert("Eroare de conexiune sau server.");
        }
    });
}

function deleteSongFromPlaylist(playlistName, songId, buttonElement) {
    if (!confirm("Ești sigur că vrei să ștergi această melodie?")) return;

    $.ajax({
        url: '/delete_song_from_playlist',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ playlist_name: playlistName, song_id: songId }),
        success: function (response) {
            if (response.success) {
                const songItem = buttonElement.closest('.song-item');
                songItem.remove();
                alert("Melodia a fost ștearsă.");
            } else {
                alert("Eroare: " + response.message);
            }
        },
        error: function () {
            alert("Eroare de conexiune la server.");
        }
    });
}

function playPlaylist(songs) {
    if (!songs || songs.length === 0) return;

    stopFade();
    [audio, audio2].forEach(a => {
        a.pause();
        a.currentTime = 0;
        a.src = "";
        a.onended = null;
    });

    currentAudio = audio;
    nextAudio = audio2;

    playlistQueue = songs;
    currentIndex = 0;

    playSongFromPlaylist();
}

function deletePlaylist(name) {
    if (!confirm(`Ești sigur că vrei să ștergi playlistul "${name}"?`)) return;

    $.ajax({
        url: '/delete_playlist',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ name: name }),
        success: function (response) {
            if (response.success) {
                // Elimină din bara laterală
                $('#sidebar-playlists .playlist-item').each(function () {
                    const text = $(this).find('div:first').text().trim();
                    if (text === name.trim()) {
                        $(this).remove();
                    }
                });

                // Elimină din biblioteca centrală
                $('.library-section .song-item').each(function () {
                    const title = $(this).find('strong').text().trim();
                    if (title === name.trim()) {
                        $(this).remove();
                    }
                });

                // Elimină din array-ul JS
                const index = initialPlaylists.indexOf(name);
                if (index !== -1) {
                    initialPlaylists.splice(index, 1);
                }

                // Mesaj fallback dacă nu mai sunt playlisturi
                if ($('.library-section .song-item').length === 0) {
                    $('.library-section').html('<p>Nu ai niciun playlist creat încă.</p>');
                }

                alert("Playlistul a fost șters cu succes!");
            } else {
                alert("Eroare: " + (response.error || "Nu s-a putut șterge playlistul."));
            }
        },
        error: function (xhr) {
            console.error("Eroare AJAX:", xhr.responseText);
            alert("Eroare de conexiune la server.");
        }
    });
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function playSongWithCrossfade(currentSong, nextSong, manual = false) {
    stopFade(); // oprim orice fade anterior

    currentAudio.src = currentSong.url;
    currentAudio.volume = userVolume;
    currentAudio.play();
    currentSongInfo.textContent = `${currentSong.artist} - ${currentSong.title}`;
    playPauseButton.innerHTML = '<i class="fa-solid fa-pause"></i>';
    setActiveAudioControls();

    if (manual || !nextSong) {
        currentAudio.onended = () => {
            currentIndex++;
            if (currentIndex < playlistQueue.length) {
                playSongWithCrossfade(playlistQueue[currentIndex], playlistQueue[currentIndex + 1] || null);
            } else {
                playPauseButton.innerHTML = '<i class="fa-solid fa-play"></i>';
            }
        };
        return;
    }

    fadeWatcher = startFadeWatcher(currentSong, nextSong);
}

function startFadeWatcher(currentSong, nextSong) {
    let fadeStarted = false;
    return setInterval(() => {
        if (!fadeStarted && !isNaN(currentAudio.duration)) {
            const timeLeft = currentAudio.duration - currentAudio.currentTime;
            if (timeLeft <= crossfadeSeconds) {
                fadeStarted = true;
                clearInterval(fadeWatcher);

                nextAudio.pause();
                nextAudio.currentTime = 0;
                nextAudio.src = nextSong.url;
                nextAudio.volume = 0;

                nextAudio.oncanplay = () => {
                    nextAudio.play();
                    nextAudio.oncanplay = null;
                };

                let step = 0;
                const totalSteps = crossfadeSeconds * 1000 / 50;

                fadeInterval = setInterval(() => {
                    step++;
                    const ratio = step / totalSteps;
                    currentAudio.volume = Math.max(userVolume * (1 - ratio), 0);
                    nextAudio.volume = Math.min(userVolume * ratio, userVolume);

                    if (step >= totalSteps) {
                        clearInterval(fadeInterval);
                        currentAudio.pause();

                        // Inversăm playerele
                        [currentAudio, nextAudio] = [nextAudio, currentAudio];

                        // Resetăm fostul next
                        nextAudio.pause();
                        nextAudio.currentTime = 0;
                        nextAudio.src = "";

                        currentIndex++;
                        setActiveAudioControls();
                        currentSongInfo.textContent = `${playlistQueue[currentIndex].artist} - ${playlistQueue[currentIndex].title}`;

                        if (currentIndex + 1 < playlistQueue.length) {
                            fadeWatcher = startFadeWatcher(
                                playlistQueue[currentIndex],
                                playlistQueue[currentIndex + 1]
                            );
                        } else {
                            currentAudio.onended = () => {
                                playPauseButton.innerHTML = '<i class="fa-solid fa-play"></i>';
                            };
                        }
                    }
                }, 50);
            }
        }
    }, 200);
}

function setActiveAudioControls() {
    // Înlocuiește butonul play/pause și actualizează referința
    const oldPlayPause = document.getElementById('play-pause-button');
    const newPlayPause = oldPlayPause.cloneNode(true);
    oldPlayPause.replaceWith(newPlayPause);
    playPauseButton = newPlayPause;

    playPauseButton.addEventListener('click', handlePlayPause);
    document.getElementById('prev-button').onclick = handlePrev;
    document.getElementById('next-button').onclick = handleNext;
    volumeBar.oninput = handleVolumeChange;
    progressBar.oninput = handleSeek;

    currentAudio.ontimeupdate = () => {
        if (!isNaN(currentAudio.duration)) {
            progressBar.value = (currentAudio.currentTime / currentAudio.duration) * 100;
            document.getElementById('current-time').textContent = formatTime(currentAudio.currentTime);
        }
    };

    currentAudio.onloadedmetadata = () => {
        document.getElementById('duration-time').textContent = formatTime(currentAudio.duration);
    };
}

function playSingleSong(url, title, artist) {
    playlistQueue = [{ url, title, artist }];
    currentIndex = 0;
    playSongWithCrossfade(playlistQueue[0], null);
}

function stopFade() {
    if (fadeWatcher) {
        clearInterval(fadeWatcher);
        fadeWatcher = null;
    }
    if (fadeInterval) {
        clearInterval(fadeInterval);
        fadeInterval = null;
    }
}