from __future__ import annotations

import hashlib
import json
from typing import Any

TIMESTAMP_KEYS = {
    "timestamp",
    "time",
    "datetime",
    "dateTime",
    "eventtime",
    "event_time",
    "updated",
    "updatedat",
    "updated_at",
    "lastupdated",
    "last_updated",
    "modified",
    "modifiedat",
    "modified_at",
}

MESSAGE_TYPE_KEYS = {
    "type",
    "messagetype",
    "message_type",
    "eventtype",
    "event_type",
    "kind",
    "action",
}

STATUS_KEYS = {
    "status",
    "state",
    "availability",
    "connectorstatus",
    "connector_status",
    "ocpistatus",
    "ocpi_status",
    "operationalstatus",
    "operational_status",
}

STATION_KEYS = {
    "stationid",
    "station_id",
    "chargingstationid",
    "charging_station_id",
    "csmdid",
    "siteid",
    "site_id",
    "locationid",
    "location_id",
}

CHARGER_KEYS = {
    "chargerid",
    "charger_id",
    "evseid",
    "evse_id",
    "evseidnumber",
    "evseidno",
    "chargepointid",
    "charge_point_id",
    "equipmentid",
    "equipment_id",
}

CONNECTOR_KEYS = {
    "connectorid",
    "connector_id",
    "connectorno",
    "connector_no",
    "connectornumber",
    "connector_number",
    "outletid",
    "outlet_id",
    "plugid",
    "plug_id",
}


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def deep_find_first(obj: Any, candidate_keys: set[str]) -> str | None:
    stack = [obj]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key.lower() in candidate_keys and value not in (None, "", [], {}):
                    return str(value)
            for value in current.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)):
                    stack.append(item)
    return None


def extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = [x for x in payload if isinstance(x, dict)]
        return records if records else [{"_raw_list": payload}]

    if isinstance(payload, dict):
        for key in ("data", "items", "results", "records", "value", "payload"):
            value = payload.get(key)
            if isinstance(value, list):
                records = [x for x in value if isinstance(x, dict)]
                if records:
                    return records
            if isinstance(value, dict):
                return [value]
        return [payload]

    return [{"_raw": payload}]


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    station_id = deep_find_first(record, STATION_KEYS)
    charger_id = deep_find_first(record, CHARGER_KEYS)
    connector_id = deep_find_first(record, CONNECTOR_KEYS)
    status = deep_find_first(record, STATUS_KEYS)
    source_ts = deep_find_first(record, {k.lower() for k in TIMESTAMP_KEYS})
    message_type = deep_find_first(record, {k.lower() for k in MESSAGE_TYPE_KEYS})

    payload_json_str = json_dumps(record)
    payload_sha1 = sha1_text(payload_json_str)

    if connector_id:
        record_key = f"connector::{connector_id}"
    elif charger_id:
        record_key = f"charger::{charger_id}"
    elif station_id:
        record_key = f"station::{station_id}"
    else:
        record_key = f"unknown::{payload_sha1}"

    return {
        "record_key": record_key,
        "station_id": station_id,
        "charger_id": charger_id,
        "connector_id": connector_id,
        "status": status,
        "message_type": message_type,
        "source_ts": source_ts,
        "payload_sha1": payload_sha1,
        "payload_json": record,
    }
