param(
    [switch]$StopContainers,
    [string]$WslDistro = "Ubuntu",
    [string]$WslUser = "dzx0902",
    [string]$Workspace = "~/ai_workspace"
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

Write-Step "stopping FastAPI uvicorn process"
$stopFastApi = @"
cd $Workspace &&
if pgrep -af '[u]vicorn services\.rag_api\.app:app' >/dev/null; then
  pkill -f '[u]vicorn services\.rag_api\.app:app'
  echo 'FastAPI uvicorn stopped.'
else
  echo 'FastAPI uvicorn is not running.'
fi
"@
Invoke-Wsl $stopFastApi

if ($StopContainers) {
    Write-Step "stopping docker compose services"
    Invoke-Wsl "cd $Workspace && docker compose down"
}
else {
    Write-Step "leaving docker compose services running; pass -StopContainers to run docker compose down"
}

Write-Step "current FastAPI process status"
Invoke-Wsl "pgrep -af '[u]vicorn services\.rag_api\.app:app' || true"

Write-Step "current docker status"
Invoke-Wsl "cd $Workspace && docker compose ps"

Write-Step "stop finished"
