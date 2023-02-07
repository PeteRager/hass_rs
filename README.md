# Reliable Services for Home Assistant

Service calls in Home Assistant don't always succeed the first time.

This may occur when communicating with a wireless device (e.g. zwave) as the command may get lost due to RF interference. Or a cloud service that is temporarily unavailable due to an internet glitch. Regardless of the reason, the end result is the switch doesn't turn on, the light did not turn off, or the heat did not come on.

The purpose of this repository is to provide a layer of reliable services that sit on-top of the home assistant services and will automatically retry and alert when the operations fail.

# How does it work

Wrappers are created for exisitng domain service calls (e.g. switch.turn_on)
The wrapper
- executes the service call
- waits for the expected condition to become true with a configurable timeout (e.g. the switch is on)
- if it timesout it will retry the service call up to 2 more times, while doubling the timeout
- if it does not succeed a notification can be sent

In addtion for each entity, it tracks the following information
- number of calls
- number of retries
- number of failures
- datetime of last call
- duration in ms of the call (wing to wing time - from service call to receiving the state update)
- status text

Generates a lovelace dashboard to visualize the aboe metrics

# Current State

The first iteration provide a shell script that will generate the reliable service stubs for the entities you identify. The end result is a set of packages and scripts than can be installed as part of your HASS configuration. Long term this will be converted into a custom integration, but for now the ability to quickly and extend by creating HASS scripts will be helpful as we work to understand the different patterns and nuances.

Supported methods:

- switch.turn_on, switch.turn_off
- fan.turn_on w/ percentage, fan.turn_off
- climate.set_hvac_action, climate.set_temperature w/ temperature

 If you need ither ones open an issue or better add it to the module_scripts.sh and open a pull request.

# Setup and Usage

You will need a linux shell, ability to edit scripts. Right now this is targeted for the power user.

You will need jq and yq installed.

Copy the test.sh script and edit it to define your entities. Examples are in there for switch, fan and climate.

Set the target directory for the output. I don't set this directly to HASS, but rather to a seperate directory so I can see what is generated before deploying it.

When you run the scripts it will generate packages in the $TARGET/packages folder, scripts in the $TARGET/scripts folder and a lovelace dashboard in $TARGET/.storage

To use the lovelace dashboard, first in HASS create a dashboard called services, go edit it and take control and then save it. This dashboard is automatically populated with your reliable service. Copy the generated dashboard into the .storage folder.

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
  - service: script.rs_thermostat_1_climate_set_temperature
    data:
      temperature: 70
```
