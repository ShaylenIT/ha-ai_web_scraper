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

PROVIDER_TYPE_OPENAI = "openai"
PROVIDER_TYPE_GEMINI = "gemini"
PROVIDER_TYPES = {
    PROVIDER_TYPE_OPENAI: "OpenAI",
    PROVIDER_TYPE_GEMINI: "Gemini",
}

ENTRY_TYPE_PROVIDER = "provider"
ENTRY_TYPE_SCRAPER = "scraper"
EXTRACTION_MODES = {
    "dom": "Text/HTML Based Extraction",
    "browser_based": "Browser Based Extraction",
}
