# Guía: Crear Proyecto, Bucket y Credenciales desde Google Cloud Console

Esta guía te muestra dónde hacer clic exactamente en la interfaz web de Google Cloud para configurar todo.

## Paso preliminar: Acceder a Google Cloud Console

1. Ve a: https://console.cloud.google.com
2. Inicia sesión con tu cuenta de Google (la que tendrá acceso al bucket)
3. Si es la primera vez, acepta los términos de servicio

---

## 📋 PASO 1: Crear un nuevo Proyecto

### 1.1 Acceder a la selector de proyectos

1. **Arriba a la izquierda**, verás un selector que dice: `Select a project` or el nombre de tu proyecto actual
2. **Haz clic en él** (es un dropdown)
3. Debería abrirse una ventana emergente

### 1.2 Crear proyecto nuevo

1. En la ventana que se abrió, **haz clic en el botón azul que dice "NEW PROJECT"** (arriba a la derecha)
2. Se abrirá un formulario con los campos:
   - **Project name**: `NOBIL Data Pipeline`
   - **Location**: Deja como está (sin organización si es tu cuenta personal)
3. **Haz clic en "CREATE"**
4. Espera 30-60 segundos a que se cree el proyecto
5. Verás notificación: "Project created successfully"

### 1.3 Cambiar al nuevo proyecto

1. Vuelve a **hacer clic en el selector de proyectos** (arriba a la izquierda)
2. **Selecciona "NOBIL Data Pipeline"** de la lista
3. Espera a que cargue

---

## 🔌 PASO 2: Habilitar APIs Necesarias

### 2.1 Abrir APIs

1. **En el menú izquierdo**, busca y haz clic en: **"APIs & Services"**
2. Luego haz clic en: **"Enabled APIs & services"**

### 2.2 Habilitar Google Cloud Storage API

1. En la página de APIs, **haz clic en el botón azul "+ ENABLE APIS AND SERVICES"** (arriba)
2. En el campo de búsqueda que aparece, escribe: `Cloud Storage`
3. **Haz clic en "Google Cloud Storage API"** (la primera opción)
4. **Haz clic en el botón azul "ENABLE"**
5. Espera a que se habilite (verás checkmark verde)

### 2.3 Habilitar APIs adicionales

Repite el proceso con:

**Cloud Resource Manager API:**
1. Haz clic en **"+ ENABLE APIS AND SERVICES"** nuevamente
2. Busca: `Cloud Resource Manager`
3. Haz clic en la opción y **click "ENABLE"**

**IAM API:**
1. Haz clic en **"+ ENABLE APIS AND SERVICES"** nuevamente
2. Busca: `Identity and Access Management`
3. Haz clic en la opción y **click "ENABLE"**

---

## 🪣 PASO 3: Crear el Bucket de Cloud Storage

### 3.1 Abrir Cloud Storage

1. **En el menú izquierdo**, busca y haz clic en: **"Cloud Storage"**
2. Luego haz clic en: **"Buckets"**

### 3.2 Crear bucket

1. **Haz clic en el botón azul "+ CREATE"** (arriba)
2. Se abrirá un formulario:

**Configuración del bucket:**

| Campo | Valor | Notas |
|-------|-------|-------|
| **Bucket name** | `nobil-events-data` | Debe ser único globalmente. Si existe, agrega fecha: `nobil-events-data-20260325` |
| **Location type** | `Region` | Lo importante es región (no multi-región) |
| **Location** | `europe-west1` | La más cercana a ti (UE = Bruselas; USA = us-central1) |
| **Default storage class** | `Standard` | Cambios rápidos, acceso frecuente |
| **Access control** | `Uniform (recomendado)` | IMPORTANTE: Selecciona esta opción |

3. **Haz clic en "CREATE"**
4. Espera a que aparezca en la lista de buckets

### 3.3 Verificar creación

1. Deberías ver el bucket `nobil-events-data` en la lista
2. Haz clic en el nombre del bucket para entrar

---

## 🔐 PASO 4: Configurar Permisos del Bucket

### 4.1 Habilitar Uniform bucket-level access

1. Estando **dentro del bucket**, ve a la pestaña: **"Permissions"**
2. Busca la sección **"Uniform bucket-level access (UBLA)"**
3. **Haz clic en "Enable"** (si no está ya habilitado)
4. Confirma haciendo clic en **"Confirm"**

### 4.2 Otorgar lectura pública

1. En la misma pestaña **"Permissions"**, verás **"Principals"** o **"Members"**
2. **Haz clic en "Grant Access"** (botón azul, arriba)
3. Se abrirá un diálogo:
   - **New principals**: Escribe `allUsers`
   - **Role**: Selecciona → **"Basic"** → **"Viewer"**
     (O busca en el field "Storage Object Viewer")
   - **Haz clic en "Save"**

