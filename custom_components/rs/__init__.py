"""ddd"""
import json
import pkgutil

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .rs_domain import RsDomain

DOMAIN = "rs"

ATTR_NAME = "name"
DEFAULT_NAME = "World"

SWITCH_KEYS: list[str] = []

entity_schema = vol.Schema(
    {
        vol.Required("entity_id"): cv.string,
        vol.Optional("timeout"): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema({vol.Optional("entities"): [entity_schema]}),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""
    hass.data[DOMAIN] = {}
    if config.get(DOMAIN) is None:
        return True

    method_data = json.loads(pkgutil.get_data(__name__, "templates/methods.json"))
    for _, (domain, methods) in enumerate(method_data.items()):
        domain = RsDomain(hass, domain, methods)
        await domain.async_register()

    #    entities = config.get(DOMAIN).get("entities")
    #    for i, entity in enumerate(entities):
    return True
