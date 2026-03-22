from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RawEvent(Base):
    __tablename__ = "raw_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source_ts: Mapped[str | None] = mapped_column(Text, nullable=True)
    record_key: Mapped[str] = mapped_column(String(255), nullable=False)
    station_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    charger_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connector_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_sha1: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("idx_raw_events_received_at", "received_at"),
        Index("idx_raw_events_source_ts", "source_ts"),
        Index("idx_raw_events_record_key", "record_key"),
        Index("idx_raw_events_status", "status"),
        Index("idx_raw_events_message_type", "message_type"),
        Index("idx_raw_events_payload_sha1", "payload_sha1"),
    )


class CurrentStatus(Base):
    __tablename__ = "current_status"

    record_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source_ts: Mapped[str | None] = mapped_column(Text, nullable=True)
    station_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    charger_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connector_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_sha1: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("idx_current_status_updated_at", "updated_at"),
        Index("idx_current_status_status", "status"),
    )


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    snapshot_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    record_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_ts: Mapped[str | None] = mapped_column(Text, nullable=True)
    station_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    charger_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connector_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_sha1: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("idx_snapshots_snapshot_ts", "snapshot_ts"),
        Index("idx_snapshots_record_key", "record_key"),
        Index("idx_snapshots_status", "status"),
    )
