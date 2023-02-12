"""template conftest."""
# pylint: disable=logging-not-lazy
# pylint: disable=logging-fstring-interpolation
# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access
import json
import logging
import os
from unittest.mock import patch

import pytest


from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import (
    assert_setup_component,
    async_mock_service,
)

from custom_components.rs.rs_domain import RsDomain

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def calls(hass):
    """Track calls to a mock service."""
    return async_mock_service(hass, "test", "automation")


@pytest.fixture
async def start_ha(hass, domains, caplog):
    """Do setup of integration."""
    for domain, value in domains.items():
        with assert_setup_component(value["count"], domain):
            assert await async_setup_component(
                hass,
                domain,
                value["config"],
            )
            await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()


@pytest.fixture
async def caplog_setup_text(caplog):
    """Return setup log of integration."""
    yield caplog.text


def loadfile(name: str, sysId: str = None) -> json:
    script_dir = os.path.dirname(__file__) + "/messages/"
    file_path = os.path.join(script_dir, name)
    with open(file_path) as f:
        data = json.load(f)
    if sysId is not None:
        data["SenderID"] = sysId
    return data


@pytest.fixture
def switch_json() -> dict:
    return {
        "switch": {
            "rs_turn_on": {
                "target_method": "turn_on",
                "conditions": {"default": "is_state('ENTITY_ID', 'on')"},
                "timeout": 5,
            },
            "rs_turn_off": {
                "target_method": "turn_off",
                "conditions": {"default": "is_state('ENTITY_ID', 'off')"},
                "timeout": 5,
            },
        }
    }


@pytest.fixture
def rs_domain_switch(hass, switch_json) -> RsDomain:
    domain = RsDomain(hass, "switch", switch_json["switch"])
    return domain
