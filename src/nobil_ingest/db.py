from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, CurrentStatus, RawEvent, Snapshot


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Database:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self.SessionLocal()

    def insert_raw_event(self, db: Session, record: dict) -> None:
        db.add(
            RawEvent(
                received_at=utc_now(),
                source_ts=record.get("source_ts"),
                record_key=record["record_key"],
                station_id=record.get("station_id"),
                charger_id=record.get("charger_id"),
                connector_id=record.get("connector_id"),
                status=record.get("status"),
                message_type=record.get("message_type"),
                payload_sha1=record["payload_sha1"],
                payload_json=record["payload_json"],
            )
        )

    def upsert_current_status(self, db: Session, record: dict) -> None:
        stmt = pg_insert(CurrentStatus).values(
            record_key=record["record_key"],
            updated_at=utc_now(),
            source_ts=record.get("source_ts"),
            station_id=record.get("station_id"),
            charger_id=record.get("charger_id"),
            connector_id=record.get("connector_id"),
            status=record.get("status"),
            message_type=record.get("message_type"),
            payload_sha1=record["payload_sha1"],
            payload_json=record["payload_json"],
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[CurrentStatus.record_key],
            set_={
                "updated_at": utc_now(),
                "source_ts": stmt.excluded.source_ts,
                "station_id": stmt.excluded.station_id,
                "charger_id": stmt.excluded.charger_id,
                "connector_id": stmt.excluded.connector_id,
                "status": stmt.excluded.status,
                "message_type": stmt.excluded.message_type,
                "payload_sha1": stmt.excluded.payload_sha1,
                "payload_json": stmt.excluded.payload_json,
            },
        )
        db.execute(stmt)

    def snapshot_current_status(self, db: Session) -> int:
        rows = db.execute(select(CurrentStatus)).scalars().all()
        now = utc_now()
        payload = [
            Snapshot(
                snapshot_ts=now,
                record_key=row.record_key,
                source_ts=row.source_ts,
                station_id=row.station_id,
                charger_id=row.charger_id,
                connector_id=row.connector_id,
                status=row.status,
                message_type=row.message_type,
                payload_sha1=row.payload_sha1,
                payload_json=row.payload_json,
            )
            for row in rows
        ]
        if payload:
            db.add_all(payload)
        return len(payload)
