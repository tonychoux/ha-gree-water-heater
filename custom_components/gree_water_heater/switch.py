"""Gree water heater timer switches.

定时组开关（Sch1 / Sch2），可读写 0/1。
组内时间字段（Wtmr1/2 的 Start/End Hr/Min）与定时模式（WschTyp）作为开关属性展示：
- WschTyp=0（定时开关）：开始时间=开机，结束时间=关机
- WschTyp=1（定时用水）：开始/用水时间生效，结束时间忽略
"""

import asyncio
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.dispatcher import async_dispatcher_send

from . import refresh_signal

_LOGGER = logging.getLogger(__name__)


class _GreeTimerSwitch(SwitchEntity):
    """定时组开关基类。"""

    def __init__(self, water_heater, field, name, entry_id):
        self._water_heater = water_heater
        self._field = field  # 'Sch1' / 'Sch2'
        self._entry_id = entry_id
        mac = getattr(water_heater, "_mac_addr", "")
        mac_str = "".join([c for c in mac if c.isalnum()])
        self._attr_unique_id = f"gree_{mac_str}_timer_{field.lower()}"
        self._attr_name = name

    @property
    def available(self):
        return self._water_heater.available

    @property
    def device_info(self):
        return self._water_heater.device_info

    @property
    def is_on(self):
        value = self._water_heater._acOptions.get(self._field)
        return value == 1

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(
            self._water_heater.SyncState, {self._field: 1}
        )
        self._water_heater.schedule_update_ha_state()
        # 通知该组时间实体按新开关状态重算 available
        async_dispatcher_send(self.hass, refresh_signal(self._entry_id))
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(
            self._water_heater.SyncState, {self._field: 0}
        )
        self._water_heater.schedule_update_ha_state()
        async_dispatcher_send(self.hass, refresh_signal(self._entry_id))
        self.async_write_ha_state()

    def _fmt_hhmm(self, hr_key, min_key):
        opts = self._water_heater._acOptions
        hr, minute = opts.get(hr_key), opts.get(min_key)
        if hr is None or minute is None:
            return None
        return f"{hr:02d}:{minute:02d}"

    @property
    def extra_state_attributes(self):
        opts = self._water_heater._acOptions
        sch_typ = opts.get("WschTyp")
        group = "1" if self._field == "Sch1" else "2"
        attrs = {
            "定时模式 (WschTyp)": (
                "定时开关" if sch_typ == 0 else "定时用水" if sch_typ == 1 else "未知"
            )
        }
        attrs["开始/用水时间"] = self._fmt_hhmm(
            f"Wtmr{group}StartHr", f"Wtmr{group}StartMin"
        )
        # WschTyp=1（定时用水）时结束时间忽略，不展示。
        if sch_typ != 1:
            attrs["结束时间"] = self._fmt_hhmm(
                f"Wtmr{group}EndHr", f"Wtmr{group}EndMin"
            )
        return attrs


async def async_setup_entry(hass, entry, async_add_entities):
    for _ in range(10):
        water_heater = hass.data["gree_water_heater_entities"].get(entry.entry_id)
        if water_heater:
            break
        await asyncio.sleep(0.2)
    else:
        _LOGGER.error(
            "gree_water_heater switch async_setup_entry: "
            "water_heater entity not found for entry_id %s",
            entry.entry_id,
        )
        return

    async_add_entities(
        [
            _GreeTimerSwitch(water_heater, "Sch1", "定时组1开关", entry.entry_id),
            _GreeTimerSwitch(water_heater, "Sch2", "定时组2开关", entry.entry_id),
        ],
        True,
    )


async def async_unload_entry(hass, entry):
    return True
