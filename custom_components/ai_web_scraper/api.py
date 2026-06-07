"""AI Web Scraper API client."""

from __future__ import annotations

import inspect
import socket
from datetime import UTC, datetime
from typing import Any

import aiohttp
import async_timeout


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
            raw = await self._api_wrapper(
                method="post",
                url=self._browserless_url,
                data={
                    "url": self._url,
                    "prompt": self._prompt,
                    "provider_name": self._provider_name,
                    "extraction_mode": self._extraction_mode,
                },
            )
            state = raw.get("text", raw.get("body", raw.get("result", "")))
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
        try:
            async with async_timeout.timeout(10):
                response = await self._session.get(
                    url,
                    headers={"Accept": "text/html"},
                )
                await _verify_response_or_raise(response)
                return await response.text()
        except TimeoutError as exception:
            msg = f"Timeout error fetching page content - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching page content - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise IntegrationBlueprintApiClientError(msg) from exception

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
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise IntegrationBlueprintApiClientError(msg) from exception
