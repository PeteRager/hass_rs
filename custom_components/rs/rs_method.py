"""Rs entity"""
import asyncio
import logging

import async_timeout

from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.template import Template
from homeassistant.helpers.condition import async_template
from homeassistant.helpers.event import async_track_template

_LOGGER = logging.getLogger(__name__)


class RsMethod:
    """Reliable switch"""

    def __init__(
        self, hass: HomeAssistant, domain, method: str, data: dict[str, dict]
    ) -> None:
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
        _LOGGER.info("execute %s:%s %s", self.domain.domain, self.method, call.data)
        """Handle the service call."""
        success: bool = False
        retry: int = 0
        wait_list: list[str] = call.data.copy()["entity_id"]
        while retry < 3:
            service_data = call.data.copy()
            service_data["entity_id"] = wait_list
            await self.hass.services.async_call(
                self.domain.domain,
                self.target_method,
                service_data,
                True,
            )
            wait_list = await self._async_wait_template(
                service_data, self.timeout * (retry + 1)
            )
            if len(wait_list) == 0:
                success = True
                break
            retry += 1
            _LOGGER.warning(
                "Retrying service call [%d] [%s] call-entities %s wait-entities %s",
                retry,
                self.method,
                call.data["entity_id"],
                wait_list,
            )
        if success is False:
            raise HomeAssistantError(
                f'Service call failed [{self.method}] call-entities {call.data["entity_id"]} failed-entities {wait_list}'
            )

    def _build_template_fragment(self, entity_id: str, call_data) -> str:
        fragments = []
        for _, (par, val) in enumerate(self.conditions.items()):
            if par == "default" or par in call_data:
                fragments.append(val.replace("ENTITY_ID", entity_id))

        template = ""
        for i in range(0, len(fragments)):
            if i != 0:
                template += " and "
            template += fragments[i]
        return template

    def _get_wait_list(self, call_data: dict, variables: dict) -> list[str]:
        wait_list = []
        for entity_id in call_data["entity_id"]:
            template = "{{" + self._build_template_fragment(entity_id, call_data) + "}}"
            wait_template = Template(template, self.hass)
            # check if condition already okay
            if async_template(self.hass, wait_template, variables, False) is False:
                wait_list.append(entity_id)
        return wait_list

    async def _async_wait_template(self, call_data: dict, timeout: int) -> list[str]:
        # Put all the call parameters into variables so they can be used in the condition template
        variables: dict = {}
        for _, (key, val) in enumerate(call_data.items()):
            if key != "entity_id":
                variables[key] = val

        # Get the list of entities whose conditions that are not true that we will wait for
        wait_list = self._get_wait_list(call_data, variables)
        if len(wait_list) == 0:
            return []

        # Build one big template for all the entity ids in the call.
        template = "{{"
        for index, entity_id in enumerate(wait_list):
            if index != 0:
                template += " and "
            template += self._build_template_fragment(entity_id, call_data)
        template += "}}"
        wait_template = Template(template, self.hass)

        @callback
        def async_script_wait(entity_id, from_s, to_s):
            """Handle script after template condition is true."""
            done.set()

        done = asyncio.Event()
        unsub = async_track_template(
            self.hass, wait_template, async_script_wait, variables=variables
        )

        timed_out = False

        task = self.hass.async_create_task(done.wait())
        try:
            async with async_timeout.timeout(timeout) as _:
                await task
        except asyncio.TimeoutError as _:
            timed_out = True
        finally:
            task.cancel()
            unsub()

        if timed_out is True:
            # Determine which entities in the list did not complete and return that list
            # If there was only 1 item to start with, it's still there are we can just return
            if len(wait_list) == 1:
                return wait_list
            return self._get_wait_list(call_data, variables)
        return []
