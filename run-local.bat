@echo off
title Claude Local Proxy Runner
echo ===================================================
echo     CLAUDE CODE LOCAL PROXY RUNNER
echo ===================================================
echo.

:: 1. Force the API base URL to point to localhost:3000
:: This overrides any persistent environment variables (e.g. in your PowerShell profile)
set ANTHROPIC_BASE_URL=http://127.0.0.1:3000
set CLAUDE_BASE_URL=http://127.0.0.1:3000
echo [+] Environment variables overridden to local server:
echo     ANTHROPIC_BASE_URL=%ANTHROPIC_BASE_URL%
echo.

:: 2. Start the local proxy server in a new window
echo [+] Starting local proxy server in a new window...
start "Claude Proxy Server" cmd /k "cd /d c:\Users\dnara\Desktop\Projects\Setups\free-claude-code && .venv\Scripts\python.exe server.py"

:: 3. Wait for uvicorn to initialize
echo [+] Waiting for the server to start (2 seconds)...
timeout /t 2 /nobreak > nul
echo.

:: 4. Run Claude Code inside my-test-project
echo [+] Navigating to my-test-project and launching Claude CLI...
echo     Running: claude %*
echo.
cd /d c:\Users\dnara\Desktop\Projects\Setups\my-test-project
call claude %*

echo.
echo ===================================================
echo     Claude session ended.
echo ===================================================
pause
