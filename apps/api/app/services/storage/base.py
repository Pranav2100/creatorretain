from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFile:
    # Where the browser loads it from.
    url: str

    # How this store finds it again to delete it. Kept separate
    # from the URL because a CDN address and a storage path are
    # not always the same string.
    key: str


class FileStore(ABC):
    """
    Anywhere a file can be put and later fetched over HTTP.

    Abstract for the same reason the email sender is: the code that
    accepts a logo should not know whether it ends up in a bucket,
    on a disk or nowhere at all, so running without cloud
    credentials stays a configuration choice rather than a
    different code path.
    """

    @abstractmethod
    def save(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredFile:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Quietly does nothing if it has already gone. Deleting a
        file that is not there is the state the caller wanted.
        """
