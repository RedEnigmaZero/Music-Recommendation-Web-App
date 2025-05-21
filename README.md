# Music Recommendation Web App

A personalized music recommendation platform that helps users discover new music based on their preferences using Spotify's API.

## Features

- User authentication via Dex
- Personalized music recommendations
- Interactive preference system
- Spotify API integration
- Like/Dislike functionality for refining recommendations

## Project Structure

```
.
├── frontend/           # Svelte frontend application
├── backend/           # Python backend application
├── docker/           # Docker configuration files
└── docs/             # Project documentation
```

## Tech Stack

- Frontend: Svelte
- Backend: Flask (Python)
- Database: MongoDB
- Authentication: Dex
- API: Spotify API
- Containerization: Docker

## Setup Instructions

### Prerequisites

- Python 3.8+ (for backend)
- Docker
- MongoDB
- Spotify Developer Account
- Modern web browser with JavaScript enabled

### Development Setup

1. Clone the repository
2. Set up the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Set up the backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   python run.py
   ```

4. Set up environment variables:
   - Create `.env` files in both frontend and backend directories
   - Add necessary API keys and configuration

## Development Phases

1. Project setup, UI wireframes, database schema
2. Frontend for login/registration & preference input / Backend user authentication & Spotify API link
3. First working demo
4. Refinement & UI polish
5. Full testing, Dockerization, bug fixing
6. Deployment and final documentation

## Contributing

Please read our contributing guidelines before submitting pull requests.

## License

[Add your license here] 