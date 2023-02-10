"""Rs entity"""
import asyncio

import async_timeout

from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.template import Template
from homeassistant.helpers.condition import async_template
from homeassistant.helpers.event import async_track_template


class RsMethod:
    """Reliable switch"""

    def __init__(
        self, hass: HomeAssistant, domain, method: str, data: dict[str, dict]
    ) -> None:
        """Init"""
        self.hass = hass
        self.domain = domain
        self.method = method
        self.target_method: str = data["target_method"]
        self.conditions: dict[str, str] = data["conditions"]
        self.timeout: int = data["timeout"]
        self.data = data

    async def async_register(self):
        """Asumc register"""
        self.hass.services.async_register(self.domain.domain, self.method, self.execute)

    async def execute(self, call: ServiceCall):
        """Handle the service call."""
        success: bool = False
        retry: int = 1
        wait_list: list[str] = call.data.copy()["entity_id"]
        while retry <= 3:
            service_data = call.data.copy()
            service_data["entity_id"] = wait_list
            await self.hass.services.async_call(
                self.domain.domain,
                self.target_method,
                service_data=service_data,
                blocking=True,
            )
            wait_list = await self._async_wait_template(call.data, self.timeout * retry)
            if len(wait_list) == 0:
                success = True
                break
            retry += 1
        if success is False:
            raise HomeAssistantError("Failed to execute service call")

    def _build_template_fragment(self, entity_id: str, call_data) -> str:
        fragments = []
        for _, (par, val) in enumerate(self.conditions.items()):
            if par == "default" or par in call_data:
                fragments.append(val.replace("ENTITY_ID", entity_id))

        template = ""
        for i in (0, len(fragments) - 1):
            if i != 0:
                template += " and "
            template += fragments[i]
        return template

    async def _async_wait_template(self, call_data: dict, timeout: int) -> list[str]:

        variables: dict = {}
        for _, (key, val) in enumerate(call_data.items()):
            if key != "entity_id":
                variables[key] = val

        wait_list = []

        for entity_id in call_data["entity_id"]:
            template = "{{" + self._build_template_fragment(entity_id, call_data) + "}}"
            wait_template = Template(template, self.hass)
            # check if condition already okay
            if async_template(self.hass, wait_template, variables, False) is False:
                wait_list.append(entity_id)

        if len(wait_list) == 0:
            return []

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

        completed = True
        unsub = async_track_template(
            self.hass, wait_template, async_script_wait, variables=variables
        )

        # self._changed()
        done = asyncio.Event()
        tasks = [self.hass.async_create_task(done.wait())]
        try:
            async with async_timeout.timeout(timeout) as _:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        except asyncio.TimeoutError as _:
            completed = False
        finally:
            for task in tasks:
                task.cancel()
            unsub()

        if completed is False:
            if len(wait_list) == 1:
                return wait_list
            wait_list = []
            for entity_id in call_data["entity_id"]:
                # check if condition already okay
                variables: dict = {}
                variables["entity_id"] = entity_id
                if async_template(self.hass, wait_template, variables, False) is False:
                    wait_list.append(entity_id)
            return wait_list
        return []