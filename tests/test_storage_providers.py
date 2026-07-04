import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from engine.storage import (
    AzureStorageProvider,
    ExternalStorageProvider,
    GoogleStorageProvider,
    LocalStorageProvider,
    StorageProvider,
    StorageRegistry,
    StorageResolver,
)


class BaseProviderComplianceTests:
    """Base compliance test suite that all concrete active StorageProvider implementations must pass."""

    @pytest.fixture
    def provider(self) -> StorageProvider:
        raise NotImplementedError("Subclasses must implement this fixture to return a configured StorageProvider.")

    def test_save_and_load(self, provider: StorageProvider) -> None:
        key = "test_file.txt"
        data = b"hello world"
        provider.save(key, data)
        assert provider.exists(key) is True
        assert provider.load(key) == data

    def test_load_missing_raises_file_not_found(self, provider: StorageProvider) -> None:
        with pytest.raises(FileNotFoundError):
            provider.load("does_not_exist.bin")

    def test_delete_existing(self, provider: StorageProvider) -> None:
        key = "to_delete.txt"
        data = b"delete me"
        provider.save(key, data)
        assert provider.exists(key) is True
        provider.delete(key)
        assert provider.exists(key) is False
        with pytest.raises(FileNotFoundError):
            provider.load(key)

    def test_delete_missing_raises_file_not_found(self, provider: StorageProvider) -> None:
        with pytest.raises(FileNotFoundError):
            provider.delete("never_existed.bin")

    def test_list(self, provider: StorageProvider) -> None:
        keys = ["a.txt", "sub/b.txt", "sub/nested/c.txt"]
        for k in keys:
            provider.save(k, b"data")

        listed = provider.list()
        for k in keys:
            assert k in listed

        assert "sub/b.txt" in listed
        assert "sub/nested/c.txt" in listed

    def test_verify_integrity(self, provider: StorageProvider) -> None:
        key = "integrity.bin"
        data = b"secure payload"
        provider.save(key, data)

        correct_hash = hashlib.sha256(data).hexdigest()
        assert provider.verify(key, correct_hash) is True

        incorrect_hash = hashlib.sha256(b"wrong payload").hexdigest()
        assert provider.verify(key, incorrect_hash) is False
        assert provider.verify("missing.bin", correct_hash) is False

    def test_directory_traversal_protection(self, provider: StorageProvider) -> None:
        # Applies to path-based storage providers
        if hasattr(provider, "_get_path"):
            with pytest.raises(ValueError):
                provider.save("../dangerous.txt", b"hack")
            with pytest.raises(ValueError):
                provider.load("../dangerous.txt")

    def test_health(self, provider: StorageProvider) -> None:
        assert provider.health() is True

    def test_capabilities_matrix(self, provider: StorageProvider) -> None:
        caps = provider.capabilities
        required_caps = ["read", "write", "delete", "verify", "snapshot", "restore"]
        for cap in required_caps:
            assert cap in caps
            assert caps[cap] in ["supported", "planned", "unsupported"]


class TestLocalStorageProvider(BaseProviderComplianceTests):
    """LocalStorageProvider compliance test runs."""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    @pytest.fixture
    def provider(self, temp_dir: Path) -> StorageProvider:
        return LocalStorageProvider(temp_dir)

    def test_local_capabilities(self, provider: StorageProvider) -> None:
        for val in provider.capabilities.values():
            assert val == "supported"


class TestExternalStorageProvider(BaseProviderComplianceTests):
    """ExternalStorageProvider compliance test runs."""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    @pytest.fixture
    def provider(self, temp_dir: Path) -> StorageProvider:
        return ExternalStorageProvider(temp_dir)

    def test_external_capabilities(self, provider: StorageProvider) -> None:
        for val in provider.capabilities.values():
            assert val == "supported"

    def test_external_missing_directory_raises(self) -> None:
        provider = ExternalStorageProvider("Z:\\non_existent_drive_mount_path")
        assert provider.health() is False
        assert provider.exists("any.txt") is False
        assert provider.list() == []

        with pytest.raises(OSError):
            provider.save("any.txt", b"data")

        with pytest.raises(OSError):
            provider.load("any.txt")

        with pytest.raises(OSError):
            provider.delete("any.txt")


class TestStubProviders:
    """Test stub cloud storage providers raise NotImplementedError for operations."""

    def test_azure_provider_stubs(self) -> None:
        provider = AzureStorageProvider("my-azure-container")
        assert provider.health() is False
        for val in provider.capabilities.values():
            assert val == "planned"

        with pytest.raises(NotImplementedError):
            provider.save("any.txt", b"data")

        with pytest.raises(NotImplementedError):
            provider.load("any.txt")

        with pytest.raises(NotImplementedError):
            provider.delete("any.txt")

        with pytest.raises(NotImplementedError):
            provider.exists("any.txt")

        with pytest.raises(NotImplementedError):
            provider.list()

    def test_google_provider_stubs(self) -> None:
        provider = GoogleStorageProvider("my-google-bucket")
        assert provider.health() is False
        for val in provider.capabilities.values():
            assert val == "planned"

        with pytest.raises(NotImplementedError):
            provider.save("any.txt", b"data")

        with pytest.raises(NotImplementedError):
            provider.load("any.txt")

        with pytest.raises(NotImplementedError):
            provider.delete("any.txt")

        with pytest.raises(NotImplementedError):
            provider.exists("any.txt")

        with pytest.raises(NotImplementedError):
            provider.list()


class TestStorageRegistryAndResolver:
    """Tests Registry and Resolver functionality."""

    def test_registry_registration_and_list(self) -> None:
        registry = StorageRegistry()
        local_prov = LocalStorageProvider("/tmp/local")
        azure_prov = AzureStorageProvider("container")

        registry.register("local", local_prov)
        registry.register("azure", azure_prov)

        assert registry.get("local") is local_prov
        assert registry.get("azure") is azure_prov
        assert registry.list_registered() == ["azure", "local"]

        with pytest.raises(KeyError):
            registry.get("google")

    def test_resolver_resolves_registered_provider(self) -> None:
        registry = StorageRegistry()
        local_prov = LocalStorageProvider("/tmp/local")
        registry.register("local", local_prov)

        resolver = StorageResolver(registry)
        assert resolver.resolve("local") is local_prov

        with pytest.raises(KeyError):
            resolver.resolve("unknown")
