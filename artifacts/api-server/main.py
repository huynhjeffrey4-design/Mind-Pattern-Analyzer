import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine
from app.models.base import Base
from app.models import user, checkin, journal, insight, safety_event
from app.routes import auth, checkins, journals, dashboard, insights, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MindPattern API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(checkins.router, prefix=API_PREFIX)
app.include_router(journals.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(insights.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)


@app.get("/api/health")
def health():
    return {"status": "ok"}
