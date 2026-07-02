@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0stop-ai-workspace.ps1" %*
pause
