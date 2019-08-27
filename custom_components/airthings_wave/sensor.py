"""
Support for Airthings Wave BLE environmental radon sensor.
https://airthings.com/

Code used to design this component is found in:
http://airthings.com/tech/read_wave.py
https://github.com/marcelm/radonwave
The aforementioned `radonwave` project is especially useful as it describes many
of the BLE characteristics specific to this product and good trouble-shooting
tips

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.airthings_wave/
"""
import logging
import struct
import threading
from datetime import datetime, timedelta

from bluepy.btle import UUID

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (ATTR_DEVICE_CLASS, ATTR_ICON, CONF_MAC,
                                 CONF_NAME, CONF_SCAN_INTERVAL,
                                 CONF_UNIT_SYSTEM, CONF_UNIT_SYSTEM_IMPERIAL,
                                 CONF_UNIT_SYSTEM_METRIC, TEMPERATURE,
                                 TEMP_CELSIUS, DEVICE_CLASS_HUMIDITY,
                                 DEVICE_CLASS_ILLUMINANCE,
                                 DEVICE_CLASS_TEMPERATURE,
                                 DEVICE_CLASS_TIMESTAMP,
                                 EVENT_HOMEASSISTANT_STOP, ILLUMINANCE,
                                 STATE_UNKNOWN)
from homeassistant.helpers.entity import Entity
VERSION = '0.5.0'

REQUIREMENTS = ['pygatt[GATTTOOL]==4.0.3']

_LOGGER = logging.getLogger(__name__)
DEFAULT_NAME = 'Airthings Wave'
CONNECT_LOCK = threading.Lock()
CONNECT_TIMEOUT = 30
SCAN_INTERVAL = timedelta(seconds=300)

ATTR_DEVICE_DATE_TIME = 'device_date_time'
ATTR_RADON_LEVEL = 'radon_level'
DEVICE_CLASS_RADON='radon'
DEVICE_CLASS_ACCELEROMETER='accelerometer'
ILLUMINANCE_LUX = 'lx'
PERCENT = '%'
SPEED_METRIC_UNITS = 'm/s2'
VOLUME_BECQUEREL = 'Bq/m3'
VOLUME_PICOCURIE = 'pCi/L'

BQ_TO_PCI_MULTIPLIER = 0.037

"""
0 - 49 Bq/m3  (0 - 1.3 pCi/L):
No action necessary.

50 - 99 Bq/m3 (1.4 - 2.6 pCi/L):
Experiment with ventilation and sealing cracks to reduce levels.

100 Bq/m3 - 299 Bq/m3 (2.7 - 8 pCi/L):
Keep measuring. If levels are maintained for more than 3 months,
contact a professional radon mitigator.

300 Bq/m3 (8.1 pCi/L) and up:
Keep measuring. If levels are maintained for more than 1 month,
contact a professional radon mitigator.
"""
VERY_LOW = [0, 49, 'very low']
LOW = [50, 99, 'low']
MODERATE = [100, 299, 'moderate']
HIGH = [300, None, 'high']

CHAR_UUID_DATETIME = UUID(0x2A08)
CHAR_UUID_TEMPERATURE = UUID(0x2A6E)
CHAR_UUID_HUMIDITY = UUID(0x2A6F)
CHAR_UUID_RADON_1DAYAVG = 'b42e01aa-ade7-11e4-89d3-123b93f75cba'
CHAR_UUID_RADON_LONG_TERM_AVG = 'b42e0a4c-ade7-11e4-89d3-123b93f75cba'
CHAR_UUID_ILLUMINANCE_ACCELEROMETER = 'b42e1348-ade7-11e4-89d3-123b93f75cba'

UNIT_SYSTEMS = [CONF_UNIT_SYSTEM_IMPERIAL, CONF_UNIT_SYSTEM_METRIC]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MAC): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    vol.Optional(CONF_UNIT_SYSTEM): vol.In(UNIT_SYSTEMS),
})

class Sensor:
    def __init__(self, name, uuid, format_type, scale):
        self.name = name
        self.uuid = uuid
        self.format_type = format_type
        self.scale = scale


