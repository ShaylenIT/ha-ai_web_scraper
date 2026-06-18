"""Constants for ai_web_scraper."""

from __future__ import annotations

from enum import StrEnum
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "ai_web_scraper"
ATTRIBUTION = "Data provided by AI Web Scraper"

SAVE_MARKDOWN_DEBUG = True

CONF_ENTRY_TYPE = "entry_type"
CONF_PROVIDER_ID = "provider_id"
CONF_PROVIDER_NAME = "provider_name"
CONF_API_KEY = "api_key"
CONF_MODEL_NAME = "model_name"
CONF_BROWSERLESS_URL = "browserless_url"
CONF_PROVIDER_TYPE = "provider_type"
CONF_SCRAPER_NAME = "scraper_name"
CONF_URL = "url"
CONF_PROMPT = "prompt"
CONF_EXTRACTION_MODE = "extraction_mode"
CONF_INTERVAL_SECONDS = "interval_seconds"
CONF_BLOCK_CONSENT_MODALS = "block_consent_modals"
CONF_NOTES = "notes"
CONF_COOL_DOWN_SECONDS = "cool_down_seconds"
CONF_REQUEST_TIMEOUT = "request_timeout"

CONF_BASE_URL = "base_url"


class ProviderType(StrEnum):
    """AI provider brand identifiers."""

    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GROQ = "groq"
    LOCALAI = "localai"
    OLLAMA = "ollama"
    OPENWEBUI = "openwebui"
    OPENROUTER = "openrouter"
    OPENAI_COMPATIBLE = "openai_compatible"
    GEMINI = "gemini"


PROVIDER_TYPES = {
    ProviderType.OPENAI: "OpenAI",
    ProviderType.DEEPSEEK: "DeepSeek",
    ProviderType.GROQ: "Groq",
    ProviderType.LOCALAI: "LocalAI",
    ProviderType.OLLAMA: "Ollama",
    ProviderType.OPENWEBUI: "Open WebUI",
    ProviderType.OPENROUTER: "OpenRouter",
    ProviderType.OPENAI_COMPATIBLE: "Custom OpenAI Compatible",
    ProviderType.GEMINI: "Google Gemini",
}

OPENAI_COMPATIBLE_TYPES = {
    ProviderType.OPENAI,
    ProviderType.DEEPSEEK,
    ProviderType.GROQ,
    ProviderType.LOCALAI,
    ProviderType.OLLAMA,
    ProviderType.OPENWEBUI,
    ProviderType.OPENROUTER,
    ProviderType.OPENAI_COMPATIBLE,
}

PROVIDER_BASE_URLS = {
    ProviderType.OPENAI: "https://api.openai.com/v1",
    ProviderType.DEEPSEEK: "https://api.deepseek.com/v1",
    ProviderType.GROQ: "https://api.groq.com/openai/v1",
    ProviderType.LOCALAI: "http://localhost:8080/v1",
    ProviderType.OLLAMA: "http://localhost:11434/v1",
    ProviderType.OPENWEBUI: "",
    ProviderType.OPENROUTER: "https://openrouter.ai/api/v1",
    ProviderType.OPENAI_COMPATIBLE: "",
}

ENTRY_TYPE_PROVIDER = "provider"
ENTRY_TYPE_SCRAPER = "scraper"
EXTRACTION_MODES = {
    "dom": "Text/HTML Based Extraction",
    "browser_based": "Browser Based Extraction",
}


class ScraperPhase(StrEnum):
    """Phase labels emitted during a scrape lifecycle."""

    IDLE = "idle"
    QUEUED = "queued"
    COOLING_DOWN = "cooling_down"
    RENDERING_PAGE = "rendering_page"
    FETCHING_PAGE = "fetching_page"
    WAITING_FOR_AI = "waiting_for_ai"
    REQUESTING_AI = "requesting_ai"
    COMPLETED = "completed"


SCRAPER_STATUS_ATTR = "scraper_status"
