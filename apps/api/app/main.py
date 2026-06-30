from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "CreatorRetain API",
        "version": "0.1.0",
    }