import struct
import time
from collections import namedtuple

import logging
from datetime import datetime

import pygatt
from pygatt.exceptions import (
    BLEError, NotConnectedError, NotificationTimeout)

from uuid import UUID

_LOGGER = logging.getLogger(__name__)

# Use full UUID since we do not use UUID from bluepy.btle
CHAR_UUID_MANUFACTURER_NAME = UUID('00002a29-0000-1000-8000-00805f9b34fb')
CHAR_UUID_SERIAL_NUMBER_STRING = UUID('00002a25-0000-1000-8000-00805f9b34fb')
CHAR_UUID_MODEL_NUMBER_STRING = UUID('00002a24-0000-1000-8000-00805f9b34fb')
CHAR_UUID_DEVICE_NAME = UUID('00002a00-0000-1000-8000-00805f9b34fb')
CHAR_UUID_DATETIME = UUID('00002a08-0000-1000-8000-00805f9b34fb')
CHAR_UUID_TEMPERATURE = UUID('00002a6e-0000-1000-8000-00805f9b34fb')
CHAR_UUID_HUMIDITY = UUID('00002a6f-0000-1000-8000-00805f9b34fb')
CHAR_UUID_RADON_1DAYAVG = UUID('b42e01aa-ade7-11e4-89d3-123b93f75cba')
CHAR_UUID_RADON_LONG_TERM_AVG = UUID('b42e0a4c-ade7-11e4-89d3-123b93f75cba')
CHAR_UUID_ILLUMINANCE_ACCELEROMETER = UUID('b42e1348-ade7-11e4-89d3-123b93f75cba')
CHAR_UUID_WAVE_PLUS_DATA = UUID('b42e2a68-ade7-11e4-89d3-123b93f75cba')

Characteristic = namedtuple('Characteristic', ['uuid', 'name', 'format'])

manufacturer_characteristics = Characteristic(CHAR_UUID_MANUFACTURER_NAME, 'manufacturer', "utf-8")
device_info_characteristics = [manufacturer_characteristics,
                               Characteristic(CHAR_UUID_SERIAL_NUMBER_STRING, 'serial_nr', "utf-8"),
                               Characteristic(CHAR_UUID_MODEL_NUMBER_STRING, 'model_nr', "utf-8"),
                               Characteristic(CHAR_UUID_DEVICE_NAME, 'device_name', "utf-8")]

class AirthingsDeviceInfo:
    def __init__(self, manufacturer='', serial_nr='', model_nr='', device_name=''):
        self.manufacturer = manufacturer
        self.serial_nr = serial_nr
        self.model_nr = model_nr
        self.device_name = device_name

    def __str__(self):
        return "Manufacturer: {} Model: {} Serial: {} Device:{}".format(
            self.manufacturer, self.model_nr, self.serial_nr, self.device_name)


sensors_characteristics_uuid = [CHAR_UUID_DATETIME, CHAR_UUID_TEMPERATURE, CHAR_UUID_HUMIDITY, CHAR_UUID_RADON_1DAYAVG,
                                CHAR_UUID_RADON_LONG_TERM_AVG, CHAR_UUID_ILLUMINANCE_ACCELEROMETER,
                                CHAR_UUID_WAVE_PLUS_DATA]

sensors_characteristics_uuid_str = [str(x) for x in sensors_characteristics_uuid]


class BaseDecode:
    def __init__(self, name, format_type, scale):
        self.name = name
        self.format_type = format_type
        self.scale = scale

    def decode_data(self, raw_data):
        val = struct.unpack(
            self.format_type,
            raw_data)
        if len(val) == 1:
            res = val[0] * self.scale
        else:
            res = val
        return {self.name:res}


class WavePlussDecode(BaseDecode):
    def decode_data(self, raw_data):
        val = super().decode_data(raw_data)
        val = val[self.name]
        data = {}
        data['date_time'] = str(datetime.isoformat(datetime.now()))
        data['humidity'] = val[1]/2.0
        data['radon_1day_avg'] = val[4] if 0 <= val[4] <= 16383 else None
        data['radon_longterm_avg'] = val[5] if 0 <= val[5] <= 16383 else None
        data['temperature'] = val[6]/100.0
        data['rel_atm_pressure'] = val[7]/50.0
        data['co2'] = val[8]*1.0
        data['voc'] = val[9]*1.0
        return data


class WaveDecodeDate(BaseDecode):
    def decode_data(self, raw_data):
        val = super().decode_data(raw_data)[self.name]
        data = {self.name:str(datetime(val[0], val[1], val[2], val[3], val[4], val[5]).isoformat())}
        return data


class WaveDecodeIluminAccel(BaseDecode):
    def decode_data(self, raw_data):
        val = super().decode_data(raw_data)[self.name]
        data = {}
        data['illuminance'] = str(val[0] * self.scale)
        data['accelerometer'] = str(val[1] * self.scale)
        return data


