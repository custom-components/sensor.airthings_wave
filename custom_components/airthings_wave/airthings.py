import struct
import time
from collections import namedtuple

import logging
from datetime import datetime

import bluepy.btle as btle

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
CHAR_UUID_WAVE_2_DATA = UUID('b42e4dcc-ade7-11e4-89d3-123b93f75cba')
CHAR_UUID_WAVEMINI_DATA = UUID('b42e3b98-ade7-11e4-89d3-123b93f75cba')

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
                                CHAR_UUID_WAVE_PLUS_DATA,CHAR_UUID_WAVE_2_DATA,CHAR_UUID_WAVEMINI_DATA]

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


class Wave2Decode(BaseDecode):
    def decode_data(self, raw_data):
        val = super().decode_data(raw_data)
        val = val[self.name]
        data = {}
        data['date_time'] = str(datetime.isoformat(datetime.now()))
        data['humidity'] = val[1]/2.0
        data['radon_1day_avg'] = val[4] if 0 <= val[4] <= 16383 else None
        data['radon_longterm_avg'] = val[5] if 0 <= val[5] <= 16383 else None
        data['temperature'] = val[6]/100.0
        return data


class WaveMiniDecode(BaseDecode):
    def decode_data(self, raw_data):
        val = super().decode_data(raw_data)
        val = val[self.name]
        data = {}
        data['date_time'] = str(datetime.isoformat(datetime.now()))
        data['temperature'] = round( val[1]/100.0 - 273.15,2)
        data['humidity'] = val[3]/100.0
        data['voc'] = val[4]*1.0
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
                   str(CHAR_UUID_TEMPERATURE):BaseDecode(name="temperature", format_type='h', scale=1.0/100.0),
                   str(CHAR_UUID_WAVE_2_DATA):Wave2Decode(name="Wave2", format_type='<4B8H', scale=1.0),
                   str(CHAR_UUID_WAVEMINI_DATA):WaveMiniDecode(name="WaveMini", format_type='<HHHHHHLL', scale=1.0),}


class AirthingsWaveDetect:
    def __init__(self, scan_interval, mac=None):
        self.airthing_devices = [] if mac is None else [mac]
        self.sensors = []
        self.sensordata = {}
        self.scan_interval = scan_interval
        self.last_scan = -1
        self._dev = None

    def _parse_serial_number(self, manufacturer_data):
        try:
            (ID, SN, _) = struct.unpack("<HLH", manufacturer_data)
        except Exception as e:  # Return None for non-Airthings devices
            return None
        else:  # Executes only if try-block succeeds
            if ID == 0x0334:
                return SN

    def find_devices(self, scans=50, timeout=0.1):
        # Search for devices, scan for BLE devices scans times for timeout seconds
        # Get manufacturer data and try to match match it to airthings ID.
        scanner = btle.Scanner()
        for _count in range(scans):
            advertisements = scanner.scan(timeout)
            for adv in advertisements:
                sn = self._parse_serial_number(adv.getValue(btle.ScanEntry.MANUFACTURER))
                if sn is not None:
                    if adv.addr not in self.airthing_devices:
                        self.airthing_devices.append(adv.addr)

        _LOGGER.debug("Found {} airthings devices".format(len(self.airthing_devices)))
        return len(self.airthing_devices)

    def connect(self, mac, retries=10):  
        tries = 0
        self.disconnect()
        while (tries < retries):
            tries += 1
            try:
                self._dev = btle.Peripheral(mac.lower())
            except Exception as e:
                print(e)
                if tries == retries:
                    pass
                else:
                    _LOGGER.debug("Retrying {}".format(mac))

    def disconnect(self):
        if self._dev is not None:
            self._dev.disconnect()
            self._dev = None

    def get_info(self):
        # Try to get some info from the discovered airthings devices
        self.devices = {}
        for mac in self.airthing_devices:
            # Lets retry some times if we get disconnected.
            # We retry in this function as this is will only be executed on setup to find devices and info.
            for i in range(10):
                self.connect(mac)
                try:
                    if self._dev is not None:
                        device = AirthingsDeviceInfo(serial_nr=mac)
                        for characteristic in device_info_characteristics:                
                            char = self._dev.getCharacteristics(uuid=characteristic.uuid)[0]
                            data = char.read()
                            setattr(device, characteristic.name, data.decode(characteristic.format))
                        # Successful read, lets break the retry loop
                        break
                except btle.BTLEDisconnectError:
                    _LOGGER.exception("Disconnected, try {}".format(i))
                    self._dev = None

                self.devices[mac] = device
            self.disconnect()
        return self.devices

    def get_sensors(self):
        self.sensors = {}
        for mac in self.airthing_devices:
            self.connect(mac)
            for i in range(10): #Retry if we fail to get sensor data, this will only be done on start.
                if self._dev is not None:
                    try:
                        characteristics = self._dev.getCharacteristics()
                        sensor_characteristics =  []
                        for characteristic in characteristics:
                            _LOGGER.debug(characteristic)
                            if characteristic.uuid in sensors_characteristics_uuid_str:
                                sensor_characteristics.append(characteristic)
                        self.sensors[mac] = sensor_characteristics
                        # We got all sensors, we are done.
                        break
                    except btle.BTLEDisconnectError:
                        _LOGGER.exception("Disconnected, {}.".format(i))
                        self._dev = None
            self.disconnect()
        return self.sensors

    def get_sensor_data(self):
        if time.monotonic() - self.last_scan > self.scan_interval:
            self.last_scan = time.monotonic()
            for mac, characteristics in self.sensors.items():
                self.connect(mac)
                if self._dev is not None:
                    try:
                        for characteristic in characteristics:
                            if str(characteristic.uuid) in sensor_decoders:
                                char = self._dev.getCharacteristics(uuid=characteristic.uuid)[0]
                                data = char.read()
                                sensor_data = sensor_decoders[str(characteristic.uuid)].decode_data(data)
                                _LOGGER.debug("{} Got sensordata {}".format(mac, sensor_data))
                                if self.sensordata.get(mac) is None:
                                    self.sensordata[mac] = sensor_data
                                else:
                                    self.sensordata[mac].update(sensor_data)
                    except btle.BTLEDisconnectError:
                        _LOGGER.exception("Disconnected, lets try again next time.")
                        self._dev = None
                self.disconnect()

        return self.sensordata


if __name__ == "__main__":
    logging.basicConfig()
    _LOGGER.setLevel(logging.DEBUG)
    ad = AirthingsWaveDetect(0)
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