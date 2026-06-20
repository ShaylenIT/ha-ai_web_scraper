"""Pytest conftest for ai_web_scraper tests."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# Ensure the project root is on sys.path so that
# custom_components.ai_web_scraper can be imported
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(autouse=True)
def _(enable_custom_integrations: None) -> None:
    """Enable loading of the ai_web_scraper custom integration."""
    return
