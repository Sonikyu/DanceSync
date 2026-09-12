"""FastAPI dependency providers for storage and the metadata catalog.

Defined as functions, not module-level singletons, so tests can override them
via `app.dependency_overrides` and point at a temp directory instead of
`config.STORAGE_ROOT`.
"""

from __future__ import annotations

from functools import lru_cache

from server.catalog import Catalog
from server.config import STORAGE_ROOT
from server.storage import LocalStorage


@lru_cache
def get_storage() -> LocalStorage:
    return LocalStorage(STORAGE_ROOT / "media")


@lru_cache
def get_catalog() -> Catalog:
    return Catalog(STORAGE_ROOT / "catalog")
