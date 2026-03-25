# Referencia Rápida: Comandos GCP/GCS para NOBIL

## Definir variables (ejecuta PRIMERO)

```bash
# En bash/Linux/Mac:
export PROJECT_ID="nobil-data-prod"
export BUCKET_NAME="nobil-events-data"
export SERVICE_ACCOUNT_NAME="nobil-data-sync"
export REGION="europe-west1"
```

```powershell
# En PowerShell (Windows):
$PROJECT_ID = "nobil-data-prod"
$BUCKET_NAME = "nobil-events-data"
$SERVICE_ACCOUNT_NAME = "nobil-data-sync"
$REGION = "europe-west1"
```

---

## Opción A: Ejecutar script completo (Recomendado)

### PowerShell (Windows):
```powershell
# Desde el directorio del proyecto:
.\gcp_setup.ps1 -ProjectId "nobil-data-prod" -BucketName "nobil-events-data"
```

### Bash (Linux/Mac):
```bash
# Primero define variables arriba ↑
bash gcp_setup.sh $PROJECT_ID $BUCKET_NAME $SERVICE_ACCOUNT_NAME $REGION
```

---

## Opción B: Comandos individuales (Si prefieres control manual)

### 1. Crear proyecto y habilitar APIs

```bash
# Crear proyecto
gcloud projects create $PROJECT_ID \
  --name="NOBIL Data Pipeline" \
  --labels=team=nobil,env=production

# Establecer como activo
gcloud config set project $PROJECT_ID

# Habilitar APIs
gcloud services enable \
  storage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com
```

### 2. Crear bucket

```bash
# Crear con Uniform bucket-level access
gsutil mb -b on -l $REGION -c STANDARD gs://$BUCKET_NAME

# Habilitar UBLA
gsutil uniformbucketlevelaccess set on gs://$BUCKET_NAME
```

### 3. Configurar permisos

```bash
# Lectura pública (anyone puede ver)
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member=allUsers \
  --role=roles/storage.objectViewer

# Obtener email de service account (necesario luego)
export SA_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:$SERVICE_ACCOUNT_NAME" \
  --format="value(email)")
```

### 4. Crear service account

```bash
# Crear
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --display-name="NOBIL Data Sync Service Account"

# Obtener email
export SA_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:$SERVICE_ACCOUNT_NAME" \
  --format="value(email)")

echo $SA_EMAIL  # Mostrar para verificar
```

### 5. Otorgar permisos a service account

```bash
# Write/delete para service account
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/storage.objectAdmin
```

### 6. Crear credenciales JSON

```bash
# En home del usuario
gcloud iam service-accounts keys create \
  ~\nobil-sa-key.json \
  --iam-account=$SA_EMAIL

# Verificar (debe existir el archivo)
ls -lh ~\nobil-sa-key.json
```

### 7. Configurar .env

```bash
# Agregar a .env:
cat >> .env <<EOF

# Google Cloud Storage
GCS_BUCKET_NAME=$BUCKET_NAME
GCS_PREFIX=nobil-data
GCS_SYNC_EVERY_MINUTES=60
GOOGLE_APPLICATION_CREDENTIALS=$HOME/nobil-sa-key.json
EOF
```

### 8. Probar acceso

```bash
# Establecer credencial
export GOOGLE_APPLICATION_CREDENTIALS=~/nobil-sa-key.json

# Probar upload
echo "test" > /tmp/test.txt
gsutil cp /tmp/test.txt gs://$BUCKET_NAME/nobil-data/test.txt

# Probar lectura pública (debería funcionar sin auth)
curl https://storage.googleapis.com/$BUCKET_NAME/nobil-data/test.txt

# Limpiar
gsutil rm gs://$BUCKET_NAME/nobil-data/test.txt
```

---

## Verificaciones post-setup

