# AI Web Scraper

A Home Assistant integration that scrapes web pages and uses AI to extract meaningful data from them. Supports **9 AI providers** including OpenAI, DeepSeek, Groq, LocalAI, Ollama, and more. Perfect for monitoring prices, tracking product availability, checking stock status, or any other information you'd normally check manually on a website.

## How it works

```
Website → Browserless renders page (optional) → AI extracts relevant data → Sensor entity
```

Each scraper is configured with a **target URL** and a **prompt** that tells the AI what to extract. The AI returns just the information you asked for — no full page content stored in Home Assistant.

## Quickstart

Get up and running in 3 minutes:

```
1. Install  →  2. Add a Provider  →  3. Add a Scraper
```

### 1. Install via HACS

1. Go to **HACS** → **Integrations** → search for **"AI Web Scraper"**
2. Click **Download this repository with HACS**
3. **Restart Home Assistant**

### 2. Add an AI Provider

1. Go to **Settings** → **Devices & Services** → **Add Integration** → select **AI Web Scraper**
2. Choose **Add AI Provider**
3. Select your provider brand (e.g. **OpenAI**)
4. Fill in:
   - **Provider name** — any label (e.g. `My OpenAI`)
   - **API key** — your API key
   - **Model name** — e.g. `gpt-4o-mini`, `deepseek-chat`, `gemini-2.0-flash`
5. Click **Submit**

### 3. Add a Scraper Entry

1. Go to **Settings** → **Devices & Services** → **Add Integration** → **AI Web Scraper** again
2. Choose **Add Scraper Entry**
3. Fill in:
   - **Scraper name** — any label (e.g. `Product Price`)
   - **URL** — the page to scrape
   - **Prompt** — what to extract (e.g. *"What is the current price?"*)
   - **Provider** — select the provider you just created
4. Click **Submit**

✅ **Done!** A new device appears with your scraped data sensor. Press the **Refresh Scraper** button to trigger an immediate scrape.

> For a visual walkthrough, see the [screenshots](#screenshots) section.

---

## Supported AI Providers

| Provider | Default Endpoint | Requires API Key |
|---|---|---|
| **OpenAI** | `https://api.openai.com/v1` | ✅ |
| **DeepSeek** | `https://api.deepseek.com/v1` | ✅ |
| **Groq** | `https://api.groq.com/openai/v1` | ✅ |
| **LocalAI** | `http://localhost:8080/v1` | ❌ (key not required) |
| **Ollama** | `http://localhost:11434/v1` | ❌ (key not required) |
| **Open WebUI** | *(user configures)* | ✅ |
| **OpenRouter** | `https://openrouter.ai/api/v1` | ✅ |
| **Custom OpenAI Compatible** | *(user configures)* | ✅ |
| **Google Gemini** | *(native API)* | ✅ |

All providers except Gemini use the **OpenAI-compatible chat completions format** — the only difference is the base URL, which is pre-filled with sensible defaults but fully editable.

For self-hosted providers (Ollama, LocalAI), simply change the host in the base URL to point to another machine, e.g. `http://192.168.1.50:11434/v1`.

## Requirements

- **An AI Provider**: API key for your chosen provider (not required for LocalAI or Ollama)
- **Browserless** (optional, but recommended): The [Browserless add-on](https://github.com/home-assistant/addons/tree/master/browserless) for rendered JavaScript pages. Without it, only raw HTML is fetched.

## Detailed Setup

### 1. Install via HACS

1. Go to **HACS > Integrations** and search for "AI Web Scraper"
2. Click **Download**
3. Restart Home Assistant

### 2. Add an AI Provider

1. Go to **Settings > Devices & Services > Add Integration** and select **AI Web Scraper**
2. Choose **Add AI Provider**

**Step 1 — Select brand**: Choose your AI provider from the dropdown (OpenAI, DeepSeek, Groq, LocalAI, Ollama, Open WebUI, OpenRouter, Custom OpenAI Compatible, or Google Gemini).

**Step 2 — Configure credentials**:
   - **Provider name** — any label (e.g. "My OpenAI")
   - **API key** — your API key (not shown for LocalAI/Ollama)
   - **Model name** — e.g. `gpt-4o-mini`, `deepseek-chat`, `llama-3.3-70b`, or `gemini-2.0-flash`
   - **Base URL** — pre-filled with the default for your selected brand. Edit if you use a custom endpoint, proxy, or self-hosted instance on another machine.
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
| `Error fetching information - 503 ...` | AI provider temporarily unavailable |
| `Error fetching information - 429 ...` | AI provider rate limit exceeded — increase the cool-down |
| `Provider response did not contain any choices` | AI provider returned an unexpected response format — check the model name and endpoint |
| `Provider returned an empty completion result` | AI returned nothing — try a different prompt or model |
| `Provider returned HTML instead of extracted text` | AI returned raw HTML — try a more specific prompt |

## Provider cool-down

When multiple scrapers share the same AI provider, a cool-down delay (default 30s) is enforced between consecutive AI calls. This prevents hitting API rate limits. The cool-down resets per-provider whenever any scraper using that provider starts scraping.

## Screenshots

> Screenshots live in `config/ai_web_scraper/screenshots/`. Replace these placeholders with actual PNG captures of your HA instance.

### Add AI Provider — Brand Selection

```ascii
┌──────────────────────────────────────┐
│  Select AI Provider Brand            │
│                                      │
│  ○ OpenAI                            │
│  ○ DeepSeek                          │
│  ○ Groq                              │
│  ○ LocalAI                           │
│  ○ Ollama                            │
│  ○ Open WebUI                        │
│  ○ OpenRouter                        │
│  ○ Custom OpenAI Compatible          │
│  ○ Google Gemini                     │
│                                      │
│        [Back]    [Next]              │
└──────────────────────────────────────┘
```

### Add AI Provider — Credentials

```ascii
┌──────────────────────────────────────┐
│  Configure OpenAI Provider           │
│                                      │
│  Provider name   [ My OpenAI      ]  │
│  API key         [ ************   ]  │
│  Model name      [ gpt-4o-mini    ]  │
│  Base URL        [ https://api.op…]  │
│  Browserless URL [               ]  │
│  Cool-down (s)   [ 30     ]         │
│  Timeout (s)     [ 60     ]         │
│                                      │
│        [Back]    [Submit]            │
└──────────────────────────────────────┘
```

### Add Scraper Entry

```ascii
┌──────────────────────────────────────┐
│  Configure Scraper Entry             │
│                                      │
│  Scraper name    [ Product Price  ]  │
│  URL             [ https://exam…  ]  │
│  Prompt          [ What is the    ]  │
│                  [ current price? ]  │
│  Provider        [ My OpenAI ▼    ]  │
│  Extraction mode [ Text/HTML ▼    ]  │
│  Interval (min)  [ 60            ]  │
│                                      │
│        [Back]    [Submit]            │
└──────────────────────────────────────┘
```

## Notes

- The **Screenshot** entity only appears when a Browserless URL is configured on the provider.
- Set **interval to `0`** if you only want to scrape on-demand via the refresh button.
- Scraper state persists across HA restarts — entities show the last known value until the first background refresh completes.
- Multiple scraper entries can share one AI provider. The global semaphore ensures only one scraper runs at a time to avoid overloading Browserless.
