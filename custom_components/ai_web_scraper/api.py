"""AI Web Scraper API client."""

from __future__ import annotations

import asyncio
import inspect
import socket
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse, urlunparse

import aiohttp
import async_timeout

HTTP_STATUS_NOT_FOUND = 404


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
    ) -> None:
        """Initialize the scraper client."""
        self._provider_name = provider_name
        self._api_key = api_key
        self._model_name = model_name
        self._browserless_url = browserless_url
        self._scraper_name = scraper_name
        self._url = url
        self._prompt = prompt
        self._extraction_mode = extraction_mode
        self._session = session
        self._missing_provider = not bool(self._provider_name and self._api_key)

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
            browserless_url = self._normalize_browserless_url(self._browserless_url)
            raw = await self._api_wrapper(
                method="post",
                url=browserless_url,
                headers={"Content-Type": "application/json"},
                data={"url": self._url},
            )
            if isinstance(raw, str):
                state = raw
            else:
                state = raw.get(
                    "text",
                    raw.get("body", raw.get("result", raw.get("data", ""))),
                )
        else:
            state = await self._fetch_page_text(self._url)
        duration = (datetime.now(tz=UTC) - start).total_seconds()

        attributes = {
            "url": self._url,
            "prompt": self._prompt,
            "provider_name": self._provider_name,
            "extraction_mode": self._extraction_mode,
            "scrape_duration_seconds": duration,
            "last_successful_scrape": datetime.now(tz=UTC).isoformat(),
        }
        return {
            "state": state,
            "attributes": attributes,
            "error_message": "",
            "last_attempt_status": "success",
        }

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
                raise (
                    IntegrationBlueprintApiClientCommunicationError(msg)
                ) from exception
            except TimeoutError as exception:
                msg = f"Timeout error fetching page content - {exception}"
                raise (
                    IntegrationBlueprintApiClientCommunicationError(msg)
                ) from exception
            except (aiohttp.ClientError, socket.gaierror) as exception:
                msg = f"Error fetching page content - {exception}"
                raise (
                    IntegrationBlueprintApiClientCommunicationError(msg)
                ) from exception
            except Exception as exception:  # pylint: disable=broad-except
                msg = f"Something really wrong happened! - {exception}"
                raise IntegrationBlueprintApiClientError(msg) from exception

        error_message = "Unable to fetch page content"
        raise IntegrationBlueprintApiClientError(error_message)

    def _normalize_browserless_url(self, browserless_url: str) -> str:
        """Normalize the browserless addon URL for fetching rendered content."""
        parsed_url = urlparse(browserless_url)
        if parsed_url.scheme in ("ws", "wss"):
            raise IntegrationBlueprintApiClientError(
                "WebSocket browserless URLs are not supported by this integration. "
                "Use the HTTP browserless addon endpoint instead."
            )
        if parsed_url.path in (None, "", "/"):
            parsed_url = parsed_url._replace(path="/content")
        return urlunparse(parsed_url)

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Make a request to the remote API."""
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
            if exception.status == HTTP_STATUS_NOT_FOUND:
                msg = (
                    "Browserless API returned 404 Not Found. "
                    "Check your configured browserless_url and the service path."
                )
            else:
                msg = (
                    "Error fetching information - "
                    f"{exception.status} {exception.message}"
                )
            raise (IntegrationBlueprintApiClientCommunicationError(msg)) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise IntegrationBlueprintApiClientError(msg) from exception
