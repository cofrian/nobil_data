from __future__ import annotations

import json
import logging
import signal
import ssl
import time
from pathlib import Path
from typing import Any

import certifi
import requests
import websocket

from .archive import DataArchiver
from .config import Settings
from .git_sync import GitBatchPusher
from .parser import extract_records, normalize_record

TOKEN_URL = "https://api.data.enova.no/nobil/real-time/v1/Realtime"
STOP = False


def on_signal(signum, frame) -> None:  # type: ignore[no-untyped-def]
    global STOP
    STOP = True
    logging.info("Señal %s recibida. Cerrando de forma ordenada...", signum)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def get_ws_url(api_key: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        # Azure API Management subscription key header.
        "Ocp-Apim-Subscription-Key": api_key,
        # Compatibility header used by some API gateway setups.
        "api-key": api_key,
    }
    params = {
        # Azure API Management subscription key query parameter.
        "subscription-key": api_key,
    }
    response = requests.post(TOKEN_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    ws_url = data.get("accessToken")
    if not ws_url:
        raise RuntimeError(f"No se recibió accessToken en la respuesta: {data}")
    return ws_url


def parse_message(raw_message: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw_message)
    except json.JSONDecodeError:
        payload = {"_raw_message": raw_message}

    return [normalize_record(record) for record in extract_records(payload)]


def maybe_snapshot(archiver: DataArchiver, last_snapshot_at: float, snapshot_every: int) -> float:
    now = time.time()
    if now - last_snapshot_at < snapshot_every:
        return last_snapshot_at

    snapshot_path = archiver.write_snapshot()
    logging.info("Snapshot guardado en %s", snapshot_path)
    return now


def run() -> None:
    settings = Settings.from_env()
    setup_logging(settings.log_level)

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    project_root = Path.cwd()
    archiver = DataArchiver(project_root=project_root, data_root=settings.data_root)
    pusher = GitBatchPusher(
        project_root=project_root,
        data_root=settings.data_root,
        branch=settings.github_branch,
        push_every_minutes=settings.github_push_every_minutes,
        repo_url=settings.github_repo_url,
    )

    logging.info("Archivo de datos habilitado en %s", (project_root / settings.data_root).resolve())

    last_snapshot_at = 0.0

    while not STOP:
        ws = None
        try:
            logging.info("Solicitando token realtime...")
            ws_url = ""
            last_exc: Exception | None = None
            keys = settings.api_keys()

            for idx, api_key in enumerate(keys):
                try:
                    ws_url = get_ws_url(api_key)
                    if idx > 0:
                        logging.warning("Token realtime obtenido con API key secundaria")
                    break
                except requests.HTTPError as exc:
                    if exc.response is not None and exc.response.status_code == 401 and idx < len(keys) - 1:
                        logging.warning("API key rechazada (401). Probando clave alternativa...")
                        last_exc = exc
                        continue
                    last_exc = exc
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    break

            if not ws_url:
                if last_exc is not None:
                    raise last_exc
                raise RuntimeError("No se pudo obtener token realtime con las claves configuradas")

            logging.info("Conectando a WebSocket...")

            ws = websocket.create_connection(
                ws_url,
                timeout=60,
                sslopt={
                    "cert_reqs": ssl.CERT_REQUIRED,
                    "ca_certs": certifi.where(),
                },
            )
            logging.info("Conectado. Escuchando eventos...")

            while not STOP:
                raw_message = ws.recv()
                records = parse_message(raw_message)
                archiver.append_records(records)

                logging.info("Mensaje procesado: %s registro(s)", len(records))
                last_snapshot_at = maybe_snapshot(archiver, last_snapshot_at, settings.snapshot_every)
                pusher.maybe_push()

        except Exception as exc:
            logging.exception("Error en el proceso realtime: %s", exc)
            time.sleep(settings.reconnect_seconds)
        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass

    pusher.maybe_push(force=True)

    logging.info("Proceso finalizado")


if __name__ == "__main__":
    run()
