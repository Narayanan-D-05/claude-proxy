
import os
from config.settings import get_settings

settings = get_settings()
print(f"MODEL_ALIAS_LLAMA_4: {os.environ.get('MODEL_ALIAS_LLAMA_4')}")
print(f"Resolving 'llama-4': {settings.resolve_model('llama-4')}")
print(f"Resolving 'sonnet': {settings.resolve_model('claude-sonnet-4-6')}")
