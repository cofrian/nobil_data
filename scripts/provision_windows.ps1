param(
    [string]$ProjectDir = "C:\opt\nobil-postgres-historico",
    [string]$ServiceName = "nobil-postgres-historico",
    [string]$ServiceUser = "nobil"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function New-RandomPassword {
    $bytes = New-Object byte[] 24
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $base = [Convert]::ToBase64String($bytes)
    return "N0bil!" + $base.Replace("=", "A").Replace("+", "B").Replace("/", "C")
}

function Ensure-LogOnAsServiceRight {
    param([Parameter(Mandatory = $true)][string]$Sid)

    $tempCfg = Join-Path $env:TEMP "nobil-secpol.cfg"
    $tempOut = Join-Path $env:TEMP "nobil-secpol-updated.cfg"

    secedit /export /cfg $tempCfg | Out-Null
    $lines = Get-Content -Path $tempCfg

    $updated = $false
    $result = @()
    foreach ($line in $lines) {
        if ($line -match '^SeServiceLogonRight\s*=') {
            if ($line -notmatch [Regex]::Escape("*$Sid")) {
                if ($line.Trim().EndsWith("=")) {
                    $line = "$line*$Sid"
                }
                else {
                    $line = "$line,*$Sid"
                }
            }
            $updated = $true
        }
        $result += $line
    }

    if (-not $updated) {
        $result += "SeServiceLogonRight = *$Sid"
    }

    Set-Content -Path $tempOut -Value $result -Encoding Unicode
    secedit /configure /db secedit.sdb /cfg $tempOut /areas USER_RIGHTS | Out-Null
}

if (-not (Test-IsAdmin)) {
    throw "Ejecuta este script en PowerShell como Administrador."
}

$sourceDir = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not (Test-Path $ProjectDir)) {
    New-Item -Path $ProjectDir -ItemType Directory -Force | Out-Null
}

# Sincroniza codigo hacia el directorio final.
$robocopyArgs = @(
    "$sourceDir",
    "$ProjectDir",
    "/MIR",
    "/XD", ".git", ".venv", "__pycache__", ".vscode",
    "/R:2",
    "/W:1"
)
$null = & robocopy @robocopyArgs
if ($LASTEXITCODE -gt 7) {
    throw "robocopy fallo con codigo $LASTEXITCODE"
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "No se encontro Python launcher (py). Instala Python 3.10+ desde python.org."
}

$user = Get-LocalUser -Name $ServiceUser -ErrorAction SilentlyContinue
$servicePassword = New-RandomPassword
$securePassword = ConvertTo-SecureString $servicePassword -AsPlainText -Force

if ($null -eq $user) {
    $user = New-LocalUser -Name $ServiceUser -Password $securePassword -PasswordNeverExpires -UserMayNotChangePassword -AccountNeverExpires -Description "Usuario de servicio para NOBIL ingest"
    Add-LocalGroupMember -Group "Users" -Member $ServiceUser
}
else {
    # Se rota password para poder configurar el servicio sin pedir datos manuales.
    $null = net user $ServiceUser $servicePassword
}

Ensure-LogOnAsServiceRight -Sid $user.SID.Value

$venvDir = Join-Path $ProjectDir ".venv"
if (-not (Test-Path $venvDir)) {
    & py -3 -m venv $venvDir
}

$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$pipExe = Join-Path $venvDir "Scripts\pip.exe"

& $pythonExe -m pip install --upgrade pip
& $pipExe install -r (Join-Path $ProjectDir "requirements.txt")

$envPath = Join-Path $ProjectDir ".env"
$envExamplePath = Join-Path $ProjectDir ".env.example"
if (-not (Test-Path $envPath)) {
    Copy-Item -Path $envExamplePath -Destination $envPath -Force
}

$envMap = @{}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $parts = $_.Split('=', 2)
    $k = $parts[0].Trim()
    $v = $parts[1].Trim()
    $envMap[$k] = $v
}

