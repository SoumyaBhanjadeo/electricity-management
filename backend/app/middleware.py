import time
import threading
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from app.database import SessionLocal
from app.models import AuditLog
from app.config import settings

request_records = defaultdict(list)
rate_limit_lock = threading.Lock()

def log_audit(path: str, method: str, status_code: int, duration_ms: float, client_ip: str):
    db = SessionLocal()
    try:
        log_entry = AuditLog(
            endpoint=path,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            client_ip=client_ip
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

async def rate_limit_and_audit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    if path in {"/health", "/api/v1/status", "/docs", "/openapi.json", "/redoc"}:
        start_time = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(duration_ms)
        return response

    current_time = time.time()
    with rate_limit_lock:
        cutoff = current_time - 60.0
        request_records[client_ip] = [
            t for t in request_records[client_ip] if t > cutoff
        ]
        if len(request_records[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
            retry_after = int(60 - (current_time - request_records[client_ip][0]))
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit of {settings.RATE_LIMIT_PER_MINUTE} requests per minute exceeded. Please try again later.",
                    "retry_after_seconds": max(1, retry_after)
                },
                headers={"Retry-After": str(max(1, retry_after))}
            )
        request_records[client_ip].append(current_time)

    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        log_audit(path, request.method, 500, duration_ms, client_ip)
        raise exc

    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(duration_ms)

    log_audit(path, request.method, response.status_code, duration_ms, client_ip)
    return response