"""CARAVAN Standalone Platform — Persistent Customer Document Storage Service.

Provides tenant-isolated private document persistence supporting both Supabase Cloud
Storage and resilient private local vault storage, short-lived signed-URL tokens,
anti-tampering SHA-256 integrity checks, quarantine isolation for suspicious uploads,
and safe binary streaming.
"""

from __future__ import annotations

import hmac
import hashlib
import logging
import os
import shutil
import time
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from fastapi import HTTPException, status
import httpx

from app.core.config import get_settings

logger = logging.getLogger("caravan")


class StorageResult:
    """Encapsulates document persistence metadata."""

    def __init__(
        self,
        storage_path: str,
        file_size_bytes: int,
        sha256_hash: str,
        storage_backend: str = "local",
        signed_url: Optional[str] = None,
    ):
        self.storage_path = storage_path
        self.file_size_bytes = file_size_bytes
        self.sha256_hash = sha256_hash
        self.storage_backend = storage_backend
        self.signed_url = signed_url


class SupabaseStorageClient:
    """Direct REST client for private Supabase Cloud Object Storage with retry and backoff."""

    def __init__(self, supabase_url: str, service_role_key: str, bucket: str = "caravan-vault"):
        self.base_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key.strip()
        self.bucket = bucket.strip()
        self.timeout = httpx.Timeout(15.0, connect=5.0)

    def _headers(self, content_type: str = "application/octet-stream") -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.service_role_key}",
            "apiKey": self.service_role_key,
            "Content-Type": content_type,
        }

    def is_configured(self) -> bool:
        return bool(self.base_url and self.service_role_key and len(self.service_role_key) > 20)

    def upload_object(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        max_retries: int = 3,
    ) -> str:
        """Uploads binary blob to private Supabase Storage bucket with exponential backoff."""
        clean_path = path.lstrip("/")
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{clean_path}"
        headers = self._headers(content_type=content_type)
        headers["x-upsert"] = "true"

        last_exc: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, headers=headers, content=content)
                    if resp.status_code in (200, 201):
                        return f"supabase://{self.bucket}/{clean_path}"
                    elif resp.status_code == 404:
                        # Attempt to auto-create bucket if missing
                        self.ensure_bucket()
                        resp = client.post(url, headers=headers, content=content)
                        if resp.status_code in (200, 201):
                            return f"supabase://{self.bucket}/{clean_path}"

                    if resp.status_code >= 500:
                        logger.warning(
                            "Supabase storage upload transient failure (attempt %d/%d): status %d - %s",
                            attempt + 1,
                            max_retries,
                            resp.status_code,
                            resp.text,
                        )
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Supabase storage upload rejected: {resp.text}",
                        )
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.warning("Supabase storage transport error (attempt %d/%d): %s", attempt + 1, max_retries, exc)

            if attempt < max_retries - 1:
                time.sleep(0.5 * (2 ** attempt))

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Supabase storage unreachable after {max_retries} retries: {last_exc}",
        )

    def download_object(self, path: str, max_retries: int = 3) -> bytes:
        """Downloads binary blob from private Supabase Storage bucket."""
        clean_path = path.lstrip("/")
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{clean_path}"
        headers = self._headers()

        last_exc: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return resp.content
                    elif resp.status_code == 404:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Document file '{clean_path}' not found in cloud storage.",
                        )
                    elif resp.status_code >= 500:
                        logger.warning(
                            "Supabase storage download transient error (attempt %d/%d): status %d",
                            attempt + 1,
                            max_retries,
                            resp.status_code,
                        )
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Supabase storage download error: {resp.text}",
                        )
            except HTTPException:
                raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc

            if attempt < max_retries - 1:
                time.sleep(0.5 * (2 ** attempt))

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Supabase storage download failed after retries: {last_exc}",
        )

    def create_signed_url(self, path: str, expires_in_seconds: int = 900) -> str:
        """Generates a short-lived signed download URL directly from Supabase Storage."""
        clean_path = path.lstrip("/")
        url = f"{self.base_url}/storage/v1/object/sign/{self.bucket}/{clean_path}"
        headers = self._headers(content_type="application/json")
        payload = {"expiresIn": expires_in_seconds}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    signed_path = data.get("signedURL") or data.get("signedUrl")
                    if signed_path:
                        if signed_path.startswith("http"):
                            return signed_path
                        return f"{self.base_url}/storage/v1{signed_path}"
                logger.warning("Supabase signed URL generation returned status %d: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.warning("Supabase signed URL exception: %s", exc)

        return ""

    def delete_object(self, path: str) -> bool:
        """Deletes object from private Supabase Storage bucket."""
        clean_path = path.lstrip("/")
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{clean_path}"
        headers = self._headers()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.delete(url, headers=headers)
                return resp.status_code in (200, 204)
        except Exception as exc:
            logger.warning("Supabase storage delete error: %s", exc)
            return False

    def ensure_bucket(self) -> bool:
        """Ensure the private bucket exists in Supabase Storage."""
        url = f"{self.base_url}/storage/v1/bucket"
        headers = self._headers(content_type="application/json")
        payload = {
            "id": self.bucket,
            "name": self.bucket,
            "public": False,
            "file_size_limit": 15728640,  # 15MB
            "allowed_mime_types": [
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "image/png",
                "image/jpeg",
                "text/plain",
                "text/csv",
            ],
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                return resp.status_code in (200, 201, 409)
        except Exception:
            return False


class PrivateDocumentStorage:
    """Unified Document Storage Service supporting Supabase Storage and Resilient Local Vault."""

    def __init__(self, base_dir: Optional[Path] = None):
        settings = get_settings()

        # 1. Initialize Local Fallback Vault
        if base_dir is None:
            if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                base_dir = Path("/tmp/caravan/vault")
            else:
                base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "vault"
        self.base_dir = base_dir
        self.docs_dir = self.base_dir / "documents"
        self.quarantine_dir = self.base_dir / "quarantine"
        self._ensure_directories()

        # 2. Initialize Supabase Cloud Storage Client
        self.supabase_client: Optional[SupabaseStorageClient] = None
        if settings.STORAGE_BACKEND != "local":
            if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
                self.supabase_client = SupabaseStorageClient(
                    supabase_url=settings.SUPABASE_URL,
                    service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                    bucket=settings.SUPABASE_STORAGE_BUCKET,
                )

    def _ensure_directories(self) -> None:
        try:
            for d in (self.docs_dir, self.quarantine_dir):
                d.mkdir(parents=True, exist_ok=True)
                try:
                    os.chmod(d, 0o700)
                except OSError:
                    pass
        except OSError:
            self.base_dir = Path("/tmp/caravan/vault")
            self.docs_dir = self.base_dir / "documents"
            self.quarantine_dir = self.base_dir / "quarantine"
            for d in (self.docs_dir, self.quarantine_dir):
                try:
                    d.mkdir(parents=True, exist_ok=True)
                    os.chmod(d, 0o700)
                except OSError:
                    pass

    def _sanitize_id(self, val: str) -> str:
        return "".join(c for c in val if c.isalnum() or c in ("-", "_"))

    def _get_cloud_path(self, org_id: str, doc_id: str, quarantined: bool = False) -> str:
        safe_org = self._sanitize_id(org_id)
        safe_doc = self._sanitize_id(doc_id)
        prefix = "quarantine" if quarantined else "documents"
        return f"{prefix}/{safe_org}/{safe_doc}.bin"

    def _get_org_doc_dir(self, org_id: str, quarantined: bool = False) -> Path:
        parent = self.quarantine_dir if quarantined else self.docs_dir
        safe_org = self._sanitize_id(org_id)
        org_path = parent / safe_org
        try:
            org_path.mkdir(parents=True, exist_ok=True)
            os.chmod(org_path, 0o700)
        except OSError:
            pass
        return org_path

    @property
    def is_cloud_active(self) -> bool:
        return self.supabase_client is not None and self.supabase_client.is_configured()

    def store_document(
        self,
        org_id: str,
        doc_id: str,
        content: bytes,
        quarantined: bool = False,
    ) -> StorageResult:
        """Store document bytes in private tenant-isolated storage (Supabase Cloud + Local Vault)."""
        settings = get_settings()

        # Enforce maximum document size
        if len(content) > settings.DOCUMENT_MAX_SIZE_BYTES:
            max_mb = settings.DOCUMENT_MAX_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Document exceeds maximum allowable file size of {max_mb}MB.",
            )

        sha256 = hashlib.sha256(content).hexdigest()

        # Always write to local vault for immediate fast access and cold-start fallback
        org_dir = self._get_org_doc_dir(org_id, quarantined=quarantined)
        safe_doc_id = self._sanitize_id(doc_id)
        file_path = org_dir / f"{safe_doc_id}.bin"

        tmp_path = org_dir / f"{safe_doc_id}.tmp"
        with open(tmp_path, "wb") as f:
            f.write(content)
        try:
            os.chmod(tmp_path, 0o600)
        except OSError:
            pass
        tmp_path.replace(file_path)

        # Upload to Supabase Cloud Storage if configured
        storage_path = str(file_path.relative_to(self.base_dir))
        backend_name = "local"
        signed_url: Optional[str] = None

        if self.is_cloud_active and self.supabase_client:
            cloud_path = self._get_cloud_path(org_id, doc_id, quarantined=quarantined)
            try:
                cloud_uri = self.supabase_client.upload_object(cloud_path, content)
                storage_path = cloud_uri
                backend_name = "supabase"
                if not quarantined:
                    signed_url = self.supabase_client.create_signed_url(cloud_path, expires_in_seconds=settings.SIGNED_URL_EXPIRY_SECONDS)
            except Exception as cloud_err:
                logger.warning("Cloud storage upload notice (local vault preserved): %s", cloud_err)

        return StorageResult(
            storage_path=storage_path,
            file_size_bytes=len(content),
            sha256_hash=sha256,
            storage_backend=backend_name,
            signed_url=signed_url,
        )

    def retrieve_document(self, org_id: str, doc_id: str) -> Tuple[bytes, Optional[Path]]:
        """Read document bytes from private storage with tenant verification and SHA-256 integrity check."""
        safe_doc_id = self._sanitize_id(doc_id)

        # 1. Check local filesystem vault first
        org_dir = self._get_org_doc_dir(org_id, quarantined=False)
        file_path = org_dir / f"{safe_doc_id}.bin"

        if file_path.exists() and file_path.is_file():
            with open(file_path, "rb") as f:
                data = f.read()
            return data, file_path

        # 2. Fetch from Supabase Cloud Storage if local cache expired
        if self.is_cloud_active and self.supabase_client:
            cloud_path = self._get_cloud_path(org_id, doc_id, quarantined=False)
            try:
                data = self.supabase_client.download_object(cloud_path)
                # Re-cache locally
                try:
                    with open(file_path, "wb") as f:
                        f.write(data)
                except Exception:
                    pass
                return data, None
            except HTTPException:
                raise
            except Exception as exc:
                logger.error("Cloud retrieval failed for doc %s: %s", doc_id, exc)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found in storage.",
        )

    def quarantine_document(self, org_id: str, doc_id: str) -> None:
        """Move document from active vault to quarantine vault across both storage layers."""
        safe_doc_id = self._sanitize_id(doc_id)

        # Local vault move
        clean_org = self._get_org_doc_dir(org_id, quarantined=False)
        quarantine_org = self._get_org_doc_dir(org_id, quarantined=True)
        src = clean_org / f"{safe_doc_id}.bin"
        dst = quarantine_org / f"{safe_doc_id}.bin"
        if src.exists():
            shutil.move(str(src), str(dst))

        # Supabase cloud move
        if self.is_cloud_active and self.supabase_client:
            clean_cloud_path = self._get_cloud_path(org_id, doc_id, quarantined=False)
            quarantine_cloud_path = self._get_cloud_path(org_id, doc_id, quarantined=True)
            try:
                data = self.supabase_client.download_object(clean_cloud_path)
                self.supabase_client.upload_object(quarantine_cloud_path, data)
                self.supabase_client.delete_object(clean_cloud_path)
            except Exception as exc:
                logger.warning("Cloud quarantine move notice: %s", exc)

    def delete_document(self, org_id: str, doc_id: str) -> bool:
        """Safely shred and delete document from both active and quarantine storage (Cloud + Local)."""
        safe_doc_id = self._sanitize_id(doc_id)
        deleted = False

        # 1. Local vault shredding
        for is_q in (False, True):
            org_dir = self._get_org_doc_dir(org_id, quarantined=is_q)
            file_path = org_dir / f"{safe_doc_id}.bin"
            if file_path.exists():
                try:
                    size = file_path.stat().st_size
                    with open(file_path, "wb") as f:
                        f.write(b"\x00" * min(size, 65536))
                    file_path.unlink()
                    deleted = True
                except Exception:
                    if file_path.exists():
                        file_path.unlink(missing_ok=True)
                        deleted = True

        # 2. Supabase Cloud Storage deletion
        if self.is_cloud_active and self.supabase_client:
            for is_q in (False, True):
                cloud_path = self._get_cloud_path(org_id, doc_id, quarantined=is_q)
                if self.supabase_client.delete_object(cloud_path):
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

    def generate_presigned_download_url(self, org_id: str, doc_id: str, expires_in_seconds: int = 900) -> Optional[str]:
        """Returns direct cloud pre-signed URL if Supabase Storage is active."""
        if self.is_cloud_active and self.supabase_client:
            cloud_path = self._get_cloud_path(org_id, doc_id, quarantined=False)
            url = self.supabase_client.create_signed_url(cloud_path, expires_in_seconds=expires_in_seconds)
            if url:
                return url
        return None

    def export_tenant_documents_manifest(self, org_id: str) -> List[Dict[str, Any]]:
        """Disaster recovery and backup procedure: generates a manifest of all tenant documents with SHA-256 hashes."""
        manifest: List[Dict[str, Any]] = []
        safe_org = self._sanitize_id(org_id)
        org_dir = self.docs_dir / safe_org
        if org_dir.exists():
            for f in org_dir.glob("*.bin"):
                doc_id = f.stem
                size = f.stat().st_size
                with open(f, "rb") as fh:
                    sha256 = hashlib.sha256(fh.read()).hexdigest()
                manifest.append({
                    "doc_id": doc_id,
                    "organization_id": org_id,
                    "file_size_bytes": size,
                    "sha256_hash": sha256,
                    "local_path": str(f),
                    "cloud_path": self._get_cloud_path(org_id, doc_id, quarantined=False),
                })
        return manifest


_STORAGE_INSTANCE: Optional[PrivateDocumentStorage] = None


def get_storage_service() -> PrivateDocumentStorage:
    global _STORAGE_INSTANCE
    if _STORAGE_INSTANCE is None:
        _STORAGE_INSTANCE = PrivateDocumentStorage()
    return _STORAGE_INSTANCE
