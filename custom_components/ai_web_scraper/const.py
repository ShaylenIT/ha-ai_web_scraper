"""Constants for ai_web_scraper."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "ai_web_scraper"
ATTRIBUTION = "Data provided by AI Web Scraper"

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

PROVIDER_TYPE_OPENAI = "openai"
PROVIDER_TYPE_DEEPSEEK = "deepseek"
PROVIDER_TYPE_GROQ = "groq"
PROVIDER_TYPE_LOCALAI = "localai"
PROVIDER_TYPE_OLLAMA = "ollama"
PROVIDER_TYPE_OPENWEBUI = "openwebui"
PROVIDER_TYPE_OPENROUTER = "openrouter"
PROVIDER_TYPE_OPENAI_COMPATIBLE = "openai_compatible"
PROVIDER_TYPE_GEMINI = "gemini"

PROVIDER_TYPES = {
    PROVIDER_TYPE_OPENAI: "OpenAI",
    PROVIDER_TYPE_DEEPSEEK: "DeepSeek",
    PROVIDER_TYPE_GROQ: "Groq",
    PROVIDER_TYPE_LOCALAI: "LocalAI",
    PROVIDER_TYPE_OLLAMA: "Ollama",
    PROVIDER_TYPE_OPENWEBUI: "Open WebUI",
    PROVIDER_TYPE_OPENROUTER: "OpenRouter",
    PROVIDER_TYPE_OPENAI_COMPATIBLE: "Custom OpenAI Compatible",
    PROVIDER_TYPE_GEMINI: "Google Gemini",
}

OPENAI_COMPATIBLE_TYPES = {
    PROVIDER_TYPE_OPENAI,
    PROVIDER_TYPE_DEEPSEEK,
    PROVIDER_TYPE_GROQ,
    PROVIDER_TYPE_LOCALAI,
    PROVIDER_TYPE_OLLAMA,
    PROVIDER_TYPE_OPENWEBUI,
    PROVIDER_TYPE_OPENROUTER,
    PROVIDER_TYPE_OPENAI_COMPATIBLE,
}

PROVIDER_BASE_URLS = {
    PROVIDER_TYPE_OPENAI: "https://api.openai.com/v1",
    PROVIDER_TYPE_DEEPSEEK: "https://api.deepseek.com/v1",
    PROVIDER_TYPE_GROQ: "https://api.groq.com/openai/v1",
    PROVIDER_TYPE_LOCALAI: "http://localhost:8080/v1",
    PROVIDER_TYPE_OLLAMA: "http://localhost:11434/v1",
    PROVIDER_TYPE_OPENWEBUI: "",
    PROVIDER_TYPE_OPENROUTER: "https://openrouter.ai/api/v1",
    PROVIDER_TYPE_OPENAI_COMPATIBLE: "",
}

ENTRY_TYPE_PROVIDER = "provider"
ENTRY_TYPE_SCRAPER = "scraper"
EXTRACTION_MODES = {
    "dom": "Text/HTML Based Extraction",
    "browser_based": "Browser Based Extraction",
}
