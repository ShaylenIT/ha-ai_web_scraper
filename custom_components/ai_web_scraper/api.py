"""AI Web Scraper API client."""

from __future__ import annotations

import asyncio
import inspect
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse, urlunparse

import aiofiles
import aiohttp
import async_timeout

from . import html2text
from .strikethrough import strikethrough_from_css
from .const import (
    LOGGER,
    PROVIDER_BASE_URLS,
    ProviderType,
    SCRAPER_STATUS_ATTR,
    ScraperPhase,
)

if TYPE_CHECKING:
    from collections.abc import Callable

HTTP_STATUS_NOT_FOUND = 404
MAX_STATE_CHARS = 255
RETRY_HTTP_5XX_LOWER = 500
RETRY_HTTP_5XX_UPPER = 600
RATE_LIMIT_STATUS = 429

# Module-level semaphore that limits concurrent scrape operations across ALL
# scraper instances. Without this, multiple scrapers starting at the same time
# (e.g. on Home Assistant restart) all hit Browserless simultaneously,
# overwhelming its limited Chrome session pool and causing 30-second timeouts.
SCRAPE_CONCURRENCY_SEMAPHORE = asyncio.Semaphore(1)

# Tracks the last API call time per provider entry ID so scrapers sharing
# the same provider can enforce a cool-down between consecutive AI calls.
_last_provider_api_call: dict[str, datetime] = {}


class Provider:
    """Base provider implementation."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        prompt: str,
        request_func: Callable[..., Any],
    ) -> None:
        """Initialize provider."""
        self._api_key = api_key
        self._model_name = model_name
        self._prompt = prompt
        self._request_func = request_func

    async def extract(self, page_text: str) -> str:
        """Extract text from the provided page text (abstract)."""
        raise NotImplementedError

    @staticmethod
    def _looks_like_html(text: str) -> bool:
        """Detect whether a plain string looks like raw HTML."""
        simplified = text.strip().lower()
        return simplified.startswith(("<!doctype html", "<html", "<body")) or (
            "<html" in simplified or "<body" in simplified
        )

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        data: dict | None = None,
    ) -> Any:
        return await self._request_func(
            method=method,
            url=url,
            headers=headers,
            data=data,
        )


class OpenAICompatibleProvider(Provider):
    """
    Provider for any OpenAI-compatible API (configurable base URL).

    Supports: OpenAI, Groq, LocalAI, Ollama (OpenAI-compatible endpoint),
    Open WebUI, OpenRouter, and any custom OpenAI-compatible endpoint.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        prompt: str,
        request_func: Callable[..., Any],
        base_url: str,
    ) -> None:
        """Initialize provider with a configurable base URL."""
        super().__init__(api_key, model_name, prompt, request_func)
        self._base_url = base_url.rstrip("/")

    async def extract(self, page_text: str) -> str:
        """Extract content using an OpenAI-compatible API."""
        url = f"{self._base_url}/chat/completions"
        response = await self._make_request(
            method="post",
            url=url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            data={
                "model": self._model_name,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that extracts relevant "
                            "information from a web page. Return only the requested "
                            "output without additional commentary."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Instructions: {self._prompt}\n\n"
                            f"Web page content:\n{page_text}\n\n"
                            "Only return the requested extracted content. "
                            "Do not return HTML tags or page markup."
                        ),
                    },
                ],
            },
        )

        if isinstance(response, dict):
            choices = response.get("choices", [])
            if not choices:
                msg = "Provider response did not contain any choices."
                raise AiWebScraperClientError(msg)

            choice = choices[0]
            if "message" in choice and isinstance(choice["message"], dict):
                content = choice["message"].get("content", "") or ""
            else:
                content = choice.get("text", "") or ""

            if not content.strip():
                msg = "Provider returned an empty completion result."
                raise AiWebScraperClientError(msg)
            if self._looks_like_html(content):
                msg = "Provider returned HTML instead of extracted text."
                raise AiWebScraperClientError(msg)
            return content.strip()

        extracted = str(response).strip()
        if self._looks_like_html(extracted):
            msg = "Provider returned HTML instead of extracted text."
            raise AiWebScraperClientError(msg)
        if not extracted:
            msg = "Provider returned an empty response."
            raise AiWebScraperClientError(msg)
        return extracted


