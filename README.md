# Harmonia Music Application 🎵

Harmonia is a sophisticated music streaming and playlist management application that uses AI-powered recommendations to enhance your music discovery experience.

## Features 

- **Smart Playlist Enhancement**: Automatically enhance your playlists with AI-powered song recommendations
- **Genre-Based Discovery**: Explore music across multiple genres including pop, rock, electronic, hip-hop, jazz, and more
- **User Preferences**: Personalized recommendations based on your listening history and genre preferences
- **Intelligent Mixing**: Create dynamic playlists that adapt to your taste
- **Secure Authentication**: Full user authentication system with email verification
- **Modern UI**: Beautiful and responsive user interface for seamless music browsing

## Technical Stack 

- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript
- **Music API**: Jamendo API
- **AI/ML**: Hybrid recommendation system combining:
  - Collaborative filtering
  - Content-based filtering
  - Genre-based recommendations
  - User similarity analysis

## Installation 

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Harmonia.git
cd Harmonia
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Unix or MacOS:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create a .env file with:
JAMENDO_CLIENT_ID=your_client_id
SECRET_KEY=your_secret_key
```

5. Run the application:
```bash
python venv/app.py
```

## Usage 

1. **Register/Login**: Create an account or log in to access personalized features
2. **Select Genres**: Choose your preferred music genres for better recommendations
3. **Create Playlists**: Build your music collections
4. **Enhance Playlists**: Use the IntelliMix feature to automatically enhance your playlists with recommended songs
5. **Discover Music**: Search for new music and explore different genres

## Architecture 

- `app.py`: Main Flask application and routes
- `mainEngine.py`: Core application logic and user management
- `recommender.py`: AI recommendation system
- `music_api.py`: Jamendo API integration
- `util.py`: Utility functions and helper classes
- `static/`: Frontend assets (CSS, JS, images)
- `templates/`: HTML templates

## AI Recommendation System 

The application uses a sophisticated hybrid recommendation system that combines:

1. **Collaborative Filtering**: Finds similar users and recommends their music
2. **Content-Based Filtering**: Analyzes song features and metadata
3. **Genre-Based Recommendations**: Uses genre preferences for new users
4. **Hybrid Approach**: Combines all methods for optimal recommendations

## Contributing 

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License 

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments 

- Jamendo for providing the music API
- All contributors who have helped shape this project
- The open-source community for the amazing tools and libraries
