
# NexaReach

### AI-Powered Multilingual Public Awareness and Mass Communication Platform

NexaReach is a platform designed to support multilingual public awareness campaigns and mass communication. It provides a foundation for managing audiences, organizing campaigns, preparing message templates, tracking delivery, and collecting feedback.

## Features

- Responsive landing page with a modern interface
- Login and registration pages with frontend routing
- FastAPI backend with a health-check endpoint
- SQLAlchemy models for database management
- Alembic migrations for database schema management
- Support for audience segments, campaigns, templates, messages, delivery logs, and feedback
- Language and communication-channel fields for multilingual messaging
- Axios service for frontend-to-backend communication

## Technology Stack

**Frontend**
- React
- Vite
- React Router
- Axios
- CSS

**Backend**
- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic Settings

**Database**
- SQLite

## Project Structure

```text
task1/
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── .env.example
│   ├── ER_DIAGRAM.md
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       └── App.jsx
└── README.md
```

## Prerequisites

- Python 3.11 or newer
- Node.js and npm

## Setup and Run

### 1. Backend

Open a terminal in the `backend` directory.

Create and activate a virtual environment if you do not already have one:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
python -m pip install "fastapi[standard]" sqlalchemy alembic pydantic-settings
```

Apply the database migrations:

```powershell
python -m alembic upgrade head
```

Start the API server:

```powershell
python -m uvicorn app.main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

API documentation: `http://127.0.0.1:8000/docs`

### 2. Frontend

Open another terminal in the `frontend` directory.

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the local URL printed in the terminal, usually `http://localhost:5173`.

## API Endpoint

### Health Check

**GET** `/health`

Example response:

```json
{
  "status": "ok",
  "message": "NexaReach backend is running"
}
```

## Database Tables

The database contains the following application tables:

1. `roles`
2. `users`
3. `audience_members`
4. `segments`
5. `campaigns`
6. `templates`
7. `messages`
8. `delivery_logs`
9. `feedback`

See [`backend/ER_DIAGRAM.md`](backend/ER_DIAGRAM.md) for the entity relationship diagram.

## Project Status

Task 1 establishes the initial frontend interface, backend API, database models, migration setup, and project documentation.

Authentication, campaign processing, message delivery, and other business workflows may require further implementation in subsequent milestones.

## License

Created as part of the Infosys Springboard Virtual Internship project.
