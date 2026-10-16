from app.core.settings import settings
from app.services.storage.base import FileStore, StoredFile
from app.services.storage.local import LocalFileStore
from app.services.storage.supabase import SupabaseFileStore

__all__ = [
    "FileStore",
    "StoredFile",
    "LocalFileStore",
    "SupabaseFileStore",
    "get_file_store",
]

_BACKENDS: dict[str, type[FileStore]] = {
    "local": LocalFileStore,
    "supabase": SupabaseFileStore,
}


def get_file_store() -> FileStore:
    backend = _BACKENDS.get(settings.STORAGE_BACKEND.lower())

    if backend is None:
        raise ValueError(
            f"Unknown STORAGE_BACKEND '{settings.STORAGE_BACKEND}'. "
            f"Expected one of: {', '.join(_BACKENDS)}."
        )

    return backend()
