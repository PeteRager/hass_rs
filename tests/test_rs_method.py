# pylint: disable=too-many-lines
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=invalid-name
# pylint: disable=protected-access
# pylint: disable=line-too-long

import asyncio
import logging
from unittest.mock import patch
import pytest

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ConditionErrorMessage
from homeassistant.helpers.template import Template

from custom_components.rs.rs_domain import RsDomain
from custom_components.rs.rs_method import RsMethodCallCounters
from custom_components.rs.const import RS_METHOD_EVENT, RS_METHOD_MESSAGE


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
                with patch.object(method, "_publish_events") as _publish_events:
                    with patch.object(method, "_publish_message") as _publish_message:
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
                        wait_list = _async_wait_template.mock_calls[0].args[0]
                        call_data = _async_wait_template.mock_calls[0].args[1]
                        assert len(call_data) == 1
                        assert len(call_data["entity_id"]) == 1
                        assert call_data["entity_id"][0] == "switch.switch_1"
                        assert _async_wait_template.mock_calls[0].args[2] == 5

                        assert len(caplog.messages) == 1
                        assert str(call_data) in caplog.messages[0]
                        assert "rs_turn_on" in caplog.messages[0]

                        _publish_events.assert_called_once()
                        assert len(_publish_events.mock_calls[0].args) == 1
                        call_counters: dict[str, RsMethodCallCounters] = _publish_events.mock_calls[0].args[0]
                        assert len(call_counters) == 1
                        assert call_counters["switch.switch_1"].retry == 0
                        assert call_counters["switch.switch_1"].is_failed is False
                        assert call_counters["switch.switch_1"].is_done is True
                        assert call_counters["switch.switch_1"].duration_ms < 100

                        assert _publish_message.call_count == 2
                        assert len(_publish_message.mock_calls[0].args) == 3
                        assert _publish_message.mock_calls[0].args[0] is call
                        assert _publish_message.mock_calls[0].args[1] == "switch.switch_1"
                        assert _publish_message.mock_calls[0].args[2] == "attempt 1"

                        assert _publish_message.mock_calls[1].args[0] is call
                        assert _publish_message.mock_calls[1].args[1] == "switch.switch_1"
                        assert _publish_message.mock_calls[1].args[2] == "success"

    call_data = {"entity_id": ["switch.switch_1", "switch.switch_2"]}
    call = ServiceCall("switch", "rs_turn_on", call_data, None)

    with caplog.at_level(logging.WARNING):
        caplog.clear()
        with patch.object(hass.services, "async_call") as async_call:
            with patch.object(method, "_async_wait_template") as _async_wait_template:
                with patch.object(method, "_publish_events") as _publish_events:
                    with patch.object(method, "_publish_message") as _publish_message:
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
                        call_data = _async_wait_template.mock_calls[0].args[1]
                        assert len(call_data) == 1
                        assert len(call_data["entity_id"]) == 2
                        assert call_data["entity_id"][0] == "switch.switch_1"
                        assert call_data["entity_id"][1] == "switch.switch_2"
                        assert _async_wait_template.mock_calls[0].args[2] == 5

                        call_data = _async_wait_template.mock_calls[1].args[1]
                        assert len(call_data) == 1
                        assert len(call_data["entity_id"]) == 1
                        assert call_data["entity_id"][0] == "switch.switch_1"
                        assert _async_wait_template.mock_calls[1].args[2] == 10

                        assert len(caplog.messages) == 1
                        assert "rs_turn_on" in caplog.messages[0]
                        assert "Retrying service call [1]" in caplog.messages[0]
                        assert "call-entities ['switch.switch_1', 'switch.switch_2']" in caplog.messages[0]
                        assert "wait-entities ['switch.switch_1']" in caplog.messages[0]

                        _publish_events.assert_called_once()
                        assert len(_publish_events.mock_calls[0].args) == 1
                        call_counters: dict[str, RsMethodCallCounters] = _publish_events.mock_calls[0].args[0]
                        assert len(call_counters) == 2
                        assert call_counters["switch.switch_1"].retry == 1
                        assert call_counters["switch.switch_1"].is_failed is False
                        assert call_counters["switch.switch_1"].is_done is True
                        assert call_counters["switch.switch_1"].duration_ms < 100

                        assert call_counters["switch.switch_2"].retry == 0
                        assert call_counters["switch.switch_2"].is_failed is False
                        assert call_counters["switch.switch_2"].is_done is True
                        assert call_counters["switch.switch_2"].duration_ms < 100

                        assert _publish_message.call_count == 5
                        assert _publish_message.mock_calls[0].args[0] is call
                        assert _publish_message.mock_calls[0].args[1] == "switch.switch_1"
                        assert _publish_message.mock_calls[0].args[2] == "attempt 1"

                        assert _publish_message.mock_calls[1].args[0] is call
                        assert _publish_message.mock_calls[1].args[1] == "switch.switch_2"
                        assert _publish_message.mock_calls[1].args[2] == "attempt 1"

                        assert _publish_message.mock_calls[2].args[0] is call
                        assert _publish_message.mock_calls[2].args[1] == "switch.switch_2"
                        assert _publish_message.mock_calls[2].args[2] == "success"

                        assert _publish_message.mock_calls[3].args[0] is call
                        assert _publish_message.mock_calls[3].args[1] == "switch.switch_1"
                        assert _publish_message.mock_calls[3].args[2] == "attempt 2"

                        assert _publish_message.mock_calls[4].args[0] is call
                        assert _publish_message.mock_calls[4].args[1] == "switch.switch_1"
                        assert _publish_message.mock_calls[4].args[2] == "success"

    with patch.object(hass.services, "async_call") as async_call:
        with patch.object(method, "_async_wait_template") as _async_wait_template:
            with patch.object(method, "_publish_events") as _publish_events:
                with patch.object(method, "_publish_message") as _publish_message:

                    _async_wait_template.return_value = ["switch.switch_1"]

                    with pytest.raises(HomeAssistantError) as hae:
                        await method.execute(call)
                        assert async_call.call_count == 3
                        assert _async_wait_template.call_count == 3
                    s = str(hae.value)
                    assert "Service call failed [rs_turn_on]" in s
                    assert "call-entities ['switch.switch_1', 'switch.switch_2']" in s
                    assert "failed-entities ['switch.switch_1']" in s

                    _publish_events.assert_called_once()
                    assert len(_publish_events.mock_calls[0].args) == 1
                    call_counters: dict[str, RsMethodCallCounters] = _publish_events.mock_calls[0].args[0]
                    assert len(call_counters) == 2
                    assert call_counters["switch.switch_1"].retry == 3
                    assert call_counters["switch.switch_1"].is_failed is True
                    assert call_counters["switch.switch_1"].is_done is True
                    assert call_counters["switch.switch_1"].duration_ms < 100

                    assert call_counters["switch.switch_2"].retry == 0
                    assert call_counters["switch.switch_2"].is_failed is False
                    assert call_counters["switch.switch_2"].is_done is True
                    assert call_counters["switch.switch_2"].duration_ms < 100

                    assert _publish_message.call_count == 6
                    assert _publish_message.mock_calls[0].args[0] is call
                    assert _publish_message.mock_calls[0].args[1] == "switch.switch_1"
                    assert _publish_message.mock_calls[0].args[2] == "attempt 1"

                    assert _publish_message.mock_calls[1].args[0] is call
                    assert _publish_message.mock_calls[1].args[1] == "switch.switch_2"
                    assert _publish_message.mock_calls[1].args[2] == "attempt 1"

                    assert _publish_message.mock_calls[2].args[0] is call
                    assert _publish_message.mock_calls[2].args[1] == "switch.switch_2"
                    assert _publish_message.mock_calls[2].args[2] == "success"

                    assert _publish_message.mock_calls[3].args[0] is call
                    assert _publish_message.mock_calls[3].args[1] == "switch.switch_1"
                    assert _publish_message.mock_calls[3].args[2] == "attempt 2"

                    assert _publish_message.mock_calls[4].args[0] is call
                    assert _publish_message.mock_calls[4].args[1] == "switch.switch_1"
                    assert _publish_message.mock_calls[4].args[2] == "attempt 3"

                    assert _publish_message.mock_calls[5].args[0] is call
                    assert _publish_message.mock_calls[5].args[1] == "switch.switch_1"
                    assert _publish_message.mock_calls[5].args[2] == "failed"

    with patch.object(hass.services, "async_call") as async_call:
        with caplog.at_level(logging.ERROR):
            caplog.clear()
            with patch.object(method, "_async_wait_template") as _async_wait_template:
                with patch.object(method, "_publish_events") as _publish_events:
                    with patch.object(method, "_publish_message") as _publish_message:
                        async_call.side_effect = HomeAssistantError("Service failed to execute")
                        _async_wait_template.return_value = ["switch.switch_1"]
                        with pytest.raises(HomeAssistantError) as hae:
                            await method.execute(call)
                            assert async_call.call_count == 3
                            assert _async_wait_template.call_count == 3
                        s = str(hae.value)
                        assert "Service call failed [rs_turn_on]" in s
                        assert "call-entities ['switch.switch_1', 'switch.switch_2']" in s
                        assert "failed-entities ['switch.switch_1', 'switch.switch_2']" in s

                        assert len(caplog.records) == 3
                        assert "rs_turn_on" in caplog.messages[0]
                        assert "switch.switch_1" in caplog.messages[0]
                        assert "switch.switch_2" in caplog.messages[0]
                        assert "rs_turn_on" in caplog.messages[0]
                        assert "Service failed to execute" in caplog.messages[0]

                        _publish_events.assert_called_once()
                        assert len(_publish_events.mock_calls[0].args) == 1
                        call_counters: dict[str, RsMethodCallCounters] = _publish_events.mock_calls[0].args[0]
                        assert len(call_counters) == 2
                        assert call_counters["switch.switch_1"].retry == 3
                        assert call_counters["switch.switch_1"].errors == 3
                        assert call_counters["switch.switch_1"].is_failed is True
                        assert call_counters["switch.switch_1"].is_done is True
                        assert call_counters["switch.switch_1"].duration_ms < 100

                        assert call_counters["switch.switch_2"].retry == 3
                        assert call_counters["switch.switch_1"].errors == 3
                        assert call_counters["switch.switch_2"].is_failed is True
                        assert call_counters["switch.switch_2"].is_done is True
                        assert call_counters["switch.switch_2"].duration_ms < 100

                        assert _publish_message.call_count == 8
                        assert _publish_message.mock_calls[0].args[0] is call
                        assert _publish_message.mock_calls[0].args[1] == "switch.switch_1"
                        assert _publish_message.mock_calls[0].args[2] == "attempt 1"

                        assert _publish_message.mock_calls[1].args[0] is call
                        assert _publish_message.mock_calls[1].args[1] == "switch.switch_2"
                        assert _publish_message.mock_calls[1].args[2] == "attempt 1"

                        assert _publish_message.mock_calls[2].args[0] is call
                        assert _publish_message.mock_calls[2].args[1] == "switch.switch_1"
                        assert _publish_message.mock_calls[2].args[2] == "attempt 2"

                        assert _publish_message.mock_calls[3].args[0] is call
                        assert _publish_message.mock_calls[3].args[1] == "switch.switch_2"
                        assert _publish_message.mock_calls[3].args[2] == "attempt 2"

                        assert _publish_message.mock_calls[4].args[0] is call
                        assert _publish_message.mock_calls[4].args[1] == "switch.switch_1"
                        assert _publish_message.mock_calls[4].args[2] == "attempt 3"

                        assert _publish_message.mock_calls[5].args[0] is call
                        assert _publish_message.mock_calls[5].args[1] == "switch.switch_2"
                        assert _publish_message.mock_calls[5].args[2] == "attempt 3"

                        assert _publish_message.mock_calls[6].args[0] is call
                        assert _publish_message.mock_calls[6].args[1] == "switch.switch_1"
                        assert _publish_message.mock_calls[6].args[2] == "failed"

                        assert _publish_message.mock_calls[7].args[0] is call
                        assert _publish_message.mock_calls[7].args[1] == "switch.switch_2"
                        assert _publish_message.mock_calls[7].args[2] == "failed"


