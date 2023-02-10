# pylint: disable=too-many-lines
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=invalid-name
# pylint: disable=protected-access
# pylint: disable=line-too-long

from unittest.mock import patch
import pytest
from custom_components.rs.rs_domain import RsDomain


@pytest.mark.asyncio
async def test_rs_domain(hass, caplog):
    methods = {
        "rs_set_temperature": {
            "target_method": "set_temperature",
            "conditions": {
                "default": "state_attr('ENTITY_ID', 'temperature')|float == temperature|float",
                "temperature": "state_attr('ENTITY_ID', 'temperature')|float == temperature|float",
                "hvac_mode": "is_state('ENTITY_ID',hvac_mode)",
            },
            "timeout": 5,
        },
        "rs_set_hvac_mode": {
            "target_method": "set_hvac_mode",
            "conditions": {"default": "is_state('ENTITY_ID',hvac_mode)"},
            "timeout": 5,
        },
    }

    rs_domain = RsDomain(hass, "climate", methods)
    assert rs_domain.hass is hass
    assert rs_domain.domain == "climate"
    assert len(rs_domain.methods) == 2

    with patch("custom_components.rs.rs_method.RsMethod.async_register") as register:
        await rs_domain.async_register()
        assert register.call_count == 2
        assert len(register.mock_calls[0].args) == 0
        assert len(register.mock_calls[1].args) == 0
