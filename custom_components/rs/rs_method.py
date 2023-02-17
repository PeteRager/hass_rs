"""Rs entity"""
# pylint: disable=line-too-long

import asyncio
import logging
import time

import async_timeout

from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.template import Template
from homeassistant.helpers.condition import async_template
from homeassistant.helpers.event import async_track_template

from .const import (
    RS_MESSAGE_CALL_ATTEMPT,
    RS_MESSAGE_CALL_FAILED,
    RS_MESSAGE_CALL_SUCCESS,
    RS_METHOD_EVENT,
    RS_METHOD_MESSAGE,
)

_LOGGER = logging.getLogger(__name__)


class RsMethodCallCounters:
    """Class to track method call counters"""

    def __init__(self) -> None:
        self.start_time: float = time.time()
        self.retry: int = 0
        self.errors: int = 0
        self.is_failed: bool = False
        self.end_time: float = None

    def inc_retry(self) -> None:
        """Increment retry"""
        self.retry += 1

    def inc_errors(self) -> None:
        """Increment retry"""
        self.errors += 1

    @property
    def is_done(self) -> bool:
        """Is method call complete"""
        return self.end_time is not None

    def done(self) -> None:
        """Mark as complete"""
        self.end_time = time.time()

    def failed(self) -> None:
        """Mark failed"""
        self.is_failed = True

    @property
    def duration_ms(self) -> int:
        """Return the duration"""
        if self.end_time is None:
            raise ValueError("End Time is none")
        return round((self.end_time - self.start_time) * 1000, 0)