@pytest.mark.asyncio
async def test_rs_method_async_wait_template(hass: HomeAssistant, rs_domain_climate: RsDomain):
    method = rs_domain_climate.methods["rs_set_temperature"]

    call_data = {
        "entity_id": ["climate.thermo_1", "climate.thermo_2"],
        "temperature": 70,
    }
    call = ServiceCall("climate", "set_temperature", call_data, None)
    wait_list = ["climate.thermo_1", "climate.thermo_2"]

    with patch("custom_components.rs.rs_method.async_track_template") as async_track_template:
        with patch("custom_components.rs.rs_method.async_template") as async_template:
            async_template.return_value = True
            new_wait_list = await method._async_wait_template(wait_list, call.data, 5)
            assert len(new_wait_list) == 0
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
            new_wait_list = await method._async_wait_template(wait_list, call.data, 5)
            assert len(new_wait_list) == 0
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

    # Test having an unparsable template
    call = ServiceCall("climate", "set_temperature", call_data, None)
    method.conditions["temperature"] = "### bad template }}} {{{{}}}}"
    with patch("custom_components.rs.rs_method.async_track_template") as async_track_template:
        with pytest.raises(ConditionErrorMessage):
            new_wait_list = await method._async_wait_template(wait_list, call.data, 5)


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
    wait_list = ["climate.thermo_1", "climate.thermo_2"]
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
            res = await hass.async_create_task(method._async_wait_template(wait_list, call.data, 5))
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
            res = await hass.async_create_task(method._async_wait_template(wait_list, call.data, 5))
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
            res = await hass.async_create_task(method._async_wait_template(wait_list, call.data, 1))
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
            res = await hass.async_create_task(method._async_wait_template(wait_list, call.data, 1))
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
            res = await hass.async_create_task(method._async_wait_template(wait_list, call.data, 1))
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


