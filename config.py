import os

# LLM — provider selection ("anthropic" or "cerebras")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"

# Cerebras (OpenAI-compatible)
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.environ.get("CEREBRAS_MODEL", "zai-glm-4.7")
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"

# Shared
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
MAX_TOKENS = 4096

# Docker
DOCKER_NETWORK = "agent-net"
SKILL_BASE_IMAGE = "python:3.12-slim"
CONTAINER_TIMEOUT = 60  # seconds — kill builds/runs that exceed this
SKILL_STARTUP_TIMEOUT = 15  # seconds — max wait for /health to respond

# Port allocation
PORT_RANGE_START = 9001
PORT_RANGE_END = 9100

# Skill Factory
MAX_BUILD_RETRIES = 3  # feed errors back to Claude and retry
