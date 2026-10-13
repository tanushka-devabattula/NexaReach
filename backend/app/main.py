from app.routers.audience import router as audience_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.campaigns import router as campaigns_router
from app.routers.templates import router as templates_router
from app.routers.messages import router as messages_router

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
app.include_router(auth_router)
app.include_router(audience_router)
app.include_router(campaigns_router)
app.include_router(templates_router)
app.include_router(messages_router)

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


