# NOBIL realtime -> JSONL + GitHub + Google Cloud Storage

Este proyecto escucha eventos realtime de NOBIL y guarda los datos en archivos locales versionados con Git, con push por lotes a GitHub y subida incremental opcional a Google Cloud Storage (GCS).

## Que hace

1. Pide token realtime a NOBIL.
2. Abre websocket y recibe mensajes.
3. Normaliza campos clave.
4. Guarda cada evento en JSONL rotado por hora.
5. Mantiene estado actual en memoria y genera snapshots periodicos en JSON.
6. Hace commit y push automatico cada X minutos sobre la carpeta `data/`.
7. Opcionalmente sube archivos nuevos/modificados de `data/` a un bucket de GCS.

## Estructura de archivos

- `data/raw/YYYY/MM/DD/events_YYYY-MM-DD_HH.jsonl`
- `data/snapshots/YYYY/MM/DD/snapshot_YYYY-MM-DD_HH-mm.json`

Cada linea de JSONL incluye:
- `received_at`
- `source_ts`
- `record_key`
- `station_id`
- `charger_id`
- `connector_id`
- `status`
- `message_type`
- `payload_json`
- `payload_sha1`

Ademas, cada evento incluye `derived` con metricas calculadas en tiempo real:
- `event_lag_seconds`
- `status_changed`
- `prev_status`
- `prev_status_duration_seconds`
- `is_duplicate_sha1`
- `missing_fields_count`

## Variables de entorno

Copia `.env.example` a `.env` y completa:

- `NOBIL_API_KEY`
- `SNAPSHOT_EVERY` (default: `300`)
- `LOG_LEVEL` (default: `INFO`)
- `RECONNECT_SECONDS` (default: `5`)
- `GITHUB_REPO_URL` (opcional si `origin` ya existe)
- `GITHUB_BRANCH` (default: `main`)
- `GITHUB_PUSH_EVERY_MINUTES` (default: `60`)
- `GCS_BUCKET_NAME` (opcional, si se define activa sync a GCS)
- `GCS_PREFIX` (opcional, prefijo dentro del bucket)
- `GCS_SYNC_EVERY_MINUTES` (default: `60`)
- `GOOGLE_APPLICATION_CREDENTIALS` (ruta a JSON de service account, opcional si usas ADC)
- `DATA_ROOT` (default: `data`)

## Instalacion

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

En Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecucion

```bash
python -m src.nobil_ingest.main
```

## Git y seguridad

- Solo se hace `git add` de `data/` para evitar subir secretos.
- `.env`, `.venv/`, logs y caches quedan fuera por `.gitignore`.
- Si no hay `origin` y no defines `GITHUB_REPO_URL`, el proceso sigue guardando archivos pero no puede hacer push.

## Push manual

```bash
git add data
git commit -m "data: append NOBIL events YYYY-MM-DD HHh"
git push -u origin main
```

## Monitoreo de estado de GitHub

- Logs de ejecucion incluyen eventos de sync, no-op y errores de push.
- Estado persistente del ultimo intento:
	- `data/status/github_sync_status.json`

Campos clave en ese archivo:
- `result`: `ok`, `noop` o `error`
- `message`: resumen del resultado
- `last_attempt_at`: ultimo intento UTC
- `last_success_at`: ultimo push exitoso UTC
- `details`: detalle tecnico del error cuando aplique

## Monitoreo de estado de GCS

- Estado persistente del ultimo intento de sync a bucket:
	- `data/status/gcs_sync_status.json`
- Manifest local de archivos ya sincronizados:
	- `data/status/gcs_manifest.json`

## Permisos recomendados de bucket GCS

Objetivo: lectura publica de objetos para cualquiera, pero subida y borrado solo para ti.

1. Activa **Uniform bucket-level access** en el bucket.
2. Concede a `allUsers` el rol `Storage Object Viewer` (`roles/storage.objectViewer`).
3. Concede a tu identidad (usuario o service account) `Storage Object Admin` (`roles/storage.objectAdmin`) para subir/borrar objetos.
4. Evita conceder roles de escritura a otras identidades.

Ejemplo con `gcloud` (sustituye variables):

```bash
gcloud storage buckets add-iam-policy-binding gs://TU_BUCKET \
	--member=allUsers \
	--role=roles/storage.objectViewer

gcloud storage buckets add-iam-policy-binding gs://TU_BUCKET \
	--member=user:tu-correo@dominio.com \
	--role=roles/storage.objectAdmin
```
