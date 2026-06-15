# AI Web Scraper

A Home Assistant integration that scrapes web pages and uses AI (OpenAI or Gemini) to extract meaningful data from them. Perfect for monitoring prices, tracking product availability, checking stock status, or any other information you'd normally check manually on a website.

## How it works

```
Website → Browserless renders page (optional) → AI extracts relevant data → Sensor entity
```

Each scraper is configured with a **target URL** and a **prompt** that tells the AI what to extract. The AI returns just the information you asked for — no full page content stored in Home Assistant.

## Requirements

- **AI Provider**: An OpenAI or Gemini API key
- **Browserless** (optional, but recommended): The [Browserless add-on](https://github.com/home-assistant/addons/tree/master/browserless) for rendered JavaScript pages. Without it, only raw HTML is fetched.

## Setup

### 1. Install via HACS

1. Go to **HACS > Integrations** and search for "AI Web Scraper"
2. Click **Download**
3. Restart Home Assistant

### 2. Add an AI Provider

1. Go to **Settings > Devices & Services > Add Integration** and select **AI Web Scraper**
2. Choose **Add AI Provider**
3. Fill in:
   - **Provider name** — any label (e.g. "My OpenAI")
   - **Provider type** — OpenAI or Gemini
   - **API key** — your API key
   - **Model name** — e.g. `gpt-4o-mini` or `gemini-2.0-flash`
   - **Browserless URL** (optional) — the HTTP endpoint of your Browserless instance, e.g. `http://browserless:3000`. Do not use `localhost` unless Browserless runs on the same container/VM. WebSocket URLs (`ws://`) are not supported.
   - **Cool-down seconds** (optional, default: 30) — minimum gap between AI API calls for this provider. Helps avoid rate limits when multiple scrapers share the same provider.

### 3. Add a Scraper Entry

1. **Settings > Devices & Services > Add Integration > AI Web Scraper**
2. Choose **Add Scraper Entry**
3. Fill in:
   - **Scraper name** — any label (e.g. "Product Price")
   - **URL** — the page to scrape
   - **Prompt** — what to extract. Be specific, e.g. "What is the current price of this product?" or "Is this item in stock?" or "What is the delivery estimate?"
   - **Provider** — select the AI provider you created
   - **Extraction mode**:
     - *Text/HTML Based Extraction* — fetches raw HTML. Faster, but may miss JavaScript-rendered content.
     - *Browser Based Extraction* — requires Browserless. Renders the full page including JavaScript.
   - **Interval** — how often to auto-scrape (in minutes). Set to `0` for manual-only refresh.

## Entities

Each scraper entry creates a device with these entities:

| Entity | Description |
|---|---|
| **Scraper Latest Data** | The AI-extracted text from the last successful scrape |
| **Scraper Previous Data** | The value from the scrape before the last (useful for comparisons) |
| **Scraper Phase** | Current stage: `queued` → `cooling_down` → `rendering_page` / `fetching_page` → `waiting_for_ai` → `requesting_ai` → `completed` / `failed - ...` |
| **Last Scrape** | Timestamp of the last scrape attempt |
| **Refresh Scraper** | Button to trigger an immediate scrape |
| **Scrape interval** | Adjustable number entity for the periodic scrape interval (minutes) |
| **Screenshot** | Full-page screenshot (only when Browserless is configured) |

## Phase reference

| Phase | Meaning |
|---|---|
| `queued` | Waiting for other scrapers to finish (global semaphore) |
| `cooling_down` | Waiting for the per-provider cool-down period |
| `rendering_page` | Browserless is rendering the page |
| `fetching_page` | Directly fetching raw HTML (no Browserless) |
| `waiting_for_ai` | Page content ready, screenshot saved (if applicable) |
| `requesting_ai` | AI provider API call in progress — may retry on transient errors |
| `completed` | Scrape succeeded |
| `failed - ...` | Scrape failed — error message appended |

## Error messages

| Error | Likely cause |
|---|---|
| `Timeout error fetching rendered page content` | Browserless took >30s to render the page |
| `Error fetching rendered page content - 503 ...` | Browserless is overloaded or down |
| `Error connecting to the browserless host` | Browserless URL is wrong or unreachable |
| `Error fetching information - 503 ...` | AI provider (OpenAI/Gemini) temporarily unavailable |
| `Error fetching information - 429 ...` | AI provider rate limit exceeded — increase the cool-down |
| `Provider returned an empty completion result` | AI returned nothing — try a different prompt or model |
| `Provider returned HTML instead of extracted text` | AI returned raw HTML — try a more specific prompt |

## Provider cool-down

When multiple scrapers share the same AI provider, a cool-down delay (default 30s) is enforced between consecutive AI calls. This prevents hitting API rate limits. The cool-down resets per-provider whenever any scraper using that provider starts scraping.

## Notes

- The **Screenshot** entity only appears when a Browserless URL is configured on the provider.
- Set **interval to `0`** if you only want to scrape on-demand via the refresh button.
- Scraper state persists across HA restarts — entities show the last known value until the first background refresh completes.
- Multiple scraper entries can share one AI provider. The global semaphore ensures only one scraper runs at a time to avoid overloading Browserless.
