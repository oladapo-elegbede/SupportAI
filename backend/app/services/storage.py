import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
import shutil

from app.core.config import settings


class StorageError(Exception):
    """Base exception for file storage operations."""
    pass


class PathTraversalError(StorageError):
    """Raised when a requested path attempts to escape the root upload directory."""
    pass


class FileStorageService(ABC):
    """Abstract Base Class defining the file storage provider interface."""

    @abstractmethod
    async def save_file(self, file_bytes: bytes, relative_path: str) -> str:
        """Saves file bytes to the destination path. Returns resolved relative path."""
        pass

    @abstractmethod
    async def get_file(self, relative_path: str) -> bytes:
        """Reads and returns raw bytes from the file path."""
        pass

    @abstractmethod
    async def delete_file(self, relative_path: str) -> bool:
        """Deletes file at relative path. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    async def file_exists(self, relative_path: str) -> bool:
        """Checks whether a file exists at relative path."""
        pass

    @abstractmethod
    async def delete_directory(self, relative_path: str) -> bool:
        """Deletes an entire directory (e.g., purging an Org or KB folder)."""
        pass


class LocalFileStorage(FileStorageService):
    """Local Filesystem Implementation of FileStorageService."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR).resolve()
        # Ensure base upload directory exists on disk
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, relative_path: str) -> Path:
        """
        Resolves relative path against base_dir and enforces strict path-traversal checks.
        """
        # Strip leading slashes to prevent Path joining override
        clean_relative = relative_path.lstrip("/\\")
        target_path = (self.base_dir / clean_relative).resolve()

        # SECURITY CHECK: Ensure target_path stays inside base_dir boundary
        try:
            target_path.relative_to(self.base_dir)
        except ValueError:
            raise PathTraversalError(
                f"Path traversal attempt detected: '{relative_path}' escapes root '{self.base_dir}'"
            )

        return target_path

    async def save_file(self, file_bytes: bytes, relative_path: str) -> str:
        target_path = self._resolve_path(relative_path)
        
        # Ensure parent directories exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        def _write():
            target_path.write_bytes(file_bytes)

        await asyncio.to_thread(_write)
        
        # Return normalized relative path using POSIX slashes for database consistency
        return str(target_path.relative_to(self.base_dir)).replace("\\", "/")

    async def get_file(self, relative_path: str) -> bytes:
        target_path = self._resolve_path(relative_path)

        if not target_path.is_file():
            raise StorageError(f"File not found: {relative_path}")

        def _read():
            return target_path.read_bytes()

        return await asyncio.to_thread(_read)

    async def delete_file(self, relative_path: str) -> bool:
        target_path = self._resolve_path(relative_path)

        if not target_path.is_file():
            return False

        def _remove():
            target_path.unlink(missing_ok=True)

        await asyncio.to_thread(_remove)
        return True

    async def file_exists(self, relative_path: str) -> bool:
        try:
            target_path = self._resolve_path(relative_path)
            return target_path.is_file()
        except PathTraversalError:
            return False

    async def delete_directory(self, relative_path: str) -> bool:
        target_path = self._resolve_path(relative_path)

        if not target_path.is_dir():
            return False

        def _rmtree():
            shutil.rmtree(target_path, ignore_errors=True)

        await asyncio.to_thread(_rmtree)
        return True


def get_storage_service() -> FileStorageService:
    """Factory function returning the configured storage service provider."""
    if settings.STORAGE_PROVIDER == "local":
        return LocalFileStorage(settings.UPLOAD_DIR)
    else:
        raise NotImplementedError(f"Storage provider '{settings.STORAGE_PROVIDER}' is not implemented.")
