from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DUPLICATE_WINDOW_SECONDS = 900


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


class DataArchiver:
    def __init__(self, project_root: Path, data_root: str) -> None:
        self.base_dir = (project_root / data_root).resolve()
        self.current_status: dict[str, dict[str, Any]] = {}
        self.last_sha1_seen_at: dict[str, datetime] = {}

    def _parse_iso_ts(self, value: Any) -> datetime | None:
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _missing_fields_count(self, event: dict[str, Any]) -> int:
        required = [
            "record_key",
            "station_id",
            "charger_id",
            "connector_id",
            "status",
            "message_type",
            "payload_sha1",
            "payload_json",
        ]
        missing = 0
        for key in required:
            value = event.get(key)
            if value in (None, "", [], {}):
                missing += 1
        return missing

    def _compute_derived(self, event: dict[str, Any], received_dt: datetime) -> dict[str, Any]:
        record_key = str(event.get("record_key") or "")
        previous = self.current_status.get(record_key) if record_key else None

        source_dt = self._parse_iso_ts(event.get("source_ts"))
        event_lag_seconds = None
        if source_dt is not None:
            event_lag_seconds = round((received_dt - source_dt).total_seconds(), 3)

        prev_status = previous.get("status") if previous else None
        current_status = event.get("status")
        status_changed = previous is not None and prev_status != current_status

        prev_status_duration_seconds = None
        if previous is not None:
            prev_received_at = self._parse_iso_ts(previous.get("received_at"))
            if prev_received_at is not None:
                prev_status_duration_seconds = round((received_dt - prev_received_at).total_seconds(), 3)

        payload_sha1 = str(event.get("payload_sha1") or "")
        prev_sha1_seen_at = self.last_sha1_seen_at.get(payload_sha1)
        is_duplicate_sha1 = False
        if payload_sha1 and prev_sha1_seen_at is not None:
            delta = (received_dt - prev_sha1_seen_at).total_seconds()
            is_duplicate_sha1 = delta <= DUPLICATE_WINDOW_SECONDS

        if payload_sha1:
            self.last_sha1_seen_at[payload_sha1] = received_dt

        return {
            "event_lag_seconds": event_lag_seconds,
            "status_changed": status_changed,
            "prev_status": prev_status,
            "prev_status_duration_seconds": prev_status_duration_seconds,
            "is_duplicate_sha1": is_duplicate_sha1,
            "missing_fields_count": self._missing_fields_count(event),
        }

    def _raw_file_path(self, dt: datetime) -> Path:
        return self.base_dir / "raw" / dt.strftime("%Y/%m/%d") / dt.strftime("events_%Y-%m-%d_%H.jsonl")

    def _snapshot_file_path(self, dt: datetime) -> Path:
        name = dt.strftime("snapshot_%Y-%m-%d_%H-%M.json")
        return self.base_dir / "snapshots" / dt.strftime("%Y/%m/%d") / name

    def append_records(self, records: list[dict[str, Any]]) -> int:
        by_file: dict[Path, list[dict[str, Any]]] = defaultdict(list)

        for record in records:
            received_dt = utc_now()
            event = {
                "received_at": iso_utc(received_dt),
                "source_ts": record.get("source_ts"),
                "record_key": record.get("record_key"),
                "station_id": record.get("station_id"),
                "charger_id": record.get("charger_id"),
                "connector_id": record.get("connector_id"),
                "status": record.get("status"),
                "message_type": record.get("message_type"),
                "payload_json": record.get("payload_json"),
                "payload_sha1": record.get("payload_sha1"),
            }
            event["derived"] = self._compute_derived(event, received_dt)

            record_key = str(event["record_key"] or "")
            if record_key:
                self.current_status[record_key] = event

            by_file[self._raw_file_path(received_dt)].append(event)

        for path, items in by_file.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                for item in items:
                    fh.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
                    fh.write("\n")

        return len(records)

    def write_snapshot(self) -> Path:
        now = utc_now()
        path = self._snapshot_file_path(now)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "snapshot_at": iso_utc(now),
            "count": len(self.current_status),
            "records": list(self.current_status.values()),
        }

        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

        return path