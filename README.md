# Overview

Reliable Services for Home Assistant

Service calls in Home Assistant don't always succeed the first time.

This may occur when communicating with a wireless device (e.g. zwave) as the command may get lost due to RF interference. Or a cloud service that is temporarily unavailable due to an internet glitch. Regardless of the reason, the end result is the switch doesn't turn on, the light did not turn off, or the heat did not come on.

The purpose of this repository is to provide a layer of reliable services that sit on-top of the home assistant services and will automatically retry and alert when the operations fail.

# Current State

This is the development branch for the python integration to handle reliable services. The code is currently in prototype mode. It does work on the happy path.

Supported methods:

- switch.turn_on, switch.turn_off
- climate.set_hvac_action, climate.set_temperature

The methods are defined in JSON, in the templates/methods.json file. Add new methods to this file.

# Setup and Usage

Copy the rs directory into your custom_component folder.

Using in an automation.

Let's say you have this:

```yaml
- service: climate.set_temperature
  target:
    entity_id: climate.thermostat_1
  data:
    temperature: 70
```

change it to

```yaml
- service: climate.rs_set_temperature
  target:
    entity_id: climate.thermostat_1
  data:
    temperature: 70
```
