from __future__ import annotations

import json
import logging
import mimetypes
import time
from datetime import datetime, timezone
from pathlib import Path


class GCSBatchUploader:
    def __init__(
        self,
        project_root: Path,
        data_root: str,
        bucket_name: str,
        prefix: str,
        sync_every_minutes: int,
        credentials_json: str,
    ) -> None:
        self.project_root = project_root
        self.data_root = data_root
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")
        self.sync_every_seconds = sync_every_minutes * 60
        self.credentials_json = credentials_json
        self.last_sync_at = 0.0

        self.enabled = bool(self.bucket_name)
        self.status_file = self.project_root / self.data_root / "status" / "gcs_sync_status.json"
        self.manifest_file = self.project_root / self.data_root / "status" / "gcs_manifest.json"

        self._client = None
        self._bucket = None

    def _iso_utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _write_status(
        self,
        result: str,
        message: str,
        files_uploaded: int = 0,
        last_success_at: str | None = None,
        details: str | None = None,
    ) -> None:
        self.status_file.parent.mkdir(parents=True, exist_ok=True)

        existing: dict[str, str] = {}
        if self.status_file.exists():
            try:
                with self.status_file.open("r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                    if isinstance(loaded, dict):
                        existing = {k: str(v) for k, v in loaded.items()}
            except Exception:
                existing = {}

        payload: dict[str, str | int] = {
            "result": result,
            "message": message,
            "last_attempt_at": self._iso_utc_now(),
            "last_success_at": last_success_at or existing.get("last_success_at", ""),
            "bucket": self.bucket_name,
            "prefix": self.prefix,
            "data_root": self.data_root,
            "files_uploaded": files_uploaded,
        }

        if details:
            payload["details"] = details

        with self.status_file.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    def _load_manifest(self) -> dict[str, dict[str, int]]:
        if not self.manifest_file.exists():
            return {}
        try:
            with self.manifest_file.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
                if not isinstance(loaded, dict):
                    return {}
                manifest: dict[str, dict[str, int]] = {}
                for key, value in loaded.items():
                    if isinstance(key, str) and isinstance(value, dict):
                        size = int(value.get("size", 0))
                        mtime_ns = int(value.get("mtime_ns", 0))
                        manifest[key] = {"size": size, "mtime_ns": mtime_ns}
                return manifest
        except Exception:
            return {}

    def _save_manifest(self, manifest: dict[str, dict[str, int]]) -> None:
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)
        with self.manifest_file.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=2)

    def _build_object_name(self, rel_path: str) -> str:
        rel = rel_path.replace("\\", "/")
        if self.prefix:
            return f"{self.prefix}/{rel}"
        return rel

    def _ensure_bucket(self) -> bool:
        if not self.enabled:
            return False

        if self._bucket is not None:
            return True

        try:
            from google.cloud import storage

            if self.credentials_json:
                self._client = storage.Client.from_service_account_json(self.credentials_json)
            else:
                self._client = storage.Client()
            self._bucket = self._client.bucket(self.bucket_name)
            return True
        except Exception as exc:
            logging.warning("No se pudo inicializar cliente de GCS: %s", exc)
            self._write_status(
                result="error",
                message="No se pudo inicializar cliente de GCS",
                details=str(exc),
            )
            return False

    def _collect_local_files(self) -> list[tuple[Path, str, int, int]]:
        root = self.project_root / self.data_root
        if not root.exists():
            return []

        files: list[tuple[Path, str, int, int]] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue

            rel = path.relative_to(root).as_posix()
            if rel.startswith("status/"):
                continue

            stat = path.stat()
            files.append((path, rel, stat.st_size, stat.st_mtime_ns))
        return files

    def maybe_sync(self, force: bool = False) -> None:
        if not self.enabled:
            return

        now = time.time()
        if not force and (now - self.last_sync_at) < self.sync_every_seconds:
            return

        if not self._ensure_bucket():
            self.last_sync_at = now
            return

        try:
            local_files = self._collect_local_files()
            current_manifest = self._load_manifest()
            next_manifest: dict[str, dict[str, int]] = {}
            files_to_upload: list[tuple[Path, str, int, int]] = []

            for abs_path, rel_path, size, mtime_ns in local_files:
                signature = {"size": size, "mtime_ns": mtime_ns}
                next_manifest[rel_path] = signature
                if current_manifest.get(rel_path) != signature:
                    files_to_upload.append((abs_path, rel_path, size, mtime_ns))

            if not files_to_upload:
                self._write_status(
                    result="noop",
                    message="No habia archivos nuevos o modificados para subir a GCS",
                    files_uploaded=0,
                )
                self.last_sync_at = now
                return

            uploaded = 0
            for abs_path, rel_path, _, _ in files_to_upload:
                object_name = self._build_object_name(rel_path)
                blob = self._bucket.blob(object_name)
                content_type, _ = mimetypes.guess_type(abs_path.name)
                blob.upload_from_filename(
                    str(abs_path),
                    content_type=content_type or "application/octet-stream",
                )
                uploaded += 1

            self._save_manifest(next_manifest)
            self._write_status(
                result="ok",
                message="Sincronizacion a GCS completada",
                files_uploaded=uploaded,
                last_success_at=self._iso_utc_now(),
            )
            logging.info("Sync GCS completada: %s archivo(s) subidos", uploaded)
        except Exception as exc:
            logging.warning("Sync GCS fallida: %s", exc)
            self._write_status(
                result="error",
                message="Sync GCS fallida",
                details=str(exc),
            )
        finally:
            self.last_sync_at = now