class GeminiProvider(Provider):
    """Google Gemini provider implementation."""

    async def extract(self, page_text: str) -> str:
        """Extract content using the Google Gemini API."""
        response = await self._make_request(
            method="post",
            url=(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self._model_name}:generateContent?key={self._api_key}"
            ),
            headers={"Content-Type": "application/json"},
            data={
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    f"Instructions: {self._prompt}\n\n"
                                    f"Web page content:\n{page_text}\n\n"
                                    "Only return the requested extracted content. "
                                    "Do not return HTML tags or page markup."
                                )
                            }
                        ],
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 1024,
                    "temperature": 0,
                    "topP": 1,
                },
            },
        )

        if isinstance(response, dict):
            candidates = response.get("candidates", [])
            if not candidates or not isinstance(candidates, list):
                msg = "Provider response did not contain any choices."
                raise AiWebScraperClientError(msg)

            candidate = candidates[0]
            content = candidate.get("content") if isinstance(candidate, dict) else None
            if isinstance(content, dict):
                parts = content.get("parts", [])
                if parts and isinstance(parts[0], dict):
                    content = parts[0].get("text", "")
                else:
                    content = ""

            if not isinstance(content, str):
                content = str(content or "")

            if not content.strip():
                msg = "Provider returned an empty completion result."
                raise AiWebScraperClientError(msg)
            if self._looks_like_html(content):
                msg = "Provider returned HTML instead of extracted text."
                raise AiWebScraperClientError(msg)
            return content.strip()

        extracted = str(response).strip()
        if self._looks_like_html(extracted):
            msg = "Provider returned HTML instead of extracted text."
            raise AiWebScraperClientError(msg)
        if not extracted:
            msg = "Provider returned an empty response."
            raise AiWebScraperClientError(msg)
        return extracted


class AiWebScraperClientError(Exception):
    """Exception to indicate a general API error."""


class AiWebScraperClientCommunicationError(
    AiWebScraperClientError,
):
    """Exception to indicate a communication error."""


class AiWebScraperClientAuthenticationError(
    AiWebScraperClientError,
):
    """Exception to indicate an authentication error."""


async def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise AiWebScraperClientAuthenticationError(msg)

    result = response.raise_for_status()
    if inspect.isawaitable(result):
        await result


