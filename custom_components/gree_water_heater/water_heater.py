#!/usr/bin/python
# Do basic imports
import socket
import base64

import logging
from functools import partial as ft
from . import DOMAIN
from homeassistant.components.water_heater import WaterHeaterEntity, WaterHeaterEntityFeature
from homeassistant.const import (
	#Platform,
	#TEMP_CELSIUS,
	UnitOfTemperature,
	PRECISION_WHOLE,
	#PRECISION_HALVES,
	ATTR_TEMPERATURE,
	# CONF_DEVICE_ID,
	# CONF_SWITCHES,
	# STATE_ON,
	STATE_OFF,
	ATTR_UNIT_OF_MEASUREMENT,
)

from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event
from Crypto.Cipher import AES
try: import simplejson
except ImportError: import json as simplejson
from datetime import timedelta


_LOGGER = logging.getLogger(__name__)


MAX_TEMP = 55
MIN_TEMP = 35

DEFAULT_NAME = 'Gree Water Heater'
DEFAULT_PORT = 7000
DEFAULT_TIMEOUT = 10
DEFAULT_TARGET_TEMP_STEP = 1
CONF_ENCRYPTION_KEY = 'encryption_key'
CONF_UID = 'uid'
CONF_MAX_ONLINE_ATTEMPTS = 'max_online_attempts'
CONF_DISABLE_AVAILABLE_CHECK  = 'disable_available_check'
CONF_ENCRYPTION_VERSION = 'encryption_version'
CONF_TARGET_TEMP = 'target_temp'
HVAC_MODES = ["heat_pump", "eco", "high_demand", "off"]

# 用户机型（格力+ App GR_Code）真实字段全集。设备只回它认识的字段，
# 按响应自带 cols 与 dat 配对，未返回的字段保持 None。
ALL_FIELDS = [
    "Pow", "AllErr", "Wmod", "SetTemInt", "SetTemDec",
    "WstpSv", "WstpH", "WstpM", "WstpL", "WatTmp", "Watpercent",
    "TemUn", "SwhBw", "BwBoard", "BwErr", "AppTimer", "Wstate", "WschTyp",
    "Sch1", "Sch2",
    "Wtmr1StartHr", "Wtmr1StartMin", "Wtmr1EndHr", "Wtmr1EndMin",
    "Wtmr2StartHr", "Wtmr2StartMin", "Wtmr2EndHr", "Wtmr2EndMin",
    "host", "name",
]
# 可写字段（下发 cmd）。只读字段不下发，避免设备拒绝。
WRITABLE_FIELDS = [
    "Pow", "Wmod", "SetTemInt", "WschTyp", "Sch1", "Sch2",
    "Wtmr1StartHr", "Wtmr1StartMin", "Wtmr1EndHr", "Wtmr1EndMin",
    "Wtmr2StartHr", "Wtmr2StartMin", "Wtmr2EndHr", "Wtmr2EndMin",
]
CONF_TEMP_SENSOR = 'temp_sensor'
CONF_TARGET_TEMP_STEP = 'target_temp_step'






# update() interval
SCAN_INTERVAL = timedelta(seconds=60)
#偏移值
TEMP_OFFSET  = 100



GCM_IV = b'\x54\x40\x78\x44\x49\x67\x5A\x51\x6C\x5E\x63\x13'
GCM_ADD = b'qualcomm-test'


def get_entry_value(entry, key, default=None):
    return entry.options.get(key, entry.data.get(key, default))

async def async_setup_entry(hass, entry, async_add_entities):
    name = get_entry_value(entry, "name", DEFAULT_NAME)
    ip_addr = get_entry_value(entry, "host")
    port = get_entry_value(entry, "port", DEFAULT_PORT)
    mac_addr = get_entry_value(entry, "mac")
    timeout = get_entry_value(entry, "timeout", DEFAULT_TIMEOUT)
    encryption_key = get_entry_value(entry, CONF_ENCRYPTION_KEY)
    uid = get_entry_value(entry, CONF_UID)
    max_online_attempts = get_entry_value(entry, CONF_MAX_ONLINE_ATTEMPTS, 3)
    disable_available_check = get_entry_value(entry, CONF_DISABLE_AVAILABLE_CHECK, False)
    encryption_version = get_entry_value(entry, CONF_ENCRYPTION_VERSION, 1)
    temp_sensor_entity_id = get_entry_value(entry, CONF_TEMP_SENSOR)
    target_temp_entity_id = get_entry_value(entry, CONF_TARGET_TEMP)
    target_temp_step = get_entry_value(entry, CONF_TARGET_TEMP_STEP, DEFAULT_TARGET_TEMP_STEP)
    hvac_modes = HVAC_MODES


    water_heater = GreeWaterHeater(
        hass, name, ip_addr, port, mac_addr, timeout,
        temp_sensor_entity_id, target_temp_entity_id, hvac_modes, target_temp_step,
        encryption_version, disable_available_check, max_online_attempts,
        encryption_key, uid
    )

    # 先存到 hass.data
    hass.data.setdefault("gree_water_heater_entities", {})[entry.entry_id] = water_heater
    # 再添加实体
    async_add_entities([water_heater])
    # 首次同步放到后台
    hass.async_create_task(water_heater.async_first_sync())




