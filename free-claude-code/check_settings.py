from config.settings import get_settings
import os

settings = get_settings()
print(f"ANTHROPIC_AUTH_TOKEN: '{settings.anthropic_auth_token}'")
print(f"PORT: {settings.port}")
print(f"Working Directory: {os.getcwd()}")
