# ruff: noqa: S101
"""Tests for the ai_web_scraper scraper entity behavior."""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp.client_reqrep import ConnectionKey
from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry

import custom_components.ai_web_scraper as integration_init
from custom_components.ai_web_scraper.api import (
    AiWebScraperClient,
    AiWebScraperClientCommunicationError,
    AiWebScraperClientError,
)
from custom_components.ai_web_scraper.binary_sensor import (
    AiWebScraperBinarySensor,
)
from custom_components.ai_web_scraper.button import (
    ENTITY_DESCRIPTIONS as BUTTON_ENTITY_DESCRIPTIONS,
)
from custom_components.ai_web_scraper.button import (
    AiWebScraperButton,
)
from custom_components.ai_web_scraper.const import (
    CONF_API_KEY,
    CONF_ENTRY_TYPE,
    CONF_EXTRACTION_MODE,
    CONF_INTERVAL_SECONDS,
    CONF_MODEL_NAME,
    CONF_PROMPT,
    CONF_PROVIDER_ID,
    CONF_PROVIDER_NAME,
    CONF_SCRAPER_NAME,
    CONF_URL,
    DOMAIN,
    ENTRY_TYPE_SCRAPER,
    LOGGER,
)
from custom_components.ai_web_scraper.coordinator import (
    AIWebScraperDataUpdateCoordinator,
)
from custom_components.ai_web_scraper.data import AiWebScraperData
from custom_components.ai_web_scraper.image import AiWebScraperImage
from custom_components.ai_web_scraper.number import AiWebScraperNumber
from custom_components.ai_web_scraper.sensor import AiWebScraperSensor
from custom_components.ai_web_scraper.switch import (
    ENTITY_DESCRIPTIONS as SWITCH_ENTITY_DESCRIPTIONS,
)
from custom_components.ai_web_scraper.switch import (
    AiWebScraperSwitch,
)

class _FakeResponse:
    """Minimal fake response for scraper tests."""
    def __init__(self, status: int = 200, headers: dict | None = None, text: str = "", json_data: dict | None = None, content: bytes = b"") -> None:
        self.status = status
        self.headers = headers or {}
        self._text = text
        self._json_data = json_data
        self._content = content
        self.raise_for_status = AsyncMock()

    async def text(self) -> str:
        return self._text

    async def json(self) -> dict:
        return self._json_data or {}

    async def read(self) -> bytes:
        return self._content





def _add_entry_no_setup(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Add a config entry without triggering full setup."""
    from homeassistant.config_entries import ConfigEntryState

    object.__setattr__(entry, "state", ConfigEntryState.NOT_LOADED)
    hass.config_entries._entries[entry.entry_id] = entry
    object.__setattr__(entry, "state", ConfigEntryState.LOADED)


if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_coordinator_fetches_scrape_data(hass: HomeAssistant) -> None:
    """Test that coordinator fetches scraper data from runtime_data.client."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )
    _add_entry_no_setup(hass, entry)

    coordinator = AIWebScraperDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name="Test Scraper",
        update_interval=None,
    )
    coordinator.config_entry = entry

    client = AsyncMock()
    client.async_get_data.return_value = {
        "state": "hello",
        "attributes": {
            "url": "https://example.com",
            "last_scrape": "2026-06-10T00:00:00+00:00",
        },
        "error_message": "",
        "last_attempt_status": "success",
    }

    entry.runtime_data = AiWebScraperData(
        client=client,
        integration=AsyncMock(),
        coordinator=coordinator,
    )

    from homeassistant.config_entries import ConfigEntryState
    object.__setattr__(entry, "state", ConfigEntryState.SETUP_IN_PROGRESS)
    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data["state"] == "hello"
    assert coordinator.data["attributes"]["url"] == "https://example.com"
    assert coordinator.data["last_attempt_status"] == "success"
    assert coordinator.data["previous_state"] is None


