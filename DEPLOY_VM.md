# Despliegue 24/7 en VM Linux (systemd + Supabase)

Este documento deja el servicio corriendo 24/7 y guardando datos **solo en PostgreSQL remoto** (Supabase), nunca en SQLite/local.

## 1) Requisitos previos

- VM Linux con systemd (Ubuntu/Debian recomendado)
- Usuario con sudo
- Proyecto copiado en: `/opt/nobil-postgres-historico`
- API key de NOBIL vigente
- Proyecto Supabase creado

## 2) Preparar Supabase

1. En Supabase, crea proyecto y recupera la cadena de conexion Postgres.
2. Usa URL con `sslmode=require`.
3. Recomendado para procesos persistentes: session pooler o conexion directa.

Ejemplo de formato (sin valores reales):

```env
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:TU_PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres?sslmode=require
```

## 3) Copiar codigo al destino final

```bash
sudo mkdir -p /opt/nobil-postgres-historico
sudo rsync -a --delete ./ /opt/nobil-postgres-historico/
```

## 4) Ejecutar provision automatizado

```bash
cd /opt/nobil-postgres-historico
sudo bash scripts/provision_vm.sh
```

El script:
- crea usuario del sistema `nobil` si no existe
- crea/usa `.venv` en `/opt/nobil-postgres-historico/.venv`
- instala dependencias de `requirements.txt`
- crea `.env` desde `.env.example` si no existe
- instala servicio `nobil-postgres-historico.service`
- habilita arranque automatico y reinicia servicio

## 5) Configurar secretos (.env)

Archivo:
- `/opt/nobil-postgres-historico/.env`

Variables:

```env
NOBIL_API_KEY=<TU_NUEVA_API_KEY>
DATABASE_URL=<TU_URL_POSTGRES_SUPABASE_CON_SSLMODE_REQUIRE>
SNAPSHOT_EVERY=300
LOG_LEVEL=INFO
RECONNECT_SECONDS=5
```

Si cambias `.env`, recarga el servicio:

```bash
sudo systemctl restart nobil-postgres-historico.service
```

## 6) Verificaciones de servicio

Estado:

```bash
sudo systemctl status nobil-postgres-historico.service --no-pager
```

Logs:

```bash
sudo journalctl -u nobil-postgres-historico.service -f
```

## 7) Verificar tablas en PostgreSQL remoto

Con `psql` apuntando a Supabase:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('raw_events', 'current_status', 'snapshots')
ORDER BY table_name;
```

Y validar que llegan eventos:

```sql
SELECT COUNT(*) FROM raw_events;
SELECT COUNT(*) FROM current_status;
SELECT COUNT(*) FROM snapshots;
```

## 8) Operacion diaria

Reiniciar:

```bash
sudo systemctl restart nobil-postgres-historico.service
```

Parar:

```bash
sudo systemctl stop nobil-postgres-historico.service
```

Arrancar:

```bash
sudo systemctl start nobil-postgres-historico.service
```

Actualizar codigo:

```bash
cd /opt/nobil-postgres-historico
sudo rsync -a --delete /ruta/de/nueva/version/ ./
sudo -u nobil /opt/nobil-postgres-historico/.venv/bin/pip install -r requirements.txt
sudo systemctl restart nobil-postgres-historico.service
```

## 9) Seguridad

- No pongas secretos en comandos del historial si puedes evitarlo.
- Mantener permisos de `.env` en `640` y propietario `nobil:nobil`.
- Si una API key se expuso antes, regenerala y reemplazala inmediatamente.
