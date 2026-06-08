"""AI Web Scraper API client."""

from __future__ import annotations

import asyncio
import html
import inspect
import re
import socket
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import aiohttp
import async_timeout

from .const import PROVIDER_TYPE_GEMINI, PROVIDER_TYPE_OPENAI

HTTP_STATUS_NOT_FOUND = 404


class Provider:
    """Base provider implementation."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        prompt: str,
        request_func,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._prompt = prompt
        self._request_func = request_func

    async def extract(self, page_text: str) -> str:
        raise NotImplementedError

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


class OpenAIProvider(Provider):
    """OpenAI provider implementation."""

    async def extract(self, page_text: str) -> str:
        response = await self._make_request(
            method="post",
            url="https://api.openai.com/v1/chat/completions",
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
                            "You are a helpful assistant that extracts relevant information "
                            "from a web page based on the user prompt. Return only the "
                            "requested output without additional commentary."
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
                raise IntegrationBlueprintApiClientError(
                    "Provider response did not contain any choices."
                )

            choice = choices[0]
            if "message" in choice and isinstance(choice["message"], dict):
                content = choice["message"].get("content", "") or ""
            else:
                content = choice.get("text", "") or ""

            if not content.strip():
                raise IntegrationBlueprintApiClientError(
                    "Provider returned an empty completion result."
                )
            if self._looks_like_html(content):
                raise IntegrationBlueprintApiClientError(
                    "Provider returned HTML instead of extracted text."
                )
            return content.strip()

        extracted = str(response).strip()
        if self._looks_like_html(extracted):
            raise IntegrationBlueprintApiClientError(
                "Provider returned HTML instead of extracted text."
            )
        if not extracted:
            raise IntegrationBlueprintApiClientError(
                "Provider returned an empty response."
            )
        return extracted

    def _looks_like_html(self, text: str) -> bool:
        simplified = text.strip().lower()
        return (
            simplified.startswith("<!doctype html")
            or simplified.startswith("<html")
            or simplified.startswith("<body")
            or "<html" in simplified
            or "<body" in simplified
        )


class GeminiProvider(Provider):
    """Google Gemini provider implementation."""

    async def extract(self, page_text: str) -> str:
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
                raise IntegrationBlueprintApiClientError(
                    "Provider response did not contain any choices."
                )

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
                raise IntegrationBlueprintApiClientError(
                    "Provider returned an empty completion result."
                )
            if self._looks_like_html(content):
                raise IntegrationBlueprintApiClientError(
                    "Provider returned HTML instead of extracted text."
                )
            return content.strip()

        extracted = str(response).strip()
        if self._looks_like_html(extracted):
            raise IntegrationBlueprintApiClientError(
                "Provider returned HTML instead of extracted text."
            )
        if not extracted:
            raise IntegrationBlueprintApiClientError(
                "Provider returned an empty response."
            )
        return extracted

    def _looks_like_html(self, text: str) -> bool:
        simplified = text.strip().lower()
        return (
            simplified.startswith("<!doctype html")
            or simplified.startswith("<html")
            or simplified.startswith("<body")
            or "<html" in simplified
            or "<body" in simplified
        )


class IntegrationBlueprintApiClientError(Exception):
    """Exception to indicate a general API error."""


class IntegrationBlueprintApiClientCommunicationError(
    IntegrationBlueprintApiClientError,
):
    """Exception to indicate a communication error."""


class IntegrationBlueprintApiClientAuthenticationError(
    IntegrationBlueprintApiClientError,
):
    """Exception to indicate an authentication error."""


async def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise IntegrationBlueprintApiClientAuthenticationError(msg)

    result = response.raise_for_status()
    if inspect.isawaitable(result):
        await result


class IntegrationBlueprintApiClient:
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
        provider_type: str = PROVIDER_TYPE_OPENAI,
    ) -> None:
        """Initialize the scraper client."""
        self._provider_name = provider_name
        self._api_key = api_key
        self._model_name = model_name
        self._browserless_url = browserless_url
        self._provider_type = provider_type
        self._scraper_name = scraper_name
        self._url = url
        self._prompt = prompt
        self._extraction_mode = extraction_mode
        self._session = session
        self._missing_provider = not bool(self._provider_name and self._api_key)
        self._scraper_status = "idle"

    def _set_scraper_status(self, status: str) -> None:
        """Update the current scraper status."""
        self._scraper_status = status

    async def async_get_data(self) -> dict[str, Any]:
        """
        Get scraped data from the configured provider or the target URL.

        This integration processes scraped content entirely in memory. No page
        HTML, screenshot, or temporary artifacts are persisted to disk.
        """
        if self._missing_provider:
            msg = (
                "Missing provider configuration. "
                "Please verify the selected Provider profile."
            )
            raise IntegrationBlueprintApiClientError(msg)

        start = datetime.now(tz=UTC)
        if self._browserless_url:
            self._set_scraper_status("rendering_page")
        else:
            self._set_scraper_status("fetching_page")

        page_text = await self._get_page_text(self._url)
        page_text = self._normalize_page_text(page_text)
        self._set_scraper_status("waiting_for_ai")
        state = await self._provider_extract(page_text)
        self._set_scraper_status("processing_ai_response")
        duration = (datetime.now(tz=UTC) - start).total_seconds()

        attributes = {
            "url": self._url,
            "prompt": self._prompt,
            "provider_name": self._provider_name,
            "extraction_mode": self._extraction_mode,
            "scrape_duration_seconds": duration,
            "last_successful_scrape": datetime.now(tz=UTC).isoformat(),
            "scraper_status": self._scraper_status,
        }

        if isinstance(state, str) and len(state) > 255:
            attributes["full_text"] = state
            state = state[:252] + "..."

        self._set_scraper_status("completed")
        attributes["scraper_status"] = self._scraper_status

        return {
            "state": state,
            "attributes": attributes,
            "error_message": "",
            "last_attempt_status": "success",
        }

    async def _get_page_text(self, url: str) -> str:
        """Fetch page text from the target URL or browserless endpoint."""
        if self._browserless_url:
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
                raise IntegrationBlueprintApiClientCommunicationError(
                    f"Error fetching page content - {exception}"
                ) from exception
            except TimeoutError as exception:
                raise IntegrationBlueprintApiClientCommunicationError(
                    f"Timeout error fetching page content - {exception}"
                ) from exception
            except (aiohttp.ClientError, socket.gaierror) as exception:
                raise IntegrationBlueprintApiClientCommunicationError(
                    f"Error fetching page content - {exception}"
                ) from exception
            except Exception as exception:  # pylint: disable=broad-except
                raise IntegrationBlueprintApiClientError(
                    f"Something really wrong happened! - {exception}"
                ) from exception

        raise IntegrationBlueprintApiClientError("Unable to fetch page content")

    async def _fetch_browserless_page_text(self, url: str) -> str:
        """Fetch rendered page content via browserless.

        The Browserless /content endpoint is asked to wait for the page to settle
        by using gotoOptions.waitUntil=networkidle2 and bestAttempt=True.
        """
        browserless_url = self._normalize_browserless_url(self._browserless_url)
        parsed_url = urlparse(browserless_url)
        parsed_url = parsed_url._replace(query=urlencode(parse_qs(parsed_url.query), doseq=True))

        payload = {
            "url": url,
            "gotoOptions": {
                "waitUntil": "networkidle2",
                "timeout": 30000,
            },
            "bestAttempt": True,
        }

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
                raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
            except TimeoutError as exception:
                msg = f"Timeout error fetching rendered page content - {exception}"
                raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
            except aiohttp.ClientResponseError as exception:
                if exception.status == HTTP_STATUS_NOT_FOUND:
                    msg = (
                        "Browserless content endpoint returned 404 Not Found. "
                        "Verify your browserless_url and ensure the service path is /content. "
                        "If you are using the Home Assistant browserless add-on, use the add-on host "
                        "instead of localhost (for example http://browserless:3000)."
                    )
                else:
                    msg = (
                        "Error fetching rendered page content - "
                        f"{exception.status} {exception.message}"
                    )
                raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
            except aiohttp.ClientConnectorError as exception:
                if isinstance(exception.os_error, socket.gaierror):
                    msg = (
                        "DNS lookup failed for the browserless host. "
                        "Verify your browserless_url host is resolvable from Home Assistant."
                    )
                else:
                    msg = (
                        "Error connecting to the browserless host. "
                        "Verify your browserless_url is correct and reachable from Home Assistant."
                    )
                raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
            except (aiohttp.ClientError, socket.gaierror) as exception:
                msg = f"Error fetching rendered page content - {exception}"
                raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
            except Exception as exception:  # pylint: disable=broad-except
                msg = f"Something really wrong happened! - {exception}"
                raise IntegrationBlueprintApiClientError(msg) from exception

        raise IntegrationBlueprintApiClientError("Unable to fetch rendered page content")

    def _get_provider(self) -> Provider:
        if self._provider_type == PROVIDER_TYPE_GEMINI:
            return GeminiProvider(
                api_key=self._api_key,
                model_name=self._model_name,
                prompt=self._prompt,
                request_func=self._api_wrapper,
            )
        return OpenAIProvider(
            api_key=self._api_key,
            model_name=self._model_name,
            prompt=self._prompt,
            request_func=self._api_wrapper,
        )

    async def _provider_extract(self, page_text: str) -> str:
        """Use the configured provider to extract the prompt result from the page text."""
        provider = self._get_provider()
        return await provider.extract(page_text)

    def _looks_like_html(self, text: str) -> bool:
        """Detect whether a plain string looks like raw HTML."""
        simplified = text.strip().lower()
        return (
            simplified.startswith("<!doctype html")
            or simplified.startswith("<html")
            or simplified.startswith("<body")
            or "<html" in simplified
            or "<body" in simplified
        )

    def _normalize_page_text(self, page_text: str) -> str:
        """Normalize page text before sending it to the AI provider."""
        if not isinstance(page_text, str):
            return ""

        text = re.sub(r"(?is)<script.*?>.*?</script>", " ", page_text)
        text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        return " ".join(text.split())

    def _normalize_browserless_url(self, browserless_url: str) -> str:
        """Normalize the browserless addon URL for fetching rendered content."""
        parsed_url = urlparse(browserless_url)
        if parsed_url.scheme in ("ws", "wss"):
            raise IntegrationBlueprintApiClientError(
                "WebSocket browserless URLs are not supported by this integration. "
                "Use the HTTP browserless addon endpoint instead."
            )

        path = parsed_url.path or ""
        if path.endswith("/") and path != "/":
            path = path.rstrip("/")
        if path in (None, "", "/"):
            path = "/content"
        parsed_url = parsed_url._replace(path=path)
        return urlunparse(parsed_url)

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Make a request to the remote API."""
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                async with async_timeout.timeout(10):
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
                raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
            except aiohttp.ClientResponseError as exception:
                if (
                    attempt < max_attempts - 1
                    and 500 <= exception.status < 600
                ):
                    await asyncio.sleep(5)
                    continue
                if exception.status == HTTP_STATUS_NOT_FOUND:
                    msg = (
                        "Browserless API returned 404 Not Found. "
                        "Check your configured browserless_url and the service path."
                    )
                elif exception.status == 429:
                    msg = (
                        "Provider rate limit exceeded (429 Too Many Requests). "
                        "Reduce scrape frequency, check provider quota, or use a different API key."
                    )
                else:
                    msg = (
                        "Error fetching information - "
                        f"{exception.status} {exception.message}"
                    )
                raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
            except (aiohttp.ClientError, socket.gaierror) as exception:
                msg = f"Error fetching information - {exception}"
                raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
            except Exception as exception:  # pylint: disable=broad-except
                msg = f"Something really wrong happened! - {exception}"
                raise IntegrationBlueprintApiClientError(msg) from exception

        raise IntegrationBlueprintApiClientCommunicationError(
            "Error fetching information - retries exhausted"
        )
