# prompts/__init__.py
# Dynamic prompt version loader.
#
# Selects which prompt version to use based on the PROMPT_VERSION environment
# variable. Defaults to "v1" if not set.
#
# How to use:
#   PROMPT_VERSION=v2 python agent/qa_agent.py
#
# How to add a new version:
#   1. Create prompts/v3.py with a SYSTEM_PROMPT string and a header changelog
#   2. Set PROMPT_VERSION=v3 when running the agent
#   No changes needed in this file or in qa_agent.py.

import os
import importlib

# Default to v1 to preserve the original behavior if PROMPT_VERSION is not set.
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")

try:
    _module = importlib.import_module(f"prompts.{PROMPT_VERSION}")
    SYSTEM_PROMPT = _module.SYSTEM_PROMPT
except ModuleNotFoundError as e:
    raise ImportError(
        f"Prompt version '{PROMPT_VERSION}' not found. "
        f"Expected file: prompts/{PROMPT_VERSION}.py. "
        f"Available versions are the *.py files in the prompts/ folder."
    ) from e
except AttributeError as e:
    raise ImportError(
        f"Prompt module 'prompts/{PROMPT_VERSION}.py' exists but does not "
        f"define SYSTEM_PROMPT. Every prompt version file must export a "
        f"SYSTEM_PROMPT string."
    ) from e

# Re-export so callers can do:
#   from prompts import SYSTEM_PROMPT, PROMPT_VERSION
__all__ = ["SYSTEM_PROMPT", "PROMPT_VERSION"]
