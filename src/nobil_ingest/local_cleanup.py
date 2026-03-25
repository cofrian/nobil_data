from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path


class LocalPreviousDayCleaner:
    def __init__(
        self,
        project_root: Path,
        data_root: str,
        enabled: bool,
    ) -> None:
        self.project_root = project_root
        self.data_root = data_root
        self.enabled = enabled
        self.base_dir = (self.project_root / self.data_root).resolve()
        self.status_file = self.base_dir / "status" / "local_cleanup_status.json"
        self.last_cleaned_day = ""

    def _iso_utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _write_status(self, result: str, message: str, deleted_paths: list[str] | None = None) -> None:
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "result": result,
            "message": message,
            "last_attempt_at": self._iso_utc_now(),
            "data_root": self.data_root,
        }
        if deleted_paths:
            payload["deleted_paths"] = deleted_paths
        with self.status_file.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    def _target_day(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=1)

    def _target_dirs(self, dt: datetime) -> list[Path]:
        yyyy = dt.strftime("%Y")
        mm = dt.strftime("%m")
        dd = dt.strftime("%d")
        return [
            self.base_dir / "raw" / yyyy / mm / dd,
            self.base_dir / "snapshots" / yyyy / mm / dd,
        ]

    def maybe_cleanup(self, force: bool = False) -> None:
        if not self.enabled:
            return

        target_day = self._target_day().strftime("%Y-%m-%d")
        if not force and self.last_cleaned_day == target_day:
            return

        deleted_paths: list[str] = []

        try:
            for directory in self._target_dirs(self._target_day()):
                if not directory.exists():
                    continue

                rel_path = directory.relative_to(self.base_dir).as_posix()
                for child in directory.rglob("*"):
                    if child.is_file():
                        child.unlink(missing_ok=True)

                for child_dir in sorted(
                    (d for d in directory.rglob("*") if d.is_dir()),
                    key=lambda item: len(item.parts),
                    reverse=True,
                ):
                    child_dir.rmdir()

                directory.rmdir()
                deleted_paths.append(rel_path)

            if deleted_paths:
                logging.info("Limpieza local completada para %s: %s", target_day, ", ".join(deleted_paths))
                self._write_status(
                    result="ok",
                    message=f"Se borraron carpetas locales del dia anterior ({target_day})",
                    deleted_paths=deleted_paths,
                )
            else:
                self._write_status(
                    result="noop",
                    message=f"No habia carpetas del dia anterior para borrar ({target_day})",
                )
        except Exception as exc:
            logging.warning("Limpieza local fallida: %s", exc)
            self._write_status(
                result="error",
                message=f"Limpieza local fallida para {target_day}",
                deleted_paths=deleted_paths,
            )
            return

        self.last_cleaned_day = target_day
