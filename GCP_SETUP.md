# Guía Completa: Crear Proyecto GCP, Bucket y Credenciales

Este archivo contiene todos los comandos necesarios para configurar Google Cloud Storage para el proyecto NOBIL data.

## Requisitos previos

- Tienes cuenta en Google Cloud (console.cloud.google.com)
- Tienes `gcloud` CLI instalado (https://cloud.google.com/sdk/docs/install)
- Tienes permisos de administrador en tu proyectoGCP

## Paso 1: Configurar proyecto GCP base

```bash
# Establece tu ID de proyecto (debe ser único globalmente, ej: nobil-data-prod-sergio)
export PROJECT_ID="nobil-data-prod"
export BUCKET_NAME="nobil-events-data"
export SERVICE_ACCOUNT_NAME="nobil-data-sync"
export REGION="europe-west1"
export ZONE="europe-west1-b"

# Crear proyecto
gcloud projects create $PROJECT_ID \
  --name="NOBIL Data Pipeline" \
  --labels=team=nobil,env=production

# Establecer como proyecto activo
gcloud config set project $PROJECT_ID
```

## Paso 2: Habilitar APIs necesarias

```bash
# Habilitar APIs requeridas
gcloud services enable \
  storage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com
```

## Paso 3: Crear bucket GCS

```bash
# Crear bucket con estrategia de locación (europa)
gsutil mb -b on \
  -l $REGION \
  -c STANDARD \
  gs://$BUCKET_NAME

# Verificar que se creó
gsutil ls -b gs://$BUCKET_NAME
```

## Paso 4: Configurar permisos de bucket

### 4.1 Habilitar Uniform bucket-level access

```bash
# Activar UBLA (Uniform Bucket-Level Access)
gsutil uniformbucketlevelaccess set on gs://$BUCKET_NAME
```

### 4.2 Otorgar lectura pública a anyone (allUsers)

```bash
# Conceder permiso de lectura pública
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member=allUsers \
  --role=roles/storage.objectViewer
```

Verifica que se aplicó:
```bash
gcloud storage buckets get-iam-policy gs://$BUCKET_NAME
```

## Paso 5: Crear Service Account para el sinc automático

```bash
# Crear service account dedicada
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --display-name="NOBIL Data Sync Service Account" \
  --description="Service account para sincronizar datos a GCS"

# Obtener email de la service account
export SA_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:$SERVICE_ACCOUNT_NAME" \
  --format="value(email)")

echo "Service Account Email: $SA_EMAIL"
```

## Paso 6: Otorgar permisos de escritura/borrado a la service account

```bash
# Conceder rol Storage Object Admin (write, delete, read)
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/storage.objectAdmin

# Verificar permisos
gcloud storage buckets get-iam-policy gs://$BUCKET_NAME
```

## Paso 7: Crear y descargar credenciales JSON

```bash
# Crear key JSON para la service account
gcloud iam service-accounts keys create \
  ~/nobil-sa-key.json \
  --iam-account=$SA_EMAIL

# Verificar que se creó
ls -lh ~/nobil-sa-key.json

echo "Credential file created at: $HOME/nobil-sa-key.json"
```

**IMPORTANTE:** Guarda este archivo en lugar seguro. Este es el único backup de la credencial.

## Paso 8: Configurar variables de entorno en .env

Copia las variables a tu archivo `.env`:

```bash
# Mostrar valores para copiar
echo "=== Variables para .env ==="
echo "GCS_BUCKET_NAME=$BUCKET_NAME"
echo "GCS_PREFIX=nobil-data"
echo "GCS_SYNC_EVERY_MINUTES=60"
echo "GOOGLE_APPLICATION_CREDENTIALS=$HOME/nobil-sa-key.json"
```

O agrega directamente:

```bash
cat >> .env <<EOF

# Google Cloud Storage
GCS_BUCKET_NAME=$BUCKET_NAME
GCS_PREFIX=nobil-data
GCS_SYNC_EVERY_MINUTES=60
GOOGLE_APPLICATION_CREDENTIALS=$HOME/nobil-sa-key.json
EOF
```

## Paso 9: Verificar acceso desde local

```bash
# Verificar que las credenciales funcionan
export GOOGLE_APPLICATION_CREDENTIALS=~/nobil-sa-key.json

# Probar upload de un archivo test
echo "test content" > /tmp/test.txt
gsutil cp /tmp/test.txt gs://$BUCKET_NAME/nobil-data/test.txt

# Listar contenido del bucket
gsutil ls -r gs://$BUCKET_NAME/

# Probar lectura pública (desde otro navegador/sesión sin auth)
# URL pública será: https://storage.googleapis.com/$BUCKET_NAME/nobil-data/test.txt
curl https://storage.googleapis.com/$BUCKET_NAME/nobil-data/test.txt
```

## Paso 10: Instalar dependencias Python

```bash
# En tu venv
pip install -r requirements.txt

# Verifica que google-cloud-storage esté instalado
pip show google-cloud-storage
```

## Paso 11: Probar sincronización

```bash
# Ejecuta el proceso con logging habilitado
export LOG_LEVEL=DEBUG
python -m src.nobil_ingest.main
```

Busca logs como:
```
Sync GCS completada: X archivo(s) subidos
```

Y verifica en `data/status/gcs_sync_status.json` que figura `"result": "ok"`.

---

## Verificaciones finales

### Listar todo lo creado en GCP

```bash
# Project
gcloud config get-value project

# Bucket
gsutil ls -b gs://$BUCKET_NAME
gsutil ls -r gs://$BUCKET_NAME

# Service Account
gcloud iam service-accounts list --filter="displayName:$SERVICE_ACCOUNT_NAME"

# Permisos del bucket
gcloud storage buckets get-iam-policy gs://$BUCKET_NAME
```

### Acceso público vs privado

```bash
# Debería funcionar (lectura pública)
curl https://storage.googleapis.com/$BUCKET_NAME/nobil-data/test.txt

# Debería fallar (sin credenciales no se puede eliminar)
gsutil rm gs://$BUCKET_NAME/nobil-data/test.txt

# Debería funcionar (con credenciales de service account)
export GOOGLE_APPLICATION_CREDENTIALS=~/nobil-sa-key.json
gsutil rm gs://$BUCKET_NAME/nobil-data/test.txt
```

### Limpiar archivo de prueba

```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/nobil-sa-key.json
gsutil rm gs://$BUCKET_NAME/nobil-data/test.txt
```

---

## Troubleshooting

### Error: "Permission denied"

**Causa:** La service account no tiene permisos suficientes en el bucket.

**Solución:**
```bash
# Verifica permisos actuales
gcloud storage buckets get-iam-policy gs://$BUCKET_NAME

# Re-aplica rol Storage Object Admin
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/storage.objectAdmin
```

### Error: "GOOGLE_APPLICATION_CREDENTIALS not set"

**Causa:** Variable de entorno no está configurada.

**Solución:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/nobil-sa-key.json

# O agrega al .env
echo "GOOGLE_APPLICATION_CREDENTIALS=$HOME/nobil-sa-key.json" >> .env
```

### Error: "Bucket already exists"

**Causa:** Ya existe un bucket con ese nombre.

**Solución:** Los nombres de bucket en GCS son globales. Elige otro nombre:
```bash
BUCKET_NAME="nobil-events-$(date +%s)"
```

### No aparecen archivos en el bucket

**Causa:** El proceso no ha sincronizado aún o hay errores.

**Solución:**
```bash
# Verifica status de GCS
cat data/status/gcs_sync_status.json

# Verifica que el archivo .env tiene las variables correctas
cat .env | grep GCS_

# Mira los logs
tail -50 logs/output.log
```

---

## Resumen de seguridad

| Recurso | Público | Privado | Cuándo |
|---------|---------|---------|--------|
| ObjAn bucket (lectura) | ✅ `allUsers` + `roles/storage.objectViewer` | - | Siempre |
| Objeto (escritura) | ❌ No | ✅ Service account + `roles/storage.objectAdmin` | Desde tu máquina |
| Objeto (borrado) | ❌ No | ✅ Service account + `roles/storage.objectAdmin` | Desde tu máquina |
| Credencial JSON | ❌ Nunca en Git | ✅ `$HOME/nobil-sa-key.json` | Siempre |

---

## Eliminação de recursos (si necesitas limpiar)

```bash
# ADVERTENCIA: Esto elimina TODO. Usa con cuidado.

# Eliminar bucket (debe estar vacío primero)
gsutil -m rm -r gs://$BUCKET_NAME

# Eliminar service account
gcloud iam service-accounts delete $SA_EMAIL

# Eliminar proyecto
gcloud projects delete $PROJECT_ID --quiet
```
