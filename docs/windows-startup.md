# Windows one-click startup

This project can be started from Windows with the scripts in `src/scripts/windows/`.
They start Docker Desktop, run `docker compose up -d` in WSL, and start the
FastAPI RAG backend when it is not already running.

## Prerequisites

- Docker Desktop is installed on Windows.
- WSL is installed and the project exists at `~/ai_workspace`.
- The default WSL distribution name used by the scripts is `Ubuntu`.

If your WSL distribution has a different name, check it with:

```powershell
wsl -l -v
```

Then update the `WslDistro` default value in:

- `src/scripts/windows/start-ai-workspace.ps1`
- `src/scripts/windows/stop-ai-workspace.ps1`

The scripts default to WSL user `dzx0902`. If your WSL user is different,
update the `WslUser` default value in the same two files.

## Start

From the project root on Windows:

```powershell
.\scripts\windows\start-ai-workspace.ps1
```

Or double-click:

```text
src/scripts/windows/aiws.bat
```

The startup script:

- starts Docker Desktop if needed;
- waits until Docker is available from WSL;
- runs `docker compose up -d` in `~/ai_workspace`;
- creates `~/ai_workspace/logs` if needed;
- starts `uvicorn services.rag_api.app:app --host 0.0.0.0 --port 8001` with
  `nohup` when FastAPI is not already running;
- writes FastAPI output to `~/ai_workspace/logs/rag_api.log`;
- checks `docker ps`, `http://127.0.0.1:8001/health`, and `http://localhost:6185`.

## Stop

Stop only the FastAPI backend:

```powershell
.\scripts\windows\stop-ai-workspace.ps1
```

Stop FastAPI and the docker compose services:

```powershell
.\scripts\windows\stop-ai-workspace.ps1 -StopContainers
```

Or double-click:

```text
src/scripts/windows/stop-aiws.bat
```

## Logs

In WSL:

```bash
tail -f ~/ai_workspace/logs/rag_api.log
```

## Verification

From Windows:

```powershell
curl http://localhost:6185
curl http://localhost:8001/health
```

In WSL:

```bash
cd ~/ai_workspace
docker ps
tail -n 50 logs/rag_api.log
```

## Common issues

- Docker Desktop is not installed or has not finished starting.
- The WSL distribution name is not `Ubuntu`; run `wsl -l -v` and update the scripts.
- Port `8001` is already occupied. The startup script refuses to start a second
  uvicorn process if the port is busy but `/health` is not healthy.
- AstrBot WebUI opens but the model is unavailable because the FastAPI backend
  is not running.
- Chroma uses port `8000`, FastAPI uses port `8001`, and AstrBot WebUI uses port
  `6185`.

Keep API keys and other secrets in `.env`. Do not write real API keys into
`astrbot-data/cmd_config.json`, logs, or documentation.