if (-not $envMap.ContainsKey('NOBIL_API_KEY') -or [string]::IsNullOrWhiteSpace($envMap['NOBIL_API_KEY'])) {
    throw "Falta NOBIL_API_KEY en $envPath"
}
if (-not $envMap.ContainsKey('DATABASE_URL') -or [string]::IsNullOrWhiteSpace($envMap['DATABASE_URL'])) {
    throw "Falta DATABASE_URL en $envPath"
}
if ($envMap['DATABASE_URL'] -notmatch 'sslmode=require') {
    throw "DATABASE_URL debe incluir sslmode=require"
}

$aclUser = "$env:COMPUTERNAME\$ServiceUser"
$null = & icacls $envPath /inheritance:r /grant:r "Administrators:F" "SYSTEM:F" "$aclUser:R"

$binDir = Join-Path $ProjectDir "bin"
if (-not (Test-Path $binDir)) {
    New-Item -Path $binDir -ItemType Directory -Force | Out-Null
}

$nssmExe = Join-Path $binDir "nssm.exe"
if (-not (Test-Path $nssmExe)) {
    $zipPath = Join-Path $env:TEMP "nssm-2.24.zip"
    $extractDir = Join-Path $env:TEMP "nssm-2.24"
    Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $zipPath
    if (Test-Path $extractDir) {
        Remove-Item -Path $extractDir -Recurse -Force
    }
    Expand-Archive -Path $zipPath -DestinationPath $extractDir
    Copy-Item -Path (Join-Path $extractDir "nssm-2.24\win64\nssm.exe") -Destination $nssmExe -Force
}

$logsDir = Join-Path $ProjectDir "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -Path $logsDir -ItemType Directory -Force | Out-Null
}

$serviceExists = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($null -eq $serviceExists) {
    & $nssmExe install $ServiceName $pythonExe "-m src.nobil_ingest.main"
}

& $nssmExe set $ServiceName AppDirectory $ProjectDir
& $nssmExe set $ServiceName AppStdout (Join-Path $logsDir "service.out.log")
& $nssmExe set $ServiceName AppStderr (Join-Path $logsDir "service.err.log")
& $nssmExe set $ServiceName AppRotateFiles 1
& $nssmExe set $ServiceName AppRotateOnline 1
& $nssmExe set $ServiceName AppRotateSeconds 86400
& $nssmExe set $ServiceName Start SERVICE_AUTO_START
& $nssmExe set $ServiceName ObjectName ".\$ServiceUser" $servicePassword

$null = & sc.exe failure $ServiceName reset= 0 actions= restart/5000/restart/5000/restart/5000
$null = & sc.exe failureflag $ServiceName 1

Start-Service -Name $ServiceName

Start-Sleep -Seconds 3
$svc = Get-Service -Name $ServiceName
Write-Host "Servicio: $($svc.Name) Estado: $($svc.Status)"
Write-Host "Proyecto: $ProjectDir"
Write-Host "Env: $envPath"
Write-Host "Log out: $(Join-Path $logsDir 'service.out.log')"
Write-Host "Log err: $(Join-Path $logsDir 'service.err.log')"

# Prueba de conectividad y tablas remotas sin exponer secretos.
$verifyCode = @'
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL", "")
if not url:
    raise SystemExit("DATABASE_URL ausente")
engine = create_engine(url, future=True)
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN ('raw_events', 'current_status', 'snapshots')
        ORDER BY table_name
    """)).fetchall()
    print("tables=" + ",".join([r[0] for r in rows]))
'@

$verifyPath = Join-Path $env:TEMP "verify_nobil_tables.py"
Set-Content -Path $verifyPath -Value $verifyCode -Encoding UTF8
Push-Location $ProjectDir
& $pythonExe $verifyPath
Pop-Location

Write-Host "Provision Windows completado."
