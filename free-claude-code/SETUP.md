# 🚀 Free Claude Code — Complete Setup Guide

Use Claude CLI (`claude`) for free by routing it through a self-hosted proxy backed by NVIDIA NIM models.

> **What this does:** Intercepts all Claude CLI requests and forwards them to free NVIDIA NIM models,
> giving you a fully working `claude` command with no Anthropic subscription required.

---

## 📋 Table of Contents

1. [How It Works](#how-it-works)
2. [Prerequisites](#prerequisites)
3. [Step 1 — Deploy the Proxy to the Cloud](#step-1--deploy-the-proxy-to-the-cloud)
4. [Step 2 — Get Your NVIDIA NIM API Key](#step-2--get-your-nvidia-nim-api-key)
5. [Step 3 — Configure the Cloud Proxy](#step-3--configure-the-cloud-proxy)
6. [Step 4 — Client Setup](#step-4--client-setup)
   - [Windows](#-windows)
   - [macOS](#-macos)
   - [Linux](#-linux)
7. [Verify Everything Works](#verify-everything-works)
8. [Available Models](#available-models)
9. [Troubleshooting](#troubleshooting)

---

## How It Works

```
Claude CLI  ──► Your Cloud Proxy (Render/Railway/etc.)  ──► NVIDIA NIM (free tier)
               (free-claude-code)                           (GLM-4.7, Kimi, etc.)
```

- The CLI thinks it's talking to Anthropic — it's actually talking to your proxy.
- The proxy translates Anthropic API calls to NVIDIA NIM's OpenAI-compatible API.
- NVIDIA NIM has a generous free tier with no credit card required.

---

## Prerequisites

| Tool | Install |
|------|---------|
| **Claude CLI** | `npm install -g @anthropic-ai/claude-code` |
| **Git** | https://git-scm.com |
| **NVIDIA NIM account** | https://build.nvidia.com (free) |
| **Render account** | https://render.com (free tier) |

---

## Step 1 — Deploy the Proxy to the Cloud

### Option A: Render (Recommended — Free Tier)

1. Fork this repo: **https://github.com/Narayanan-D-05/claude-proxy**
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your forked GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api.app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
5. Click **Deploy** — note your URL (e.g. `https://your-app.onrender.com`)

### Option B: Railway

1. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub**
2. Connect your forked repo
3. Railway auto-detects the Python app and deploys it
4. Note your URL from the **Settings → Domains** tab

### Option C: Self-Hosted (any Linux VPS)

```bash
git clone https://github.com/Narayanan-D-05/claude-proxy
cd claude-proxy/free-claude-code
pip install -r requirements.txt
uvicorn api.app:app --host 0.0.0.0 --port 3000
```

---

## Step 2 — Get Your NVIDIA NIM API Key

1. Go to **https://build.nvidia.com/settings/api-keys**
2. Sign up / log in (free, no credit card)
3. Click **Generate Key**
4. Copy the key — it starts with `nvapi-`

---

## Step 3 — Configure the Cloud Proxy

In your Render/Railway dashboard, add these **environment variables**:

| Variable | Value |
|----------|-------|
| `NVIDIA_NIM_API_KEY` | `nvapi-xxxxxxxxxxxxxxxxxxxx` |
| `MODEL` | `nvidia_nim/z-ai/glm4.7` |
| `MODEL_SONNET` | `nvidia_nim/z-ai/glm4.7` |
| `MODEL_HAIKU` | `nvidia_nim/moonshotai/kimi-k2-instruct-0905` |
| `MODEL_OPUS` | `nvidia_nim/minimaxai/minimax-m2.7` |
| `ANTHROPIC_AUTH_TOKEN` | *(leave empty — no auth required)* |

> After saving, your proxy redeploys automatically (~2 min).

**Verify your proxy is live:**
```bash
curl https://your-app.onrender.com/health
# Expected: {"status":"healthy"}
```

---

## Step 4 — Client Setup

Replace `https://your-app.onrender.com` with your actual proxy URL in all commands below.

---

### 🪟 Windows

#### 1. Create the settings file

Save this as `C:\Users\<you>\claude-proxy-settings.json`:

```json
{
    "anthropic_auth_token": "sk-ant-dummy",
    "anthropic_api_key": "sk-ant-dummy",
    "anthropic_base_url": "https://your-app.onrender.com"
}
```

> ⚠️ Do **not** add `/v1` to the URL — Claude CLI appends it automatically.

#### 2. Set permanent environment variables

Open **PowerShell as Administrator** and run:

```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", "https://your-app.onrender.com", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-dummy", "User")
```

#### 3. Add the global `claude` function to your PowerShell profile

Open your profile file:
```powershell
notepad $PROFILE
```

Append this block (update the paths to match yours):

```powershell
# ==== Free Claude Code — Global Proxy ====
$env:ANTHROPIC_BASE_URL = "https://your-app.onrender.com"
$env:ANTHROPIC_API_KEY  = "sk-ant-dummy"

function Invoke-ClaudeProxy {
    $settingsFile = "C:\Users\<you>\claude-proxy-settings.json"
    $claudeBin    = "C:\Users\<you>\.local\bin\claude.exe"
    $hasSettings  = $args -contains "--settings"
    if (-not $hasSettings) {
        & $claudeBin @args --settings $settingsFile
    } else {
        & $claudeBin @args
    }
}

Set-Alias -Name claude -Value Invoke-ClaudeProxy -Force
# ==========================================
```

Reload the profile:
```powershell
. $PROFILE
```

#### 4. Use from any directory

```powershell
# From any folder:
claude                         # Opens with default (sonnet)
claude --model haiku
claude --model sonnet
claude --resume <session-id>
```

---

### 🍎 macOS

#### 1. Create the settings file

```bash
cat > ~/claude-proxy-settings.json << 'EOF'
{
    "anthropic_auth_token": "sk-ant-dummy",
    "anthropic_api_key": "sk-ant-dummy",
    "anthropic_base_url": "https://your-app.onrender.com"
}
EOF
```

#### 2. Add to your shell profile

For **zsh** (default on macOS):
```bash
nano ~/.zshrc
```

Append:
```bash
# ==== Free Claude Code — Global Proxy ====
export ANTHROPIC_BASE_URL="https://your-app.onrender.com"
export ANTHROPIC_API_KEY="sk-ant-dummy"

claude() {
    local settings="$HOME/claude-proxy-settings.json"
    local has_settings=false
    for arg in "$@"; do
        [[ "$arg" == "--settings" ]] && has_settings=true
    done
    if [ "$has_settings" = false ]; then
        command claude "$@" --settings "$settings"
    else
        command claude "$@"
    fi
}
# ==========================================
```

Reload:
```bash
source ~/.zshrc
```

For **bash** (older macOS or if you use bash):
```bash
nano ~/.bashrc   # or ~/.bash_profile
# Append the same block above, then:
source ~/.bashrc
```

#### 3. Use from any directory

```bash
# From any folder:
claude
claude --model haiku
claude --model sonnet
claude --resume <session-id>
```

---

### 🐧 Linux

#### 1. Create the settings file

```bash
cat > ~/claude-proxy-settings.json << 'EOF'
{
    "anthropic_auth_token": "sk-ant-dummy",
    "anthropic_api_key": "sk-ant-dummy",
    "anthropic_base_url": "https://your-app.onrender.com"
}
EOF
```

#### 2. Add to your shell profile

For **bash**:
```bash
nano ~/.bashrc
```

Append:
```bash
# ==== Free Claude Code — Global Proxy ====
export ANTHROPIC_BASE_URL="https://your-app.onrender.com"
export ANTHROPIC_API_KEY="sk-ant-dummy"

claude() {
    local settings="$HOME/claude-proxy-settings.json"
    local has_settings=false
    for arg in "$@"; do
        [[ "$arg" == "--settings" ]] && has_settings=true
    done
    if [ "$has_settings" = false ]; then
        command claude "$@" --settings "$settings"
    else
        command claude "$@"
    fi
}
# ==========================================
```

Reload:
```bash
source ~/.bashrc
```

For **zsh** (`~/.zshrc`) or **fish** (`~/.config/fish/config.fish`):

```fish
# fish shell equivalent
set -Ux ANTHROPIC_BASE_URL "https://your-app.onrender.com"
set -Ux ANTHROPIC_API_KEY "sk-ant-dummy"

function claude
    set settings "$HOME/claude-proxy-settings.json"
    if not contains -- "--settings" $argv
        command claude $argv --settings $settings
    else
        command claude $argv
    end
end
funcsave claude
```

#### 3. Use from any directory

```bash
claude
claude --model haiku
claude --model sonnet
claude --resume <session-id>
```

---

## Verify Everything Works

### 1. Check proxy health
```bash
curl https://your-app.onrender.com/health
# → {"status":"healthy"}
```

### 2. Check proxy diagnostics
```bash
curl https://your-app.onrender.com/v1/diagnostics
# → {"status":"ready","has_nvidia_key":true,...}
```

### 3. Check environment variables (Windows)
```powershell
echo $env:ANTHROPIC_BASE_URL   # should print your proxy URL
echo $env:ANTHROPIC_API_KEY    # should print sk-ant-dummy
```

### 3. Check environment variables (Mac/Linux)
```bash
echo $ANTHROPIC_BASE_URL   # should print your proxy URL
echo $ANTHROPIC_API_KEY    # should print sk-ant-dummy
```

### 4. Launch Claude
```bash
claude --model sonnet
# Type "hi" — you should get a response within ~10 seconds
```

---

## Available Models

| `--model` flag | Actual model | Best for |
|---|---|---|
| `sonnet` | `z-ai/glm4.7` | General coding, reasoning |
| `haiku` | `moonshotai/kimi-k2-instruct` | Fast responses, simple tasks |
| `opus` | `minimaxai/minimax-m2.7` | Complex, long-context tasks |

You can add more model aliases in your Render env vars using the pattern `MODEL_ALIAS_<NAME>`.

---

## Troubleshooting

### "Retrying in 5s" loop
The proxy is reachable but returning an error. Check diagnostics:
```bash
curl https://your-app.onrender.com/v1/diagnostics
```
Look at `last_error` — it will show the exact failure reason.

### Render free tier cold starts
Render free instances spin down after 15 minutes of inactivity. The first request after idle takes **30-60 seconds**. This is normal — subsequent requests are fast.

**Fix:** Use a free uptime monitor like [UptimeRobot](https://uptimerobot.com) to ping `/health` every 10 minutes.

### "Model does not exist" error immediately
- Make sure `anthropic_base_url` does **not** have `/v1` at the end (Claude CLI adds it)
- Verify the env vars are set: `echo $env:ANTHROPIC_BASE_URL` (Windows) or `echo $ANTHROPIC_BASE_URL` (Mac/Linux)

### "Not logged in" error
- Ensure `anthropic_auth_token` in the settings JSON is a non-empty string (e.g. `"sk-ant-dummy"`)
- An empty `""` token causes the CLI to treat you as logged out

### Proxy not receiving requests (last_error empty)
- Double-check the URL has no `/v1` suffix
- Confirm the settings JSON is being loaded: run with `--settings /full/path/to/settings.json` explicitly

---

## File Summary

| File | Purpose |
|------|---------|
| `~/claude-proxy-settings.json` | CLI settings: auth token, API key, base URL |
| `~/.zshrc` / `$PROFILE` | Shell profile: env vars + `claude` wrapper function |
| `.env` (on server) | Server config: NVIDIA key, model mappings |
