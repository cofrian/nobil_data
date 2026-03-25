# Script PowerShell para configurar GCP y GCS para NOBIL Data Pipeline
# Uso: .\gcp_setup.ps1 -ProjectId "nobil-data-prod" -BucketName "nobil-events-data"

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$true)]
    [string]$BucketName,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "europe-west1",
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceAccountName = "nobil-data-sync"
)

Write-Host "=== NOBIL GCP y GCS Setup ===" -ForegroundColor Cyan
Write-Host "Project ID: $ProjectId"
Write-Host "Bucket Name: $BucketName"
Write-Host "Service Account: $ServiceAccountName"
Write-Host "Region: $Region"
Write-Host ""

# Función para ejecutar comandos y mostrar feedback
function Invoke-GCloudCmd {
    param([string]$Description, [string[]]$Command)
    
    Write-Host "► $Description..." -ForegroundColor Yellow
    try {
        & gcloud @Command 2>&1
        Write-Host "✓ $Description completado" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "✗ Error en $Description`: $_" -ForegroundColor Red
        return $false
    }
}

# Paso 1: Crear proyecto
Write-Host "`n### PASO 1: Crear Proyecto GCP ###" -ForegroundColor Cyan

Invoke-GCloudCmd "Crear proyecto" @(
    "projects", "create", $ProjectId,
    "--name=NOBIL Data Pipeline",
    "--labels=team=nobil,env=production"
)

Invoke-GCloudCmd "Establecer proyecto activo" @(
    "config", "set", "project", $ProjectId
)

# Paso 2: Habilitar APIs
Write-Host "`n### PASO 2: Habilitar APIs ###" -ForegroundColor Cyan

Invoke-GCloudCmd "Habilitar APIs de Storage e IAM" @(
    "services", "enable",
    "storage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com"
)

# Paso 3: Crear bucket
Write-Host "`n### PASO 3: Crear Bucket GCS ###" -ForegroundColor Cyan

Write-Host "► Crear bucket con Uniform bucket-level access..." -ForegroundColor Yellow
try {
    # gsutil mb para crear
    & gsutil mb -b on -l $Region -c STANDARD "gs://$BucketName" 2>&1
    Write-Host "✓ Bucket creado" -ForegroundColor Green
} catch {
    Write-Host "✗ Error creando bucket: $_" -ForegroundColor Red
}

# Paso 4: Habilitar UBLA y permisos
Write-Host "`n### PASO 4: Configurar Permisos ###" -ForegroundColor Cyan

Write-Host "► Habilitar Uniform Bucket-Level Access..." -ForegroundColor Yellow
try {
    & gsutil uniformbucketlevelaccess set on "gs://$BucketName" 2>&1
    Write-Host "✓ UBLA habilitado" -ForegroundColor Green
} catch {
    Write-Host "✗ Error activando UBLA: $_" -ForegroundColor Red
}

Invoke-GCloudCmd "Conceder lectura pública (allUsers)" @(
    "storage", "buckets", "add-iam-policy-binding", "gs://$BucketName",
    "--member=allUsers",
    "--role=roles/storage.objectViewer"
)

# Paso 5: Crear Service Account
Write-Host "`n### PASO 5: Crear Service Account ###" -ForegroundColor Cyan

Invoke-GCloudCmd "Crear service account" @(
    "iam", "service-accounts", "create", $ServiceAccountName,
    "--display-name=NOBIL Data Sync Service Account",
    "--description=Service account para sincronizar datos a GCS"
)

# Obtener email de service account
Write-Host "► Obtener email de service account..." -ForegroundColor Yellow
$SAEmail = & gcloud iam service-accounts list --filter="displayName:$ServiceAccountName" --format="value(email)" 2>&1 | Select-Object -First 1
if ($SAEmail) {
    Write-Host "✓ Service Account Email: $SAEmail" -ForegroundColor Green
} else {
    Write-Host "✗ No se pudo obtener email de service account" -ForegroundColor Red
    exit 1
}

# Paso 6: Otorgar permisos a service account
Write-Host "`n### PASO 6: Otorgar Permisos Storage Object Admin ###" -ForegroundColor Cyan

Invoke-GCloudCmd "Conceder Storage Object Admin a service account" @(
    "storage", "buckets", "add-iam-policy-binding", "gs://$BucketName",
    "--member=serviceAccount:$SAEmail",
    "--role=roles/storage.objectAdmin"
)

# Paso 7: Crear credenciales JSON
Write-Host "`n### PASO 7: Crear Credenciales JSON ###" -ForegroundColor Cyan

$Home = $env:USERPROFILE
$KeyPath = "$Home\nobil-sa-key.json"

