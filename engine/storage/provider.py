"""Portability storage providers, registry, and resolver interfaces for NAC."""
from __future__ import annotations

import hashlib
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path


class StorageProvider(ABC):
    """Abstract interface defining the core API for all storage providers in NAC."""

    @abstractmethod
    def save(self, key: str, data: bytes) -> None:
        """Persist data to the storage provider under the specified key."""
        pass

    @abstractmethod
    def load(self, key: str) -> bytes:
        """Retrieve data from the storage provider under the specified key.
        Raises FileNotFoundError if the key does not exist."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the data under the specified key.
        Raises FileNotFoundError if the key does not exist."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in the storage provider."""
        pass

    @abstractmethod
    def list(self) -> list[str]:
        """List all keys currently stored by the provider."""
        pass

    def verify(self, key: str, expected_hash: str) -> bool:
        """Verify the integrity of the data stored at the key against a SHA-256 hash.
        Returns False if the key does not exist or if the hash mismatch occurs.
        """
        try:
            data = self.load(key)
            actual_hash = hashlib.sha256(data).hexdigest()
            return actual_hash == expected_hash
        except FileNotFoundError:
            return False

    @abstractmethod
    def health(self) -> bool:
        """Perform a basic health/liveness check on the storage provider."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> dict[str, str]:
        """Returns the capability map for this provider.
        Values can be:
        - "supported" (represented as ✅ in UI)
        - "planned" (represented as 🚧 in UI)
        - "unsupported" (represented as ❌ in UI)
        """
        pass


class LocalStorageProvider(StorageProvider):
    """Storage provider targeting the local workstation workspace filesystem."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()

    def _get_path(self, key: str) -> Path:
        # Prevent directory traversal attacks by resolving and checking path prefix
        target_path = Path(self.base_dir / key).resolve()
        if not target_path.is_relative_to(self.base_dir):
            raise ValueError(f"Directory traversal detected for key: {key}")
        return target_path

    def save(self, key: str, data: bytes) -> None:
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def load(self, key: str) -> bytes:
        path = self._get_path(key)
        if not path.is_file():
            raise FileNotFoundError(f"Key not found in local storage: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._get_path(key)
        if not path.is_file():
            raise FileNotFoundError(f"Key not found in local storage: {key}")
        path.unlink()

    def exists(self, key: str) -> bool:
        try:
            path = self._get_path(key)
            return path.is_file()
        except ValueError:
            return False

    def list(self) -> list[str]:
        if not self.base_dir.exists():
            return []
        keys = []
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.base_dir)
                keys.append(relative_path.as_posix())
        return sorted(keys)

    def health(self) -> bool:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            # Perform a canary write/read/delete
            canary_key = ".health_canary"
            canary_data = b"health_ok"
            self.save(canary_key, canary_data)
            if self.load(canary_key) != canary_data:
                return False
            self.delete(canary_key)
            return True
        except Exception:
            return False

    @property
    def capabilities(self) -> dict[str, str]:
        return {
            "read": "supported",
            "write": "supported",
            "delete": "supported",
            "verify": "supported",
            "snapshot": "supported",
            "restore": "supported",
        }


