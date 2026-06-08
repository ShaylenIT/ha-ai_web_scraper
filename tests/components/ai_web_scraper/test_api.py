"""Unit tests for the ai_web_scraper API client."""

import asyncio
from unittest.mock import AsyncMock

from custom_components.ai_web_scraper.api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientError,
)
from custom_components.ai_web_scraper.const import PROVIDER_TYPE_GEMINI


class DummySession:
    """Minimal fake session for API client tests."""


def test_gemini_provider_extract_uses_gemini_generate_endpoint() -> None:
    client = IntegrationBlueprintApiClient(
        provider_name="Test Provider",
        api_key="test-key",
        model_name="gemini-1.0",
        browserless_url="",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=DummySession(),
        provider_type=PROVIDER_TYPE_GEMINI,
    )
    client._get_page_text = AsyncMock(return_value="<html>hello</html>")
    client._api_wrapper = AsyncMock(
        return_value={
            "candidates": [
                {"content": {"parts": [{"text": "Extracted result"}]}}
            ]
        }
    )

    result = asyncio.run(client.async_get_data())

    client._api_wrapper.assert_awaited_once()
    assert "generativelanguage.googleapis.com" in client._api_wrapper.call_args.kwargs["url"]
    assert result["state"] == "Extracted result"


def test_gemini_provider_extract_raises_for_empty_candidate() -> None:
    client = IntegrationBlueprintApiClient(
        provider_name="Test Provider",
        api_key="test-key",
        model_name="gemini-1.0",
        browserless_url="",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=DummySession(),
        provider_type=PROVIDER_TYPE_GEMINI,
    )
    client._get_page_text = AsyncMock(return_value="<html>hello</html>")
    client._api_wrapper = AsyncMock(return_value={"candidates": []})

    try:
        asyncio.run(client.async_get_data())
        assert False, "Expected IntegrationBlueprintApiClientError"
    except IntegrationBlueprintApiClientError:
        pass
