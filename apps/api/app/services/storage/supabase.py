import httpx

from app.core.settings import settings
from app.services.storage.base import FileStore, StoredFile

TIMEOUT = httpx.Timeout(20.0)


class SupabaseFileStore(FileStore):
    """
    Supabase Storage, over its REST API.

    Deliberately not the supabase-py client: this needs three HTTP
    calls in total, and a plain request keeps a large dependency
    and its own transitive tree out of the project.

    The secret key used here bypasses row level security, so it
    lives only on the API and never reaches a browser. The
    bucket is public to read, which is what makes a logo loadable
    from an <img> without signing every URL; writing still needs
    this key.
    """

    def __init__(self):
        base = (settings.SUPABASE_URL or "").rstrip("/")
        key = settings.SUPABASE_SECRET_KEY

        if not base or not key:
            raise ValueError(
                "STORAGE_BACKEND is 'supabase' but SUPABASE_URL or "
                "SUPABASE_SECRET_KEY is not set."
            )

        self.base = base
        self.key = key
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
        }

    def save(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredFile:
        response = httpx.post(
            f"{self.base}/storage/v1/object/{self.bucket}/{key}",
            content=data,
            headers={
                **self._headers(),
                "Content-Type": content_type,
                # Replace rather than fail when a workspace uploads
                # a second logo to the same path.
                "x-upsert": "true",
            },
            timeout=TIMEOUT,
        )

        if response.status_code >= 400:
            raise ValueError(
                "Could not store the image. "
                f"Supabase said {response.status_code}."
            )

        return StoredFile(
            url=(
                f"{self.base}/storage/v1/object/public/"
                f"{self.bucket}/{key}"
            ),
            key=key,
        )

    def delete(self, key: str) -> None:
        response = httpx.request(
            "DELETE",
            f"{self.base}/storage/v1/object/{self.bucket}/{key}",
            headers=self._headers(),
            timeout=TIMEOUT,
        )

        # 404 means the caller already has what they wanted.
        if response.status_code not in (200, 204, 404):
            raise ValueError(
                "Could not remove the image. "
                f"Supabase said {response.status_code}."
            )