class AiWebScraperClient:
    """AI Web Scraper API Client."""

    def __init__(  # noqa: PLR0913
        self,
        provider_name: str,
        api_key: str,
        model_name: str,
        browserless_url: str,
        scraper_name: str,
        url: str,
        prompt: str,
        extraction_mode: str,
        session: aiohttp.ClientSession,
        provider_type: str = ProviderType.OPENAI,
        base_url: str = "",
        request_timeout: int = 30,
        screenshot_dir: str | None = None,
        screenshot_filename: str | None = None,
        markdown_dir: str | None = None,
        markdown_filename: str | None = None,
        *,
        block_consent_modals: bool = True,
        save_markdown_debug: bool = False,
        status_callback: Callable[[str], None] | None = None,
        provider_id: str = "",
        cooldown_seconds: int = 0,
    ) -> None:
        """Initialize the scraper client."""
        self._provider_name = provider_name
        self._api_key = api_key
        self._model_name = model_name
        self._browserless_url = browserless_url
        self._provider_type = provider_type
        self._base_url = base_url
        self._scraper_name = scraper_name
        self._url = url
        self._prompt = prompt
        self._extraction_mode = extraction_mode
        self._session = session
        self._missing_provider = not bool(self._provider_name and self._api_key)
        self._scraper_status = ScraperPhase.IDLE
        self._screenshot_dir = screenshot_dir
        self._screenshot_filename = screenshot_filename
        self._markdown_dir = markdown_dir
        self._markdown_filename = markdown_filename
        self._save_markdown_debug = save_markdown_debug
        self._block_consent_modals = block_consent_modals
        self._status_callback = status_callback
        self._provider_id = provider_id
        self._cooldown_seconds = cooldown_seconds
        self._request_timeout = request_timeout or 30

    def set_status_callback(self, callback: Callable[[str], None] | None) -> None:
        """Set or clear the live status update callback."""
        self._status_callback = callback

    def _set_scraper_status(self, status: str) -> None:
        """Update the current scraper status and notify the coordinator."""
        self._scraper_status = status
        if self._status_callback:
            self._status_callback(status)

    async def async_get_data(self) -> dict[str, Any]:
        """
        Get scraped data from the configured provider or the target URL.

        This integration persists screenshots for the configured scraper entry
        under the Home Assistant config directory so they remain available
        across restarts.
        """
        # Show queued status immediately so the phase sensor updates
        # even when we're waiting behind other scrapers at the semaphore.
        self._set_scraper_status(ScraperPhase.QUEUED)
        async with SCRAPE_CONCURRENCY_SEMAPHORE:
            return await self._do_scrape()

        # unreachable

    async def _do_scrape(self) -> dict[str, Any]:
        """Execute the actual scrape — always called under the concurrency semaphore."""
        if self._missing_provider:
            msg = (
                "Missing provider configuration. "
                "Please verify the selected Provider profile."
            )
            raise AiWebScraperClientError(msg)

        start = datetime.now(tz=UTC)

        # Per-provider cool-down: wait before the Browserless / AI
        # pipeline so the total gap between consecutive scrapes using
        # the same provider accounts for both rendering and extraction.
        if self._provider_id and self._cooldown_seconds > 0:
            last_call = _last_provider_api_call.get(self._provider_id)
            if last_call is not None:
                elapsed = (datetime.now(tz=UTC) - last_call).total_seconds()
                remaining = self._cooldown_seconds - elapsed
                if remaining > 0:
                    self._set_scraper_status(ScraperPhase.COOLING_DOWN)
                    await asyncio.sleep(remaining)
            _last_provider_api_call[self._provider_id] = datetime.now(tz=UTC)

        if self._browserless_url and self._extraction_mode == "browser_based":
            self._set_scraper_status(ScraperPhase.RENDERING_PAGE)
        else:
            self._set_scraper_status(ScraperPhase.FETCHING_PAGE)

        page_text = await self._get_page_text(self._url)
        page_text = self._normalize_page_text(page_text)
        self._set_scraper_status(ScraperPhase.WAITING_FOR_AI)
        screenshot = None
        if self._browserless_url and self._extraction_mode == "browser_based":
            try:
                screenshot = await self._fetch_browserless_page_screenshot(self._url)
            except AiWebScraperClientCommunicationError as exception:
                LOGGER.warning(
                    "Screenshot capture failed for %s: %s",
                    self._url,
                    exception,
                )

        # Save screenshot BEFORE the AI call so it persists even if the
        # provider rate-limits or errors out.
        screenshot_path = None
        if screenshot is not None and self._screenshot_dir:
            screenshot_path = await self._save_screenshot(screenshot)

        # Save debug Markdown alongside screenshots for inspection.
        # Only active when save_markdown_debug=True — no config flow toggle.
        if self._save_markdown_debug and self._markdown_dir and self._markdown_filename:
            await self._save_debug_markdown(page_text)

        self._set_scraper_status(ScraperPhase.REQUESTING_AI)
        state = await self._provider_extract(page_text)
        duration = (datetime.now(tz=UTC) - start).total_seconds()
        now = datetime.now(tz=UTC).isoformat()

        attributes = {
            "url": self._url,
            "prompt": self._prompt,
            "provider_name": self._provider_name,
            "extraction_mode": self._extraction_mode,
            "scrape_duration_seconds": duration,
            "last_successful_scrape": now,
            "last_scrape": now,
            SCRAPER_STATUS_ATTR: self._scraper_status,
        }

        if screenshot_path:
            attributes["screenshot_path"] = screenshot_path

        if isinstance(state, str) and len(state) > MAX_STATE_CHARS:
            attributes["full_text"] = state
            state = state[: MAX_STATE_CHARS - 3] + "..."

        self._set_scraper_status(ScraperPhase.COMPLETED)
        attributes[SCRAPER_STATUS_ATTR] = self._scraper_status

        return {
            "state": state,
            "attributes": attributes,
            "error_message": "",
            "last_attempt_status": "success",
        }

    async def _get_page_text(self, url: str) -> str:
        """
        Fetch page text from the target URL or browserless endpoint.

        Uses Browserless only when both a browserless_url is configured
        AND the extraction mode is set to "browser_based". If the scraper
        uses "dom" mode, the URL is fetched directly regardless of any
        Browserless config on the provider.
        """
        if self._browserless_url and self._extraction_mode == "browser_based":
            return await self._fetch_browserless_page_text(url)
        return await self._fetch_page_text(url)

    async def _fetch_page_text(self, url: str) -> str:
        """Fetch a page and return its text content."""
        for attempt in range(2):
            try:
                async with async_timeout.timeout(10):
                    response = await self._session.get(
                        url,
                        headers={
                            "Accept": "text/html",
                            "User-Agent": "Mozilla/5.0 (HomeAssistant) ai_web_scraper",
                        },
                    )
                    await _verify_response_or_raise(response)
                    return await response.text()
            except aiohttp.ServerDisconnectedError as exception:
                if attempt == 0:
                    await asyncio.sleep(1)
                    continue
                msg = f"Error fetching page content - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception
            except TimeoutError as exception:
                msg = f"Timeout error fetching page content - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception
            except (aiohttp.ClientError, socket.gaierror) as exception:
                msg = f"Error fetching page content - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception
            except asyncio.CancelledError:
                raise
            except Exception as exception:  # pylint: disable=broad-except
                msg = f"Something really wrong happened! - {exception}"
                raise AiWebScraperClientError(msg) from exception

        msg = "Unable to fetch page content"
        raise AiWebScraperClientError(msg)

    # JS injected via addScriptTag when overlay blocking is enabled (Option 1).
    # Sweeps all elements after page load and removes any that are position:fixed
    # or position:sticky with z-index > 99. Also unlocks scroll on <body>/<html>.
    # Safe structural tags (HEADER, NAV, FOOTER, etc.) are excluded.
    # See overlay-block-spec.md for the full option comparison.
    _OVERLAY_BLOCK_SCRIPT = (
        "(function(){"
        "document.body.style.overflow='';"
        "document.documentElement.style.overflow='';"
        "var SAFE=new Set(['HEADER','NAV','FOOTER','SCRIPT','STYLE','LINK']);"
        "var VW=window.innerWidth,VH=window.innerHeight;"
        "document.querySelectorAll('*').forEach(function(el){"
        "if(SAFE.has(el.tagName))return;"
        "var s=window.getComputedStyle(el);"
        "if(s.position!=='fixed'&&s.position!=='sticky')return;"
        "var z=parseInt(s.zIndex,10);"
        "if(!isNaN(z)&&z>99){el.remove();return;}"
        "if(s.zIndex==='auto'){"
        "var r=el.getBoundingClientRect();"
        "var pctH=r.height/VH;"
        "if(r.top>=VH*0.5){el.remove();return;}"
        "if(r.width>=VW*0.9&&r.height>=VH*0.9&&el.children.length>3){return;}"
        "el.remove();"
        "}"
        "});"
        "})();"
    )

    # JS injected to mark strikethrough text with ~~syntax~~.
    # Uses window.getComputedStyle() after full page render so Browserless
    # computes all CSS (both inline and stylesheet rules). This catches
    # strikethroughs from CSS classes like .product-price span
    # { text-decoration: line-through; } that regex-only approaches miss.
    # The ~~ markers pass through html2text naturally.
    _STRIKETHROUGH_SCRIPT = (
        "(function(){"
        "var els=document.querySelectorAll('del,s,strike,span,ins,u,p,a,li,td,th,div,strong,em');"
        "els.forEach(function(el){"
        "var s=window.getComputedStyle(el);"
        "if(s.textDecoration.includes('line-through')||s.textDecorationLine==='line-through'){"
        "el.textContent='~~'+el.textContent+'~~';"
        "}"
        "});"
        "})();"
    )

    async def _fetch_browserless_page_text(self, url: str) -> str:
        """
        Fetch rendered page content via browserless.

        The Browserless /content endpoint is asked to wait for the page to settle
        by using gotoOptions.waitUntil=networkidle2 and bestAttempt=True.

        When block_consent_modals is enabled, a self-contained JS snippet is
        injected via addScriptTag (Option 1 from overlay-block-spec.md). It sweeps
        the DOM for fixed/sticky high-z-index elements and removes them, covering
        cookie banners, newsletter popups, login walls, and any other viewport-
        blocking overlay — without requiring a maintained selector list.

        Note: blockConsentModals is a cloud/enterprise-only Browserless feature
        that causes 400 Bad Request on self-hosted instances and is not used.
        """
        browserless_url = self._normalize_browserless_url(self._browserless_url)
        parsed_url = urlparse(browserless_url)

        payload: dict[str, Any] = {
            "url": url,
            "gotoOptions": {
                "waitUntil": "networkidle2",
                "timeout": 30000,
            },
            "bestAttempt": True,
        }

        if self._block_consent_modals:
            payload["addScriptTag"] = [
                {"content": self._OVERLAY_BLOCK_SCRIPT},
                {"content": self._STRIKETHROUGH_SCRIPT},
            ]
            LOGGER.debug(
                "Overlay blocking enabled for %s — injecting z-index sweep + strikethrough scripts.",
                url,
            )
        else:
            payload["addScriptTag"] = [
                {"content": self._STRIKETHROUGH_SCRIPT},
            ]
            LOGGER.debug(
                "Injecting strikethrough marker script for %s.",
                url,
            )

        for attempt in range(2):
            try:
                async with async_timeout.timeout(30):
                    response = await self._session.post(
                        urlunparse(parsed_url),
                        json=payload,
                        headers={
                            "Accept": "text/html",
                            "User-Agent": "Mozilla/5.0 (HomeAssistant) ai_web_scraper",
                        },
                    )
                    await _verify_response_or_raise(response)
                    return await response.text()
            except aiohttp.ServerDisconnectedError as exception:
                if attempt == 0:
                    await asyncio.sleep(1)
                    continue
                msg = f"Error fetching rendered page content - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception
            except TimeoutError as exception:
                msg = f"Timeout error fetching rendered page content - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception
            except aiohttp.ClientResponseError as exception:
                if exception.status == HTTP_STATUS_NOT_FOUND:
                    msg = (
                        "Browserless content endpoint returned 404 Not Found. "
                        "Verify your browserless_url and ensure the service "
                        "path is /content. If you are using the Home Assistant "
                        "browserless add-on, use the add-on host instead of "
                        "localhost (for example http://browserless:3000)."
                    )
                else:
                    msg = (
                        "Error fetching rendered page content - "
                        f"{exception.status} {exception.message}"
                    )
                raise AiWebScraperClientCommunicationError(msg) from exception
            except aiohttp.ClientConnectorError as exception:
                if isinstance(exception.os_error, socket.gaierror):
                    msg = (
                        "DNS lookup failed for the browserless host. "
                        "Verify your browserless_url host is resolvable "
                        "from Home Assistant."
                    )
                else:
                    msg = (
                        "Error connecting to the browserless host. "
                        "Verify your browserless_url is correct and reachable "
                        "from Home Assistant."
                    )
                raise AiWebScraperClientCommunicationError(msg) from exception
            except (aiohttp.ClientError, socket.gaierror) as exception:
                msg = f"Error fetching rendered page content - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception
            except asyncio.CancelledError:
                raise
            except Exception as exception:  # pylint: disable=broad-except
                msg = f"Something really wrong happened! - {exception}"
                raise AiWebScraperClientError(msg) from exception

        msg = "Unable to fetch rendered page content"
        raise AiWebScraperClientError(msg)

    async def _fetch_browserless_page_screenshot(self, url: str) -> bytes:
        """
        Capture a full-page screenshot via browserless.

        The Browserless /screenshot endpoint is asked to wait for the page to
        settle by using gotoOptions.waitUntil=networkidle2 and fullPage=True.

        When block_consent_modals is enabled, the same self-contained JS snippet
        used for page-text fetching is injected via addScriptTag. This removes
        fixed/sticky high-z-index overlays before the screenshot is taken.

        Note: blockConsentModals is a cloud/enterprise-only Browserless feature
        that causes 400 Bad Request on self-hosted instances and is not used.
        """
        browserless_url = self._normalize_browserless_url(self._browserless_url)
        parsed_url = urlparse(browserless_url)
        parsed_url = parsed_url._replace(path="/screenshot")

        payload: dict[str, Any] = {
            "url": url,
            "gotoOptions": {
                "waitUntil": "networkidle2",
                "timeout": 30000,
            },
            "options": {
                "fullPage": True,
                "type": "png",
            },
        }

        if self._block_consent_modals:
            payload["addScriptTag"] = [{"content": self._OVERLAY_BLOCK_SCRIPT}]
            LOGGER.debug(
                "Overlay blocking enabled for %s — injecting z-index sweep script (screenshot).",
                url,
            )

        for attempt in range(2):
            try:
                async with async_timeout.timeout(30):
                    response = await self._session.post(
                        urlunparse(parsed_url),
                        json=payload,
                        headers={
                            "Accept": "image/png",
                            "User-Agent": "Mozilla/5.0 (HomeAssistant) ai_web_scraper",
                        },
                    )
                    LOGGER.debug(
                        "Browserless screenshot attempt %d for %s returned status %d",
                        attempt + 1,
                        url,
                        response.status,
                    )
                    await _verify_response_or_raise(response)
                    return await response.read()
            except aiohttp.ClientResponseError as exception:
                LOGGER.debug(
                    "Browserless screenshot attempt %d for %s failed with status %d: %s",
                    attempt + 1,
                    url,
                    exception.status,
                    exception.message,
                )
                if exception.status == HTTP_STATUS_NOT_FOUND:
                    msg = (
                        "Browserless screenshot endpoint returned 404 Not Found. "
                        "Verify your browserless_url and ensure the service "
                        "path is /screenshot. If you are using the Home Assistant "
                        "browserless add-on, use the add-on host instead of "
                        "localhost (for example http://browserless:3000)."
                    )
                    raise AiWebScraperClientCommunicationError(msg) from exception
                if (
                    attempt == 0
                    and RETRY_HTTP_5XX_LOWER <= exception.status < RETRY_HTTP_5XX_UPPER
                ):
                    await asyncio.sleep(3)
                    continue
                msg = (
                    "Error fetching rendered page screenshot - "
                    f"{exception.status} {exception.message}"
                )
                raise AiWebScraperClientCommunicationError(msg) from exception
            except aiohttp.ServerDisconnectedError as exception:
                if attempt == 0:
                    await asyncio.sleep(1)
                    continue
                msg = f"Error fetching rendered page screenshot - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception
            except TimeoutError as exception:
                msg = f"Timeout error fetching rendered page screenshot - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception
            except aiohttp.ClientConnectorError as exception:
                if isinstance(exception.os_error, socket.gaierror):
                    msg = (
                        "DNS lookup failed for the browserless host. "
                        "Verify your browserless_url host is resolvable "
                        "from Home Assistant."
                    )
                else:
                    msg = (
                        "Error connecting to the browserless host. "
                        "Verify your browserless_url is correct and reachable "
                        "from Home Assistant."
                    )
                raise AiWebScraperClientCommunicationError(msg) from exception
            except (aiohttp.ClientError, socket.gaierror) as exception:
                msg = f"Error fetching rendered page screenshot - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception
            except asyncio.CancelledError:
                raise
            except Exception as exception:  # pylint: disable=broad-except
                msg = f"Something really wrong happened! - {exception}"
                raise AiWebScraperClientError(msg) from exception

        msg = "Unable to fetch rendered page screenshot"
        raise AiWebScraperClientError(msg)

    async def _save_screenshot(self, screenshot: bytes) -> str:
        if not self._screenshot_dir or not self._screenshot_filename:
            msg = "Screenshot storage location is not configured."
            raise AiWebScraperClientError(msg)

        screenshot_path = Path(self._screenshot_dir) / self._screenshot_filename
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(screenshot_path, "wb") as f:
            await f.write(screenshot)
        return str(screenshot_path)

    async def _save_debug_markdown(self, markdown_text: str) -> None:
        """
        Save normalized Markdown to disk for debugging.

        Writes the normalized Markdown (before AI extraction) to the
        configured markdown directory for visual inspection.
        """
        if not self._markdown_dir or not self._markdown_filename:
            return

        md_path = Path(self._markdown_dir) / self._markdown_filename
        md_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
            await f.write(markdown_text)
        LOGGER.debug("Saved debug Markdown to %s", md_path)

    def _get_provider(self) -> Provider:
        if self._provider_type == ProviderType.GEMINI:
            return GeminiProvider(
                api_key=self._api_key,
                model_name=self._model_name,
                prompt=self._prompt,
                request_func=self._api_wrapper,
            )
        # All OpenAI-compatible providers use the same class with a configurable base URL
        resolved_base_url = self._base_url or PROVIDER_BASE_URLS.get(
            self._provider_type, "https://api.openai.com/v1"
        )
        return OpenAICompatibleProvider(
            api_key=self._api_key,
            model_name=self._model_name,
            prompt=self._prompt,
            request_func=self._api_wrapper,
            base_url=resolved_base_url,
        )

    async def _provider_extract(self, page_text: str) -> str:
        """Extract the prompt result from the provided page text."""
        provider = self._get_provider()
        return await provider.extract(page_text)

    def _normalize_page_text(self, page_text: str) -> str:
        """
        Normalize page text before sending it to the AI provider.

        Converts HTML to Markdown to preserve structural information
        (headings, links, lists, bold, italic, tables) that helps AI
        models better understand the page layout.

        When Browserless is configured, ~~strikethrough~~ Markdown markers
        are injected into elements with CSS-computed line-through styling
        (via `_STRIKETHROUGH_SCRIPT`) so the output preserves which text
        was struck through — something regex-only approaches miss because
        they don't interpret CSS.

        When using DOM mode (direct HTTP fetch), CSS rules from <style>
        blocks are parsed to apply the same strikethrough treatment
        via `_strikethrough_from_css`.
        """
        if not isinstance(page_text, str):
            return ""

        # Inject ~~ markers from CSS line-through rules (DOM mode)
        page_text = strikethrough_from_css(page_text)

        # Clean up empty ~~ markers left by injected Browserless script
        page_text = page_text.replace("~~~~", "")

        # Convert HTML to Markdown for richer structural output
        converter = html2text.HTML2Text()
        converter.body_width = 0  # Don't wrap lines
        converter.ignore_links = False
        converter.ignore_images = True
        converter.ignore_emphasis = False
        converter.ignore_tables = False
        converter.protect_links = True
        converter.unicode_snob = True
        converter.skip_internal_links = True
        text = converter.handle(page_text)

        return text.strip()

    def _normalize_browserless_url(self, browserless_url: str) -> str:
        """Normalize the browserless addon URL for fetching rendered content.

        Query parameters are stripped because Browserless configuration
        (blockConsentModals, etc.) is passed via the JSON payload body,
        not URL query strings. Legacy URLs with ?blockConsentModals=true
        in particular cause 400 Bad Request on self-hosted instances since
        that is a cloud/enterprise-only feature.
        """
        parsed_url = urlparse(browserless_url)
        if parsed_url.scheme in ("ws", "wss"):
            msg = (
                "WebSocket browserless URLs are not supported by this integration. "
                "Use the HTTP browserless addon endpoint instead."
            )
            raise AiWebScraperClientError(msg)

        path = parsed_url.path or ""
        if path.endswith("/") and path != "/":
            path = path.rstrip("/")
        if path in (None, "", "/"):
            path = "/content"
        parsed_url = parsed_url._replace(path=path, query="")
        return urlunparse(parsed_url)

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Make a request to the remote API."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                async with async_timeout.timeout(self._request_timeout):
                    response = await self._session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data,
                    )
                    await _verify_response_or_raise(response)
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        return await response.json()
                    try:
                        return await response.json()
                    except (aiohttp.ContentTypeError, ValueError):
                        return await response.text()

            except TimeoutError as exception:
                msg = f"Timeout error fetching information - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception

            except aiohttp.ClientResponseError as exception:
                if (
                    attempt < max_attempts - 1
                    and RETRY_HTTP_5XX_LOWER <= exception.status < RETRY_HTTP_5XX_UPPER
                ):
                    backoff = 5 * (attempt + 1)
                    await asyncio.sleep(backoff)
                    continue

                if exception.status == HTTP_STATUS_NOT_FOUND:
                    msg = (
                        "Browserless API returned 404 Not Found. "
                        "Check your configured browserless_url and the service path."
                    )
                elif exception.status == RATE_LIMIT_STATUS:
                    msg = (
                        "Provider rate limit exceeded (429 Too Many Requests). "
                        "Reduce scrape frequency, check provider quota, or "
                        "use a different API key."
                    )
                else:
                    msg = (
                        "Error fetching information - "
                        f"{exception.status} {exception.message}"
                    )

                raise AiWebScraperClientCommunicationError(msg) from exception

            except (aiohttp.ClientError, socket.gaierror) as exception:
                msg = f"Error fetching information - {exception}"
                raise AiWebScraperClientCommunicationError(msg) from exception

            except asyncio.CancelledError:
                raise
            except Exception as exception:  # pylint: disable=broad-except
                msg = f"Something really wrong happened! - {exception}"
                raise AiWebScraperClientError(msg) from exception

        msg = "Error fetching information - retries exhausted"
        raise AiWebScraperClientCommunicationError(msg)