4. Confirma que aparezca `allUsers` en la lista de miembros

### 4.3 Resultado esperado

La tabla de miembros debería verse así:

```
principals              Role
--------------------  --------------------------------
allUsers               Storage Object Viewer
(Tu service account)   Storage Object Admin
your-email@gmail.com   Storage Object Admin
```

---

## 👤 PASO 5: Crear Service Account

### 5.1 Abrir Service Accounts

1. **En el menú izquierdo**, haz clic en: **"APIs & Services"**
2. Luego haz clic en: **"Service Accounts"**

### 5.2 Crear service account

1. **Haz clic en "+ CREATE SERVICE ACCOUNT"** (arriba)
2. Completa no campos:
   - **Service account name**: `nobil-data-sync`
   - **Service account ID**: Se llena automáticamente (ej: `nobil-data-sync@nobil-data-prod.iam.gserviceaccount.com`)
   - **Description**: `Service account para sincronizar datos a GCS`
3. **Haz clic en "CREATE AND CONTINUE"**

### 5.3 Otorgar rol (Paso 2/2)

1. Se abre otra pantalla: **"Grant this service account access to project"**
2. En el dropdown **"Select a role"**, busca: `Storage Object Admin`
3. Selecciona: **"Storage Object Admin"** (roles/storage.objectAdmin)
4. **Haz clic en "CONTINUE"**

### 5.4 Crear credenciales (Paso 3/3)

1. Se abre: **"Grant users access to this service account"**
2. Haz clic en **"DONE"** (por ahora, sin agregar usuarios aquí)
3. Volverás a la lista de Service Accounts

---

## 🔑 PASO 6: Crear y Descargar Credenciales JSON

### 6.1 Seleccionar la service account

1. En la lista de Service Accounts, **haz clic en el nombre: `nobil-data-sync`**
2. Esto abre los detalles de la service account

### 6.2 Crear key JSON

1. Ve a la pestaña **"Keys"** (arriba)
2. **Haz clic en "Add Key"** → **"Create new key"**
3. Se abre un diálogo:
   - **Key type**: Selecciona **"JSON"** (es la opción por defecto)
   - **Haz clic en "Create"**

### 6.3 Descargar el archivo

1. **Se descargará automáticamente** un archivo llamado: `nobil-data-prod-xxx.json`
2. El archivo contiene las credenciales (¡NO compartir!)
3. **Mueve el archivo a tu home directory:**
   
   **Ubicación final:**
   - **Windows:** `C:\Users\TuUsuario\nobil-sa-key.json`
   - **Mac/Linux:** `~/nobil-sa-key.json`

### 6.4 Verificación

1. En la pestaña "Keys", deberías ver:
   - Un entry con tu key
   - Mostrador de fecha de creación
   - Una nota: "Delete-after" (si aplica)

---

## 🔗 PASO 7: Asignar permisos de Service Account al Bucket

### 7.1 Volver al bucket

1. **En el menú lateral**, ve a: **"Cloud Storage"** → **"Buckets"**
2. **Haz clic en tu bucket: `nobil-events-data`**
3. Ve a la pestaña: **"Permissions"**

### 7.2 Agregar service account

1. **Haz clic en "Grant Access"** (botón azul)
2. En el diálogo:
   - **New principals**: Pega el email de tu service account:
     ```
     nobil-data-sync@nobil-data-prod.iam.gserviceaccount.com
     ```
   - **Select a role**: Busca y selecciona **"Storage Object Admin"**
   - **Haz clic en "Save"**

3. Deberías ver a la service account en la lista de miembros

---

## ✅ PASO 8: Verificaciones

### 8.1 Confirmar permisos públicos

1. Ve a la pestaña **"Objects"** de tu bucket
2. Crea un archivo de prueba:
   - **Haz clic en "Upload files"**
   - Sube cualquier archivo (ej: un `.txt`)
   - El archivo aparece en la lista

### 8.2 Probar acceso público

1. **Haz clic en el archivo** que subiste
2. Se abre un panel con información
3. Busca **"Public URL"** o copia la URL
4. **Abre en navegador anónimo** (Ctrl+Shift+P en Chrome):
   - Deberías poder ver/descargar el archivo
   - Esto verifica que `allUsers` tiene acceso

### 8.3 Verificar service account con credenciales

