"""
core/storage/__init__.py — Phase 6 S5-T22: Document storage abstraction.

Defines the `Storage` Protocol and provides two implementations:
  - `LocalStorage`: default; writes to the local filesystem
  - `S3Storage`:    stub; raises NotImplementedError — enable in Phase 6.2+

Usage in routers / services:
    from core.storage import get_storage, Storage

    # FastAPI Depends injection
    def my_endpoint(..., storage: Storage = Depends(get_storage)):
        storage.put(path, data)

    # Or module-level singleton (useful in plain service functions)
    from core.storage import default_storage
    default_storage.put(path, data)

Environment variables:
    STORAGE_BACKEND    "local" (default) | "s3"
    DOCUMENT_STORAGE_PATH    Base directory for LocalStorage (default: ./data/documents)
"""
from __future__ import annotations

import logging
import os
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

__all__ = [
    "Storage",
    "LocalStorage",
    "S3Storage",
    "get_storage",
    "default_storage",
]


# ── Protocol definition ───────────────────────────────────────────────────────

@runtime_checkable
class Storage(Protocol):
    """
    Abstract interface for document byte storage.

    *path* is an opaque key in the same format used by `storage_path` in the
    `documents` table.  For `LocalStorage` it is a filesystem path.  For
    future `S3Storage` it would be a bucket-relative key.
    """

    def put(self, path: str, data: bytes) -> None:
        """Write *data* to *path*, creating parent directories as needed."""
        ...

    def get(self, path: str) -> bytes:
        """Return the raw bytes stored at *path*."""
        ...

    def delete(self, path: str) -> None:
        """Remove the object at *path*.  Best-effort: no error if absent."""
        ...

    def exists(self, path: str) -> bool:
        """Return True if *path* refers to an existing object."""
        ...


# ── Local filesystem implementation ──────────────────────────────────────────

class LocalStorage:
    """
    Stores documents on the local filesystem under *root_dir*.

    This is the default backend.  The *root_dir* defaults to the value of the
    ``DOCUMENT_STORAGE_PATH`` environment variable, falling back to
    ``./data/documents``.
    """

    def __init__(self, root_dir: str | None = None) -> None:
        self._root = root_dir or os.environ.get(
            "DOCUMENT_STORAGE_PATH", "./data/documents"
        )

    @property
    def root_dir(self) -> str:
        return self._root

    def put(self, path: str, data: bytes) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)

    def get(self, path: str) -> bytes:
        with open(path, "rb") as fh:
            return fh.read()

    def delete(self, path: str) -> None:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning("LocalStorage.delete: could not remove %s: %s", path, exc)

    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def make_path(self, ws_id: str, filename: str) -> str:
        """
        Build a canonical storage path for a new document file.

        Returns an absolute-ish path within *root_dir*:
          ``{root_dir}/{ws_id}/{filename}``

        Callers are responsible for ensuring *filename* is unique (e.g. by
        prefixing with a UUID).
        """
        return os.path.join(self._root, ws_id, filename)


# ── S3 stub (Phase 6.2+) ─────────────────────────────────────────────────────

class S3Storage:
    """
    Stub for Amazon S3 / S3-compatible object storage.

    All methods raise ``NotImplementedError`` until implemented in Phase 6.2.

    Constructor parameters (reserved for future use):
        bucket          S3 bucket name
        prefix          Key prefix (e.g. "documents/")
        region          AWS region
        aws_access_key_id, aws_secret_access_key   — or use IAM instance role
        endpoint_url    For MinIO / other S3-compatible stores
    """

    def __init__(
        self,
        bucket: str = "",
        prefix: str = "documents/",
        region: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        self._access_key = aws_access_key_id
        self._secret_key = aws_secret_access_key
        self.endpoint_url = endpoint_url

    def put(self, path: str, data: bytes) -> None:
        raise NotImplementedError("S3Storage is not yet implemented — Phase 6.2")

    def get(self, path: str) -> bytes:
        raise NotImplementedError("S3Storage is not yet implemented — Phase 6.2")

    def delete(self, path: str) -> None:
        raise NotImplementedError("S3Storage is not yet implemented — Phase 6.2")

    def exists(self, path: str) -> bool:
        raise NotImplementedError("S3Storage is not yet implemented — Phase 6.2")

    def make_path(self, ws_id: str, filename: str) -> str:
        """Build an S3 object key for a new document."""
        return f"{self.prefix}{ws_id}/{filename}"


# ── Factory & singleton ───────────────────────────────────────────────────────

def _build_storage() -> LocalStorage | S3Storage:
    backend = os.environ.get("STORAGE_BACKEND", "local").lower()
    if backend == "s3":
        logger.info("Using S3Storage backend (stub — Phase 6.2)")
        return S3Storage(
            bucket=os.environ.get("S3_BUCKET", ""),
            prefix=os.environ.get("S3_PREFIX", "documents/"),
            region=os.environ.get("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
        )
    logger.debug("Using LocalStorage backend (root=%s)", os.environ.get("DOCUMENT_STORAGE_PATH", "./data/documents"))
    return LocalStorage()


#: Module-level default storage instance.
#: Import and use directly in service functions that don't use FastAPI Depends.
default_storage: LocalStorage | S3Storage = _build_storage()


def get_storage() -> LocalStorage | S3Storage:
    """
    FastAPI dependency that returns the active storage backend.

    Usage::

        @router.post("/{ws_id}/documents/upload")
        async def upload(..., storage: Storage = Depends(get_storage)):
            storage.put(path, data)
    """
    return default_storage
