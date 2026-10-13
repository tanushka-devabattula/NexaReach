
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.health import router as health_router

from app.db.session import Base, engine
from app.models import (
    User,
    Role,
    AudienceMember,
    Segment,
    Campaign,
    Template,
    Message,
    DeliveryLog,
    Feedback,
)

app = FastAPI(
    title="NexaReach API",
    description=(
        "AI-Powered Multilingual Public Awareness "
        "and Mass Communication Platform"
    ),
    version="1.0.0",
)

app.include_router(health_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_database_tables():
    Base.metadata.create_all(bind=engine)


