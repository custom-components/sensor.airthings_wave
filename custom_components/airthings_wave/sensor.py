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
from datetime import timedelta

from .airthings import AirthingsWaveDetect

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
                                 DEVICE_CLASS_PRESSURE,
                                 DEVICE_CLASS_TIMESTAMP,
                                 EVENT_HOMEASSISTANT_STOP, ILLUMINANCE,
                                 STATE_UNKNOWN)
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)
CONNECT_TIMEOUT = 30
SCAN_INTERVAL = timedelta(seconds=300)

ATTR_DEVICE_DATE_TIME = 'device_date_time'
ATTR_RADON_LEVEL = 'radon_level'
DEVICE_CLASS_RADON='radon'
DEVICE_CLASS_ACCELEROMETER='accelerometer'
DEVICE_CLASS_CO2='co2'
DEVICE_CLASS_VOC='voc'

ILLUMINANCE_LUX = 'lx'
PERCENT = '%'
SPEED_METRIC_UNITS = 'm/s2'
VOLUME_BECQUEREL = 'Bq/m3'
VOLUME_PICOCURIE = 'pCi/L'
ATM_METRIC_UNITS = 'mbar'
CO2_METRIC_UNITS = 'ppm'
VOC_METRIC_UNITS = 'ppb'

BQ_TO_PCI_MULTIPLIER = 0.027

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


DOMAIN = 'airthings'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_MAC, default=''): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
})


class Sensor:
    def __init__(self, unit, unit_scale, device_class, icon):
        self.unit = unit
        self.unit_scale = unit_scale
        self.device_class = device_class
        self.icon = icon

    def set_unit_scale(self, unit, unit_scale):
        self.unit = unit
        self.unit_scale = unit_scale

    def get_extra_attributes(self, data):
        return {}


class RadonSensor(Sensor):
    def get_extra_attributes(self, data):
        if VERY_LOW[0] <= float(data) <= VERY_LOW[1]:
            radon_level = VERY_LOW[2]
        elif LOW[0] <= float(data) <= LOW[1]:
            radon_level = LOW[2]
        elif MODERATE[0] <= float(data) <= MODERATE[1]:
            radon_level = MODERATE[2]
        else:
            radon_level = HIGH[2]
        return {ATTR_RADON_LEVEL: radon_level}


DEVICE_SENSOR_SPECIFICS = { "date_time":Sensor('time', None, None, None),
                            "temperature":Sensor(TEMP_CELSIUS, None, DEVICE_CLASS_TEMPERATURE, None),
                            "humidity": Sensor(PERCENT, None, DEVICE_CLASS_HUMIDITY, None),
                            "rel_atm_pressure": Sensor(ATM_METRIC_UNITS, None, DEVICE_CLASS_PRESSURE, None),
                            "co2": Sensor(CO2_METRIC_UNITS, None, DEVICE_CLASS_CO2, 'mdi:periodic-table-co2'),
                            "voc": Sensor(VOC_METRIC_UNITS, None, DEVICE_CLASS_VOC, 'mdi:cloud'),
                            "illuminance": Sensor(ILLUMINANCE_LUX, None, DEVICE_CLASS_ILLUMINANCE, None),
                            "accelerometer": Sensor(SPEED_METRIC_UNITS, None, DEVICE_CLASS_ACCELEROMETER, 'mdi:vibrate'),
                            "radon_1day_avg": RadonSensor(VOLUME_BECQUEREL, None, DEVICE_CLASS_RADON, 'mdi:radioactive'),
                            "radon_longterm_avg": RadonSensor(VOLUME_BECQUEREL, None, DEVICE_CLASS_RADON, 'mdi:radioactive')
                           }


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Airthings sensor."""
    scan_interval = config.get(CONF_SCAN_INTERVAL).total_seconds()
    mac = config.get(CONF_MAC)
    mac = None if mac == '' else mac

    if not hass.config.units.is_metric:
        DEVICE_SENSOR_SPECIFICS["radon_1day_avg"].set_unit_scale(VOLUME_PICOCURIE, BQ_TO_PCI_MULTIPLIER)
        DEVICE_SENSOR_SPECIFICS["radon_longterm_avg"].set_unit_scale(VOLUME_PICOCURIE, BQ_TO_PCI_MULTIPLIER)

    _LOGGER.debug("Searching for Airthings sensors...")
    airthingsdetect = AirthingsWaveDetect(scan_interval, mac)
    try:
        if mac is None:
            num_devices_found = airthingsdetect.find_devices()
            _LOGGER.info("Found {} airthings device(s)".format(num_devices_found))

        if mac is None and num_devices_found == 0:
            _LOGGER.warning("No airthings devices found.")
            return

        _LOGGER.debug("Getting info about device(s)")
        devices_info = airthingsdetect.get_info()
        for mac, dev in devices_info.items():
            _LOGGER.info("{}: {}".format(mac, dev))

        _LOGGER.debug("Getting sensors")
        devices_sensors = airthingsdetect.get_sensors()
        for mac, sensors in devices_sensors.items():
            for sensor in sensors:
                _LOGGER.debug("{}: Found sensor UUID: {} Handle: {}".format(mac, sensor.uuid, sensor.handle))

        _LOGGER.debug("Get initial sensor data to populate HA entities")
        ha_entities = []
        sensordata = airthingsdetect.get_sensor_data()
        for mac, data in sensordata.items():
            for name, val in data.items():
                _LOGGER.debug("{}: {}: {}".format(mac, name, val))
                ha_entities.append(AirthingsSensor(mac, name, airthingsdetect, devices_info[mac],
                                                   DEVICE_SENSOR_SPECIFICS[name]))
    except:
        _LOGGER.exception("Failed intial setup.")
        return

    add_entities(ha_entities, True)


class AirthingsSensor(Entity):
    """General Representation of an Airthings sensor."""
    def __init__(self, mac, name, device, device_info, sensor_specifics):
        """Initialize a sensor."""
        self.device = device
        self._mac = mac
        self._name = '{}-{}'.format(mac, name)
        _LOGGER.debug("Added sensor entity {}".format(self._name))
        self._sensor_name = name

        self._device_class = sensor_specifics.device_class
        self._state = STATE_UNKNOWN
        self._sensor_specifics = sensor_specifics

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._sensor_specifics.icon

    @property
    def device_class(self):
        """Return the icon of the sensor."""
        return self._sensor_specifics.device_class

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._sensor_specifics.unit

    @property
    def unique_id(self):
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        attributes = self._sensor_specifics.get_extra_attributes(self._state)
        try:
            attributes[ATTR_DEVICE_DATE_TIME] = self.device.sensordata[self._mac]['date_time']
        except KeyError:
            _LOGGER.exception("No date time of sensor reading data available.")
        return attributes

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self.device.get_sensor_data()
        value = self.device.sensordata[self._mac][self._sensor_name]
        if self._sensor_specifics.unit_scale is None:
            self._state = value
        else:
            self._state = round(float(value * self._sensor_specifics.unit_scale), 2)
        _LOGGER.debug("State {} {}".format(self._name, self._state))
