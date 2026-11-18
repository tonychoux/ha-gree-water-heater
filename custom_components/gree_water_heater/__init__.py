DOMAIN = "gree_water_heater"

async def async_setup_entry(hass, entry):
    # 保证数据结构一定存在
    hass.data.setdefault("gree_water_heater_entities", {})
    await hass.config_entries.async_forward_entry_setups(entry, ["water_heater", "sensor", "switch", "time", "select"])
    return True

async def async_unload_entry(hass, entry):
    await hass.config_entries.async_unload_platforms(entry, ["water_heater", "sensor", "switch", "time", "select"])
    return True