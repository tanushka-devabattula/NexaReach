# NexaReach

### AI-Powered Multilingual Public Awareness and Mass Communication Platform

NexaReach is a platform designed to support multilingual public awareness campaigns and mass communication. It provides a foundation for managing audiences, organizing campaigns, preparing message templates, tracking delivery, and collecting feedback.

## Features

- Responsive landing page with a modern interface
- Login and registration pages with frontend routing
- FastAPI backend with a health-check endpoint
- SQLAlchemy models for database management
- Alembic migrations for database schema management
- Audience management and audience segmentation APIs
- Campaign creation and management APIs
- Message template management APIs
- Message creation and retrieval APIs
- Database support for delivery logs and feedback
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
│   ├── alembic.ini
│   ├── requirements.txt
│   └── ER_DIAGRAM.md
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── .gitignore
├── ER_DIAGRAM.md
└── README.md
```

## Prerequisites

- Python 3.11 or newer
- Node.js and npm
- Visual Studio Code or another code editor

## Setup and Run

### 1. Backend Setup

Open a terminal in the project root and navigate to the backend directory:

```powershell
cd backend
```

Create a virtual environment if one does not already exist:

```powershell
python -m venv .venv
```

Activate the virtual environment in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
python -m pip install -r requirements.txt
```

Apply the database migrations:

```powershell
python -m alembic upgrade head
```

Start the FastAPI server:

```powershell
python -m uvicorn app.main:app --reload
```

Backend URL: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

Health check: http://127.0.0.1:8000/health

### 2. Frontend Setup

Open a **second terminal** and navigate to the frontend directory from the project root:

```powershell
cd frontend
```

Install the frontend dependencies:

```powershell
npm install
```

Start the React development server:

```powershell
npm run dev
```

Open the local URL shown in the terminal, usually:

http://localhost:5173

Keep both the backend and frontend terminals running while using the application.

## API Endpoints

The backend provides the following endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check backend status |
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Authenticate a user |
| GET | `/audience` | List audience members |
| POST | `/audience` | Create an audience member |
| GET | `/campaigns` | List campaigns |
| POST | `/campaigns` | Create a campaign |
| GET | `/campaigns/{campaign_id}` | Retrieve a campaign |
| GET | `/segments` | List audience segments |
| POST | `/segments` | Create an audience segment |
| GET | `/segments/{segment_id}` | Retrieve a segment |
| GET | `/templates` | List message templates |
| POST | `/templates` | Create a message template |
| GET | `/templates/{template_id}` | Retrieve a template |
| GET | `/messages` | List messages |
| POST | `/messages` | Create a message |
| GET | `/messages/{message_id}` | Retrieve a message |

### Health Check Example

Request:

```http
GET /health
```

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

The database schema is managed using SQLAlchemy models and Alembic migrations.

See `ER_DIAGRAM.md` for the entity relationship diagram.

## Project Status

Milestone 1 establishes the NexaReach frontend, FastAPI backend, database models, migration setup, and project documentation.

Implemented features include:

- Responsive landing page and frontend routing
- Registration and login API endpoints
- Audience, campaign, segment, template, and message APIs
- Database models and migration setup
- Frontend forms connected to backend APIs

The project is under active development. Advanced features such as automated message delivery, delivery tracking, and complete campaign workflows may require further implementation.

## License

Created as part of the Infosys Springboard Virtual Internship project.