# pylint: disable=too-many-lines
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=invalid-name
# pylint: disable=protected-access
# pylint: disable=line-too-long

import logging
from unittest.mock import patch
import pytest

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.template import Template

from custom_components.rs.rs_domain import RsDomain


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
async def test_rs_method_execute(hass: HomeAssistant, rs_domain_switch: RsDomain, caplog):
    method = rs_domain_switch.methods["rs_turn_on"]

    call_data = {"entity_id": ["switch.switch_1"]}
    call = ServiceCall("switch", "rs_turn_on", call_data, None)

    with caplog.at_level(logging.INFO):
        caplog.clear()
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

                assert len(caplog.messages) == 1
                assert str(call_data) in caplog.messages[0]
                assert "rs_turn_on" in caplog.messages[0]

    call_data = {"entity_id": ["switch.switch_1", "switch.switch_2"]}
    call = ServiceCall("switch", "rs_turn_on", call_data, None)

    with caplog.at_level(logging.WARNING):
        caplog.clear()
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

                assert len(caplog.messages) == 1
                assert "rs_turn_on" in caplog.messages[0]
                assert "Retrying service call [1]" in caplog.messages[0]
                assert "call-entities ['switch.switch_1', 'switch.switch_2']" in caplog.messages[0]
                assert "wait-entities ['switch.switch_1']" in caplog.messages[0]

    with patch.object(hass.services, "async_call") as async_call:
        with patch.object(method, "_async_wait_template") as _async_wait_template:
            _async_wait_template.return_value = ["switch.switch_1"]

            with pytest.raises(HomeAssistantError) as hae:
                await method.execute(call)
                assert async_call.call_count == 3
                assert _async_wait_template.call_count == 3
            s = str(hae.value)
            assert "Service call failed [rs_turn_on]" in s
            assert "call-entities ['switch.switch_1', 'switch.switch_2']" in s
            assert "failed-entities ['switch.switch_1']" in s


@pytest.mark.asyncio
async def test_rs_method_async_wait_template(hass: HomeAssistant, rs_domain_climate: RsDomain):
    method = rs_domain_climate.methods["rs_set_temperature"]

    call_data = {
        "entity_id": ["climate.thermo_1", "climate.thermo_2"],
        "temperature": 70,
    }
    call = ServiceCall("climate", "set_temperature", call_data, None)

    with patch("custom_components.rs.rs_method.async_track_template") as async_track_template:
        with patch("custom_components.rs.rs_method.async_template") as async_template:
            async_template.return_value = True
            wait_list = await method._async_wait_template(call.data, 5)
            assert len(wait_list) == 0
            assert async_template.call_count == 2

            assert async_track_template.assert_not_called

            assert len(async_template.mock_calls[0].args) == 4
            assert async_template.mock_calls[0].args[0] is hass
            template = async_template.mock_calls[0].args[1]
            assert (
                template.template == "{{state_attr('climate.thermo_1', 'temperature')|float(0) == temperature|float}}"
            )
            variables = async_template.mock_calls[0].args[2]
            assert len(variables) == 1
            assert variables["temperature"] == 70
            assert async_template.mock_calls[0].args[3] is False

            assert len(async_template.mock_calls[1].args) == 4
            assert async_template.mock_calls[1].args[0] is hass
            template = async_template.mock_calls[1].args[1]
            assert (
                template.template == "{{state_attr('climate.thermo_2', 'temperature')|float(0) == temperature|float}}"
            )
            variables = async_template.mock_calls[1].args[2]
            assert len(variables) == 1
            assert variables["temperature"] == 70
            assert async_template.mock_calls[1].args[3] is False

    call_data = {
        "entity_id": ["climate.thermo_1", "climate.thermo_2"],
        "temperature": 70,
        "hvac_mode": "heat",
    }
    call = ServiceCall("climate", "set_temperature", call_data, None)
    with patch("custom_components.rs.rs_method.async_track_template") as async_track_template:
        with patch("custom_components.rs.rs_method.async_template") as async_template:
            async_template.return_value = True
            wait_list = await method._async_wait_template(call.data, 5)
            assert len(wait_list) == 0
            assert async_template.call_count == 2

            assert len(async_template.mock_calls[0].args) == 4
            assert async_template.mock_calls[0].args[0] is hass
            template = async_template.mock_calls[0].args[1]
            assert (
                template.template
                == "{{state_attr('climate.thermo_1', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_1',hvac_mode)}}"
            )
            variables = async_template.mock_calls[0].args[2]
            assert len(variables) == 2
            assert variables["temperature"] == 70
            assert variables["hvac_mode"] == "heat"
            assert async_template.mock_calls[0].args[3] is False

            assert len(async_template.mock_calls[1].args) == 4
            assert async_template.mock_calls[1].args[0] is hass
            template = async_template.mock_calls[1].args[1]
            assert (
                template.template
                == "{{state_attr('climate.thermo_2', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_2',hvac_mode)}}"
            )
            variables = async_template.mock_calls[1].args[2]
            assert len(variables) == 2
            assert variables["temperature"] == 70
            assert variables["hvac_mode"] == "heat"
            assert async_template.mock_calls[1].args[3] is False


class TemplateMock:
    """Class to mock the template"""

    def __init__(self, timeout: bool):
        self.template: Template = None
        self.hass: HomeAssistant = None
        self.variables = None
        self.my_unsub_count = 0
        self.my_async_track_template_count = 0
        self.timeout = timeout

    def my_async_track_template(self, hass: HomeAssistant, template: Template, action, variables):
        self.hass = hass
        self.template = template
        self.variables = variables
        self.my_async_track_template_count += 1
        if self.timeout is False:
            action("entity_id", "from", "to")
        return self.my_unsub

    def my_unsub(self):
        self.my_unsub_count += 1


async def test_rs_method_async_wait_template_1(hass: HomeAssistant, rs_domain_climate: RsDomain):
    method = rs_domain_climate.methods["rs_set_temperature"]
    call_data = {
        "entity_id": ["climate.thermo_1", "climate.thermo_2"],
        "temperature": 70,
        "hvac_mode": "heat",
    }
    call = ServiceCall("climate", "set_temperature", call_data, None)

    mock = TemplateMock(False)

    with patch(
        "custom_components.rs.rs_method.async_track_template",
        mock.my_async_track_template,
    ):
        with patch(
            "custom_components.rs.rs_method.async_template",
        ) as async_template:
            async_template.return_value = False
            res = await hass.async_create_task(method._async_wait_template(call.data, 5))
            assert mock.my_async_track_template_count == 1
            assert mock.my_unsub_count == 1
            assert (
                mock.template.template
                == "{{state_attr('climate.thermo_1', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_1',hvac_mode) and state_attr('climate.thermo_2', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_2',hvac_mode)}}"
            )
            assert res == []

    mock = TemplateMock(False)
    with patch(
        "custom_components.rs.rs_method.async_track_template",
        mock.my_async_track_template,
    ):
        with patch(
            "custom_components.rs.rs_method.async_template",
        ) as async_template:
            async_template.side_effect = [True, False]
            res = await hass.async_create_task(method._async_wait_template(call.data, 5))
            assert mock.my_async_track_template_count == 1
            assert mock.my_unsub_count == 1
            assert (
                mock.template.template
                == "{{state_attr('climate.thermo_2', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_2',hvac_mode)}}"
            )
            assert res == []

    mock = TemplateMock(True)
    with patch(
        "custom_components.rs.rs_method.async_track_template",
        mock.my_async_track_template,
    ):
        with patch(
            "custom_components.rs.rs_method.async_template",
        ) as async_template:
            async_template.side_effect = [True, False]
            res = await hass.async_create_task(method._async_wait_template(call.data, 1))
            assert mock.my_async_track_template_count == 1
            assert mock.my_unsub_count == 1
            assert (
                mock.template.template
                == "{{state_attr('climate.thermo_2', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_2',hvac_mode)}}"
            )
            assert len(res) == 1
            assert res[0] == "climate.thermo_2"

    mock = TemplateMock(True)
    with patch(
        "custom_components.rs.rs_method.async_track_template",
        mock.my_async_track_template,
    ):
        with patch(
            "custom_components.rs.rs_method.async_template",
        ) as async_template:
            async_template.side_effect = [False, False, False, False]
            res = await hass.async_create_task(method._async_wait_template(call.data, 1))
            assert async_template.call_count == 4
            assert async_template.mock_calls[3]
            assert mock.my_async_track_template_count == 1
            assert mock.my_unsub_count == 1
            assert (
                mock.template.template
                == "{{state_attr('climate.thermo_1', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_1',hvac_mode) and state_attr('climate.thermo_2', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_2',hvac_mode)}}"
            )
            assert len(res) == 2
            assert res[0] == "climate.thermo_1"
            assert res[1] == "climate.thermo_2"

            assert len(async_template.mock_calls[2].args) == 4
            assert async_template.mock_calls[2].args[0] is hass
            template = async_template.mock_calls[2].args[1]
            assert (
                template.template
                == "{{state_attr('climate.thermo_1', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_1',hvac_mode)}}"
            )
            variables = async_template.mock_calls[2].args[2]
            assert len(variables) == 2
            assert variables["temperature"] == 70
            assert variables["hvac_mode"] == "heat"
            assert async_template.mock_calls[2].args[3] is False

            assert len(async_template.mock_calls[3].args) == 4
            assert async_template.mock_calls[3].args[0] is hass
            template = async_template.mock_calls[3].args[1]
            assert (
                template.template
                == "{{state_attr('climate.thermo_2', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_2',hvac_mode)}}"
            )
            variables = async_template.mock_calls[3].args[2]
            assert len(variables) == 2
            assert variables["temperature"] == 70
            assert variables["hvac_mode"] == "heat"
            assert async_template.mock_calls[3].args[3] is False

    mock = TemplateMock(True)
    with patch(
        "custom_components.rs.rs_method.async_track_template",
        mock.my_async_track_template,
    ):
        with patch(
            "custom_components.rs.rs_method.async_template",
        ) as async_template:
            async_template.side_effect = [False, False, False, True]
            res = await hass.async_create_task(method._async_wait_template(call.data, 1))
            assert async_template.call_count == 4
            assert async_template.mock_calls[3]
            assert mock.my_async_track_template_count == 1
            assert mock.my_unsub_count == 1
            assert (
                mock.template.template
                == "{{state_attr('climate.thermo_1', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_1',hvac_mode) and state_attr('climate.thermo_2', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_2',hvac_mode)}}"
            )
            assert len(res) == 1
            assert res[0] == "climate.thermo_1"

            assert len(async_template.mock_calls[2].args) == 4
            assert async_template.mock_calls[2].args[0] is hass
            template = async_template.mock_calls[2].args[1]
            assert (
                template.template
                == "{{state_attr('climate.thermo_1', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_1',hvac_mode)}}"
            )
            variables = async_template.mock_calls[2].args[2]
            assert len(variables) == 2
            assert variables["temperature"] == 70
            assert variables["hvac_mode"] == "heat"
            assert async_template.mock_calls[2].args[3] is False

            assert len(async_template.mock_calls[3].args) == 4
            assert async_template.mock_calls[3].args[0] is hass
            template = async_template.mock_calls[3].args[1]
            assert (
                template.template
                == "{{state_attr('climate.thermo_2', 'temperature')|float(0) == temperature|float and is_state('climate.thermo_2',hvac_mode)}}"
            )
            variables = async_template.mock_calls[3].args[2]
            assert len(variables) == 2
            assert variables["temperature"] == 70
            assert variables["hvac_mode"] == "heat"
            assert async_template.mock_calls[3].args[3] is False
