from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.middleware import rate_limit_and_audit_middleware
from app.routes import auth, records, history, reports, map_feed, upload
from datetime import datetime, timezone

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.middleware("http")(rate_limit_and_audit_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(records.router)
app.include_router(history.router)
app.include_router(reports.router)
app.include_router(map_feed.router)
app.include_router(upload.router)

@app.get("/health", tags=["Monitoring"])
@app.get("/api/v1/status", tags=["Monitoring"])
def health_check():
    return {
        "status": "healthy",
        "service": "electricity-management-backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }