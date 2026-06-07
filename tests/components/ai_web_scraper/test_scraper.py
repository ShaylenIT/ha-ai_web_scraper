# ruff: noqa: S101
"""Tests for the ai_web_scraper scraper entity behavior."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry

from custom_components.ai_web_scraper import __init__ as integration_init
from custom_components.ai_web_scraper.api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientError,
)
from custom_components.ai_web_scraper.binary_sensor import (
    IntegrationBlueprintBinarySensor,
)
from custom_components.ai_web_scraper.button import (
    ENTITY_DESCRIPTIONS as BUTTON_ENTITY_DESCRIPTIONS,
)
from custom_components.ai_web_scraper.button import (
    IntegrationBlueprintButton,
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
from custom_components.ai_web_scraper.data import IntegrationBlueprintData
from custom_components.ai_web_scraper.sensor import IntegrationBlueprintSensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_coordinator_fetches_scrape_data(hass: HomeAssistant) -> None:
    """Test that coordinator fetches scraper data from runtime_data.client."""
    entry = ConfigEntry(
        version=1,
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
        options={},
        entry_id="scraper-entry-id",
    )
    entry.add_to_hass(hass)

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
        "attributes": {"url": "https://example.com"},
        "error_message": "",
        "last_attempt_status": "success",
    }

    entry.runtime_data = IntegrationBlueprintData(
        client=client,
        integration=None,
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data["state"] == "hello"
    assert coordinator.data["attributes"]["url"] == "https://example.com"
    assert coordinator.data["last_attempt_status"] == "success"


async def test_coordinator_logs_scrape_failure(
    hass: HomeAssistant, caplog: Any
) -> None:
    """Test that coordinator logs failures when scraper data fetch fails."""
    entry = ConfigEntry(
        version=1,
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
        options={},
        entry_id="scraper-entry-id",
    )
    entry.add_to_hass(hass)

    coordinator = AIWebScraperDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name="Test Scraper",
        update_interval=None,
    )
    coordinator.config_entry = entry

    client = AsyncMock()
    client.async_get_data.side_effect = IntegrationBlueprintApiClientError(
        "Missing provider configuration"
    )

    entry.runtime_data = IntegrationBlueprintData(
        client=client,
        integration=None,
        coordinator=coordinator,
    )

    caplog.set_level("ERROR")
    await coordinator.async_config_entry_first_refresh()

    assert "Scraper data fetch failed for Test Scraper" in caplog.text
    assert coordinator.data["last_attempt_status"] == "failure"


class DummyCoordinator:
    """Minimal coordinator stub used by button and sensor tests."""

    def __init__(self, entry: ConfigEntry, data: dict[str, Any]) -> None:
        """Initialize the dummy coordinator."""
        self.config_entry = entry
        self.data = data
        self.async_request_refresh = AsyncMock()


async def test_refresh_button_requests_refresh() -> None:
    """Test that pressing the refresh button requests coordinator refresh."""
    entry = ConfigEntry(
        version=1,
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
        options={},
        entry_id="scraper-entry-id",
    )

    coordinator = DummyCoordinator(entry, {})
    button = IntegrationBlueprintButton(
        coordinator=coordinator,
        entity_description=BUTTON_ENTITY_DESCRIPTIONS[0],
    )

    await button.async_press()

    coordinator.async_request_refresh.assert_awaited_once()


def test_sensor_reports_coordinator_state() -> None:
    """Test that the sensor reports the coordinator state and attributes."""
    entry = ConfigEntry(
        version=1,
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
        options={},
        entry_id="scraper-entry-id",
    )

    state = {
        "state": "parsed result",
        "attributes": {"url": "https://example.com", "scrape_duration_seconds": 1},
    }
    coordinator = DummyCoordinator(entry, state)
    sensor = IntegrationBlueprintSensor(
        coordinator=coordinator,
        entity_description=SensorEntityDescription(
            key="ai_web_scraper_data",
            name="Scraper Data",
        ),
    )

    assert sensor.native_value == "parsed result"
    assert sensor.extra_state_attributes == state["attributes"]


def test_status_binary_sensor_failure_state() -> None:
    """Test the status binary sensor failure state and attributes."""
    entry = ConfigEntry(
        version=1,
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
        options={},
        entry_id="scraper-entry-id",
    )

    state = {
        "state": None,
        "attributes": {"url": "https://example.com"},
        "error_message": "Missing provider",
        "last_attempt_status": "failure",
    }
    coordinator = DummyCoordinator(entry, state)
    binary_sensor = IntegrationBlueprintBinarySensor(
        coordinator=coordinator,
        entity_description=BinarySensorEntityDescription(
            key="ai_web_scraper_status",
            name="Scraper Status",
            device_class="problem",
        ),
    )

    assert binary_sensor.is_on is True
    assert binary_sensor.extra_state_attributes["error_message"] == "Missing provider"
    assert binary_sensor.extra_state_attributes["last_attempt_status"] == "failure"


async def test_build_entry_client_missing_provider_raises_error() -> None:
    """Test that missing provider configuration raises an API error."""
    client = IntegrationBlueprintApiClient(
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
        IntegrationBlueprintApiClientError,
        match="Missing provider configuration",
    ):
        await client.async_get_data()


async def test_client_fetches_page_text_when_no_browserless_url() -> None:
    """Test that the client fetches page text directly when browserless_url is unset."""
    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(return_value="Hello from example.com")

    session = AsyncMock()
    session.get.return_value.__aenter__.return_value = response

    client = IntegrationBlueprintApiClient(
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

    assert data["state"] == "Hello from example.com"
    session.get.assert_awaited_once_with(
        "https://example.com",
        headers={
            "Accept": "text/html",
            "User-Agent": "Mozilla/5.0 (HomeAssistant) ai_web_scraper",
        },
    )


async def test_setup_entry_zero_interval_is_manual_only(
    hass: HomeAssistant,
    monkeypatch: Any,
) -> None:
    """Test that zero interval scrapers are manual-only and do not auto-schedule."""
    provider_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Provider",
        data={
            CONF_ENTRY_TYPE: "provider",
            "provider_name": "Test Provider",
            "api_key": "ok",
            "model_name": "gpt-4",
        },
        source="user",
        options={},
        entry_id="provider-entry-id",
    )
    provider_entry.add_to_hass(hass)

    scraper_entry = ConfigEntry(
        version=1,
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
        options={},
        entry_id="scraper-entry-id",
    )
    scraper_entry.add_to_hass(hass)

    class DummyClient:
        """Dummy API client that returns static scrape data."""

        async def async_get_data(self) -> dict[str, Any]:
            return {
                "state": "hello",
                "attributes": {},
                "error_message": "",
                "last_attempt_status": "success",
            }

    monkeypatch.setattr(integration_init, "IntegrationBlueprintApiClient", DummyClient)

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
        domain=DOMAIN,
        title="Test Provider",
        data={
            CONF_ENTRY_TYPE: "provider",
            CONF_PROVIDER_NAME: "Test Provider",
            CONF_API_KEY: "provider-key",
            CONF_MODEL_NAME: "gpt-4",
        },
        source="user",
        options={},
        entry_id="provider-entry-id",
    )
    provider_entry.add_to_hass(hass)

    scraper_entry = ConfigEntry(
        version=1,
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
        options={},
        entry_id="scraper-entry-id",
    )
    scraper_entry.add_to_hass(hass)

    class DummyClient:
        """Dummy API client that returns static scrape data."""

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

    monkeypatch.setattr(integration_init, "IntegrationBlueprintApiClient", DummyClient)

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
            self.headers = {"Content-Type": "application/json"}

        async def json(self) -> dict[str, str]:
            return {"body": "no persist"}

        async def text(self) -> str:
            return "no persist"

        def raise_for_status(self) -> None:
            return None

    session = AsyncMock()
    session.request.return_value = DummyResponse()

    client = IntegrationBlueprintApiClient(
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
