import logging
from datetime import datetime
from homeassistant.components.event import EventEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .const import DOMAIN, ALERT_TYPE, OPEN_TYPE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """event 플랫폼 설정"""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = [
        ZigbangDoorlockEvent(coordinator, device_id)
        for device_id in coordinator.data
    ]

    if entities:
        async_add_entities(entities)


class ZigbangDoorlockEvent(CoordinatorEntity, EventEntity):
    """직방 도어락 이벤트 엔티티"""

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_event"
        self._attr_has_entity_name = True
        
        # translations 디렉토리를 통한 다국어 처리 지원
        self._attr_translation_key = "doorlock_alert"
        self._attr_icon = "mdi:message-badge-outline"
        self._attr_event_types = ["doorlock_activity"]

        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
        }

    def _handle_coordinator_update(self) -> None:
        """코디네이터 데이터가 업데이트될 때 호출됨"""
        device_data = self.coordinator.data.get(self._device_id, {})
        new_events = device_data.get("new_events", [])

        # 시스템 언어 설정 가져오기 (예: 'ko', 'en-US' 등) -> 'ko'로 시작하면 한국어, 그 외는 영어로 폴백
        system_lang = self.coordinator.hass.config.language
        lang_key = "ko" if system_lang.startswith("ko") else "en"
        
        alert_dict = ALERT_TYPE.get(lang_key, ALERT_TYPE["en"])
        open_dict = OPEN_TYPE.get(lang_key, OPEN_TYPE["en"])

        # __init__.py 에서 수집해준 새 이벤트가 있을 경우, 이를 Home Assistant 엔티티 이벤트로 발송
        for evt in new_events:
            raw_dt = evt.get("rgstDt")
            formatted_dt = raw_dt
            
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
                    _LOGGER.error("시간 변환 오류: %s", e)

            self._trigger_event(
                "doorlock_activity",
                {
                    "message": evt.get("msgText"),
                    "alert_type": alert_dict.get(evt.get("msgCd"), evt.get("msgCd")),
                    "open_type": open_dict.get(evt.get("pinTypeCd"), evt.get("pinTypeCd")),
                    "user_name": evt.get("pinNm"),
                    "alert_at": formatted_dt,
                }
            )

        super()._handle_coordinator_update()
