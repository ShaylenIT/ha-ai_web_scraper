"""Constants for ai_web_scraper."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "ai_web_scraper"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

# Provider constants
CONF_PROVIDER = "provider"
CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
PROVIDERS = {
	"openai": {
		"name": "OpenAI",
		"fields": ["api_key"],
	},
	"anthropic": {
		"name": "Anthropic",
		"fields": ["api_key"],
	},
	"ollama": {
		"name": "Ollama",
		"fields": ["base_url"],
	},
}
