"""notification-service/app/main.py"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import notify

app = FastAPI(title="DocSign Notification Service", version="1.0.0")
app.include_router(notify.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "notification-service"}
