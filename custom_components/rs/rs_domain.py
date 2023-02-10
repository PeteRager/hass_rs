"""Rs entity"""

from homeassistant.core import HomeAssistant
from .rs_method import RsMethod


class RsDomain:
    """Reliable switch"""

    def __init__(
        self, hass: HomeAssistant, domain: str, method_list: dict[str, dict]
    ) -> None:
        """Init"""
        self.hass = hass
        self.domain = domain
        self.methods: dict[str, RsMethod] = {}
        for _, method_name in enumerate(method_list):
            met = RsMethod(hass, self, method_name, method_list[method_name])
            self.methods[method_name] = met

    async def async_register(self):
        """register"""
        for _, method in enumerate(self.methods.values()):
            await method.async_register()