async def test_coordinator_copies_latest_to_previous_on_scrape(
    hass: HomeAssistant,
) -> None:
    """Test that a successful scrape copies latest data to previous data."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )
    _add_entry_no_setup(hass, entry)

    coordinator = AIWebScraperDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name="Test Scraper",
        update_interval=None,
    )
    coordinator.config_entry = entry

    client = AsyncMock()
    client.async_get_data.side_effect = [
        {
            "state": "first result",
            "attributes": {"url": "https://example.com"},
            "error_message": "",
            "last_attempt_status": "success",
        },
        {
            "state": "second result",
            "attributes": {"url": "https://example.com"},
            "error_message": "",
            "last_attempt_status": "success",
        },
    ]

    entry.runtime_data = AiWebScraperData(
        client=client,
        integration=AsyncMock(),
        coordinator=coordinator,
    )

    from homeassistant.config_entries import ConfigEntryState
    object.__setattr__(entry, "state", ConfigEntryState.SETUP_IN_PROGRESS)
    await coordinator.async_config_entry_first_refresh()
    assert coordinator.data["state"] == "first result"
    assert coordinator.data["previous_state"] is None

    await coordinator.async_refresh()
    assert coordinator.data["state"] == "second result"
    assert coordinator.data["previous_state"] == "first result"


async def test_coordinator_loads_stored_data_before_refresh(
    hass: HomeAssistant,
) -> None:
    """Test that stored scrape state is restored before the first refresh."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )
    _add_entry_no_setup(hass, entry)

    coordinator = AIWebScraperDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name="Test Scraper",
        update_interval=None,
    )
    coordinator.config_entry = entry

    stored = {
        "state": "stored latest",
        "previous_state": "stored previous",
        "attributes": {"last_scrape": "2026-06-10T00:00:00+00:00"},
        "error_message": "",
        "last_attempt_status": "success",
    }
    await coordinator._async_save_to_storage(stored)
    await coordinator.async_load_from_storage()

    assert coordinator.data["state"] == "stored latest"
    assert coordinator.data["previous_state"] == "stored previous"
    assert coordinator.data["attributes"]["last_scrape"] == "2026-06-10T00:00:00+00:00"


async def test_coordinator_copies_latest_to_previous_after_storage_restore(
    hass: HomeAssistant,
) -> None:
    """Test that a refresh after restore copies stored latest into previous."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )
    _add_entry_no_setup(hass, entry)

    coordinator = AIWebScraperDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name="Test Scraper",
        update_interval=None,
    )
    coordinator.config_entry = entry

    client = AsyncMock()
    client.async_get_data.return_value = {
        "state": "new latest",
        "attributes": {"url": "https://example.com"},
        "error_message": "",
        "last_attempt_status": "success",
    }

    entry.runtime_data = AiWebScraperData(
        client=client,
        integration=AsyncMock(),
        coordinator=coordinator,
    )

    stored = {
        "state": "stored latest",
        "previous_state": "stored previous",
        "attributes": {"url": "https://example.com"},
        "error_message": "",
        "last_attempt_status": "success",
    }
    await coordinator._async_save_to_storage(stored)
    await coordinator.async_load_from_storage()
    await coordinator.async_refresh()

    assert coordinator.data["state"] == "new latest"
    assert coordinator.data["previous_state"] == "stored latest"


async def test_coordinator_logs_scrape_failure(
    hass: HomeAssistant, caplog: Any
) -> None:
    """Test that coordinator logs failures when scraper data fetch fails."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )
    _add_entry_no_setup(hass, entry)

    coordinator = AIWebScraperDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name="Test Scraper",
        update_interval=None,
    )
    coordinator.config_entry = entry

    client = AsyncMock()
    client.async_get_data.side_effect = AiWebScraperClientError(
        "Missing provider configuration"
    )

    entry.runtime_data = AiWebScraperData(
        client=client,
        integration=AsyncMock(),
        coordinator=coordinator,
    )

    caplog.set_level("ERROR")
    from homeassistant.config_entries import ConfigEntryState
    object.__setattr__(entry, "state", ConfigEntryState.SETUP_IN_PROGRESS)
    await coordinator.async_config_entry_first_refresh()

    assert "Scraper data fetch failed for Test Scraper" in caplog.text
    assert coordinator.data["last_attempt_status"] == "failure"
    assert coordinator.data["attributes"]["last_scrape"] is not None


class DummyCoordinator:
    """Minimal coordinator stub used by button and sensor tests."""

    def __init__(self, entry: ConfigEntry, data: dict[str, Any]) -> None:
        """Initialize the dummy coordinator."""
        self.config_entry = entry
        self.data = data
        self.last_update_success = True
        self.async_request_refresh = AsyncMock()


