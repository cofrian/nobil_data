# Despliegue 24/7 en Windows (Servicio)

Este proyecto queda ejecutando 24/7 en Windows usando un servicio de Windows con NSSM, guardando datos solo en PostgreSQL remoto (Supabase).

## Objetivo cubierto en Windows

- Usuario dedicado del servicio: `nobil`
- Proyecto en: `C:\opt\nobil-postgres-historico`
- Entorno virtual en: `C:\opt\nobil-postgres-historico\.venv`
- Variables de entorno en: `C:\opt\nobil-postgres-historico\.env`
- Ejecucion: `python -m src.nobil_ingest.main`
- Reinicio automatico ante fallo
- Datos solo en PostgreSQL remoto con `sslmode=require`

## Requisitos

- PowerShell 5.1 o superior
- Ejecutar PowerShell como Administrador
- Python 3.10+ instalado (comando `py` disponible)
- NOBIL API key
- Supabase creado con `DATABASE_URL` remota

## 1) Preparar .env

En el repo local, completa `.env` (o deja que se copie desde `.env.example` y luego lo editas):

```env
NOBIL_API_KEY=<TU_NUEVA_API_KEY>
DATABASE_URL=<TU_URL_SUPABASE_CON_SSLMODE_REQUIRE>
SNAPSHOT_EVERY=300
LOG_LEVEL=INFO
RECONNECT_SECONDS=5
```

## 2) Provision automatizado

Desde la raiz del proyecto, en PowerShell como Administrador:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\provision_windows.ps1
```

El script realiza:

- Sincroniza codigo a `C:\opt\nobil-postgres-historico`
- Crea usuario local `nobil` (o rota password si ya existe)
- Otorga permiso `Log on as a service`
- Crea `.venv` e instala dependencias
- Verifica `NOBIL_API_KEY` y `DATABASE_URL` con `sslmode=require`
- Protege ACL de `.env`
- Instala NSSM automaticamente
- Crea/configura servicio `nobil-postgres-historico`
- Habilita auto start y reinicio por fallo
- Arranca servicio
- Verifica tablas remotas `raw_events`, `current_status`, `snapshots`

## 3) Ver estado y logs

Estado del servicio:

```powershell
Get-Service nobil-postgres-historico
```

Logs del proceso:

```powershell
Get-Content C:\opt\nobil-postgres-historico\logs\service.out.log -Tail 100 -Wait
```

Errores:

```powershell
Get-Content C:\opt\nobil-postgres-historico\logs\service.err.log -Tail 100 -Wait
```

## 4) Operacion diaria

Reiniciar:

```powershell
Restart-Service nobil-postgres-historico
```

Parar:

```powershell
Stop-Service nobil-postgres-historico
```

Arrancar:

```powershell
Start-Service nobil-postgres-historico
```

## 5) Actualizar codigo

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\provision_windows.ps1
```

Ese comando vuelve a sincronizar codigo, reinstala deps si hace falta y deja el servicio actualizado.

## 6) Rotar API key o DATABASE_URL

1. Edita `C:\opt\nobil-postgres-historico\.env`
2. Reinicia el servicio:

```powershell
Restart-Service nobil-postgres-historico
```

## 7) Seguridad

- No expongas secretos en consola ni capturas.
- Si alguna key previa pudo quedar expuesta, regenerala y reemplazala en `.env`.
- El proyecto valida en arranque que no se use SQLite/local y que `DATABASE_URL` tenga `sslmode=require`.
