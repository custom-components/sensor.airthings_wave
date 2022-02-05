# sensor.airthings_wave
[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![custom_updater][customupdaterbadge]][customupdater]
[![License][license-shield]](LICENSE.md)

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
[![BuyMeCoffee][buymebeerbadge]][buymebeer]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

hassio support for Airthings Wave, Airthings Wave Plus, and Airthings Wave Mini BLE environmental sensors.

![ScreenShot](ScreenShot.png)

Much of the code to build this component was inspired by these projects:
* http://airthings.com/raspberry-pi/
* https://github.com/marcelm/radonwave

The aforementioned `radonwave` project is especially useful as it describes
many of the BLE characteristics specific to this product and has good
trouble-shooting tips. The script provided is also very useful in determining
the MAC address of your AW device. See here:
https://github.com/marcelm/radonwave/issues/3

## Getting started

Download
```
/custom_components/airthings_wave/
```
into
```
<config directory>/custom_components/airthings_wave/
```
**Example configuration.yaml:**

```yaml
# Example configuration.yaml entry
sensor:
  - platform: airthings_wave
    scan_interval: 120
    elevation: 998
    voltage_100: 3.2
    voltage_0: 2.2
```
### Optional Configuration Variables

**mac**

  (string)(Optional) The airthings_wave mac address, if not provided will scan for all airthings devices at startup

**scan_interval**

  (string)(Optional) The interval between polls. Defaults to 300 seconds (5 minutes)

**elevation**

  (float)(Optional) The current elevation in meters. Used to correct the pressure sensor to sea level conditions.

**voltage_100**

  (float)(Optional) The voltage for 100% battery, calculated linearly between voltage_0 and voltage_100 (on supported device), default is 3.2

**voltage_0**

  (float)(Optional) The voltage for 0% battery, calculated linearly between voltage_0 and voltage_100 (on supported device), default is 2.2

## Limitations

Users has reported that it is possible to get data without first registering with the official app, 
so it should be possible to use the sensor with this integration without registering.

The radon level history stored on the Wave itself cannot be accessed
with this component. To get around this, it connects regularly to the radon
detector.

It might be beneficial to install the latest firmware on the device using the official app
first.

Battery level only works for the Airthings wave pluss device. 

## Known Issues

* Not yet able to specify the `monitored_conditions` configuration

* No translations available yet


## Hardware Requirements

* An Airthings Wave __OR__ Airthings Wave Plus __OR__ Airthings Wave Mini

* A Raspberry Pi 3/4 with built-in Bluetooth __OR__ a Bluetooth adapter that supports Bluetooth Low Energy (BLE). such as this
one: https://www.amazon.com/dp/B01N5MGEUS/ref=cm_sw_r_tw_dp_U_x_ObdNCb03P7QZJ

## Other Resources
* https://github.com/marcelm/radonwave/issues/1
* https://community.home-assistant.io/t/radoneye-ble-interface/94962
* https://support.airthings.com/hc/en-us/articles/115002910089-How-to-respond-to-your-radon-levels?mobile_site=true
* https://community.home-assistant.io/t/converting-sensor-measurement-units/98807
* http://certi.us/Downloads/Canada_Meas_BW.pdf

[airthings_wave]: https://github.com/custom-components/sensor.airthings_wave
[buymecoffee]: https://buymeacoff.ee/MartyTremblay
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[buymebeer]: https://paypal.me/MartyTremblay
[buymebeerbadge]: https://img.shields.io/badge/buy%20me%20a%20beer-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/custom-components/sensor.airthings_wave.svg?style=for-the-badge
[commits]: https://github.com/custom-components/sensor.airthings_wave/commits/master
[customupdater]: https://github.com/custom-components/custom_updater
[customupdaterbadge]: https://img.shields.io/badge/custom__updater-true-success.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/custom-components/sensor.airthings_wave.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-MartyTremblay-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/custom-components/sensor.airthings_wave.svg?style=for-the-badge
[releases]: https://github.com/custom-components/sensor.airthings_wave/releases
