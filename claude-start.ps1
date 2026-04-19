# Universal Claude Proxy Launcher
# Replace YOUR-PROXY-URL with your actual Render/Railway proxy URL
# See free-claude-code/SETUP.md for full setup instructions

# NOTE: The CLI automatically appends /v1 — do NOT include it in the base URL
$env:ANTHROPIC_BASE_URL = "https://YOUR-PROXY-URL.onrender.com"
$env:ANTHROPIC_API_KEY  = "sk-ant-dummy"

Write-Host "Launching Claude with Proxy Override..." -ForegroundColor Cyan

# Launch with absolute path to settings
claude --model sonnet --settings "$PSScriptRoot\claude-proxy-settings.json"