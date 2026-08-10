[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$toolsDirectory = Join-Path $projectRoot ".tools"
$frontendDirectory = Join-Path $projectRoot "frontend"
$backendDirectory = Join-Path $projectRoot "backend"
$dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$cloudflared = Join-Path $toolsDirectory "cloudflared.exe"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Test-Port([int]$Port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Wait-ForPort([int]$Port, [int]$TimeoutSeconds, [string]$ServiceName) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $Port) {
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "$ServiceName did not start on port $Port within $TimeoutSeconds seconds."
}

function Wait-ForDocker([int]$TimeoutSeconds = 120) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        & docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 3
    }
    throw "Docker Desktop did not become ready within $TimeoutSeconds seconds."
}

function Wait-ForContainerHealth([string]$ContainerName, [int]$TimeoutSeconds = 120) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $health = & docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $ContainerName 2>$null
        if ($LASTEXITCODE -eq 0 -and $health -in @("healthy", "running")) {
            return
        }
        if ($health -eq "unhealthy") {
            throw "$ContainerName reported an unhealthy state."
        }
        Start-Sleep -Seconds 2
    }
    throw "$ContainerName did not become healthy within $TimeoutSeconds seconds."
}

New-Item -ItemType Directory -Path $toolsDirectory -Force | Out-Null

Write-Step "Checking Docker Desktop"
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    if (-not (Test-Path $dockerDesktop)) {
        throw "Docker Desktop was not found at $dockerDesktop."
    }
    Write-Host "Starting Docker Desktop..."
    Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
    Wait-ForDocker
}
Write-Host "Docker is ready." -ForegroundColor Green

Write-Step "Starting MySQL and OSRM"
Push-Location $projectRoot
try {
    & docker compose up -d mysql osrm
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose could not start MySQL and OSRM."
    }
} finally {
    Pop-Location
}
Wait-ForContainerHealth "escape_mysql"
Wait-ForContainerHealth "escape_osrm"
Write-Host "MySQL and OSRM are healthy." -ForegroundColor Green

Write-Step "Starting FastAPI"
if (-not (Test-Port 8000)) {
    $backendPython = Join-Path $backendDirectory ".venv\Scripts\python.exe"
    if (-not (Test-Path $backendPython)) {
        throw "The backend virtual environment is missing. Expected $backendPython."
    }
    Start-Process -FilePath $backendPython `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $backendDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $toolsDirectory "backend-current.out.log") `
        -RedirectStandardError (Join-Path $toolsDirectory "backend-current.err.log")
    Wait-ForPort 8000 45 "FastAPI"
}
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 15
} catch {
    throw "FastAPI is listening but its health check failed: $($_.Exception.Message)"
}
Write-Host "FastAPI is ready." -ForegroundColor Green

Write-Step "Starting Next.js"
if (-not (Test-Port 3000)) {
    if (-not (Test-Path (Join-Path $frontendDirectory "node_modules"))) {
        throw "Frontend dependencies are missing. Run npm install in the frontend folder first."
    }
    Push-Location $frontendDirectory
    try {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) {
            throw "The frontend production build failed."
        }
    } finally {
        Pop-Location
    }
    Start-Process -FilePath "npm.cmd" `
        -ArgumentList @("run", "start", "--", "-H", "127.0.0.1") `
        -WorkingDirectory $frontendDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $toolsDirectory "frontend-production-current.out.log") `
        -RedirectStandardError (Join-Path $toolsDirectory "frontend-production-current.err.log")
    Wait-ForPort 3000 45 "Next.js"
}
Write-Host "Next.js is ready at http://127.0.0.1:3000." -ForegroundColor Green

Write-Step "Starting Cloudflare Tunnel"
if (-not (Test-Path $cloudflared)) {
    throw "cloudflared.exe is missing from $toolsDirectory."
}
$tunnelLog = Join-Path $toolsDirectory "frontend-tunnel-current.err.log"
$runningTunnel = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "cloudflared.exe" -and $_.CommandLine -like "*127.0.0.1:3000*"
}
if (-not $runningTunnel) {
    Remove-Item $tunnelLog -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $toolsDirectory "frontend-tunnel-current.out.log") -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $cloudflared `
        -ArgumentList @("tunnel", "--url", "http://127.0.0.1:3000", "--no-autoupdate") `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $toolsDirectory "frontend-tunnel-current.out.log") `
        -RedirectStandardError $tunnelLog
}

$deadline = (Get-Date).AddSeconds(45)
$publicUrl = $null
while ((Get-Date) -lt $deadline) {
    if (Test-Path $tunnelLog) {
        $match = Select-String -Path $tunnelLog -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -Last 1
        if ($match) {
            $publicUrl = $match.Matches[0].Value
            break
        }
    }
    Start-Sleep -Seconds 1
}
if (-not $publicUrl) {
    throw "Cloudflare Tunnel started, but no public URL appeared within 45 seconds."
}

Write-Host "`neScape is ready." -ForegroundColor Green
Write-Host "Local:  http://127.0.0.1:3000"
Write-Host "Public: $publicUrl" -ForegroundColor Yellow
Write-Host "`nThe public URL stops working when this PC or the tunnel process stops."
