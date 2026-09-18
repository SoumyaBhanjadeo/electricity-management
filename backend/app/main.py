from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.middleware import RateLimitAndAuditMiddleware
from app.routes import auth
from datetime import datetime, timezone

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(RateLimitAndAuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/health", tags=["Monitoring"])
@app.get("/api/v1/status", tags=["Monitoring"])
def health_check():
    return {
        "status": "healthy",
        "service": "electricity-management-backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }