# pylint: disable=too-many-lines
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=invalid-name
# pylint: disable=protected-access
# pylint: disable=line-too-long

from unittest.mock import patch
import pytest
from custom_components.rs.rs_method import RsMethod
from custom_components.rs.rs_domain import RsDomain
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError


@pytest.mark.asyncio
async def test_rs_method_init(hass, rs_domain_switch: RsDomain):
    method = rs_domain_switch.methods["rs_turn_on"]
    assert method.hass is hass
    assert method.domain is rs_domain_switch
    assert method.target_method == "turn_on"
    assert len(method.conditions) == 1
    assert method.conditions["default"] == "is_state('ENTITY_ID', 'on')"
    assert method.timeout == 5


@pytest.mark.asyncio
async def test_rs_method_register(hass: HomeAssistant, rs_domain_switch: RsDomain):
    method = rs_domain_switch.methods["rs_turn_on"]

    with patch.object(hass.services, "async_register") as async_register:
        await method.async_register()
        assert async_register.call_count == 1
        assert len(async_register.mock_calls[0].args) == 3
        assert async_register.mock_calls[0].args[0] == "switch"
        assert async_register.mock_calls[0].args[1] == "rs_turn_on"
        assert async_register.mock_calls[0].args[2] == method.execute


@pytest.mark.asyncio
async def test_rs_method_execute(hass: HomeAssistant, rs_domain_switch: RsDomain):
    method = rs_domain_switch.methods["rs_turn_on"]

    call_data = {"entity_id": ["switch.switch_1"]}
    call = ServiceCall("switch", "rs_turn_on", call_data, None)

    with patch.object(hass.services, "async_call") as async_call:
        with patch.object(method, "_async_wait_template") as _async_wait_template:
            _async_wait_template.return_value = []
            await method.execute(call)
            assert async_call.call_count == 1
            assert len(async_call.mock_calls[0].args) == 4
            assert async_call.mock_calls[0].args[0] == "switch"
            assert async_call.mock_calls[0].args[1] == "turn_on"
            call_data = async_call.mock_calls[0].args[2]
            assert len(call_data) == 1
            assert len(call_data["entity_id"]) == 1
            assert call_data["entity_id"][0] == "switch.switch_1"

            assert _async_wait_template.call_count == 1
            call_data = _async_wait_template.mock_calls[0].args[0]
            assert len(call_data) == 1
            assert len(call_data["entity_id"]) == 1
            assert call_data["entity_id"][0] == "switch.switch_1"
            assert _async_wait_template.mock_calls[0].args[1] == 5

    call_data = {"entity_id": ["switch.switch_1", "switch.switch_2"]}
    call = ServiceCall("switch", "rs_turn_on", call_data, None)

    with patch.object(hass.services, "async_call") as async_call:
        with patch.object(method, "_async_wait_template") as _async_wait_template:
            _async_wait_template.side_effect = [["switch.switch_1"], []]
            await method.execute(call)
            assert async_call.call_count == 2
            assert len(async_call.mock_calls[0].args) == 4
            assert async_call.mock_calls[0].args[0] == "switch"
            assert async_call.mock_calls[0].args[1] == "turn_on"
            call_data = async_call.mock_calls[0].args[2]
            assert len(call_data) == 1
            assert len(call_data["entity_id"]) == 2
            assert call_data["entity_id"][0] == "switch.switch_1"
            assert call_data["entity_id"][1] == "switch.switch_2"

            assert len(async_call.mock_calls[1].args) == 4
            assert async_call.mock_calls[1].args[0] == "switch"
            assert async_call.mock_calls[1].args[1] == "turn_on"
            call_data = async_call.mock_calls[1].args[2]
            assert len(call_data) == 1
            assert len(call_data["entity_id"]) == 1
            assert call_data["entity_id"][0] == "switch.switch_1"

            assert _async_wait_template.call_count == 2
            call_data = _async_wait_template.mock_calls[0].args[0]
            assert len(call_data) == 1
            assert len(call_data["entity_id"]) == 2
            assert call_data["entity_id"][0] == "switch.switch_1"
            assert call_data["entity_id"][1] == "switch.switch_2"
            assert _async_wait_template.mock_calls[0].args[1] == 5

            call_data = _async_wait_template.mock_calls[1].args[0]
            assert len(call_data) == 1
            assert len(call_data["entity_id"]) == 1
            assert call_data["entity_id"][0] == "switch.switch_1"
            assert _async_wait_template.mock_calls[1].args[1] == 10

    with patch.object(hass.services, "async_call") as async_call:
        with patch.object(method, "_async_wait_template") as _async_wait_template:
            _async_wait_template.return_value = ["switch.switch_1"]

            with pytest.raises(HomeAssistantError) as hae:
                await method.execute(call)
                assert async_call.call_count == 3
                assert _async_wait_template.call_count == 3
