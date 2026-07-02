param(
    [string]$WslDistro = "Ubuntu",
    [string]$WslUser = "dzx0902",
    [string]$Workspace = "~/ai_workspace",
    [int]$DockerTimeoutSeconds = 120,
    [int]$FastApiTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[aiws] $Message"
}

function Invoke-Wsl {
    param([string]$Command)
    wsl -d $WslDistro -u $WslUser -- bash -lc $Command
}

function Test-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 3
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSeconds
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    }
    catch {
        return $false
    }
}

function Test-PortOpen {
    param([int]$Port)

    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    return $null -ne $connection
}

Write-Step "checking Docker Desktop"
$dockerDesktop = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerDesktop) {
    $dockerDesktopPath = Join-Path $Env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dockerDesktopPath)) {
        throw "Docker Desktop was not found at '$dockerDesktopPath'. Install Docker Desktop first."
    }

    Write-Step "starting Docker Desktop"
    Start-Process -FilePath $dockerDesktopPath
}
else {
    Write-Step "Docker Desktop process is already running"
}

Write-Step "waiting for Docker engine"
$deadline = (Get-Date).AddSeconds($DockerTimeoutSeconds)
do {
    $dockerReady = $false
    try {
        Invoke-Wsl "docker info >/dev/null 2>&1"
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
        }
    }
    catch {
        $dockerReady = $false
    }

    if (-not $dockerReady) {
        Start-Sleep -Seconds 3
    }
} until ($dockerReady -or (Get-Date) -gt $deadline)

if (-not $dockerReady) {
    throw "Docker engine did not become ready within $DockerTimeoutSeconds seconds. Open Docker Desktop and check its status."
}

Write-Step "starting docker compose services"
Invoke-Wsl "cd $Workspace && docker compose up -d"
if ($LASTEXITCODE -ne 0) {
    throw "docker compose up -d failed in WSL workspace '$Workspace'."
}

Write-Step "checking FastAPI on port 8001"
$fastApiHealthy = Test-HttpOk -Url "http://127.0.0.1:8001/health"
if ($fastApiHealthy) {
    Write-Step "FastAPI is already running"
}
else {
    $portInUse = Test-PortOpen -Port 8001
    if ($portInUse) {
        Write-Warning "Port 8001 is already in use, but http://127.0.0.1:8001/health is not healthy."
        Write-Warning "Run 'Get-NetTCPConnection -LocalPort 8001 -State Listen | Select-Object *' to identify the listener."
        throw "Refusing to start another uvicorn process on occupied port 8001."
    }

    Write-Step "starting FastAPI RAG backend"
    $startFastApi = @"
cd $Workspace &&
mkdir -p logs &&
if pgrep -af '[u]vicorn services\.rag_api\.app:app' >/dev/null; then
  echo 'FastAPI uvicorn process is already running.'
else
  . .venv/bin/activate &&
  nohup uvicorn services.rag_api.app:app --host 0.0.0.0 --port 8001 >> logs/rag_api.log 2>&1 &
  echo 'FastAPI uvicorn started. Log: logs/rag_api.log'
fi
"@
    Invoke-Wsl $startFastApi
    if ($LASTEXITCODE -ne 0) {
        throw "failed to start FastAPI in WSL."
    }

    Write-Step "waiting for FastAPI health endpoint"
    $deadline = (Get-Date).AddSeconds($FastApiTimeoutSeconds)
    do {
        Start-Sleep -Seconds 2
        $fastApiHealthy = Test-HttpOk -Url "http://127.0.0.1:8001/health"
    } until ($fastApiHealthy -or (Get-Date) -gt $deadline)

    if (-not $fastApiHealthy) {
        Write-Warning "FastAPI did not pass health check within $FastApiTimeoutSeconds seconds."
        Write-Warning "Check logs with: wsl -d $WslDistro -u $WslUser -- bash -lc 'cd $Workspace && tail -n 50 logs/rag_api.log'"
    }
}

Write-Step "docker ps"
Invoke-Wsl "docker ps"

Write-Step "checking FastAPI health"
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -UseBasicParsing -TimeoutSec 5 |
        Select-Object StatusCode, Content |
        Format-List
}
catch {
    Write-Warning "FastAPI health check failed: $($_.Exception.Message)"
}

Write-Step "checking AstrBot WebUI"
if (Test-HttpOk -Url "http://localhost:6185") {
    Write-Step "AstrBot WebUI is reachable at http://localhost:6185"
}
else {
    Write-Warning "AstrBot WebUI is not reachable at http://localhost:6185 yet. Check docker ps and container logs if needed."
}

Write-Step "startup finished"