sensor_decoders = {str(CHAR_UUID_WAVE_PLUS_DATA):WavePlussDecode(name="Pluss", format_type='BBBBHHHHHHHH', scale=0),
                   str(CHAR_UUID_DATETIME):WaveDecodeDate(name="date_time", format_type='HBBBBB', scale=0),
                   str(CHAR_UUID_HUMIDITY):BaseDecode(name="humidity", format_type='H', scale=1.0/100.0),
                   str(CHAR_UUID_RADON_1DAYAVG):BaseDecode(name="radon_1day_avg", format_type='H', scale=1.0),
                   str(CHAR_UUID_RADON_LONG_TERM_AVG):BaseDecode(name="radon_longterm_avg", format_type='H', scale=1.0),
                   str(CHAR_UUID_ILLUMINANCE_ACCELEROMETER):WaveDecodeIluminAccel(name="illuminance_accelerometer", format_type='BB', scale=1.0),
                   str(CHAR_UUID_TEMPERATURE):BaseDecode(name="temperature", format_type='h', scale=1.0/100.0),}


class AirthingsWaveDetect:
    def __init__(self, scan_interval, mac=None):
        self.adapter = pygatt.backends.GATTToolBackend()
        self.airthing_devices = [] if mac is None else [mac]
        self.sensors = []
        self.sensordata = {}
        self.scan_interval = scan_interval
        self.last_scan = -1


    def find_devices(self):
        # Scan for devices and try to figure out if it is an airthings device.
        self.adapter.start(reset_on_start=False)
        devices = self.adapter.scan(timeout=3)
        self.adapter.stop()

        for device in devices:
            mac = device['address']
            _LOGGER.debug("connecting to {}".format(mac))
            try:
                self.adapter.start(reset_on_start=False)
                dev = self.adapter.connect(mac, 3)
                _LOGGER.debug("Connected")
                try:
                    data = dev.char_read(manufacturer_characteristics.uuid)
                    manufacturer_name = data.decode(manufacturer_characteristics.format)
                    if "airthings" in manufacturer_name.lower():
                        self.airthing_devices.append(mac)
                except (BLEError, NotConnectedError, NotificationTimeout):
                    _LOGGER.debug("connection to {} failed".format(mac))
                finally:
                    dev.disconnect()
            except (BLEError, NotConnectedError, NotificationTimeout):
                _LOGGER.debug("Faild to connect")
            finally:
                self.adapter.stop()

        _LOGGER.debug("Found {} airthings devices".format(len(self.airthing_devices)))
        return len(self.airthing_devices)

    def get_info(self):
        # Try to get some info from the discovered airthings devices
        self.devices = {}

        for mac in self.airthing_devices:
            device = AirthingsDeviceInfo(serial_nr=mac)
            try:
                self.adapter.start(reset_on_start=False)
                dev = self.adapter.connect(mac, 3)
                for characteristic in device_info_characteristics:
                    try:
                        data = dev.char_read(characteristic.uuid)
                        setattr(device, characteristic.name, data.decode(characteristic.format))
                    except (BLEError, NotConnectedError, NotificationTimeout):
                        _LOGGER.exception("")
                dev.disconnect()
            except (BLEError, NotConnectedError, NotificationTimeout):
                _LOGGER.exception("")
            self.adapter.stop()
            self.devices[mac] = device

        return self.devices

    def get_sensors(self):
        self.sensors = {}
        for mac in self.airthing_devices:
            try:
                self.adapter.start(reset_on_start=False)
                dev = self.adapter.connect(mac, 3)
                characteristics = dev.discover_characteristics()
                sensor_characteristics =  []
                for characteristic in characteristics.values():
                    _LOGGER.debug(characteristic)
                    if characteristic.uuid in sensors_characteristics_uuid_str:
                        sensor_characteristics.append(characteristic)
                self.sensors[mac] = sensor_characteristics
            except (BLEError, NotConnectedError, NotificationTimeout):
                _LOGGER.exception("Failed to discover sensors")

        return self.sensors

    def get_sensor_data(self):
        if time.monotonic() - self.last_scan > self.scan_interval:
            self.last_scan = time.monotonic()
            for mac, characteristics in self.sensors.items():
                try:
                    self.adapter.start(reset_on_start=False)
                    dev = self.adapter.connect(mac, 3)
                    for characteristic in characteristics:
                        try:
                            data = dev.char_read_handle("0x{:04x}".format(characteristic.handle))
                            if characteristic.uuid in sensor_decoders:
                                sensor_data = sensor_decoders[characteristic.uuid].decode_data(data)
                                _LOGGER.debug("{} Got sensordata {}".format(mac, sensor_data))
                                if self.sensordata.get(mac) is None:
                                    self.sensordata[mac] = sensor_data
                                else:
                                    self.sensordata[mac].update(sensor_data)
                        except (BLEError, NotConnectedError, NotificationTimeout):
                            _LOGGER.exception("Failed to read characteristic")

                    dev.disconnect()
                except (BLEError, NotConnectedError, NotificationTimeout):
                    _LOGGER.exception("Failed to connect")
                self.adapter.stop()

        return self.sensordata


if __name__ == "__main__":
    logging.basicConfig()
    _LOGGER.setLevel(logging.INFO)
    ad = AirthingsWaveDetect(180)
    num_dev_found = ad.find_devices()
    if num_dev_found > 0:
        devices = ad.get_info()
        for mac, dev in devices.items():
            _LOGGER.info("{}: {}".format(mac, dev))

        devices_sensors = ad.get_sensors()
        for mac, sensors in devices_sensors.items():
            for sensor in sensors:
                _LOGGER.info("{}: {}".format(mac, sensor))

        sensordata = ad.get_sensor_data()
        for mac, data in sensordata.items():
            for name, val in data.items():
                _LOGGER.info("{}: {}: {}".format(mac, name, val))

