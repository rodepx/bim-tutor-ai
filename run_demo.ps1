# Agente Profesor BIM - levanta la demo completa (PowerShell 5.1+).
# Uso, desde la raiz del repo:  powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
#   -NoSeed    no ejecuta demo/seed.py
#   -FreshDb   borra backend\profesor_bim.db antes de arrancar (BD limpia)
param(
    [switch]$NoSeed,
    [switch]$FreshDb
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$py = Join-Path $root 'backend\.venv\Scripts\python.exe'
$api = 'http://127.0.0.1:8000/api'  # IPv4: uvicorn escucha en 127.0.0.1 y 'localhost' puede resolver primero a ::1
$dashboard = 'http://localhost:5173'

if (-not (Test-Path $py)) {
    Write-Host "No se encontro $py. Crea el entorno: cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}
$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npm -and (Test-Path 'C:\Program Files\nodejs\npm.cmd')) { $npm = 'C:\Program Files\nodejs\npm.cmd' }
if (-not $npm) { Write-Host 'No se encontro npm (instala Node.js 20+).' -ForegroundColor Red; exit 1 }
$nodeDir = Split-Path $npm -Parent
if (-not (Test-Path (Join-Path $root 'frontend\node_modules'))) {
    Write-Host 'Instalando dependencias del dashboard (npm install)...'
    Push-Location (Join-Path $root 'frontend'); & $npm install; Pop-Location
}

if ($FreshDb) {
    $db = Join-Path $root 'backend\profesor_bim.db'
    if (Test-Path $db) { Remove-Item $db -Force -Confirm:$false; Write-Host 'BD anterior borrada.' }
}

Write-Host 'Iniciando backend (ventana nueva, puerto 8000)...'
Start-Process powershell -WorkingDirectory (Join-Path $root 'backend') -ArgumentList @(
    '-NoExit', '-Command', "`$host.UI.RawUI.WindowTitle='Profesor BIM - backend'; & '$py' -m uvicorn app.main:app --port 8000")

Write-Host 'Iniciando dashboard (ventana nueva, puerto 5173)...'
Start-Process powershell -WorkingDirectory (Join-Path $root 'frontend') -ArgumentList @(
    '-NoExit', '-Command', "`$host.UI.RawUI.WindowTitle='Profesor BIM - dashboard'; `$env:Path='$nodeDir;' + `$env:Path; & '$npm' run dev")

Write-Host -NoNewline 'Esperando /api/health'
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $h = Invoke-RestMethod -Uri "$api/health" -TimeoutSec 2 -ErrorAction Stop
    } catch { $h = $null }
    if ($h -and $h.status -eq 'ok') { $ok = $true; break }
    Write-Host -NoNewline '.'
    Start-Sleep -Seconds 1
}
Write-Host ''
if (-not $ok) { Write-Host 'El backend no respondio en 60 s. Revisa la ventana del backend.' -ForegroundColor Red; exit 1 }
Write-Host "Backend OK (version $($h.version), IA en modo $($h.llm_mode))." -ForegroundColor Green

if (-not $NoSeed) {
    Write-Host 'Cargando datos de demo (demo/seed.py)...'
    $env:PYTHONIOENCODING = 'utf-8'
    & $py (Join-Path $root 'demo\seed.py') --base $api
    if ($LASTEXITCODE -ne 0) { Write-Host 'seed.py fallo.' -ForegroundColor Red; exit $LASTEXITCODE }
}

Write-Host ''
Write-Host "Dashboard: $dashboard" -ForegroundColor Cyan
Write-Host "API docs:  http://localhost:8000/docs"
Write-Host 'Para detener: cierra las dos ventanas abiertas.'
