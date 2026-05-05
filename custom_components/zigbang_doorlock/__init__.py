import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store
from .api import ZigbangAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# 지원하는 플랫폼 플랫폼 정의
PLATFORMS = ["lock", "sensor", "event"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """통합 구성 요소 설정 """

    # 1. API 인스턴스 생성
    api = ZigbangAPI(entry.data["username"], entry.data["password"], entry.data["imei"])
    session = async_get_clientsession(hass)

    # 재부팅 시에도 이벤트를 기억하기 위해 Home Assistant 스토리지 사용
    store = Store(hass, 1, f"{DOMAIN}_events_{entry.entry_id}")
    stored_data = await store.async_load() or {}
    processed_events = set(stored_data.values())

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
            device_dict = {device["deviceId"]: device for device in devices}

            # 새로운 알림 이벤트 처리 로직
            for device_id in device_dict:
                history_list = await api.fetch_inouthistory(session, device_id)
                
                # lock, sensor, event 등 다른 엔티티에서 최근 이력을 참조할 수 있도록 데이터 저장
                if history_list:
                    device_dict[device_id]["recentHistoryVOList"] = history_list[0]
                else:
                    device_dict[device_id]["recentHistoryVOList"] = {}

                last_known_event_id = stored_data.get(device_id)
                new_events = []
                current_latest_id = None

                # 리스트의 첫 번째에서 최대 세 번째까지 확인
                for history in history_list[:3]:
                    event_id = history.get("eventId")
                    if current_latest_id is None:
                        current_latest_id = event_id

                    if event_id == last_known_event_id or event_id in processed_events:
                        break  # 이전에 처리했던 이벤트를 만나면 중단

                    processed_events.add(event_id)
                    # 최초 등록 시점(last_known_event_id가 없을 때)에는 알림을 보내지 않음
                    if last_known_event_id is not None:
                        new_events.append(history)
                
                # 새로운 이벤트를 HA 이벤트 버스에 발송 (오래된 것부터 발생시키기 위해 역순 처리)
                for evt in reversed(new_events):
                    # 사용자가 요청한 msgText, msgCd, rgstDt와 기기를 식별할 수 있는 deviceId 포함
                    event_data = {"msgText": evt.get("msgText"), "msgCd": evt.get("msgCd"), "rgstDt": evt.get("rgstDt"), "device_id": device_id, "pinTypeCd": evt.get("pinTypeCd"), "pinNm": evt.get("pinNm")}
                    hass.bus.async_fire(f"{DOMAIN}_event", event_data)

                # event.py 엔티티에서 처리할 수 있도록 코디네이터 데이터에 새 이벤트 추가
                device_dict[device_id]["new_events"] = new_events

                # 가장 최신 이벤트 ID를 스토리지에 저장하여 재부팅 후에도 유지
                if current_latest_id and current_latest_id != last_known_event_id:
                    stored_data[device_id] = current_latest_id
                    await store.async_save(stored_data)

            return device_dict
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