@pytest.mark.asyncio
async def test_rs_method_call_counters():
    call_counter = RsMethodCallCounters()
    assert call_counter.retry == 0
    assert call_counter.is_failed is False
    assert call_counter.is_done is False
    call_counter.inc_retry()
    assert call_counter.retry == 1
    call_counter.inc_retry()
    assert call_counter.retry == 2
    call_counter.failed()
    assert call_counter.is_failed is True
    assert call_counter.end_time is None
    await asyncio.sleep(1.0)
    call_counter.done()
    assert call_counter.is_done is True
    assert call_counter.end_time is not None
    assert call_counter.duration_ms > 1000
    assert call_counter.duration_ms < 1100

    call_counter = RsMethodCallCounters()
    with pytest.raises(ValueError) as vue:
        _ = call_counter.duration_ms
    assert "End Time is none" in str(vue)


async def test_rs_method_publish_event(hass: HomeAssistant, rs_domain_climate: RsDomain):
    method = rs_domain_climate.methods["rs_set_temperature"]
    call_counters: dict[str, RsMethodCallCounters] = {}
    switch_1_counter = RsMethodCallCounters()
    call_counters["switch.switch_1"] = switch_1_counter
    switch_2_counter = RsMethodCallCounters()
    call_counters["switch.switch_2"] = switch_2_counter
    switch_3_counter = RsMethodCallCounters()
    call_counters["switch.switch_3"] = switch_3_counter

    switch_1_counter.done()
    switch_2_counter.inc_retry()
    switch_2_counter.done()
    switch_3_counter.inc_retry()
    switch_3_counter.inc_retry()
    switch_3_counter.inc_retry()
    switch_3_counter.done()
    switch_3_counter.failed()

    with patch.object(hass.bus, "async_fire") as fire_event:
        method._publish_events(call_counters)
        assert fire_event.call_count == 3
        assert len(fire_event.mock_calls[0].args) == 2
        assert fire_event.mock_calls[0].args[0] == RS_METHOD_EVENT

        event: dict = fire_event.mock_calls[0].args[1]
        assert event["rs_method"] == "rs_set_temperature"
        assert event["target_method"] == "set_temperature"
        assert event["entity_id"] == "switch.switch_1"
        assert event["start_time"] == switch_1_counter.start_time
        assert event["end_time"] == switch_1_counter.end_time
        assert event["duration_ms"] == switch_1_counter.duration_ms
        assert event["retry"] == 0
        assert event["failed"] is False

        event: dict = fire_event.mock_calls[1].args[1]
        assert event["rs_method"] == "rs_set_temperature"
        assert event["target_method"] == "set_temperature"
        assert event["entity_id"] == "switch.switch_2"
        assert event["start_time"] == switch_2_counter.start_time
        assert event["end_time"] == switch_2_counter.end_time
        assert event["duration_ms"] == switch_2_counter.duration_ms
        assert event["retry"] == 1
        assert event["failed"] is False

        event: dict = fire_event.mock_calls[2].args[1]
        assert event["rs_method"] == "rs_set_temperature"
        assert event["target_method"] == "set_temperature"
        assert event["entity_id"] == "switch.switch_3"
        assert event["start_time"] == switch_3_counter.start_time
        assert event["end_time"] == switch_3_counter.end_time
        assert event["duration_ms"] == switch_3_counter.duration_ms
        assert event["retry"] == 3
        assert event["failed"] is True