1. Abre terminal y ejecuta:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=~/nobil-sa-key.json
   gsutil ls gs://nobil-events-data
   ```
2. Si no da error, las credenciales funcionan ✓

---

## 📝 PASO 9: Configurar Variables de Entorno

### 9.1 Obtener información necesaria

En la interfaz de GCP, recopila:

1. **Nombre del bucket**: `nobil-events-data` (lo ves en Cloud Storage → Buckets)
2. **Ruta del archivo de credenciales**: `$HOME/nobil-sa-key.json`

### 9.2 Editar `.env`

1. En tu proyecto (`nobil_data`), ve a `.env`
2. Agrega (o edita) estas líneas:

```bash
GCS_BUCKET_NAME=nobil-events-data
GCS_PREFIX=nobil-data
GCS_SYNC_EVERY_MINUTES=60
GOOGLE_APPLICATION_CREDENTIALS=$HOME/nobil-sa-key.json
```

3. Guarda el archivo

---

## 🚀 PASO 10: Probar Sincronización

### 10.1 Instalar dependencias

```bash
pip install -r requirements.txt
```

### 10.2 Ejecutar el proceso

```bash
python -m src.nobil_ingest.main
```

### 10.3 Verificar en consola

1. Vuelve a Google Cloud Console
2. Ve a **Cloud Storage → Buckets → nobil-events-data**
3. **Pestaña "Objects"**: Deberías ver archivos subidos en carpeta `nobil-data/`
4. Haz clic en un archivo: **"Public URL"** debería funcionar

---

## 🎯 Resumen: Dónde hacer clic

| Acción | Ubicación en la UI | Botón |
|--------|-------------------|-------|
| Crear proyecto | Top-left selector | "NEW PROJECT" |
| Habilitar APIs | Menu → APIs & Services → Enabled APIs | "+ ENABLE APIS" |
| Crear bucket | Menu → Cloud Storage → Buckets | "+ CREATE" |
| Permisos público | Bucket → Permissions | "Grant Access" + allUsers |
| Service Account | Menu → APIs & Services → Service Accounts | "+ CREATE SERVICE ACCOUNT" |
| Crear key JSON | Service Account → Keys | "Add Key" → "Create new" |
| Asignar permisos | Bucket → Permissions | "Grant Access" + Service Account email |
| Probar acceso | Bucket → Objects | Haz clic en archivo → "Public URL" → Abre en incógnito |

---

## 🔐 Checklist de Seguridad

Antes de empezar:

- [ ] Credencial JSON guardada en `$HOME/nobil-sa-key.json` (NO en proyecto)
- [ ] Archivo `.gitignore` incluye `nobil-sa-key.json`
- [ ] Bucket tiene `allUsers` como Viewer (solo lectura)
- [ ] Service account tiene `Storage Object Admin` (solo subida/borrado)
- [ ] Credencial JSON NO está en email/chat/GitHub

---

## ❌ Errores comunes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| "Permission denied" en gsutil | Service account sin permisos | Ve a Bucket → Permissions → Grant Access con Storage Object Admin |
| Bucket name already taken | Nombre no es único globalmente | Agrega timestamp: `nobil-events-data-20260325` |
| No veo "Uniform bucket-level access" | UBLA deshabilitado | Bucket → Permissions → Enable |
| No puedo descargar JSON | Permisos insuficientes | Asegúrate ser propietario del proyecto |
| "Public URL not found" | allUsers sin permisos | Bucket → Permissions → Grant Access allUsers + Viewer |

---

## 📞 Preguntas frecuentes

**P: ¿Puedo usar otra región?**
R: Sí, pero `europe-west1` es más rápido desde Europa. También válidas: `us-central1`, `asia-east1`.

**P: ¿Es obligatorio UBLA?**
R: Recomendado sí. Sin UBLA, necesitas gestionar ACLs por objeto (más complicado).

**P: ¿Puedo cambiar permisos después?**
R: Sí, en cualquier momento. Bucket → Permissions → Edita miembros.

**P: ¿Se carga el bucket con datos de NOBIL automáticamente?**
R: Sí, una vez que configures `.env` y ejecutes el proceso Python.

---

## 🎓 Próximo: Verificar todo está OK

Una vez completaído todo:

```bash
# 1. Verifica archivo de credenciales
ls -lh ~/nobil-sa-key.json

# 2. Verifica variables en .env
cat .env | grep GCS_

# 3. Instala librerías
pip install -r requirements.txt

# 4. Ejecuta proceso
export LOG_LEVEL=DEBUG
python -m src.nobil_ingest.main

# 5. Abre Google Cloud Console y verifica archivos en el bucket
# Cloud Storage → Buckets → nobil-events-data → Objects
```

Si ves archivos en `nobil-data/` carpeta, ¡está funcionando correctamente! 🎉
