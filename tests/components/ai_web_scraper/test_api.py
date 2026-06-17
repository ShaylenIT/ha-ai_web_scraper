"""Unit tests for the ai_web_scraper API client."""

import asyncio
from unittest.mock import AsyncMock

import aiohttp

from custom_components.ai_web_scraper.api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
    OpenAICompatibleProvider,
)
from custom_components.ai_web_scraper.const import (
    OPENAI_COMPATIBLE_TYPES,
    PROVIDER_BASE_URLS,
    PROVIDER_TYPE_GEMINI,
    PROVIDER_TYPE_GROQ,
    PROVIDER_TYPE_LOCALAI,
    PROVIDER_TYPE_OLLAMA,
    PROVIDER_TYPE_OPENAI,
    PROVIDER_TYPE_OPENAI_COMPATIBLE,
    PROVIDER_TYPE_OPENROUTER,
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


def test_provider_factory_selects_openai_compatible_by_default() -> None:
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

    assert isinstance(provider, OpenAICompatibleProvider)


def test_provider_factory_returns_openai_compatible_for_all_types() -> None:
    """Every OpenAI-compatible provider type returns OpenAICompatibleProvider."""
    for provider_type in OPENAI_COMPATIBLE_TYPES:
        client = IntegrationBlueprintApiClient(
            provider_name="Test Provider",
            api_key="test-key",
            model_name="test-model",
            browserless_url="",
            scraper_name="Test Scraper",
            url="https://example.com",
            prompt="Extract text",
            extraction_mode="dom",
            session=DummySession(),
            provider_type=provider_type,
        )
        provider = client._get_provider()
        assert isinstance(provider, OpenAICompatibleProvider), (
            f"Expected OpenAICompatibleProvider for {provider_type}, "
            f"got {type(provider).__name__}"
        )


def test_provider_factory_uses_correct_default_base_url() -> None:
    """Each provider type defaults to the correct base URL."""
    test_cases = [
        (PROVIDER_TYPE_OPENAI, "https://api.openai.com/v1/chat/completions"),
        (PROVIDER_TYPE_GROQ, "https://api.groq.com/openai/v1/chat/completions"),
        (PROVIDER_TYPE_LOCALAI, "http://localhost:8080/v1/chat/completions"),
        (PROVIDER_TYPE_OLLAMA, "http://localhost:11434/v1/chat/completions"),
        (PROVIDER_TYPE_OPENROUTER, "https://openrouter.ai/api/v1/chat/completions"),
    ]
    for provider_type, expected_url in test_cases:
        client = IntegrationBlueprintApiClient(
            provider_name="Test",
            api_key="key",
            model_name="model",
            browserless_url="",
            scraper_name="Scraper",
            url="https://example.com",
            prompt="Extract",
            extraction_mode="dom",
            session=DummySession(),
            provider_type=provider_type,
        )
        provider = client._get_provider()
        assert isinstance(provider, OpenAICompatibleProvider)
        # The URL is only resolved when extract() is called, but we can
        # verify the internal _base_url was set correctly
        assert provider._base_url == PROVIDER_BASE_URLS.get(provider_type), (
            f"Wrong base URL for {provider_type}"
        )


def test_provider_factory_uses_custom_base_url() -> None:
    """Custom base URL overrides the default."""
    custom_url = "https://my-custom-proxy.example.com/v1"
    client = IntegrationBlueprintApiClient(
        provider_name="Test",
        api_key="key",
        model_name="model",
        browserless_url="",
        scraper_name="Scraper",
        url="https://example.com",
        prompt="Extract",
        extraction_mode="dom",
        session=DummySession(),
        provider_type=PROVIDER_TYPE_OPENAI_COMPATIBLE,
        base_url=custom_url,
    )
    provider = client._get_provider()
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider._base_url == custom_url


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


def test_browserless_screenshot_is_saved_to_disk(tmp_path) -> None:
    client = IntegrationBlueprintApiClient(
        provider_name="Test Provider",
        api_key="test-key",
        model_name="gpt-4",
        browserless_url="https://example.com/api",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=DummySession(),
        screenshot_dir=str(tmp_path),
        screenshot_filename="scraper-entry-id.png",
    )

    client._fetch_browserless_page_text = AsyncMock(return_value="<html>hello</html>")
    client._fetch_browserless_page_screenshot = AsyncMock(return_value=b"PNGDATA")
    client._provider_extract = AsyncMock(return_value="Extracted result")

    result = asyncio.run(client.async_get_data())

    assert result["attributes"]["screenshot_path"] == str(
        tmp_path / "scraper-entry-id.png"
    )
    assert (tmp_path / "scraper-entry-id.png").read_bytes() == b"PNGDATA"


def test_browserless_screenshot_falls_back_on_400_bad_request() -> None:
    class FakeResponse:
        def __init__(self, status: int, content: bytes = b"") -> None:
            self.status = status
            self.headers = {"Content-Type": "image/png"}
            self._content = content
            self.raise_for_status = AsyncMock(
                side_effect=aiohttp.ClientResponseError(
                    request_info=None,
                    history=(),
                    status=status,
                    message="Bad Request",
                )
                if status >= 400
                else AsyncMock()
            )

        async def read(self) -> bytes:
            return self._content

    error_response = FakeResponse(status=400)
    success_response = FakeResponse(status=200, content=b"PNGDATA")

    session = AsyncMock()
    session.post.side_effect = [
        error_response,
        error_response,
        success_response,
    ]

    client = IntegrationBlueprintApiClient(
        provider_name="Test Provider",
        api_key="test-key",
        model_name="gpt-4",
        browserless_url="https://example.com/api",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=session,
        screenshot_dir=".",
        screenshot_filename="scraper-entry-id.png",
    )

    screenshot = asyncio.run(
        client._fetch_browserless_page_screenshot("https://example.com")
    )

    assert screenshot == b"PNGDATA"
    assert session.post.await_count == 3


def test_browserless_screenshot_uses_standard_payload_first() -> None:
    class FakeResponse:
        def __init__(self, status: int, content: bytes = b"") -> None:
            self.status = status
            self.headers = {"Content-Type": "image/png"}
            self._content = content
            self.raise_for_status = AsyncMock()

        async def read(self) -> bytes:
            return self._content

    success_response = FakeResponse(status=200, content=b"PNGDATA")

    session = AsyncMock()
    session.post.return_value = success_response

    client = IntegrationBlueprintApiClient(
        provider_name="Test Provider",
        api_key="test-key",
        model_name="gpt-4",
        browserless_url="https://example.com/api",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=session,
        screenshot_dir=".",
        screenshot_filename="scraper-entry-id.png",
    )

    screenshot = asyncio.run(
        client._fetch_browserless_page_screenshot("https://example.com")
    )

    assert screenshot == b"PNGDATA"
    assert session.post.await_count == 1

    # Verify the first call JSON payload is standard schema
    call_kwargs = session.post.call_args.kwargs
    assert "json" in call_kwargs
    payload = call_kwargs["json"]
    assert payload["url"] == "https://example.com"
    assert payload["gotoOptions"] == {
        "waitUntil": "networkidle2",
        "timeout": 30000,
    }
    assert payload["options"] == {
        "fullPage": True,
        "type": "png",
    }