async def test_rs_method_publish_message(hass: HomeAssistant, rs_domain_climate: RsDomain):
    method = rs_domain_climate.methods["rs_set_temperature"]
    call_data = {
        "entity_id": ["climate.thermo_1", "climate.thermo_2"],
        "temperature": 70,
    }
    call = ServiceCall("climate", "set_temperature", call_data, None)

    with patch.object(hass.bus, "async_fire") as fire_event:
        method._publish_message(call, "climate.thermo_2", "success")
        assert fire_event.call_count == 1
        assert len(fire_event.mock_calls[0].args) == 2
        assert fire_event.mock_calls[0].args[0] == RS_METHOD_MESSAGE

        event: dict = fire_event.mock_calls[0].args[1]
        assert event["rs_method"] == "rs_set_temperature"
        assert event["target_method"] == "set_temperature"
        assert event["entity_id"] == "climate.thermo_2"
        assert event["message"] == "success"
        assert event["parameters"] == "70"

    call_data = {"entity_id": ["climate.thermo_1", "climate.thermo_2"], "temperature": 70, "hvac_mode": "heat"}
    call = ServiceCall("climate", "set_temperature", call_data, None)

    with patch.object(hass.bus, "async_fire") as fire_event:
        method._publish_message(call, "climate.thermo_2", "success")
        assert fire_event.call_count == 1
        assert len(fire_event.mock_calls[0].args) == 2
        assert fire_event.mock_calls[0].args[0] == RS_METHOD_MESSAGE

        event: dict = fire_event.mock_calls[0].args[1]
        assert event["rs_method"] == "rs_set_temperature"
        assert event["target_method"] == "set_temperature"
        assert event["entity_id"] == "climate.thermo_2"
        assert event["message"] == "success"
        assert event["parameters"] == "70 heat"

    call_data = {"entity_id": ["climate.thermo_1", "climate.thermo_2"]}
    call = ServiceCall("climate", "set_temperature", call_data, None)

    with patch.object(hass.bus, "async_fire") as fire_event:
        method._publish_message(call, "climate.thermo_2", "success")
        assert fire_event.call_count == 1
        assert len(fire_event.mock_calls[0].args) == 2
        assert fire_event.mock_calls[0].args[0] == RS_METHOD_MESSAGE

        event: dict = fire_event.mock_calls[0].args[1]
        assert event["rs_method"] == "rs_set_temperature"
        assert event["target_method"] == "set_temperature"
        assert event["entity_id"] == "climate.thermo_2"
        assert event["message"] == "success"
        assert event["parameters"] == ""
