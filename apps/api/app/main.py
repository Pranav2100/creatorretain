from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.workspace import router as workspace_router
from app.api.workspace_invitations import (
    router as workspace_invitation_router,
)
from app.api.workspace_members import (
    router as workspace_member_router,
)
from app.core.settings import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(auth_router)
app.include_router(workspace_router)
app.include_router(workspace_member_router)
app.include_router(workspace_invitation_router)
app.include_router(health_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
