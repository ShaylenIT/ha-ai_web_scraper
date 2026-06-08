"""Unit tests for the ai_web_scraper API client."""

import asyncio
from unittest.mock import AsyncMock

import aiohttp

from custom_components.ai_web_scraper.api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
    OpenAIProvider,
)
from custom_components.ai_web_scraper.const import (
    PROVIDER_TYPE_GEMINI,
    PROVIDER_TYPE_OPENAI,
)


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
            "candidates": [{"content": {"parts": [{"text": "Extracted result"}]}}]
        }
    )

    result = asyncio.run(client.async_get_data())

    client._api_wrapper.assert_awaited_once()
    assert (
        "generativelanguage.googleapis.com"
        in client._api_wrapper.call_args.kwargs["url"]
    )
    assert result["state"] == "Extracted result"
    assert result["attributes"]["scraper_status"] == "completed"


def test_provider_factory_selects_openai_by_default() -> None:
    client = IntegrationBlueprintApiClient(
        provider_name="Test Provider",
        api_key="test-key",
        model_name="gpt-4",
        browserless_url="",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=DummySession(),
        provider_type=PROVIDER_TYPE_OPENAI,
    )

    provider = client._get_provider()

    assert isinstance(provider, OpenAIProvider)


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


def test_api_wrapper_rate_limit_error_message() -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.status = 429
            self.headers = {"Content-Type": "application/json"}
            self.raise_for_status = AsyncMock(
                side_effect=aiohttp.ClientResponseError(
                    request_info=None,
                    history=(),
                    status=429,
                    message="Too Many Requests",
                )
            )

        async def json(self) -> dict[str, str]:
            return {}

        async def text(self) -> str:
            return ""

    response = FakeResponse()

    class FakeRequestContext:
        def __init__(self, response: FakeResponse) -> None:
            self._response = response

        async def __aenter__(self) -> FakeResponse:
            return self._response

        async def __aexit__(self, exc_type, exc, tb) -> bool:  # type: ignore[override]
            return False

    class FakeSession:
        async def request(
            self,
            method: str,
            url: str,
            headers: dict | None = None,
            json: dict | None = None,
        ) -> FakeResponse:
            return response

    session = FakeSession()

    client = IntegrationBlueprintApiClient(
        provider_name="Test Provider",
        api_key="test-key",
        model_name="gpt-4",
        browserless_url="",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=session,
    )

    try:
        asyncio.run(
            client._api_wrapper(
                method="post",
                url="https://api.example.com",
                data={},
                headers={},
            )
        )
        assert False, "Expected IntegrationBlueprintApiClientCommunicationError"
    except IntegrationBlueprintApiClientCommunicationError as exception:
        assert "Provider rate limit exceeded" in str(exception)


def test_api_wrapper_retries_server_errors_once() -> None:
    class FakeResponse:
        def __init__(self, status: int, raise_error: bool = False) -> None:
            self.status = status
            self.headers = {"Content-Type": "application/json"}
            if raise_error:
                self.raise_for_status = AsyncMock(
                    side_effect=aiohttp.ClientResponseError(
                        request_info=None,
                        history=(),
                        status=status,
                        message="Service Unavailable",
                    )
                )
            else:
                self.raise_for_status = AsyncMock()

        async def json(self) -> dict[str, str]:
            return {"choices": [{"message": {"content": "Extracted after retry"}}]}

        async def text(self) -> str:
            return ""

    class FakeSession:
        def __init__(self) -> None:
            self.calls = 0

        async def request(
            self,
            method: str,
            url: str,
            headers: dict | None = None,
            json: dict | None = None,
        ) -> FakeResponse:
            self.calls += 1
            if self.calls == 1:
                return FakeResponse(503, raise_error=True)
            return FakeResponse(200)

    session = FakeSession()

    client = IntegrationBlueprintApiClient(
        provider_name="Test Provider",
        api_key="test-key",
        model_name="gpt-4",
        browserless_url="",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=session,
    )
    client._get_page_text = AsyncMock(return_value="<html>hello</html>")

    result = asyncio.run(client.async_get_data())

    assert session.calls == 2
    assert result["state"] == "Extracted after retry"


def test_normalize_page_text_removes_html_tags() -> None:
    client = IntegrationBlueprintApiClient(
        provider_name="Test Provider",
        api_key="test-key",
        model_name="gpt-4",
        browserless_url="",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=DummySession(),
    )

    normalized = client._normalize_page_text(
        "<html><head><style>.hidden{}</style></head><body><h1>Hello</h1><p>World</p></body></html>"
    )

    assert normalized == "Hello World"
