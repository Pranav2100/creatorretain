from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.core.settings import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "CreatorRetain API",
        "version": settings.APP_VERSION,
    }