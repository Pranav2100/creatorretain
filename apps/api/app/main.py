from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.brands import router as brand_router
from app.api.creator_profile import (
    categories_router,
    router as creator_profile_router,
)
from app.api.conversations import router as conversation_router
from app.api.discovery import router as discovery_router
from app.api.health import router as health_router
from app.api.pulse import router as pulse_router
from app.api.retainers import router as retainer_router
from app.api.workspace_plan import router as workspace_plan_router
from app.api.workspace import router as workspace_router
from app.api.workspace_invitations import (
    router as workspace_invitation_router,
)
from app.api.workspace_members import (
    router as workspace_member_router,
)
from app.core.logging import configure_logging
from app.core.settings import settings

configure_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(workspace_router)
app.include_router(workspace_plan_router)
app.include_router(creator_profile_router)
# Only when files live on this machine. With a real bucket the
# browser loads them from the CDN and this route never exists, so
# nothing in production is quietly serving a directory.
if settings.STORAGE_BACKEND.lower() == "local":
    from fastapi.staticfiles import StaticFiles

    media_root = Path(settings.LOCAL_MEDIA_ROOT)
    media_root.mkdir(parents=True, exist_ok=True)

    app.mount(
        "/media",
        StaticFiles(directory=media_root),
        name="media",
    )

app.include_router(discovery_router)
app.include_router(brand_router)
app.include_router(retainer_router)
app.include_router(categories_router)
app.include_router(workspace_member_router)
app.include_router(workspace_invitation_router)
app.include_router(conversation_router)
app.include_router(pulse_router)
app.include_router(health_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
