import logging
from contextlib import asynccontextmanager
from app.services.scheduler_service import start_scheduler, stop_scheduler
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    health,
    auth,
    audience,
    segments,
    templates,
    campaigns,
    ai,
    translation,
    personalization,
    review,
    workflow,
    broadcast,
    campaign_content,
    webhooks,
    push,
    whatsapp,
    analysis,
    messages,
    admin,
    analytics,
)
from app.core.security import get_current_user
from app.db.session import Base, SessionLocal, engine
from app.services.auth_service import ensure_default_roles

logger = logging.getLogger(__name__)

# Create DB tables
Base.metadata.create_all(bind=engine)

# Make sure the default roles exist (admin, campaign_manager, communication_team, user)
_db = SessionLocal()
try:
    ensure_default_roles(_db)
except Exception:  # never stop the app from starting because of seeding
    logger.exception("Could not create default roles")
finally:
    _db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    logger.info("NexaReach scheduler started")
    yield
    stop_scheduler()
    logger.info("NexaReach scheduler stopped")

app = FastAPI(
    title="NexaReach API",
    description="AI-Powered Multilingual Public Awareness and Mass Communication Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers that anyone may call: health, login/register, provider webhooks
# (they are checked by signature instead), and the public push/broadcast endpoints.
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(push.router)       # /push/test needs login (set inside push.py)
app.include_router(broadcast.router)  # /broadcast/send needs a role (set inside broadcast.py)

# Everything below needs a valid login token (401 without one).
protected = [Depends(get_current_user)]
app.include_router(audience.router, dependencies=protected)
app.include_router(segments.router, dependencies=protected)
app.include_router(templates.router, dependencies=protected)
app.include_router(campaigns.router, dependencies=protected)
app.include_router(ai.router, dependencies=protected)
app.include_router(translation.router, dependencies=protected)
app.include_router(personalization.router, dependencies=protected)
app.include_router(review.router, dependencies=protected)
app.include_router(analysis.router, dependencies=protected)
app.include_router(analytics.router, dependencies=protected)
app.include_router(messages.router, dependencies=protected)
app.include_router(workflow.router, dependencies=protected)
app.include_router(whatsapp.router, dependencies=protected)
app.include_router(campaign_content.router)  # has its own login checks
app.include_router(admin.router)             # admin only (set inside admin.py)

@app.get("/")
def root_read():
    return {"message": "NexaReach Multilingual Mass Communication Platform API is Running"}