class RsMethod:
    """Reliable switch"""

    def __init__(self, hass: HomeAssistant, domain, method: str, data: dict[str, dict]) -> None:
        """Init"""
        self.hass: HomeAssistant = hass
        self.domain = domain
        self.method: str = method
        self.target_method: str = data["target_method"]
        self.conditions: dict[str, str] = data["conditions"]
        self.timeout: int = data["timeout"]

    async def async_register(self):
        """Asumc register"""
        self.hass.services.async_register(self.domain.domain, self.method, self.execute)

    async def execute(self, call: ServiceCall):
        """Handle the service call."""
        _LOGGER.info("execute %s:%s %s", self.domain.domain, self.method, call.data)
        success: bool = False
        retry: int = 0
        wait_list: list[str] = call.data.copy()["entity_id"]
        call_counters: dict[str, RsMethodCallCounters] = {}
        for entity_id in wait_list:
            call_counters[entity_id] = RsMethodCallCounters()
        while retry < 3:
            if retry > 0:
                _LOGGER.warning(
                    "Retrying service call [%d] [%s] call-entities %s wait-entities %s",
                    retry,
                    self.method,
                    call.data["entity_id"],
                    wait_list,
                )
            service_data = call.data.copy()
            service_data["entity_id"] = wait_list
            self._publish_call_attempt(call, wait_list, retry)
            try:
                await self.hass.services.async_call(self.domain.domain, self.target_method, service_data, True)
                wait_list = await self._async_wait_template(wait_list, service_data, self.timeout * (retry + 1))
            except Exception as ex:  # pylint: disable=broad-except
                # Right now if we get an error we will retry anyways
                _LOGGER.error("execute %s:%s %s error: %s", self.domain.domain, self.method, call.data, ex)
                self._wait_list_inc_errors(call_counters, wait_list)

            self._update_call_counters_after_wait(call, call_counters, wait_list)

            if len(wait_list) == 0:
                success = True
                break
            retry += 1
        for _, (entity_id, call_counter) in enumerate(call_counters.items()):
            if call_counter.is_done is False:
                call_counter.done()
                call_counter.failed()
                self._publish_call_failed(call, entity_id)

        self._publish_events(call_counters)
        if success is False:
            raise HomeAssistantError(
                f'Service call failed [{self.method}] call-entities {call.data["entity_id"]} failed-entities {wait_list}'
            )

    def _wait_list_inc_errors(self, call_counters: dict[str, RsMethodCallCounters], wait_list: list[str]) -> None:
        for entity_id in wait_list:
            call_counters[entity_id].inc_errors()

    def _update_call_counters_after_wait(
        self, call: ServiceCall, call_counters: dict[str, RsMethodCallCounters], wait_list: list[str]
    ) -> None:
        for _, (entity_id, call_counter) in enumerate(call_counters.items()):
            if entity_id in wait_list:
                call_counter.inc_retry()
            elif call_counter.is_done is False:
                call_counter.done()
                self._publish_call_success(call, entity_id)

    def _build_template_fragment(self, entity_id: str, call_data) -> str:
        fragments = []
        for _, (par, val) in enumerate(self.conditions.items()):
            if par == "default" or par in call_data:
                fragments.append(val.replace("ENTITY_ID", entity_id))

        template = ""
        for i in range(0, len(fragments)):  # pylint: disable=consider-using-enumerate
            if i != 0:
                template += " and "
            template += fragments[i]
        return template

    def _create_wait_list_template(self, wait_list: list[str], call_data) -> str:
        template = "{{"
        for index, entity_id in enumerate(wait_list):
            if index != 0:
                template += " and "
            template += self._build_template_fragment(entity_id, call_data)
        template += "}}"
        return template

    def _get_wait_list(self, wait_list: list[str], call_data: dict, variables: dict) -> list[str]:
        new_wait_list: list[str] = []
        for entity_id in wait_list:
            template = "{{" + self._build_template_fragment(entity_id, call_data) + "}}"
            _LOGGER.debug("_get_wait_list entity %s template %s", entity_id, template)
            wait_template = Template(template, self.hass)
            # check if condition already okay
            if async_template(self.hass, wait_template, variables, False) is False:
                new_wait_list.append(entity_id)
        _LOGGER.debug("_get_wait_list returning new_wait_list %s", new_wait_list)
        return new_wait_list

    async def _async_wait_template(self, wait_list: list[str], call_data: dict, timeout: int) -> list[str]:
        # Put all the call parameters into variables so they can be used in the condition template
        variables: dict = {}
        for _, (key, val) in enumerate(call_data.items()):
            if key != "entity_id":
                variables[key] = val

        # Get the list of entities whose conditions that are not true that we will wait for
        wait_list = self._get_wait_list(wait_list, call_data, variables)
        if len(wait_list) == 0:
            return []

        # Build one big template for all the entity ids in the call.
        template = self._create_wait_list_template(wait_list, call_data)
        wait_template = Template(template, self.hass)
        _LOGGER.debug("_async_wait_template wait_template [%s]", wait_template)

        @callback
        def async_script_wait(entity_id, from_s, to_s):  # pylint: disable=unused-argument
            """Handle script after template condition is true."""
            done.set()

        done = asyncio.Event()
        timed_out = False

        unsub = async_track_template(self.hass, wait_template, async_script_wait, variables=variables)
        task = self.hass.async_create_task(done.wait())
        try:
            async with async_timeout.timeout(timeout) as _:
                await task
        except asyncio.TimeoutError as _:
            timed_out = True
        task.cancel()
        unsub()

        if timed_out is True:
            # Determine which entities in the list did not complete and return that list
            # If there was only 1 item to start with, it's still there are we can just return
            if len(wait_list) == 1:
                return wait_list
            return self._get_wait_list(wait_list, call_data, variables)
        return []

    def _publish_events(self, call_counters: dict[str, RsMethodCallCounters]):
        for _, (entity_id, counter) in enumerate(call_counters.items()):
            event = {
                "rs_method": self.method,
                "target_method": self.target_method,
                "entity_id": entity_id,
                "start_time": counter.start_time,
                "end_time": counter.end_time,
                "duration_ms": counter.duration_ms,
                "retry": counter.retry,
                "failed": counter.is_failed,
            }
            _LOGGER.debug("_publish_events event %s", event)
            self.hass.bus.async_fire(RS_METHOD_EVENT, event)

    def _publish_call_attempt(self, call: ServiceCall, entity_list: list[str], retry: int):
        message = f"{RS_MESSAGE_CALL_ATTEMPT} {retry+1}"
        for entity_id in entity_list:
            self._publish_message(call, entity_id, message)

    def _publish_call_success(self, call: ServiceCall, entity_id: str):
        self._publish_message(call, entity_id, RS_MESSAGE_CALL_SUCCESS)

    def _publish_call_failed(self, call: ServiceCall, entity_id: str):
        self._publish_message(call, entity_id, RS_MESSAGE_CALL_FAILED)

    def _publish_message(self, call: ServiceCall, entity_id: str, message: str):
        parameters: str = ""
        for _, (parameter, val) in enumerate(call.data.items()):
            if parameter != "entity_id":
                if len(parameters) > 0:
                    parameters = parameters + " "
                parameters = parameters + str(val)
        event = {
            "rs_method": self.method,
            "target_method": self.target_method,
            "entity_id": entity_id,
            "message": message,
            "parameters": parameters,
        }
        _LOGGER.debug("_publish_message event %s", event)
        self.hass.bus.async_fire(RS_METHOD_MESSAGE, event)
