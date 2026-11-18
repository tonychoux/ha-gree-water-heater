from homeassistant import config_entries
import voluptuous as vol

class GreeWatConfigFlow(config_entries.ConfigFlow, domain="gree_water_heater"):
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input["mac"].lower().replace(":", ""))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input["name"], data=user_input)
        data_schema = vol.Schema({
            vol.Required("name", default="Gree WaterHeater"): str,
            vol.Required("host"): str,
            vol.Required("port", default=7000): int,
            vol.Required("mac"): str,
            vol.Optional("timeout", default=10): int,
            vol.Required("encryption_version", default=1): vol.In([1, 2]),
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


class GreeWatOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        # 取现有配置作为默认值
        data_schema = vol.Schema({
            vol.Required("name", default=self.config_entry.data.get("name", "")): str,
            vol.Required("host", default=self.config_entry.data.get("host", "")): str,
            vol.Required("port", default=self.config_entry.data.get("port", 7000)): int,
            vol.Required("mac", default=self.config_entry.data.get("mac", "")): str,
            vol.Optional("timeout", default=self.config_entry.data.get("timeout", 10)): int,
            vol.Required("encryption_version", default=self.config_entry.data.get("encryption_version", 1)): vol.In([1, 2]),
        })
        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)