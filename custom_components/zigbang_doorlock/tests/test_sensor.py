from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.zigbang_doorlock.const import DOMAIN
from unittest.mock import patch

async def test_battery_sensor(hass, mock_zigbang_api_client):
    """배터리 센서 상태 테스트"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test", "password": "test", "imei": "123456789012345"},
    )
    entry.add_to_hass(hass)

    with patch("custom_components.zigbang_doorlock.ZigbangAPI", return_value=mock_zigbang_api_client):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # 엔티티 ID (sensor.py에서 unique_id 기반으로 생성됨)
    entity_id = "sensor.test_doorlock_battery"

    # 상태 확인 (Mock 데이터에서 battery=85)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "85"
    assert state.attributes["unit_of_measurement"] == "%"
