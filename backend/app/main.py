from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.middleware import RateLimitAndAuditMiddleware
from app.routes import auth

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