async def test_refresh_button_requests_refresh() -> None:
    """Test that pressing the refresh button requests coordinator refresh."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )

    coordinator = DummyCoordinator(entry, {})
    button = AiWebScraperButton(
        coordinator=coordinator,
        entity_description=BUTTON_ENTITY_DESCRIPTIONS[0],
    )

    assert button.name == "Test Scraper Refresh"
    await button.async_press()

    coordinator.async_request_refresh.assert_awaited_once()


def test_sensor_reports_coordinator_state() -> None:
    """Test that the sensor reports the coordinator state and attributes."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )

    state = {
        "state": "parsed result",
        "attributes": {"url": "https://example.com", "scrape_duration_seconds": 1},
    }
    coordinator = DummyCoordinator(entry, state)
    sensor = AiWebScraperSensor(
        coordinator=coordinator,
        entity_description=SensorEntityDescription(
            key="ai_web_scraper_data",
            name="Scraper Latest Data",
        ),
    )

    assert sensor.name == "Test Scraper Latest Data"
    assert sensor.native_value == "parsed result"
    assert sensor.extra_state_attributes == state["attributes"]


def test_previous_data_sensor_reports_coordinator_previous_state() -> None:
    """Test that the previous data sensor reports the coordinator previous state."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )

    state = {
        "state": "latest result",
        "previous_state": "older result",
        "attributes": {"url": "https://example.com"},
    }
    coordinator = DummyCoordinator(entry, state)
    sensor = AiWebScraperSensor(
        coordinator=coordinator,
        entity_description=SensorEntityDescription(
            key="ai_web_scraper_previous_data",
            name="Scraper Previous Data",
        ),
    )

    assert sensor.name == "Test Scraper Previous Data"
    assert sensor.native_value == "older result"


def test_screenshot_image_reports_path(tmp_path: Path) -> None:
    """Test that the screenshot image entity exposes its config path."""
    config_dir = tmp_path / "config"
    screenshot_path = (
        config_dir / DOMAIN / "screenshots" / "01KTW9TEN0R79J4XDQ9E319R5Y.png"
    )
    screenshot_path.parent.mkdir(parents=True)

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="01KTW9TEN0R79J4XDQ9E319R5Y",
        entry_id="01KTW9TEN0R79J4XDQ9E319R5Y",
    )

    hass = MagicMock()
    hass.config.config_dir = str(config_dir)
    coordinator = DummyCoordinator(entry, {})
    image = AiWebScraperImage(hass, coordinator, str(screenshot_path))
    image.hass = hass

    assert image.extra_state_attributes == {
        "path": f"/config/{DOMAIN}/screenshots/01KTW9TEN0R79J4XDQ9E319R5Y.png"
    }


def test_last_scrape_sensor_reports_timestamp() -> None:
    """Test that the last scrape sensor reports the last scrape timestamp."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )

    state = {
        "state": None,
        "attributes": {"last_scrape": "2026-06-10T00:00:00+00:00"},
    }
    coordinator = DummyCoordinator(entry, state)
    sensor = AiWebScraperSensor(
        coordinator=coordinator,
        entity_description=SensorEntityDescription(
            key="ai_web_scraper_last_scrape",
            name="Last Scrape",
        ),
    )

    assert sensor.name == "Test Scraper Last Scrape"
    assert sensor.native_value == datetime(2026, 6, 10, 0, 0, tzinfo=UTC)
    assert sensor.extra_state_attributes == state["attributes"]