Write-Host "► Crear key JSON en $KeyPath..." -ForegroundColor Yellow
try {
    & gcloud iam service-accounts keys create $KeyPath --iam-account=$SAEmail 2>&1
    Write-Host "✓ Credenciales creadas en: $KeyPath" -ForegroundColor Green
    Write-Host "  ⚠ IMPORTANTE: Guarda este archivo en lugar seguro" -ForegroundColor Red
} catch {
    Write-Host "✗ Error creando credenciales: $_" -ForegroundColor Red
    exit 1
}

# Paso 8: Mostrar variables para .env
Write-Host "`n### PASO 8: Variables para .env ###" -ForegroundColor Cyan

$EnvVars = @"
# Google Cloud Storage
GCS_BUCKET_NAME=$BucketName
GCS_PREFIX=nobil-data
GCS_SYNC_EVERY_MINUTES=60
GOOGLE_APPLICATION_CREDENTIALS=$KeyPath
"@

Write-Host "Copia estas líneas a tu archivo .env:" -ForegroundColor Yellow
Write-Host $EnvVars -ForegroundColor White

# Guardar a archivo temporal
$EnvPath = ".\GCS_ENV_VARS.txt"
$EnvVars | Set-Content $EnvPath
Write-Host "`n✓ Variables guardadas en $EnvPath" -ForegroundColor Green

# Paso 9: Verificaciones
Write-Host "`n### PASO 9: Verificaciones ###" -ForegroundColor Cyan

Write-Host "► Verificar proyecto actual..." -ForegroundColor Yellow
& gcloud config get-value project >&2 | Out-Host

Write-Host "`n► Verificar bucket..." -ForegroundColor Yellow
& gsutil ls -b "gs://$BucketName" 2>&1

Write-Host "`n► Verificar permisos del bucket..." -ForegroundColor Yellow
& gcloud storage buckets get-iam-policy "gs://$BucketName" 2>&1

# Paso 10: Probar acceso
Write-Host "`n### PASO 10: Probar Acceso ###" -ForegroundColor Cyan

$TestFile = "c:\temp\nobil_test.txt"
$TestContent = "Test from NOBIL setup - $(Get-Date)"

Write-Host "► Crear archivo de prueba..." -ForegroundColor Yellow
if (-not (Test-Path "c:\temp")) { New-Item -ItemType Directory -Path "c:\temp" | Out-Null }
$TestContent | Set-Content $TestFile

$env:GOOGLE_APPLICATION_CREDENTIALS = $KeyPath

Write-Host "► Subir archivo de prueba a GCS..." -ForegroundColor Yellow
try {
    & gsutil cp $TestFile "gs://$BucketName/nobil-data/test.txt" 2>&1
    Write-Host "✓ Archivo subido" -ForegroundColor Green
} catch {
    Write-Host "✗ Error subiendo archivo: $_" -ForegroundColor Red
}

Write-Host "`n► Listar contenido del bucket..." -ForegroundColor Yellow
try {
    & gsutil ls -r "gs://$BucketName/" 2>&1
} catch {
    Write-Host "✗ Error listando bucket: $_" -ForegroundColor Red
}

Write-Host "`n► Eliminar archivo de prueba..." -ForegroundColor Yellow
try {
    & gsutil rm "gs://$BucketName/nobil-data/test.txt" 2>&1
    Write-Host "✓ Archivo de prueba eliminado" -ForegroundColor Green
} catch {
    Write-Host "✗ Error eliminando archivo: $_" -ForegroundColor Red
}

# Resumen final
Write-Host "`n" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "✓ SETUP DE GCP/GCS COMPLETADO" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Cyan

Write-Host "`nPróximos pasos:" -ForegroundColor Yellow
Write-Host "1. Copia las variables de $EnvPath a tu archivo .env"
Write-Host "2. Verifica que GOOGLE_APPLICATION_CREDENTIALS=$KeyPath esté en .env"
Write-Host "3. Ejecuta: pip install -r requirements.txt"
Write-Host "4. Ejecuta: python -m src.nobil_ingest.main"
Write-Host ""
Write-Host "Información importante:" -ForegroundColor Yellow
Write-Host "• Bucket Name: $BucketName"
Write-Host "• Service Account: $SAEmail"
Write-Host "• Credentials: $KeyPath"
Write-Host "• Project: $ProjectId"
Write-Host ""
Write-Host "⚠ SEGURIDAD:" -ForegroundColor Red
Write-Host "  - NUNCA subas $KeyPath a GitHub"
Write-Host "  - NUNCA compartas este archivo"
Write-Host "  - Guarda backup seguro de $KeyPath"
Write-Host ""
