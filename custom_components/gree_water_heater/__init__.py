DOMAIN = "gree_water_heater"


def refresh_signal(entry_id):
    """定时实体互相刷新用的信号（模式/组开关变化后立即重算 available）。"""
    return f"{DOMAIN}_{entry_id}_timer_refresh"


async def async_setup_entry(hass, entry):
    # 保证数据结构一定存在
    hass.data.setdefault("gree_water_heater_entities", {})
    await hass.config_entries.async_forward_entry_setups(entry, ["water_heater", "sensor", "binary_sensor", "switch", "time", "select"])
    return True

async def async_unload_entry(hass, entry):
    await hass.config_entries.async_unload_platforms(entry, ["water_heater", "sensor", "binary_sensor", "switch", "time", "select"])
    return True