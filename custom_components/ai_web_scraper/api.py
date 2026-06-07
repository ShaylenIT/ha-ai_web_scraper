"""AI Web Scraper API client."""

from __future__ import annotations

import socket
from datetime import datetime
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


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise IntegrationBlueprintApiClientAuthenticationError(msg)
    response.raise_for_status()


class IntegrationBlueprintApiClient:
    """AI Web Scraper API Client."""

    def __init__(
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
        """Get scraped data from the placeholder API."""
        if self._missing_provider:
            raise IntegrationBlueprintApiClientError(
                "Missing provider configuration. Please verify the selected Provider profile."
            )

        start = datetime.utcnow()
        raw = await self._api_wrapper(
            method="get",
            url="https://jsonplaceholder.typicode.com/posts/1",
        )
        duration = (datetime.utcnow() - start).total_seconds()

        state = raw.get("body", "")
        attributes = {
            "url": self._url,
            "prompt": self._prompt,
            "provider_name": self._provider_name,
            "extraction_mode": self._extraction_mode,
            "scrape_duration_seconds": duration,
            "last_successful_scrape": datetime.utcnow().isoformat(),
        }
        return {
            "state": state,
            "attributes": attributes,
            "error_message": "",
            "last_attempt_status": "success",
        }

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
                _verify_response_or_raise(response)
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
