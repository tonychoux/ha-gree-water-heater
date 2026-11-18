"""Gree water heater sensors.

字段映射来自用户机型（格力+ App GR_Code）实际回报的字段：
- 可用热水量  <- Watpercent（原始值 -100，如 200 -> 100%）
- 运行状态    <- Wstate（0=保温中, 1=正在加热）
- 整机故障    <- AllErr（0=正常, 非0=故障码）

所有值读取自主实体的 _acOptions 字典（由设备响应自带的 cols/dat 配对得到）。
"""

import asyncio
import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass

_LOGGER = logging.getLogger(__name__)


class _GreeBaseSensor(SensorEntity):
    """公共基类：提供唯一 id、设备信息、可用性。"""

    def __init__(self, water_heater, sensor_type, name, unit=None):
        self._water_heater = water_heater
        self._sensor_type = sensor_type
        mac = getattr(water_heater, "_mac_addr", "")
        mac_str = "".join([c for c in mac if c.isalnum()])
        self._attr_unique_id = f"gree_{mac_str}_re_shui_qi_{sensor_type.lower()}"
        self._attr_name = name
        if unit is not None:
            self._attr_native_unit_of_measurement = unit

    @property
    def available(self):
        return self._water_heater.available

    @property
    def device_info(self):
        return self._water_heater.device_info


class GreeHotWaterAmountSensor(_GreeBaseSensor):
    """可用热水量百分比（Watpercent - 100）。"""

    def __init__(self, water_heater):
        super().__init__(water_heater, "Watpercent", "可用热水量", "%")
        # HA 无合法的 percentage device_class，用 % 单位 + measurement 状态类。
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        value = self._water_heater._acOptions.get("Watpercent")
        if value is None:
            return None
        return value - 100


class GreeRunningStateSensor(_GreeBaseSensor):
    """当前运行状态（Wstate: 0=保温中, 1=正在加热）。"""

    _STATES = {0: "保温中", 1: "正在加热"}

    def __init__(self, water_heater):
        super().__init__(water_heater, "Wstate", "运行状态")

    @property
    def native_value(self):
        value = self._water_heater._acOptions.get("Wstate")
        if value is None:
            return None
        return self._STATES.get(value, f"未知({value})")


class GreeFaultSensor(_GreeBaseSensor):
    """整机综合故障码（AllErr: 0=正常）。"""

    def __init__(self, water_heater):
        super().__init__(water_heater, "AllErr", "整机故障")

    @property
    def native_value(self):
        value = self._water_heater._acOptions.get("AllErr")
        if value is None:
            return None
        return "正常" if value == 0 else f"故障({value})"


async def async_setup_entry(hass, entry, async_add_entities):
    # 主实体可能还在首次同步中，最多等 2 秒。
    for _ in range(10):
        water_heater = hass.data["gree_water_heater_entities"].get(entry.entry_id)
        if water_heater:
            break
        await asyncio.sleep(0.2)
    else:
        _LOGGER.error(
            "gree_water_heater sensor async_setup_entry: "
            "water_heater entity not found for entry_id %s",
            entry.entry_id,
        )
        return

    async_add_entities(
        [
            GreeHotWaterAmountSensor(water_heater),
            GreeRunningStateSensor(water_heater),
            GreeFaultSensor(water_heater),
        ],
        True,
    )


async def async_unload_entry(hass, entry):
    return True