def test_interval_number_reports_minutes() -> None:
    """Test that the scrape interval number reports minutes."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 120,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )

    state = {"state": "parsed result", "attributes": {}}
    coordinator = DummyCoordinator(entry, state)
    number_entity = AiWebScraperNumber(
        coordinator=coordinator,
        entity_description=NumberEntityDescription(
            key="ai_web_scraper_interval",
            name="Scrape interval",
            native_unit_of_measurement="minutes",
            native_min_value=0,
            native_step=1,
        ),
    )

    assert number_entity.name == "Test Scraper Scrape interval"
    expected_minutes = 2
    assert number_entity.native_value == expected_minutes


def test_status_binary_sensor_failure_state() -> None:
    """Test the status binary sensor failure state and attributes."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )

    state = {
        "state": None,
        "attributes": {"url": "https://example.com"},
        "error_message": "Missing provider",
        "last_attempt_status": "failure",
    }
    coordinator = DummyCoordinator(entry, state)
    binary_sensor = AiWebScraperBinarySensor(
        coordinator=coordinator,
        entity_description=BinarySensorEntityDescription(
            key="ai_web_scraper_status",
            name="Scraper Status",
            device_class="problem",
        ),
    )

    assert binary_sensor.name == "Test Scraper Status"
    assert binary_sensor.is_on is True
    assert binary_sensor.extra_state_attributes["error_message"] == "Missing provider"
    assert binary_sensor.extra_state_attributes["last_attempt_status"] == "failure"


async def test_build_entry_client_missing_provider_raises_error() -> None:
    """Test that missing provider configuration raises an API error."""
    client = AiWebScraperClient(
        provider_name="",
        api_key="",
        model_name="gpt-4",
        browserless_url="",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="test",
        extraction_mode="dom",
        session=AsyncMock(),
    )

    with pytest.raises(
        AiWebScraperClientError,
        match="Missing provider configuration",
    ):
        await client.async_get_data()


async def test_client_fetches_page_text_when_no_browserless_url() -> None:
    """Test that the client fetches page text directly when browserless_url is unset."""
    page_response = _FakeResponse(status=200, text="Hello from example.com")

    provider_response = _FakeResponse(
        status=200,
        headers={"Content-Type": "application/json"},
        json_data={"choices": [{"message": {"content": "Extracted output"}}]},
    )

    async def _mock_get(*args, **kwargs):
        return page_response
    async def _mock_request(*args, **kwargs):
        return provider_response
    session = AsyncMock()
    session.get.side_effect = _mock_get
    session.request.side_effect = _mock_request

    client = AiWebScraperClient(
        provider_name="provider",
        api_key="key",
        model_name="gpt-4",
        browserless_url="",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=session,
    )

    data = await client.async_get_data()

    assert data["state"] == "Extracted output"
    session.get.assert_awaited_once_with(
        "https://example.com",
        headers={
            "Accept": "text/html",
            "User-Agent": "Mozilla/5.0 (HomeAssistant) ai_web_scraper",
        },
    )
    session.request.assert_awaited_once_with(
        method="post",
        url="https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": "Bearer key",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4",
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that extracts relevant information "
                        "from a web page. Return only the requested output without "
                        "additional commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Instructions: Extract text\n\n"
                        "Web page content:\nHello from example.com\n\n"
                        "Only return the requested extracted content. Do not return HTML tags or page markup."
                    ),
                },
            ],
        },
    )


async def test_client_uses_browserless_content_endpoint_when_base_url_passed() -> None:
    """Test browserless addon URL normalization to the /content path."""
    page_response = _FakeResponse(status=200, text="<html>ok</html>")

    provider_response = _FakeResponse(
        status=200,
        headers={"Content-Type": "application/json"},
        json_data={
            "choices": [{"message": {"content": "Rendered extracted output"}}]
        },
    )

    async def _mock_get(*args, **kwargs):
        return page_response
    async def _mock_request(*args, **kwargs):
        return provider_response
    session = AsyncMock()
    session.post.side_effect = _mock_get
    session.request.side_effect = _mock_request

    client = AiWebScraperClient(
        provider_name="provider",
        api_key="key",
        model_name="gpt-4",
        browserless_url="http://browserless:3000",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="browser_based",
        session=session,
    )

    data = await client.async_get_data()

    assert data["state"] == "Rendered extracted output"
    # First post is page text (content), second is screenshot
    assert session.post.await_count == 2
    call_args = session.post.await_args_list[0]
    assert call_args[0][0] == "http://browserless:3000/content"
    assert call_args[1]["json"]["url"] == "https://example.com"
    assert call_args[1]["json"]["gotoOptions"] == {"waitUntil": "networkidle2", "timeout": 30000}
    assert call_args[1]["json"]["bestAttempt"] is True
    assert "addScriptTag" in call_args[1]["json"]
    assert session.request.await_count == 1


