from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    AIContentHistory,
    ContentReview,
    TranslationRecord,
    ComplianceRule,
    ContentVariant,
    CampaignContent,
)
from app.routers import segments
from app.routers.ai import router as ai_router
from app.routers.analysis import router as analysis_router
from app.routers.audience import router as audience_router
from app.routers.auth import router as auth_router
from app.routers.campaigns import router as campaigns_router
from app.routers.health import router as health_router
from app.routers.messages import router as messages_router
from app.routers.personalization import router as personalization_router
from app.routers.review import router as review_router
from app.routers.templates import router as templates_router
from app.routers.translation import router as translation_router
from app.routers.workflow import router as workflow_router

app = FastAPI(
    title="NexaReach API",
    description=(
        "AI-Powered Multilingual Public Awareness "
        "and Mass Communication Platform"
    ),
    version="1.0.0",
)

# Milestone 1 routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(audience_router)
app.include_router(campaigns_router)
app.include_router(templates_router)
app.include_router(messages_router)
app.include_router(segments.router)

# Milestone 2 routers
app.include_router(ai_router)
app.include_router(translation_router)
app.include_router(personalization_router)
app.include_router(analysis_router)
app.include_router(review_router)
app.include_router(workflow_router)

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
    # Seed minimal data for tests and demo environments
    try:
        from app.seed import seed_initial_data
        seed_initial_data()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Seeding failed during startup: {e}")
