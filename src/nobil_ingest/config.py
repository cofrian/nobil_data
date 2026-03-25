from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    nobil_api_key: str
    nobil_api_key_secondary: str = ""
    snapshot_every: int = 300
    log_level: str = "INFO"
    reconnect_seconds: int = 5
    github_repo_url: str = ""
    github_branch: str = "main"
    github_push_every_minutes: int = 60
    gcs_bucket_name: str = ""
    gcs_prefix: str = ""
    gcs_sync_every_minutes: int = 60
    gcs_credentials_json: str = ""
    data_root: str = "data"

    @classmethod
    def from_env(cls) -> "Settings":
        nobil_api_key = os.getenv("NOBIL_API_KEY", "").strip()
        nobil_api_key_secondary = os.getenv("NOBIL_API_KEY_SECONDARY", "").strip()
        snapshot_every = int(os.getenv("SNAPSHOT_EVERY", "300"))
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        reconnect_seconds = int(os.getenv("RECONNECT_SECONDS", "5"))
        github_repo_url = os.getenv("GITHUB_REPO_URL", "").strip()
        github_branch = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
        github_push_every_minutes = int(os.getenv("GITHUB_PUSH_EVERY_MINUTES", "60"))
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME", "").strip()
        gcs_prefix = os.getenv("GCS_PREFIX", "").strip().strip("/")
        gcs_sync_every_minutes = int(os.getenv("GCS_SYNC_EVERY_MINUTES", "60"))
        gcs_credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        data_root = os.getenv("DATA_ROOT", "data").strip() or "data"

        if not nobil_api_key:
            raise RuntimeError("Falta la variable de entorno NOBIL_API_KEY")
        if snapshot_every <= 0:
            raise RuntimeError("SNAPSHOT_EVERY debe ser mayor que 0")
        if reconnect_seconds <= 0:
            raise RuntimeError("RECONNECT_SECONDS debe ser mayor que 0")
        if github_push_every_minutes <= 0:
            raise RuntimeError("GITHUB_PUSH_EVERY_MINUTES debe ser mayor que 0")
        if gcs_sync_every_minutes <= 0:
            raise RuntimeError("GCS_SYNC_EVERY_MINUTES debe ser mayor que 0")

        return cls(
            nobil_api_key=nobil_api_key,
            nobil_api_key_secondary=nobil_api_key_secondary,
            snapshot_every=snapshot_every,
            log_level=log_level,
            reconnect_seconds=reconnect_seconds,
            github_repo_url=github_repo_url,
            github_branch=github_branch,
            github_push_every_minutes=github_push_every_minutes,
            gcs_bucket_name=gcs_bucket_name,
            gcs_prefix=gcs_prefix,
            gcs_sync_every_minutes=gcs_sync_every_minutes,
            gcs_credentials_json=gcs_credentials_json,
            data_root=data_root,
        )

    def api_keys(self) -> list[str]:
        keys: list[str] = []
        if self.nobil_api_key:
            keys.append(self.nobil_api_key)
        if self.nobil_api_key_secondary and self.nobil_api_key_secondary not in keys:
            keys.append(self.nobil_api_key_secondary)
        return keys
