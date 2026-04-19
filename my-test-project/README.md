# my-test-project

A sample project demonstrating Claude CLI with the free-claude-code proxy.

## How to use

Once you've set up the global proxy (see [SETUP.md](../free-claude-code/SETUP.md)), just open this folder and run:

```bash
claude
```

Claude will automatically use the proxy settings from `.claude/settings.local.json`.

## Project Structure

```
my-test-project/
├── .claude/
│   └── settings.local.json   # Per-project Claude proxy settings
├── calculator.py              # Sample Python project
└── README.md
```

## Per-project settings

The `.claude/settings.local.json` file overrides global settings for this specific project.
Edit `anthropic_base_url` to point to your deployed proxy URL.

> See the root `claude-proxy-settings.json` and `claude-start.ps1` for the global launcher approach.
