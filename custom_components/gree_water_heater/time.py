"""Gree water heater timer time entities.

定时组开始/结束时间（Wtmr1/2 的 Start/End Hr+Min），可调写入。
每个时间实体写入时同时下发对应的 时/分 两个字段。

可用规则（避免展示不生效的时间）：
- 定时模式 WschTyp=1（定时用水）：结束时间被忽略 → 结束时间实体不可用
- 定时组开关 Sch1/Sch2=0（组关闭）：该组所有时间实体不可用
"""

import asyncio
import logging
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import refresh_signal

_LOGGER = logging.getLogger(__name__)


class _GreeTimerTime(TimeEntity):
    """单个定时时间实体（时+分）。"""

    _attr_should_poll = True  # 兜底：定期重算 available，避免首次同步时序导致一直灰

    def __init__(self, water_heater, hr_key, min_key, name, unique_suffix,
                 sch_field, is_end, entry_id):
        self._water_heater = water_heater
        self._hr_key = hr_key
        self._min_key = min_key
        self._sch_field = sch_field      # 'Sch1' / 'Sch2'
        self._is_end = is_end            # 是否结束时间
        mac = getattr(water_heater, "_mac_addr", "")
        mac_str = "".join([c for c in mac if c.isalnum()])
        self._attr_unique_id = f"gree_{mac_str}_timer_{unique_suffix}"
        self._attr_name = name
        self._entry_id = entry_id

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        # 模式/组开关变化后立即重算 available，无需等轮询
        self.async_on_unload(
            async_dispatcher_connect(
                self.hass, refresh_signal(self._entry_id), self.async_write_ha_state
            )
        )

    @property
    def available(self):
        if not self._water_heater.available:
            return False
        opts = self._water_heater._acOptions
        # 定时组关闭 → 该组时间不可用
        if opts.get(self._sch_field) != 1:
            return False
        # 定时用水模式下结束时间被设备忽略 → 不可用
        if self._is_end and opts.get("WschTyp") == 1:
            return False
        return True

    @property
    def device_info(self):
        return self._water_heater.device_info

    @property
    def native_value(self):
        opts = self._water_heater._acOptions
        hr, minute = opts.get(self._hr_key), opts.get(self._min_key)
        if hr is None or minute is None:
            return None
        try:
            return time(int(hr), int(minute))
        except (ValueError, TypeError):
            return None

    async def async_set_value(self, value: time) -> None:
        changes = {self._hr_key: value.hour, self._min_key: value.minute}
        await self.hass.async_add_executor_job(self._water_heater.SyncState, changes)
        self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    for _ in range(10):
        water_heater = hass.data["gree_water_heater_entities"].get(entry.entry_id)
        if water_heater:
            break
        await asyncio.sleep(0.2)
    else:
        _LOGGER.error(
            "gree_water_heater time async_setup_entry: "
            "water_heater entity not found for entry_id %s",
            entry.entry_id,
        )
        return

    eid = entry.entry_id
    async_add_entities(
        [
            _GreeTimerTime(water_heater, "Wtmr1StartHr", "Wtmr1StartMin",
                           "定时1开始时间", "t1_start", "Sch1", False, eid),
            _GreeTimerTime(water_heater, "Wtmr1EndHr", "Wtmr1EndMin",
                           "定时1结束时间", "t1_end", "Sch1", True, eid),
            _GreeTimerTime(water_heater, "Wtmr2StartHr", "Wtmr2StartMin",
                           "定时2开始时间", "t2_start", "Sch2", False, eid),
            _GreeTimerTime(water_heater, "Wtmr2EndHr", "Wtmr2EndMin",
                           "定时2结束时间", "t2_end", "Sch2", True, eid),
        ],
        True,
    )


async def async_unload_entry(hass, entry):
    return True
