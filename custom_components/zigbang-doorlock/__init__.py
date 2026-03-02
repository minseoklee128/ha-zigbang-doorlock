import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import ZigbangAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# 지원하는 플랫폼 플랫폼 정의
PLATFORMS = ["lock", "sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """통합 구성 요소 설정 """

    # 1. API 인스턴스 생성
    api = ZigbangAPI(entry.data["username"], entry.data["password"], entry.data["imei"])
    session = async_get_clientsession(hass)

    # 2. 데이터 업데이트 코디네이터 정의
    async def async_update_data():
        """10초마다 실행될 상태 갱신 로직"""
        try:
            if not api.auth_token:
                if not await api.login(session):
                    raise UpdateFailed("로그인 인증 실패")
            # api.py의 fetch_doorlock_list 호출
            devices = await api.fetch_doorlock_list(session)
            # deviceId를 키로 하는 딕셔너리로 저장 (엔티티에서 접근하기 위함)
            return {device["deviceId"]: device for device in devices}
        except Exception as err:
            _LOGGER.error("데이터 업데이트 중 오류 발생: %s", err)
            raise UpdateFailed(f"서버 통신 실패: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="zigbang_doorlock_update",
        update_method=async_update_data,
        update_interval=timedelta(seconds=10),
    )

    # 3. 최초 데이터 불러오기
    await coordinator.async_config_entry_first_refresh()

    # 4. 엔티티에서 사용할 수 있도록 hass.data에 저장
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator
    }

    # 5. 플랫폼(lock.py, sensor.py) 로드
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """통합 구성 요소 언로드"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