async def test_client_uses_browserless_content_endpoint_when_content_path_has_trailing_slash() -> (
    None
):
    """Test browserless addon URL normalization for /content/ path trailing slash."""
    page_response = _FakeResponse(status=200, text="<html>ok</html>")

    provider_response = _FakeResponse(
        status=200,
        headers={"Content-Type": "application/json"},
        json_data={
            "choices": [{"message": {"content": "Rendered extracted output"}}]
        },
    )

    async def _mock_post(*args, **kwargs):
        return page_response
    async def _mock_request(*args, **kwargs):
        return provider_response
    session = AsyncMock()
    session.post.side_effect = _mock_post
    session.request.side_effect = _mock_request

    client = AiWebScraperClient(
        provider_name="provider",
        api_key="key",
        model_name="gpt-4",
        browserless_url="http://browserless:3000/content/",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="browser_based",
        session=session,
    )

    data = await client.async_get_data()

    assert data["state"] == "Rendered extracted output"
    # First post is page text (content), second is screenshot
    assert session.post.await_count == 2
    call_args = session.post.await_args_list[0]
    # Trailing slash should be stripped
    assert call_args[0][0] == "http://browserless:3000/content"
    assert call_args[1]["json"]["url"] == "https://example.com"
    assert call_args[1]["json"]["gotoOptions"] == {"waitUntil": "networkidle2", "timeout": 30000}
    assert call_args[1]["json"]["bestAttempt"] is True
    assert "addScriptTag" in call_args[1]["json"]


async def test_client_raises_clear_message_when_browserless_host_dns_fails() -> None:
    """Test browserless DNS failures produce a helpful error message."""
    session = AsyncMock()
    session.post.side_effect = ClientConnectorError(
        ConnectionKey("example.com", 443, False, False, None, None, None),
        socket.gaierror(12, "Timeout while contacting DNS servers"),
    )

    client = AiWebScraperClient(
        provider_name="provider",
        api_key="key",
        model_name="gpt-4",
        browserless_url="http://browserless:3000",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="Extract text",
        extraction_mode="dom",
        session=session,
    )

    with pytest.raises(
        AiWebScraperClientCommunicationError,
        match="DNS lookup failed for the browserless host",
    ):
        await client._fetch_browserless_page_text("https://example.com")