```bash
# ¿Proyecto actual?
gcloud config get-value project

# ¿Bucket existe?
gsutil ls -b gs://$BUCKET_NAME

# ¿Permisos configurados?
gcloud storage buckets get-iam-policy gs://$BUCKET_NAME

# ¿Service account existe?
gcloud iam service-accounts describe $SA_EMAIL

# ¿Credenciales funcionan?
export GOOGLE_APPLICATION_CREDENTIALS=~/nobil-sa-key.json
gsutil ls gs://$BUCKET_NAME
```

---

## Troubleshooting rápido

| Problema | Comando de diagnóstico | Solución |
|----------|------------------------|----------|
| gcloud no reconocido | `gcloud --version` | Instala Google Cloud SDK |
| Proyecto no existe | `gcloud projects list` | Crea primero con `gcloud projects create` |
| No puedo subir archivo | `echo $GOOGLE_APPLICATION_CREDENTIALS` | Verifica que variable esté set y archivo exista |
| Permission denied | `gcloud storage buckets get-iam-policy gs://$BUCKET_NAME` | Service account sin permisos Storage Object Admin |
| Bucket vacío después de tests | `gsutil ls -r gs://$BUCKET_NAME` | Normal, los buckets comienzan vacíos |

---

## Seguridad: lo que NO debes hacer ❌

```bash
# ❌ NO: Subir credencial a Git
git add ~nobil-sa-key.json

# ❌ NO: Poner credencial en un fichero public
GOOGLE_APPLICATION_CREDENTIALS="/var/www/html/key.json"

# ❌ NO: Compartir credencial por email/chat
"Aquí está mi key: {credenciales}"

# ❌ NO: Deletrear credential en logs detectables
gcloud iam service-accounts keys list  # OK
gcloud iam service-accounts keys create  # Anota el KEY_ID, no el contenido

# ✅ SI: Guardar en ~/.config o $HOME directorio privado
GOOGLE_APPLICATION_CREDENTIALS=$HOME/nobil-sa-key.json
```

---

## Variables finales para .env

Una vez completados todos los pasos, tu `.env` debería incluir:

```bash
NOBIL_API_KEY=tu_api_key_aqui
SNAPSHOT_EVERY=300
LOG_LEVEL=INFO
RECONNECT_SECONDS=5
GITHUB_REPO_URL=https://github.com/cofrian/nobil_data.git
GITHUB_BRANCH=main
GITHUB_PUSH_EVERY_MINUTES=60

GCS_BUCKET_NAME=nobil-events-data
GCS_PREFIX=nobil-data
GCS_SYNC_EVERY_MINUTES=60
GOOGLE_APPLICATION_CREDENTIALS=/Users/tu_usuario/nobil-sa-key.json

DATA_ROOT=data
```

---

## Iniciar después del setup

```bash
# Crear/activar venv
python -m venv .venv
source .venv/bin/activate  # o \.venv\Scripts\Activate.ps1 en Windows

# Instalar dependencias (incluye google-cloud-storage)
pip install -r requirements.txt

# Ejecutar proceso
python -m src.nobil_ingest.main
```

Busca en logs:
```
Sync GCS completada: X archivo(s) subidos
```

Verifica `data/status/gcs_sync_status.json` que tenga `"result": "ok"`.

---

## Limpiar todo (CUIDADO - destructivo)

```bash
# Eliminar bucket
gsutil -m rm -r gs://$BUCKET_NAME

# Eliminar service account
gcloud iam service-accounts delete $SA_EMAIL

# Eliminar proyecto
gcloud projects delete $PROJECT_ID --quiet

# Limpiar credencial local (OPCIONAL)
rm ~/nobil-sa-key.json
```

---

## Soporte y links útiles

- Documentación: [README.md](./README.md) y [GCP_SETUP.md](./GCP_SETUP.md)
- Google Cloud SDK: https://cloud.google.com/sdk/docs
- GCS IAM Roles: https://cloud.google.com/iam/docs/understanding-service-accounts
- Python Client: https://cloud.google.com/python/docs/reference/storage/latest
