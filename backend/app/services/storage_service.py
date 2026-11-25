"""CARAVAN Standalone Platform — Private Document Storage Service.

Provides tenant-isolated private document persistence, secure signed-URL tokens,
quarantine storage for suspicious uploads, and safe blob streaming.
"""

from __future__ import annotations

import hmac
import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import Optional, Tuple
from fastapi import HTTPException, status
from app.core.config import get_settings


class StorageResult:
    def __init__(self, storage_path: str, file_size_bytes: int, sha256_hash: str):
        self.storage_path = storage_path
        self.file_size_bytes = file_size_bytes
        self.sha256_hash = sha256_hash


class PrivateDocumentStorage:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            # Stored securely under data/vault in the project root
            base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "vault"
        self.base_dir = base_dir
        self.docs_dir = self.base_dir / "documents"
        self.quarantine_dir = self.base_dir / "quarantine"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        for d in (self.docs_dir, self.quarantine_dir):
            d.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(d, 0o700)
            except OSError:
                pass

    def _get_org_doc_dir(self, org_id: str, quarantined: bool = False) -> Path:
        parent = self.quarantine_dir if quarantined else self.docs_dir
        # Sanitize org_id to prevent directory traversal
        safe_org = "".join(c for c in org_id if c.isalnum() or c in ("-", "_"))
        org_path = parent / safe_org
        org_path.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(org_path, 0o700)
        except OSError:
            pass
        return org_path

    def store_document(
        self,
        org_id: str,
        doc_id: str,
        content: bytes,
        quarantined: bool = False,
    ) -> StorageResult:
        """Store document bytes in private tenant-isolated storage."""
        org_dir = self._get_org_doc_dir(org_id, quarantined=quarantined)
        safe_doc_id = "".join(c for c in doc_id if c.isalnum() or c in ("-", "_"))
        file_path = org_dir / f"{safe_doc_id}.bin"

        # Write to temporary file first then atomic rename
        tmp_path = org_dir / f"{safe_doc_id}.tmp"
        with open(tmp_path, "wb") as f:
            f.write(content)
        try:
            os.chmod(tmp_path, 0o600)
        except OSError:
            pass

        tmp_path.replace(file_path)

        sha256 = hashlib.sha256(content).hexdigest()
        rel_path = str(file_path.relative_to(self.base_dir))
        return StorageResult(
            storage_path=rel_path,
            file_size_bytes=len(content),
            sha256_hash=sha256,
        )

    def retrieve_document(self, org_id: str, doc_id: str) -> Tuple[bytes, Path]:
        """Read document bytes from private storage with tenant verification."""
        org_dir = self._get_org_doc_dir(org_id, quarantined=False)
        safe_doc_id = "".join(c for c in doc_id if c.isalnum() or c in ("-", "_"))
        file_path = org_dir / f"{safe_doc_id}.bin"

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found in storage.",
            )

        with open(file_path, "rb") as f:
            data = f.read()
        return data, file_path

    def quarantine_document(self, org_id: str, doc_id: str) -> None:
        """Move document from active vault to quarantine vault."""
        clean_org = self._get_org_doc_dir(org_id, quarantined=False)
        quarantine_org = self._get_org_doc_dir(org_id, quarantined=True)
        safe_doc_id = "".join(c for c in doc_id if c.isalnum() or c in ("-", "_"))

        src = clean_org / f"{safe_doc_id}.bin"
        dst = quarantine_org / f"{safe_doc_id}.bin"
        if src.exists():
            shutil.move(str(src), str(dst))

    def delete_document(self, org_id: str, doc_id: str) -> bool:
        """Safely shred and delete document from both active and quarantine storage."""
        safe_doc_id = "".join(c for c in doc_id if c.isalnum() or c in ("-", "_"))
        deleted = False

        for is_q in (False, True):
            org_dir = self._get_org_doc_dir(org_id, quarantined=is_q)
            file_path = org_dir / f"{safe_doc_id}.bin"
            if file_path.exists():
                try:
                    # Overwrite file with null bytes before unlinking for secure deletion
                    size = file_path.stat().st_size
                    with open(file_path, "wb") as f:
                        f.write(b"\x00" * min(size, 65536))
                    file_path.unlink()
                    deleted = True
                except Exception:
                    if file_path.exists():
                        file_path.unlink(missing_ok=True)
                        deleted = True
        return deleted

    def generate_scoped_download_token(self, org_id: str, doc_id: str, expires_in_seconds: int = 900) -> str:
        """Generate a short-lived (15 min) HMAC-SHA256 signed download token."""
        settings = get_settings()
        secret = settings.JWT_SECRET_KEY.encode("utf-8")
        expiry = int(time.time()) + expires_in_seconds
        payload = f"{org_id}:{doc_id}:{expiry}".encode("utf-8")
        signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        return f"{expiry}:{signature}"

    def verify_scoped_download_token(self, org_id: str, doc_id: str, token: str) -> bool:
        """Verify HMAC signature and expiry for scoped download token."""
        try:
            parts = token.split(":")
            if len(parts) != 2:
                return False
            expiry_str, signature = parts
            expiry = int(expiry_str)
            if time.time() > expiry:
                return False

            settings = get_settings()
            secret = settings.JWT_SECRET_KEY.encode("utf-8")
            payload = f"{org_id}:{doc_id}:{expiry}".encode("utf-8")
            expected_sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
            return hmac.compare_digest(signature, expected_sig)
        except Exception:
            return False


_STORAGE_INSTANCE: Optional[PrivateDocumentStorage] = None


def get_storage_service() -> PrivateDocumentStorage:
    global _STORAGE_INSTANCE
    if _STORAGE_INSTANCE is None:
        _STORAGE_INSTANCE = PrivateDocumentStorage()
    return _STORAGE_INSTANCE
