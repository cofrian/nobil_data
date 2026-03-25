from __future__ import annotations

import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


class GitBatchPusher:
    def __init__(
        self,
        project_root: Path,
        data_root: str,
        branch: str,
        push_every_minutes: int,
        repo_url: str,
    ) -> None:
        self.project_root = project_root
        self.data_root = data_root
        self.branch = branch
        self.push_every_seconds = push_every_minutes * 60
        self.repo_url = repo_url
        self.last_push_at = 0.0
        self.remote_warned = False
        self.status_file = self.project_root / self.data_root / "status" / "github_sync_status.json"

    def _iso_utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _write_status(
        self,
        result: str,
        message: str,
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

        payload = {
            "result": result,
            "message": message,
            "last_attempt_at": self._iso_utc_now(),
            "last_success_at": last_success_at or existing.get("last_success_at", ""),
            "branch": self.branch,
            "data_root": self.data_root,
        }

        if details:
            payload["details"] = details

        with self.status_file.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    def _run_git(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.project_root,
            check=check,
            capture_output=True,
            text=True,
        )

    def _ensure_repo(self) -> bool:
        try:
            probe = self._run_git(["rev-parse", "--is-inside-work-tree"], check=False)
            if probe.returncode != 0:
                self._run_git(["init"])

            self._run_git(["checkout", "-B", self.branch])

            if self.repo_url:
                remote_get = self._run_git(["remote", "get-url", "origin"], check=False)
                if remote_get.returncode != 0:
                    self._run_git(["remote", "add", "origin", self.repo_url])
                elif remote_get.stdout.strip() != self.repo_url:
                    self._run_git(["remote", "set-url", "origin", self.repo_url])

            return True
        except Exception as exc:
            logging.warning("No se pudo preparar git para push: %s", exc)
            return False

    def maybe_push(self, force: bool = False) -> None:
        now = time.time()
        if not force and (now - self.last_push_at) < self.push_every_seconds:
            return

        if not self._ensure_repo():
            self._write_status(
                result="error",
                message="No se pudo preparar el repositorio git para sincronizar",
            )
            self.last_push_at = now
            return

        try:
            logging.info("Iniciando sync de data/ a GitHub...")
            self._run_git(["add", "--ignore-removal", "--", self.data_root])
            staged = self._run_git(["diff", "--cached", "--quiet"], check=False)
            if staged.returncode == 0:
                logging.info("Sync GitHub omitido: no hay cambios en %s", self.data_root)
                self._write_status(
                    result="noop",
                    message="No habia cambios para commit/push",
                )
                self.last_push_at = now
                return

            stamp = datetime.now().strftime("%Y-%m-%d %Hh")
            message = f"data: append NOBIL events {stamp}"
            self._run_git(["commit", "-m", message])

            has_origin = self._run_git(["remote", "get-url", "origin"], check=False).returncode == 0
            if not has_origin:
                if not self.remote_warned:
                    logging.warning("No existe remoto origin. Configura GITHUB_REPO_URL o origin manualmente")
                    self.remote_warned = True
                self._write_status(
                    result="error",
                    message="No existe remoto origin para push",
                )
                self.last_push_at = now
                return

            self._run_git(["push", "-u", "origin", self.branch])
            logging.info("Push de datos completado a origin/%s", self.branch)
            self._write_status(
                result="ok",
                message="Push completado correctamente",
                last_success_at=self._iso_utc_now(),
            )
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            detail = stderr if stderr else str(exc)
            logging.warning("Push GitHub fallido: %s", detail)
            self._write_status(
                result="error",
                message="Push GitHub fallido",
                details=detail,
            )
        finally:
            self.last_push_at = now