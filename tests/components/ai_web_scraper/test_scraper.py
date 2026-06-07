"""Tests for the ai_web_scraper scraper entity behavior."""

from pathlib import Path
from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorEntityDescription

from custom_components.ai_web_scraper.button import (
    ENTITY_DESCRIPTIONS as BUTTON_ENTITY_DESCRIPTIONS,
    IntegrationBlueprintButton,
)
from custom_components.ai_web_scraper.binary_sensor import IntegrationBlueprintBinarySensor
from custom_components.ai_web_scraper.const import (
    CONF_ENTRY_TYPE,
    CONF_PROVIDER_ID,
    CONF_SCRAPER_NAME,
    CONF_URL,
    CONF_PROMPT,
    CONF_EXTRACTION_MODE,
    CONF_INTERVAL_SECONDS,
    DOMAIN,
    ENTRY_TYPE_SCRAPER,
)
from custom_components.ai_web_scraper.coordinator import AIWebScraperDataUpdateCoordinator
from custom_components.ai_web_scraper.const import LOGGER
from custom_components.ai_web_scraper.data import IntegrationBlueprintData
from custom_components.ai_web_scraper.sensor import (
    ENTITY_DESCRIPTIONS as SENSOR_ENTITY_DESCRIPTIONS,
    IntegrationBlueprintSensor,
)
from custom_components.ai_web_scraper.api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientError,
)
from custom_components.ai_web_scraper import __init__ as integration_init


async def test_coordinator_fetches_scrape_data(hass):
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


class DummyCoordinator:
    def __init__(self, entry, data):
        self.config_entry = entry
        self.data = data
        self.async_request_refresh = AsyncMock()


async def test_refresh_button_requests_refresh():
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


def test_sensor_reports_coordinator_state():
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


def test_status_binary_sensor_failure_state():
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


async def test_build_entry_client_missing_provider_raises_error():
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

    try:
        await client.async_get_data()
    except IntegrationBlueprintApiClientError as exception:
        assert "Missing provider configuration" in str(exception)
    else:
        raise AssertionError("Expected IntegrationBlueprintApiClientError")


async def test_setup_entry_zero_interval_is_manual_only(hass, monkeypatch):
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
        def __init__(self, *args, **kwargs):
            pass

        async def async_get_data(self):
            return {
                "state": "hello",
                "attributes": {},
                "error_message": "",
                "last_attempt_status": "success",
            }

    monkeypatch.setattr(integration_init, "IntegrationBlueprintApiClient", DummyClient)
    monkeypatch.setattr(integration_init, "async_get_loaded_integration", lambda hass, domain: None)

    result = await integration_init.async_setup_entry(hass, scraper_entry)
    assert result is True
    assert scraper_entry.runtime_data.coordinator.update_interval is None


async def test_setup_entry_creates_scraper_entities_and_initial_scrape(hass, monkeypatch):
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
        def __init__(self, *args, **kwargs):
            self.async_get_data = AsyncMock(
                return_value={
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
            )

    monkeypatch.setattr(integration_init, "IntegrationBlueprintApiClient", DummyClient)
    monkeypatch.setattr(integration_init, "async_get_loaded_integration", lambda hass, domain: None)

    forward_setups = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", forward_setups)

    result = await integration_init.async_setup_entry(hass, scraper_entry)

    assert result is True
    forward_setups.assert_awaited_once_with(scraper_entry, integration_init.PLATFORMS)
    assert scraper_entry.runtime_data.coordinator.data["state"] == "hello"
    assert (
        scraper_entry.runtime_data.coordinator.data["attributes"]["provider_name"]
        == "Test Provider"
    )


async def test_scraper_privacy_does_not_persist_files(monkeypatch):
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

    client = IntegrationBlueprintApiClient(
        provider_name="provider",
        api_key="key",
        model_name="gpt-4",
        browserless_url="",
        scraper_name="Test Scraper",
        url="https://example.com",
        prompt="test",
        extraction_mode="dom",
        session=AsyncMock(),
    )

    client._api_wrapper = AsyncMock(return_value={"body": "no persist"})

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
