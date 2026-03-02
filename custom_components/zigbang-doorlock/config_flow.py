import voluptuous as vol
from homeassistant import config_entries
from .api import ZigbangAPI
from .const import DOMAIN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from util import generate_random_imei

class ZigbangConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # API 세션 생성 및 로그인 테스트
            session = async_get_clientsession(self.hass)
            if not user_input.get("imei"):
                user_input["imei"] = generate_random_imei()

            api = ZigbangAPI(user_input["username"], user_input["password"], user_input["imei"])

            if await api.login(session):
                return self.async_create_entry(title="직방 도어락", data=user_input)
            else:
                errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Optional("imei"): str,
            }),
            errors=errors,
        )