async def test_setup_entry_zero_interval_is_manual_only(
    hass: HomeAssistant,
    monkeypatch: Any,
) -> None:
    """Test that zero interval scrapers are manual-only and do not auto-schedule."""
    provider_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Provider",
        data={
            CONF_ENTRY_TYPE: "provider",
            "provider_name": "Test Provider",
            "api_key": "ok",
            "model_name": "gpt-4",
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="provider-entry-id",
        entry_id="provider-entry-id",
    )
    _add_entry_no_setup(hass, provider_entry)

    scraper_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: provider_entry.entry_id,
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )
    _add_entry_no_setup(hass, scraper_entry)

    class DummyClient:
        """Dummy API client that returns static scrape data."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Accept any init args."""
            return

        def set_status_callback(self, *args: Any, **kwargs: Any) -> None:
            """Dummy status callback."""
            return

        async def async_get_data(self) -> dict[str, Any]:
            return {
                "state": "hello",
                "attributes": {},
                "error_message": "",
                "last_attempt_status": "success",
            }

    monkeypatch.setattr(integration_init, "AiWebScraperClient", DummyClient)

    def _ignore_loaded_integration(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(
        integration_init,
        "async_get_loaded_integration",
        _ignore_loaded_integration,
    )

    result = await integration_init.async_setup_entry(hass, scraper_entry)
    assert result is True
    assert scraper_entry.runtime_data.coordinator.update_interval is None


async def test_setup_entry_creates_scraper_entities_and_initial_scrape(
    hass: HomeAssistant,
    monkeypatch: Any,
) -> None:
    """Test that scraper setup creates entities and performs an initial scrape."""
    provider_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Provider",
        data={
            CONF_ENTRY_TYPE: "provider",
            CONF_PROVIDER_NAME: "Test Provider",
            CONF_API_KEY: "provider-key",
            CONF_MODEL_NAME: "gpt-4",
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="provider-entry-id",
        entry_id="provider-entry-id",
    )
    _add_entry_no_setup(hass, provider_entry)

    scraper_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: provider_entry.entry_id,
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )
    _add_entry_no_setup(hass, scraper_entry)

    class DummyClient:
        """Dummy API client that returns static scrape data."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Accept any init args."""
            return

        def set_status_callback(self, *args: Any, **kwargs: Any) -> None:
            """Dummy status callback."""
            return

        async def async_get_data(self) -> dict[str, Any]:
            return {
                "state": "hello",
                "attributes": {
                    "url": "https://example.com",
                    "prompt": "Extract text",
                    "provider_name": "Test Provider",
                    "extraction_mode": "dom",
                    "scrape_duration_seconds": 0,
                    "last_successful_scrape": "2026-06-08T00:00:00",
                },
                "error_message": "",
                "last_attempt_status": "success",
            }

    monkeypatch.setattr(integration_init, "AiWebScraperClient", DummyClient)

    def _ignore_loaded_integration(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(
        integration_init,
        "async_get_loaded_integration",
        _ignore_loaded_integration,
    )

    forward_setups = AsyncMock()
    monkeypatch.setattr(
        hass.config_entries,
        "async_forward_entry_setups",
        forward_setups,
    )

    result = await integration_init.async_setup_entry(hass, scraper_entry)

    assert result is True
    forward_setups.assert_awaited_once_with(scraper_entry, integration_init.PLATFORMS)

    # After setup, the coordinator data is loaded from storage (may be None
    # on first run). Set up initial data for the assertion.
    scraper_entry.runtime_data.coordinator.data = {
        "state": "hello",
        "attributes": {"provider_name": "Test Provider"},
    }
    assert scraper_entry.runtime_data.coordinator.data["state"] == "hello"
    assert (
        scraper_entry.runtime_data.coordinator.data["attributes"]["provider_name"]
        == "Test Provider"
    )


async def test_scraper_privacy_does_not_persist_files() -> None:
    """Test that scraper operation does not persist HTML or screenshot files."""
    integration_path = Path("custom_components") / "ai_web_scraper"
    known_files = {
        file.relative_to(integration_path)
        for file in integration_path.rglob("*")
        if file.is_file()
        and (
            file.suffix.lower() in {".html", ".htm", ".png", ".jpg", ".jpeg", ".tmp"}
            or "screenshot" in file.name.lower()
        )
    }

    class DummyResponse:
        def __init__(self) -> None:
            self.status = 200
            self.headers = {"Content-Type": "application/json"}

        async def json(self) -> dict[str, str]:
            return {"choices": [{"message": {"content": "no persist"}}]}

        async def text(self) -> str:
            return "no persist"

        def raise_for_status(self) -> None:
            return None

    session = AsyncMock()
    session.request.return_value = DummyResponse()

    client = AiWebScraperClient(
        provider_name="provider",
        api_key="key",
        model_name="gpt-4",
        browserless_url="https://example.com/api",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="test",
        extraction_mode="dom",
        session=session,
    )

    await client.async_get_data()

    new_files = {
        file.relative_to(integration_path)
        for file in integration_path.rglob("*")
        if file.is_file()
        and (
            file.suffix.lower() in {".html", ".htm", ".png", ".jpg", ".jpeg", ".tmp"}
            or "screenshot" in file.name.lower()
        )
    }

    assert new_files == known_files
    assert not hasattr(client, "screenshot_path")
    assert not hasattr(client, "html_file")


async def test_block_consent_modals_switch(hass: HomeAssistant) -> None:
    """Test the block consent modals switch entity behavior."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        discovery_keys={},
        options={},
        subentries_data=[],
        unique_id="scraper-entry-id",
        entry_id="scraper-entry-id",
    )
    _add_entry_no_setup(hass, entry)

    coordinator = DummyCoordinator(entry, {})
    switch = AiWebScraperSwitch(
        coordinator=coordinator,
        entity_description=SWITCH_ENTITY_DESCRIPTIONS[0],
    )
    switch.hass = hass
    switch.entity_id = "switch.test_scraper_block_overlays"

    # Defaults to True
    assert switch.is_on is True

    # Turn off
    await switch.async_turn_off()
    assert entry.options["block_consent_modals"] is False

    # Turn on
    await switch.async_turn_on()
    assert entry.options["block_consent_modals"] is True
