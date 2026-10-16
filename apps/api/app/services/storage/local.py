from pathlib import Path

from app.core.settings import settings
from app.services.storage.base import FileStore, StoredFile


class LocalFileStore(FileStore):
    """
    Files on the API machine's own disk, served back by the app.

    For development, so the whole upload flow works before anyone
    has pasted a cloud key anywhere. Not for production: the files
    live beside the process and vanish with it the moment the API
    is deployed somewhere with an ephemeral filesystem.
    """

    def __init__(self, root: Path | None = None):
        self.root = root or Path(settings.LOCAL_MEDIA_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # The key is built by us, never by the uploader, but a
        # traversal check costs nothing and the day someone passes
        # a key through from a request is the day it matters.
        target = (self.root / key).resolve()

        if not target.is_relative_to(self.root.resolve()):
            raise ValueError("Refusing to write outside the media root.")

        return target

    def save(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredFile:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

        return StoredFile(
            url=f"{settings.API_URL}/media/{key}",
            key=key,
        )

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
