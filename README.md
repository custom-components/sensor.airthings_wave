# sensor.airthings_wave
hassio support for Airthings Wave BLE environmental radon sensor. Much of The
code to build this component was inspired by these projects:
* http://airthings.com/tech/read_wave.py
* https://github.com/marcelm/radonwave

The aforementioned `radonwave` project is especially useful as it describes many of the BLE characteristics specific to this product and good trouble-shooting tips

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

  (string)(Optional) The interval between polls

## Limitations

It may be possible that the Wave must be connected to the official app at least
once before you can use this program, so you will probably not get around
registering an account with Airthings.

The radon level history stored on the Wave itself cannot be accessed
with this component. To get around this, it connects regularly to the radon
detector.

Make sure you install the latest firmware on the device using the official app
first.

## Hardware requirements

* An Airthings Wave
* A Bluetooth adapter that supports Bluetooth Low Energy (BLE). such as this
one: https://www.amazon.com/dp/B01N5MGEUS/ref=cm_sw_r_tw_dp_U_x_ObdNCb03P7QZJ
