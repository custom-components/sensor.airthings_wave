# sensor.airthings_wave
hassio support for Airthings Wave BLE environmental radon sensor.

![ScreenShot][ScreenShot.png]

Much of The
code to build this component was inspired by these projects:
* http://airthings.com/raspberry-pi/
* https://github.com/marcelm/radonwave

The aforementioned `radonwave` project is especially useful as it describes
many of the BLE characteristics specific to this product and good has
trouble-shooting tips

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
    mac: "98:07:2D:4A:97:5C"
    name: 'Basement Airthings Wave'
    scan_interval: 120
```
### Configuration Variables

**mac**

  (string)(Required) The airthings_wave mac address

**name**

  (string)(Optional) The name of the device. Defaults to 'Airthings Wave'

**scan_interval**

  (string)(Optional) The interval between polls. Defaults to 1 minute

## Limitations

It may be possible that the Wave must be connected to the official app at least
once before you can use this program, so you will probably not get around
registering an account with Airthings.

The radon level history stored on the Wave itself cannot be accessed
with this component. To get around this, it connects regularly to the radon
detector.

Make sure you install the latest firmware on the device using the official app
first.

## Known Issues

* Component returns metric values only (for now)
https://github.com/custom-components/sensor.airthings_wave/issues/1
* Values only appear after first scan_interval (default 1 minute) has passed
and will remain as `unknown` until then
https://github.com/custom-components/sensor.airthings_wave/issues/2
* Component keeps a persistent connection thread to the BLE dongle which may
block phone app from connecting to the AW device
* Not yet compatible with [custom_updater](https://github.com/custom-components/custom_updater) and [tracker-card](https://github.com/custom-cards/tracker-card)
* Not yet able to specify the `monitored_conditions` configuration


## Hardware requirements

* An Airthings Wave
* A Bluetooth adapter that supports Bluetooth Low Energy (BLE). such as this
one: https://www.amazon.com/dp/B01N5MGEUS/ref=cm_sw_r_tw_dp_U_x_ObdNCb03P7QZJ