class ExternalStorageProvider(StorageProvider):
    """Storage provider targeting an external SSD/HDD storage device."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()

    def _get_path(self, key: str) -> Path:
        target_path = Path(self.base_dir / key).resolve()
        if not target_path.is_relative_to(self.base_dir):
            raise ValueError(f"Directory traversal detected for key: {key}")
        return target_path

    def save(self, key: str, data: bytes) -> None:
        if not self.base_dir.exists():
            raise OSError(f"External storage device is not mounted or directory does not exist: {self.base_dir}")
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def load(self, key: str) -> bytes:
        if not self.base_dir.exists():
            raise OSError(f"External storage device is not mounted or directory does not exist: {self.base_dir}")
        path = self._get_path(key)
        if not path.is_file():
            raise FileNotFoundError(f"Key not found in external storage: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        if not self.base_dir.exists():
            raise OSError(f"External storage device is not mounted or directory does not exist: {self.base_dir}")
        path = self._get_path(key)
        if not path.is_file():
            raise FileNotFoundError(f"Key not found in external storage: {key}")
        path.unlink()

    def exists(self, key: str) -> bool:
        if not self.base_dir.exists():
            return False
        try:
            path = self._get_path(key)
            return path.is_file()
        except ValueError:
            return False

    def list(self) -> list[str]:
        if not self.base_dir.exists():
            return []
        keys = []
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.base_dir)
                keys.append(relative_path.as_posix())
        return sorted(keys)

    def health(self) -> bool:
        if not self.base_dir.exists():
            return False
        try:
            canary_key = ".health_canary"
            canary_data = b"health_ok"
            self.save(canary_key, canary_data)
            if self.load(canary_key) != canary_data:
                return False
            self.delete(canary_key)
            return True
        except Exception:
            return False

    @property
    def capabilities(self) -> dict[str, str]:
        return {
            "read": "supported",
            "write": "supported",
            "delete": "supported",
            "verify": "supported",
            "snapshot": "supported",
            "restore": "supported",
        }


class AzureStorageProvider(StorageProvider):
    """Stub implementation of Azure Blob storage provider."""

    def __init__(self, container_name: str) -> None:
        self.container_name = container_name

    def save(self, key: str, data: bytes) -> None:
        raise NotImplementedError("AzureStorageProvider is not yet implemented.")

    def load(self, key: str) -> bytes:
        raise NotImplementedError("AzureStorageProvider is not yet implemented.")

    def delete(self, key: str) -> None:
        raise NotImplementedError("AzureStorageProvider is not yet implemented.")

    def exists(self, key: str) -> bool:
        raise NotImplementedError("AzureStorageProvider is not yet implemented.")

    def list(self) -> list[str]:
        raise NotImplementedError("AzureStorageProvider is not yet implemented.")

    def health(self) -> bool:
        return False

    @property
    def capabilities(self) -> dict[str, str]:
        return {
            "read": "planned",
            "write": "planned",
            "delete": "planned",
            "verify": "planned",
            "snapshot": "planned",
            "restore": "planned",
        }


class GoogleStorageProvider(StorageProvider):
    """Stub implementation of Google Cloud Storage provider."""

    def __init__(self, bucket_name: str) -> None:
        self.bucket_name = bucket_name

    def save(self, key: str, data: bytes) -> None:
        raise NotImplementedError("GoogleStorageProvider is not yet implemented.")

    def load(self, key: str) -> bytes:
        raise NotImplementedError("GoogleStorageProvider is not yet implemented.")

    def delete(self, key: str) -> None:
        raise NotImplementedError("GoogleStorageProvider is not yet implemented.")

    def exists(self, key: str) -> bool:
        raise NotImplementedError("GoogleStorageProvider is not yet implemented.")

    def list(self) -> list[str]:
        raise NotImplementedError("GoogleStorageProvider is not yet implemented.")

    def health(self) -> bool:
        return False

    @property
    def capabilities(self) -> dict[str, str]:
        return {
            "read": "planned",
            "write": "planned",
            "delete": "planned",
            "verify": "planned",
            "snapshot": "planned",
            "restore": "planned",
        }


class StorageRegistry:
    """Registry to register and retrieve storage providers by name."""

    def __init__(self) -> None:
        self._providers: dict[str, StorageProvider] = {}

    def register(self, name: str, provider: StorageProvider) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> StorageProvider:
        if name not in self._providers:
            raise KeyError(f"Storage provider '{name}' is not registered.")
        return self._providers[name]

    def list_registered(self) -> list[str]:
        return sorted(self._providers.keys())


class StorageResolver:
    """Resolves keys or configurations to storage providers via a registry."""

    def __init__(self, registry: StorageRegistry) -> None:
        self.registry = registry

    def resolve(self, provider_name: str) -> StorageProvider:
        """Resolve the provider by registered name."""
        return self.registry.get(provider_name)
