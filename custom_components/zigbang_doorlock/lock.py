import logging
from datetime import datetime
from homeassistant.components.lock import LockEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """lock 플랫폼 설정"""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    # 코디네이터 데이터(dict)의 key인 deviceId를 순회하며 엔티티 생성
    entities = [
        ZigbangDoorlock(coordinator, device_id)
        for device_id in coordinator.data
    ]

    if entities:
        async_add_entities(entities)

class ZigbangDoorlock(CoordinatorEntity, LockEntity):
    """직방 도어락 엔티티 (코디네이터 연동)"""

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator)
        self._device_id = device_id
        # 고정값 설정
        self._attr_unique_id = f"{device_id}_lock"
        self._attr_has_entity_name = True
        self._attr_name = None # 기기 이름은 device_info의 name을 따름

        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": self._device_data.get("deviceNm", "직방 도어락"),
            "model": self._device_data.get("productId", "SHP-Series"),
            "manufacturer": "Zigbang",
        }

    @property
    def _device_data(self):
        """코디네이터에서 내 기기의 최신 데이터 추출"""
        return self.coordinator.data.get(self._device_id, {})

    @property
    def is_locked(self):
        """잠금 상태 반환 (doorlockStatusVO -> locked)"""
        status = self._device_data.get("doorlockStatusVO", {})
        return status.get("locked", True)

    @property
    def extra_state_attributes(self):
        """도어락의 추가 속성 (최근 이력 정보)"""
        history = self.coordinator.data[self._device_id].get("recentHistoryVOList", {})
        if not history:
            return None

        raw_dt = history.get("rgstDt")
        formatted_dt = raw_dt

        # 문자열 시간을 HA 타임존 객체로 변환
        if raw_dt:
            try:
                # 1. 문자열을 naive datetime으로 파싱
                naive_dt = datetime.strptime(raw_dt, "%Y-%m-%d %H:%M:%S")
                _LOGGER.debug("naive_dt: %s", naive_dt)
                utc_dt = naive_dt.replace(tzinfo=dt_util.UTC)
                _LOGGER.debug("utc_dt: %s", utc_dt)
                # 2. HA 시스템 타임존 주입 (as_local은 타임존이 없을 경우 시스템 타임존으로 간주)
                local_dt = dt_util.as_local(utc_dt)
                _LOGGER.debug("local_dt: %s", local_dt)
                # 3. ISO 포맷 문자열로 변환 (HA UI에서 시간으로 인식하기 좋음)
                formatted_dt = local_dt.isoformat()
                _LOGGER.debug("formatted_dt: %s", formatted_dt)
            except Exception as e:
                _LOGGER.error("일시 timezone 적용 시 오류, %s", e)
                formatted_dt = raw_dt

        return {
            "last_event_time": formatted_dt,
            "last_event_msg": history.get("msgText"),
            "last_event_code": history.get("msgCd"),
            "event_id": history.get("eventId")
        }

    async def async_unlock(self, **kwargs):
        """도어락 열기 명령 실행"""
        api = self.coordinator.hass.data[DOMAIN][self.coordinator.config_entry.entry_id]["api"]
        session = async_get_clientsession(self.coordinator.hass)

        _LOGGER.debug("[Zigbang] %s 기기에 열기 명령을 전송합니다.", self.name)

        # API 호출
        success = await api.control_unlock(session, self._device_id)

        if success:
            # 명령 성공 시 즉시 상태를 업데이트하여 사용자에게 피드백 제공
            # (실제 문이 열린 뒤 다음 30초 주기에서 다시 확인됨)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("[Zigbang] 열기 명령 전송에 실패했습니다.")