sensors = []
sensors.append(Sensor('date_time', CHAR_UUID_DATETIME, 'HBBBBB', 0))
sensors.append(Sensor('temperature', CHAR_UUID_TEMPERATURE, 'h', 1.0/100.0))
sensors.append(Sensor('humidity', CHAR_UUID_HUMIDITY, 'H', 1.0/100.0))
sensors.append(Sensor('radon_1day_avg', CHAR_UUID_RADON_1DAYAVG, 'H', 1.0))
sensors.append(Sensor('radon_longterm_avg',
    CHAR_UUID_RADON_LONG_TERM_AVG, 'H', 1.0))
sensors.append(Sensor('illuminance_accelerometer',
    CHAR_UUID_ILLUMINANCE_ACCELEROMETER, 'BB', 1.0))


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Airthings sensor."""
    name = config.get(CONF_NAME)
    mac = config.get(CONF_MAC)
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    unit_system = config.get(CONF_UNIT_SYSTEM)

    _LOGGER.debug("Setting up...")

    if CONF_UNIT_SYSTEM in config:
        unit_system = config[CONF_UNIT_SYSTEM]
    elif hass.config.units.is_metric:
        unit_system = UNIT_SYSTEMS[1]
    else:
        unit_system = UNIT_SYSTEMS[0]

    mon = Monitor(hass, mac, name, scan_interval)
    add_entities([AirthingsTemperature(name + " Temperature", mon)])
    add_entities([AirthingsHumidity(name + " Humidity", mon)])
    add_entities([AirthingsRadon(name + " Radon 1 Day Average",
        mon, 'radon_1day_avg', unit_system)])
    add_entities([AirthingsRadon(name + " Radon Long Term Average",
        mon, 'radon_longterm_avg', unit_system)])
    add_entities([AirthingsIlluminance(name + " Illuminance", mon)])
    add_entities([AirthingsAccel(name + " Acceleration", mon)])

    def monitor_stop(_service_or_event):
        """Stop the monitor thread."""
        _LOGGER.info("Stopping monitor for %s", name)
        mon.terminate()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, monitor_stop)
    mon.start()

class AirthingsHumidity(Entity):
    """Representation of a Airthings humidity sensor."""

    def __init__(self, name, mon):
        """Initialize a sensor."""
        self.mon = mon
        self._name = name

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self.mon.data[DEVICE_CLASS_HUMIDITY]

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return PERCENT

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_DEVICE_CLASS: DEVICE_CLASS_HUMIDITY,
            ATTR_DEVICE_DATE_TIME: self.mon.data['date_time']
        }

class AirthingsTemperature(Entity):
    """Representation of a Airthings temperature sensor."""

    def __init__(self, name, mon):
        """Initialize a sensor."""
        self.mon = mon
        self._name = name

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self.mon.data[TEMPERATURE]

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return TEMP_CELSIUS

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
            ATTR_DEVICE_DATE_TIME: self.mon.data['date_time']
        }

class AirthingsRadon(Entity):
    """Representation of a Airthings radon sensor."""

    def __init__(self, name, mon, subclass, unit_system):
        """Initialize a sensor."""
        self.mon = mon
        self._subclass = subclass
        self._name = name
        self.radon_level = STATE_UNKNOWN
        self.unit_system = unit_system

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        try:
            if self.unit_system == CONF_UNIT_SYSTEM_IMPERIAL:
                self.converted_radon_data = round(
                    float(self.mon.data[self._subclass]) *
                        BQ_TO_PCI_MULTIPLIER, 2)
            else:
                self.converted_radon_data = self.mon.data[self._subclass]

        except Exception as ex:
            _LOGGER.warn("Radon data is : got an exception: %s", ex)
            self.converted_radon_data = self.mon.data[self._subclass]

        return self.converted_radon_data

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if (self.unit_system == CONF_UNIT_SYSTEM_IMPERIAL) :
            return VOLUME_PICOCURIE
        else :
            return VOLUME_BECQUEREL

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""

        try:
            if VERY_LOW[0] <= float(self.mon.data[self._subclass]) <= VERY_LOW[1]:
                self.radon_level = VERY_LOW[2]
            elif LOW[0] <= float(self.mon.data[self._subclass]) <= LOW[1]:
                self.radon_level = LOW[2]
            elif MODERATE[0] <= float(self.mon.data[self._subclass]) <= MODERATE[1]:
                self.radon_level = MODERATE[2]
            else:
                self.radon_level = HIGH[2]
        except Exception as ex:
            _LOGGER.warn("Radon level is : got an exception: %s", ex)
            self.radon_level = STATE_UNKNOWN

        return {
            ATTR_DEVICE_CLASS: DEVICE_CLASS_RADON,
            ATTR_DEVICE_DATE_TIME: self.mon.data['date_time'],
            ATTR_RADON_LEVEL: self.radon_level,
            ATTR_ICON: 'mdi:radioactive'
        }


class AirthingsIlluminance(Entity):
    """Representation of a Airthings illuminance sensor."""

    def __init__(self, name, mon):
        """Initialize a sensor."""
        self.mon = mon
        self._name = name

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self.mon.data[ILLUMINANCE]

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return ILLUMINANCE_LUX

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_DEVICE_CLASS: DEVICE_CLASS_ILLUMINANCE,
            ATTR_DEVICE_DATE_TIME: self.mon.data['date_time']
        }

class AirthingsAccel(Entity):
    """Representation of a Airthings accelerometer sensor."""

    def __init__(self, name, mon):
        """Initialize a sensor."""
        self.mon = mon
        self._name = name

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self.mon.data['accelerometer']

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return SPEED_METRIC_UNITS

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_DEVICE_CLASS: DEVICE_CLASS_ACCELEROMETER,
            ATTR_DEVICE_DATE_TIME: self.mon.data['date_time'],
            ATTR_ICON: 'mdi:vibrate'
        }

class Monitor(threading.Thread):
    """Connection handling."""

    def __init__(self, hass, mac, name, scan_interval):
        """Construct interface object."""
        threading.Thread.__init__(self)
        self.daemon = False
        self.hass = hass
        self.mac = mac
        self.name = name
        self.scan_interval = scan_interval
        self.data = {'date_time': STATE_UNKNOWN, 'temperature': STATE_UNKNOWN,
            'humidity': STATE_UNKNOWN, 'radon_1day_avg': STATE_UNKNOWN,
            'radon_longterm_avg': STATE_UNKNOWN, 'illuminance': STATE_UNKNOWN,
            'accelerometer' : STATE_UNKNOWN}
        self.keep_going = True
        self.event = threading.Event()

    def run(self):
        """Thread that keeps connection alive."""
        # pylint: disable=import-error
        import pygatt
        from pygatt.exceptions import (
            BLEError, NotConnectedError, NotificationTimeout)

        adapter = pygatt.backends.GATTToolBackend()
        while self.keep_going:
            try:
                _LOGGER.debug("Connecting to %s", self.name)

                # We need concurrent connect, so lets not reset the device
                adapter.start(reset_on_start=False)
                device = adapter.connect(self.mac, CONNECT_TIMEOUT)

                # Give the adaptor a breather
                self.event.wait(1)
                for s in sensors:
                    val = struct.unpack(
                        s.format_type,
                        device.char_read(
                            s.uuid, timeout=CONNECT_TIMEOUT))
                    _LOGGER.debug("Sensor %s: %s", s.name, val)

                    if s.name == 'date_time':
                        val = str(datetime(val[0], val[1], val[2], val[3],
                                        val[4], val[5]).isoformat())
                        self.data[s.name] = val
                    elif s.name == 'illuminance_accelerometer':
                        self.data['illuminance'] = str(val[0] * s.scale)
                        self.data['accelerometer'] = str(val[1] * s.scale)
                    else:
                        self.data[s.name] = str(round(val[0] * s.scale, 1))
            except (BLEError, NotConnectedError, NotificationTimeout) as ex:
                _LOGGER.error("Exception: %s ", str(ex))
            finally:
                adapter.stop()
                self.event.wait(self.scan_interval.total_seconds())

    def terminate(self):
        """Signal runner to stop and join thread."""
        _LOGGER.debug("Terminating the thread")
        self.keep_going = False
        self.event.set()
        self.join()
