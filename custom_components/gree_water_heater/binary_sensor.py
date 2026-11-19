"""Gree water heater binary sensors.

- 整机故障  <- AllErr（0=正常，非0=故障），device_class=problem
- 运行状态  <- Wstate（0=未运行/保温中，1=正在加热），device_class=running

这两个字段本质都是二值状态、用户不可改，按 HA 规范用 binary_sensor：
前端自动给出对应图标与状态文案，自动化可直接用 on/off 判断，
无需匹配中文字符串。故障原始码保留在状态属性里。
"""

import asyncio
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

_LOGGER = logging.getLogger(__name__)


class _GreeBaseBinarySensor(BinarySensorEntity):
    """公共基类：唯一 id、设备信息、可用性。"""

    def __init__(self, water_heater, field, name):
        self._water_heater = water_heater
        self._field = field
        mac = getattr(water_heater, "_mac_addr", "")
        mac_str = "".join([c for c in mac if c.isalnum()])
        self._attr_unique_id = f"gree_{mac_str}_re_shui_qi_{field.lower()}"
        self._attr_name = name

    @property
    def available(self):
        return self._water_heater.available

    @property
    def device_info(self):
        return self._water_heater.device_info


class GreeFaultBinarySensor(_GreeBaseBinarySensor):
    """整机故障：AllErr=0 → off(正常)，非0 → on(故障)。"""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, water_heater):
        super().__init__(water_heater, "AllErr", "整机故障")

    @property
    def is_on(self):
        value = self._water_heater._acOptions.get("AllErr")
        return value is not None and value != 0

    @property
    def extra_state_attributes(self):
        return {"故障码 (AllErr)": self._water_heater._acOptions.get("AllErr")}


class GreeRunningBinarySensor(_GreeBaseBinarySensor):
    """运行状态：Wstate=1 → on(正在加热)，其他 → off(未运行/保温中)。"""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, water_heater):
        super().__init__(water_heater, "Wstate", "运行状态")

    @property
    def is_on(self):
        return self._water_heater._acOptions.get("Wstate") == 1


async def async_setup_entry(hass, entry, async_add_entities):
    # 主实体可能还在首次同步中，最多等 2 秒。
    for _ in range(10):
        water_heater = hass.data["gree_water_heater_entities"].get(entry.entry_id)
        if water_heater:
            break
        await asyncio.sleep(0.2)
    else:
        _LOGGER.error(
            "gree_water_heater binary_sensor async_setup_entry: "
            "water_heater entity not found for entry_id %s",
            entry.entry_id,
        )
        return

    async_add_entities(
        [
            GreeFaultBinarySensor(water_heater),
            GreeRunningBinarySensor(water_heater),
        ],
        True,
    )


async def async_unload_entry(hass, entry):
    return True