class GreeWaterHeater(WaterHeaterEntity):
    def __init__(self, hass, name, ip_addr, port, mac_addr, timeout, temp_sensor_entity_id,target_temp_entity_id,hvac_modes,target_temp_step, encryption_version, disable_available_check, max_online_attempts, encryption_key=None, uid=None):
        _LOGGER.info('Initialize the GREE Water Heater device')
        self.hass = hass
        self._name = name
        self._ip_addr = ip_addr
        self._port = port
        self._mac_addr = mac_addr.lower().replace(':', '')
        self._timeout = timeout
        self._unique_id = 'waterHeater.gree_' + mac_addr.lower().replace(':', '')
        self._device_online = None
        self._online_attempts = 0
        self._max_online_attempts = max_online_attempts
        self._disable_available_check = disable_available_check



        self._current_temperature = None

        self._target_temp_entity_id = target_temp_entity_id
        self._target_temperature = None

        self._firstTimeRun = True



        self.encryption_version = encryption_version
        self.CIPHER = None

        self._hvac_modes = hvac_modes
        self._hvac_mode = STATE_OFF

        self._unit_of_measurement = '°C'
        self._temp_sensor_entity_id = temp_sensor_entity_id
        self._target_temperature_step = target_temp_step



        if encryption_key:
            _LOGGER.info('Using configured encryption key: {}'.format(encryption_key))
            self._encryption_key = encryption_key.encode("utf8")
            if encryption_version == 1:
                # Cipher to use to encrypt/decrypt
                self.CIPHER = AES.new(self._encryption_key, AES.MODE_ECB)
            elif encryption_version != 2:
                _LOGGER.error('Encryption version %s is not implemented.' % encryption_version)
        else:
            self._encryption_key = None

        if uid:
            self._uid = uid
        else:
            self._uid = 0

        self._acOptions = {key: None for key in ALL_FIELDS}
        self._optionsToFetch = list(ALL_FIELDS)




        if temp_sensor_entity_id:
            _LOGGER.info('Setting up temperature sensor: ' + str(temp_sensor_entity_id))
            async_track_state_change_event(hass, temp_sensor_entity_id, self._async_temp_sensor_changed)


        if target_temp_entity_id:
            _LOGGER.info('Setting up target temp entity: ' + str(target_temp_entity_id))
            async_track_state_change_event(hass, target_temp_entity_id, self._async_target_temp_entity_state_changed)

    async def async_first_sync(self):
        """首次同步状态，后台执行，不阻塞主线程。"""
        await self.hass.async_add_executor_job(self.update)
        # 需要时可调用 self.async_write_ha_state() 更新界面
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac_addr)},
            "name": self._name,
            "manufacturer": "Gree",
            "model": "Water Heater",
        }



    def Pad(self, s):
        aesBlockSize = 16
        return s + (aesBlockSize - len(s) % aesBlockSize) * chr(aesBlockSize - len(s) % aesBlockSize)            

    def FetchResult(self, cipher, ip_addr, port, timeout, json):
        _LOGGER.info('Fetching(%s, %s, %s, %s)' % (ip_addr, port, timeout, json))
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        clientSock.settimeout(timeout)
        clientSock.sendto(bytes(json, "utf-8"), (ip_addr, port))
        _LOGGER.info('3')
        data, addr = clientSock.recvfrom(64000)
        receivedJson = simplejson.loads(data)
        clientSock.close()
        pack = receivedJson['pack']
        base64decodedPack = base64.b64decode(pack)
        decryptedPack = cipher.decrypt(base64decodedPack)
        if self.encryption_version == 2:
            tag = receivedJson['tag']
            cipher.verify(base64.b64decode(tag))
        decodedPack = decryptedPack.decode("utf-8")
        end = decodedPack.rfind("}")
        if end == -1:
            raise ValueError(f"No valid JSON object in device response: {decodedPack!r}")
        replacedPack = decodedPack[:end + 1].replace("\x0f", "")
        loadedJsonPack = simplejson.loads(replacedPack)
        return loadedJsonPack

    def GetDeviceKey(self):
        _LOGGER.info('Retrieving HVAC encryption key')
        GENERIC_GREE_DEVICE_KEY = "a3K8Bx%2r8Y7#xDh"
        cipher = AES.new(GENERIC_GREE_DEVICE_KEY.encode("utf8"), AES.MODE_ECB)
        pack = base64.b64encode(cipher.encrypt(self.Pad('{"mac":"' + str(self._mac_addr) + '","t":"bind","uid":0}').encode("utf8"))).decode('utf-8')
        jsonPayloadToSend = '{"cid": "app","i": 1,"pack": "' + pack + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid": 0}'
        try:
            self._encryption_key = self.FetchResult(cipher, self._ip_addr, self._port, self._timeout, jsonPayloadToSend)['key'].encode("utf8")
        except (OSError, ValueError) as err:
            _LOGGER.warning("Error getting device encryption key: %s", err)
            self._device_online = False
            self._online_attempts = 0
            return False
        else:
            _LOGGER.info('Fetched device encryption key: %s' % str(self._encryption_key))
            self.CIPHER = AES.new(self._encryption_key, AES.MODE_ECB)
            self._device_online = True
            self._online_attempts = 0
            return True

    def GetGCMCipher(self, key):
        cipher = AES.new(key, AES.MODE_GCM, nonce=GCM_IV)
        cipher.update(GCM_ADD)
        return cipher

    def EncryptGCM(self, key, plaintext):
        encrypted_data, tag = self.GetGCMCipher(key).encrypt_and_digest(plaintext.encode("utf8"))
        pack = base64.b64encode(encrypted_data).decode('utf-8')
        tag = base64.b64encode(tag).decode('utf-8')
        return (pack, tag)

    def GetDeviceKeyGCM(self):
        _LOGGER.info('Retrieving HVAC encryption key')
        GENERIC_GREE_DEVICE_KEY = b'{yxAHAY_Lm6pbC/<'
        plaintext = '{"cid":"' + str(self._mac_addr) + '", "mac":"' + str(self._mac_addr) + '","t":"bind","uid":0}'
        pack, tag = self.EncryptGCM(GENERIC_GREE_DEVICE_KEY, plaintext)
        jsonPayloadToSend = '{"cid": "app","i": 1,"pack": "' + pack + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid": 0, "tag" : "' + tag + '"}'
        try:
            self._encryption_key = self.FetchResult(self.GetGCMCipher(GENERIC_GREE_DEVICE_KEY), self._ip_addr, self._port, self._timeout, jsonPayloadToSend)['key'].encode("utf8")
        except (OSError, ValueError) as err:
            _LOGGER.warning("Error getting device encryption key: %s", err)
            self._device_online = False
            self._online_attempts = 0
            return False
        else:
            _LOGGER.info('Fetched device encryption key: %s' % str(self._encryption_key))
            self._device_online = True
            self._online_attempts = 0
            return True

    def GreeGetValues(self, propertyNames):
        plaintext = '{"cols":' + simplejson.dumps(propertyNames) + ',"mac":"' + str(self._mac_addr) + '","t":"status"}'
        if self.encryption_version == 1:
            cipher = self.CIPHER
            jsonPayloadToSend = '{"cid":"app","i":0,"pack":"' + base64.b64encode(cipher.encrypt(self.Pad(plaintext).encode("utf8"))).decode('utf-8') + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid":{}'.format(self._uid) + '}'
        elif self.encryption_version == 2:
            pack, tag = self.EncryptGCM(self._encryption_key, plaintext)
            jsonPayloadToSend = '{"cid":"app","i":0,"pack":"' + pack + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid":{}'.format(self._uid) + ',"tag" : "' + tag + '"}'
            cipher = self.GetGCMCipher(self._encryption_key)
        response = self.FetchResult(cipher, self._ip_addr, self._port, self._timeout, jsonPayloadToSend)
        # 按设备响应自带的 cols/dat 配对，而不是按我们请求的字段顺序猜。
        # 不同机型返回的字段集合和顺序都可能不同，cols 才是字段名的事实来源。
        cols = response.get("cols")
        dat = response.get("dat")
        if not cols or dat is None:
            _LOGGER.warning("Device status response missing cols/dat: %s", response)
            return {}
        result = dict(zip(cols, dat))
        _LOGGER.debug("Device status parsed fields: %s", result)
        return result

    def SetAcOptions(self, acOptions, newOptionsToOverride, optionValuesToOverride = None):
        if not (optionValuesToOverride is None):
            _LOGGER.info('Setting acOptions with retrieved HVAC values')
            # 设备通常只返回它实际支持的字段，长度可能少于请求的字段数。
            # 必须按实际返回长度安全配对，否则用固定下标取值会 IndexError，
            # 导致整个 SyncState 中断、HA 实体状态永远不更新。
            if isinstance(optionValuesToOverride, dict):
                for key, value in optionValuesToOverride.items():
                    if key in acOptions:
                        _LOGGER.info('Setting %s: %s' % (key, value))
                        acOptions[key] = value
            else:
                _LOGGER.info('Device returned %s values for %s requested fields',
                             len(optionValuesToOverride), len(newOptionsToOverride))
                for i, key in enumerate(newOptionsToOverride):
                    if i >= len(optionValuesToOverride):
                        _LOGGER.debug('Device did not return field %s (index %s); keeping previous value', key, i)
                        continue
                    _LOGGER.info('Setting %s: %s' % (key, optionValuesToOverride[i]))
                    acOptions[key] = optionValuesToOverride[i]
            _LOGGER.info('Done setting acOptions')
        else:
            _LOGGER.info('Overwriting acOptions with new settings')
            for key, value in newOptionsToOverride.items():
                _LOGGER.info('Overwriting %s: %s' % (key, value))
                acOptions[key] = value
            _LOGGER.info('Done overwriting acOptions')
        return acOptions

    def SendStateToAc(self, timeout):
        # 只下发有值且可写的字段；未读到（None）的字段不下发，避免设备误判。
        fields = [k for k in WRITABLE_FIELDS if self._acOptions.get(k) is not None]
        if not fields:
            _LOGGER.warning("No writable fields available; skip sending state to AC")
            return
        opt = ",".join('"%s"' % k for k in fields)
        p = ",".join(str(self._acOptions[k]) for k in fields)

        statePackJson = '{"opt":[' + opt + '],"p":[' + p + '],"t":"cmd"}'
        _LOGGER.debug("Sending state to AC: %s", statePackJson)
        if self.encryption_version == 1:
            cipher = self.CIPHER
            sentJsonPayload = '{"cid":"app","i":0,"pack":"' + base64.b64encode(cipher.encrypt(self.Pad(statePackJson).encode("utf8"))).decode('utf-8') + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid":{}'.format(self._uid) + '}'
        elif self.encryption_version == 2:
            pack, tag = self.EncryptGCM(self._encryption_key, statePackJson)
            sentJsonPayload = '{"cid":"app","i":0,"pack":"' + pack + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid":{}'.format(self._uid) + ',"tag":"' + tag +'"}'
            cipher = self.GetGCMCipher(self._encryption_key)
        receivedJsonPayload = self.FetchResult(cipher, self._ip_addr, self._port, timeout, sentJsonPayload)
        _LOGGER.info('Done sending state to HVAC: ' + str(receivedJsonPayload))

    def UpdateHATargetTemperature(self):
        # SetTemInt 是设定温度的直接值（如 50 = 50°C），无 +100 偏移、无需 ÷10。
        set_tem = self._acOptions.get('SetTemInt')
        if set_tem is None:
            return
        self._target_temperature = float(set_tem)
        if self._target_temp_entity_id:
            target_temp_state = self.hass.states.get(self._target_temp_entity_id)
            if target_temp_state:
                attr = target_temp_state.attributes
                if MIN_TEMP <= self._target_temperature <= MAX_TEMP:
                    self.hass.states.async_set(self._target_temp_entity_id, float(self._target_temperature), attr)
        _LOGGER.info('HA target temperature set from SetTemInt: %s', self._target_temperature)



    def UpdateHAHvacMode(self):
        # Sync current HVAC operation mode to HA
        if (self._acOptions['Pow'] == 0):
            self._hvac_mode = STATE_OFF
        else:
            wmod = self._acOptions['Wmod']
            if wmod is not None and 0 <= wmod < len(self._hvac_modes):
                self._hvac_mode = self._hvac_modes[wmod]
            else:
                _LOGGER.warning("Unexpected Wmod value %s, defaulting mode to off", wmod)
                self._hvac_mode = STATE_OFF
        _LOGGER.info('HA operation mode set according to HVAC state to: ' + str(self._hvac_mode))

    def UpdateHACurrentTemperature(self):
        if not self._temp_sensor_entity_id:
            wat = self._acOptions.get('WatTmp')
            if wat is not None:
                temp = wat - TEMP_OFFSET if wat > TEMP_OFFSET else wat
                self._current_temperature = self.hass.config.units.temperature(float(temp), self._unit_of_measurement)
                _LOGGER.info('HA current temperature set from WatTmp: %s', self._current_temperature)

    def UpdateHAStateToCurrentACState(self):
        self.UpdateHATargetTemperature()
        self.UpdateHAHvacMode()
        self.UpdateHACurrentTemperature()

    def SyncState(self, acOptions = {}):
        #Fetch current settings from HVAC
        _LOGGER.info('Starting SyncState')

        optionsToFetch = self._optionsToFetch

        try:
            currentValues = self.GreeGetValues(optionsToFetch)
        except (OSError, ValueError) as err:
            _LOGGER.warning("Could not connect with device: %s", err)
            if not self._disable_available_check:
                self._online_attempts +=1
                if (self._online_attempts == self._max_online_attempts):
                    _LOGGER.info('Could not connect with device %s times. Set it as offline.' % self._max_online_attempts)
                    self._device_online = False
                    self._online_attempts = 0
        else:
            if not self._disable_available_check:
                if not self._device_online:
                    self._device_online = True
                    self._online_attempts = 0
            # Set latest status from device
            self._acOptions = self.SetAcOptions(self._acOptions, optionsToFetch, currentValues)

            # Overwrite status with our choices
            if not(acOptions == {}):
                self._acOptions = self.SetAcOptions(self._acOptions, acOptions)

            # Initialize the receivedJsonPayload variable (for return)
            receivedJsonPayload = ''

            # If not the first (boot) run, update state towards the HVAC
            if not (self._firstTimeRun):
                if not(acOptions == {}):
                    # loop used to send changed settings from HA to HVAC
                    self.SendStateToAc(self._timeout)
            else:
                # loop used once for Gree Climate initialisation only
                self._firstTimeRun = False

            # Update HA state to current HVAC state
            self.UpdateHAStateToCurrentACState()

            _LOGGER.info('Finished SyncState')
            return receivedJsonPayload

    async def _async_temp_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        s = str(old_state.state) if hasattr(old_state,'state') else "None"
        _LOGGER.info('temp_sensor state changed | ' + str(entity_id) + ' from ' + s + ' to ' + str(new_state.state))
        # Handle temperature changes.
        if new_state is None:
            return
        self._async_update_current_temp(new_state)
        self.async_write_ha_state()

    @callback
    def _async_update_current_temp(self, state):
        _LOGGER.info('Thermostat updated with changed temp_sensor state | ' + str(state.state))
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        try:
            _state = state.state
            _LOGGER.info('Current state temp_sensor: ' + _state)
            if self.represents_float(_state):
                self._current_temperature = self.hass.config.units.temperature(
                    float(_state), unit)
                _LOGGER.info('Current temp: ' + str(self._current_temperature))
        except ValueError as ex:
            _LOGGER.error('Unable to update from temp_sensor: %s' % ex)

    def represents_float(self, s):
        _LOGGER.info('temp_sensor state represents_float |' + str(s))
        try: 
            float(s)
            return True
        except ValueError:
            return False     

    async def _async_target_temp_entity_state_changed(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        _LOGGER.info('target_temp_entity state changed | ' + str(entity_id) + ' from ' + (str(old_state.state) if hasattr(old_state,'state') else "None") + ' to ' + str(new_state.state))
        if new_state is None:
            return
        if new_state.state == "off" and (old_state is None or old_state.state is None):
            _LOGGER.info('target_temp_entity state changed to off, but old state is None. Ignoring to avoid beeps.')
            return
        if int(float(new_state.state)) is self._target_temperature:
            # do nothing if state change is triggered due to Sync with HVAC
            return
        self._async_update_current_target_temp(new_state)
        self.async_write_ha_state()

    @callback
    def _async_update_current_target_temp(self, state):
        s = int(float(state.state))
        _LOGGER.info('Updating HVAC with changed target_temp_entity state | ' + str(s))
        if (s >= MIN_TEMP) and (s <= MAX_TEMP):
            self.SyncState({'SetTemInt': s})
            return
        _LOGGER.error('Unable to update from target_temp_entity!')





    @property
    def should_poll(self):
        _LOGGER.info('should_poll()')
        # Return the polling state.
        return True

    @property
    def available(self):
        if self._disable_available_check:
            return True
        else:
            if self._device_online:
                _LOGGER.info('available(): Device is online')
                return True
            else:
                _LOGGER.info('available(): Device is offline')
                return False

    def update(self) -> None:
        _LOGGER.info('update()')
        if not self._encryption_key:
            if self.encryption_version == 1:
                if self.GetDeviceKey():
                    self.SyncState()
            elif self.encryption_version == 2:
                if self.GetDeviceKeyGCM():
                    self.SyncState()
            else:
                _LOGGER.error('Encryption version %s is not implemented.' % self.encryption_version)
        else:
            self.SyncState()

    @property
    def name(self):
        _LOGGER.info('name(): ' + str(self._name))
        # Return the name of the climate device.
        return self._name


    @property
    def supported_features(self):
        return WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE



    @property
    def min_temp(self):
        _LOGGER.info('min_temp(): ' + str(MIN_TEMP))
        # Return the minimum temperature.
        return MIN_TEMP
    @property
    def max_temp(self):
        _LOGGER.info('max_temp(): ' + str(MAX_TEMP))
        # Return the maximum temperature.
        return MAX_TEMP

    @property
    def target_temperature_low(self):
        return self.min_temp

    @property
    def target_temperature_high(self):
        return self.max_temp

    @property
    def precision(self):
        return PRECISION_WHOLE

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS
        # return TEMP_CELSIUS

    @property
    def current_operation(self):
        _LOGGER.info('hvac_mode(): ' + str(self._hvac_mode))
        # Return current operation mode ie. heat, cool, idle.
        return self._hvac_mode

    @property
    def current_temperature(self):
        _LOGGER.info('current_temperature(): ' + str(self._current_temperature))
        # Return the current temperature.
        return self._current_temperature

    @property
    def target_temperature(self):
        _LOGGER.info('target_temperature(): ' + str(self._target_temperature))
        # Return the temperature we try to reach.
        return self._target_temperature

    @property
    def unique_id(self):
        # Return unique_id
        return self._unique_id

    @property
    def extra_state_attributes(self) -> dict:
        """Return the optional device state attributes."""
        data = {
            "target_temp_step": self._target_temperature_step,
            "温度单位 (TemUn)": "摄氏" if self._acOptions.get('TemUn') == 0 else "华氏",
            "设备名 (name)": self._acOptions.get('name'),
        }
        return data

    def _format_time(self, minutes):
        if minutes is None:
            return "未设置"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def set_temperature(self, **kwargs) -> None:
        _LOGGER.info('set_temperature(): ' + str(kwargs.get(ATTR_TEMPERATURE)))
        # Set new target temperatures.
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            # do nothing if HVAC is switched off
            if not (self._acOptions['Pow'] == 0):
                # SetTemInt 是直接值（如 50 = 50°C），不再 ×10。
                temp = int(kwargs.get(ATTR_TEMPERATURE))
                _LOGGER.info('SyncState with SetTemInt=%s', temp)
                self.SyncState({ 'SetTemInt': temp })
                self.schedule_update_ha_state()

    def set_operation_mode(self, hvac_mode) -> None:
        _LOGGER.info('set_hvac_mode(): ' + str(hvac_mode))
        # Set new operation mode.
        c = {}
        if (hvac_mode == STATE_OFF):
            c.update({'Pow': 0})
        else:
            c.update({'Pow': 1, 'Wmod': self._hvac_modes.index(hvac_mode)})

        self.SyncState(c)
        self.schedule_update_ha_state()

    @property
    def operation_list(self):
        return self._hvac_modes

    def turn_on(self) -> None:
        _LOGGER.info('turn_on(): ')
        # Turn on.
        c = {'Pow': 1}

        self.SyncState(c)
        self.schedule_update_ha_state()

    def turn_off(self) -> None:
        _LOGGER.info('turn_off(): ')
        # Turn off.
        c = {'Pow': 0}

        self.SyncState(c)
        self.schedule_update_ha_state()

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(ft.partial(self.turn_on, **kwargs))

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(ft.partial(self.turn_off, **kwargs))