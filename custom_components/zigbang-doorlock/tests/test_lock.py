from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.zigbang_doorlock.const import DOMAIN
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED
from unittest.mock import patch

async def test_lock_entity(hass, mock_zigbang_api_client):
    """도어락 엔티티 상태 및 제어 테스트"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test", "password": "test", "imei": "123456789012345"},
    )
    entry.add_to_hass(hass)

    with patch("custom_components.zigbang_doorlock.ZigbangAPI", return_value=mock_zigbang_api_client):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # 엔티티 ID (lock.py에서 unique_id 기반으로 생성됨)
    entity_id = "lock.test_doorlock"

    # 1. 초기 상태 확인 (Mock 데이터에서 locked=True)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_LOCKED

    # 속성 확인
    assert state.attributes["model"] == "SHP-DP960"
    assert state.attributes["last_event_msg"] == "Locked"

    # 2. 잠금 해제(Unlock) 서비스 호출 테스트
    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": entity_id},
        blocking=True,
    )

    # API control_unlock 호출 확인
    mock_zigbang_api_client.control_unlock.assert_called_once_with(
        hass.helpers.aiohttp_client.async_get_clientsession(hass), "test_device_id"
    )
