"""Gree water heater timer mode select.

定时模式 WschTyp：
- 定时开关 (0)：开始时间=开机，结束时间=关机
- 定时用水 (1)：开始/用水时间生效，结束时间忽略
"""

import asyncio
import logging

from homeassistant.components.select import SelectEntity

_LOGGER = logging.getLogger(__name__)

MODE_OPTIONS = ["定时开关", "定时用水"]


class _GreeTimerModeSelect(SelectEntity):
    """定时模式选择实体。"""

    _attr_options = MODE_OPTIONS

    def __init__(self, water_heater):
        self._water_heater = water_heater
        mac = getattr(water_heater, "_mac_addr", "")
        mac_str = "".join([c for c in mac if c.isalnum()])
        self._attr_unique_id = f"gree_{mac_str}_timer_mode"
        self._attr_name = "定时模式"

    @property
    def available(self):
        return self._water_heater.available

    @property
    def device_info(self):
        return self._water_heater.device_info

    @property
    def current_option(self):
        value = self._water_heater._acOptions.get("WschTyp")
        if value == 0:
            return MODE_OPTIONS[0]
        if value == 1:
            return MODE_OPTIONS[1]
        return None

    async def async_select_option(self, option: str) -> None:
        if option not in MODE_OPTIONS:
            return
        mode = MODE_OPTIONS.index(option)
        await self.hass.async_add_executor_job(
            self._water_heater.SyncState, {"WschTyp": mode}
        )
        self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    for _ in range(10):
        water_heater = hass.data["gree_water_heater_entities"].get(entry.entry_id)
        if water_heater:
            break
        await asyncio.sleep(0.2)
    else:
        _LOGGER.error(
            "gree_water_heater select async_setup_entry: "
            "water_heater entity not found for entry_id %s",
            entry.entry_id,
        )
        return

    async_add_entities([_GreeTimerModeSelect(water_heater)], True)


async def async_unload_entry(hass, entry):
    return True
