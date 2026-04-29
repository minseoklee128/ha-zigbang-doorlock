import logging
import json
import datetime
import hashlib
import aiohttp
from typing import Dict, Any, Optional

_LOGGER = logging.getLogger(__name__)

class ZigbangAPI:
    def __init__(self, username, password, imei):
        self.base_url = "https://iot.samsung-ihp.com:8088/openhome"
        self.username = username
        self.password = password
        self.imei = imei
        self.app_ver = None
        self.auth_token = None
        self.member_id = None
        self.auth_code = None

    def _get_timestamp(self) -> str:
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    def _hash(self, data: str) -> str:
        return hashlib.sha512(data.encode()).hexdigest()

    def _encrypt_password(self, password: str) -> str:
        return self._hash(password)

    def _generate_hash_data(self, payload: Dict[str, Any]) -> str:
        combined_values = "".join([str(v) for v in payload.values() if v is not None])
        return self._hash(combined_values)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SamsungIHP/ADR",
            "Accept": "application/json"
        }
        auth_val = f"CUL {self.auth_token}" if self.auth_token else "CUL "
        headers["Authorization"] = auth_val
        if self.auth_code:
            headers["AuthCode"] = self.auth_code
        return headers

    async def async_request(self, method: str, uri: str, session: aiohttp.ClientSession, params: Optional[Dict] = None, body: Optional[Dict] = None, loginRetry = True) -> Optional[Dict[str, Any]]:
        """명시적으로 params(쿼리)와 body(JSON)를 받아 처리하는 공통 요청 함수"""
        url = f"{self.base_url}{uri}"
        headers = self._get_headers()

        # [LOG] 상세 Request 정보 출력
        _LOGGER.debug(
                "[Zigbang REQUEST]\nMethod: %s\nURL: %s\nParams: %s\nBody: %s\nHeaders: %s",
            method, url, params, json.dumps(body, indent=2, ensure_ascii=False) if body else "None", json.dumps(headers, indent=2, ensure_ascii=False)
        )

        try:
            # 명시적으로 params와 json 인자에 매핑하여 호출
            # 로그인 미처리시 로그인 로직 추가
            async with session.request(method, url, headers=headers, params=params, json=body) as response:
                response_text = await response.text()
                _LOGGER.debug("[Zigbang RESPONSE]\nStatus: %s\nBody: %s", response.status, response_text)

                # 401 Unauthorized 처리 (자동 재로그인)
                if response.status == 401:
                    _LOGGER.info("[Zigbang] 401 감지. 토큰 갱신 시도...")
                    if loginRetry == False:
                        _LOGGER.error("[Zigbang] 재로그인 후 처리하였으나 오류 검출(%s)", response_text)
                        raise Exception("auth failed")
                    if await self.login(session):
                        _LOGGER.info("[Zigbang] 재로그인 성공. 요청 재시도.")
                        # 재시도 시에는 갱신된 헤더가 적용되도록 함수를 다시 호출
                        result = await self.async_request(method, uri, session, params, body, False)
                        return result
                    return None

                if response.status == 200:
                    return json.loads(response_text)
                _LOGGER.error("[Zigbang] 직방 API 호출 시 오류 확인됨(%s)", response_text)
                raise Exception("API Call failed")

        except Exception as e:
            _LOGGER.error("[Zigbang] 통신 예외: %s", str(e))
            return None

    async def login(self, session: aiohttp.ClientSession) -> bool:
        """로그인 및 토큰 확보"""
        await self.fetch_app_ver(session)

        uri = "/v10/user/login"
        payload = {
            "apiVer": "v20", "authNumber": "", "countryCd": "KR", "locale": "ko_KR",
            "locationAgreeYn": "N", "mobileNum": "", "osVer": "13", "overwrite": True,
            "pushToken": "", "timeZone": 0, "appVer": self.app_ver, "osTypeCd": "ADR",
            "createDate": self._get_timestamp(), "loginId": self.username,
            "pwd": self._encrypt_password(self.password), "imei": self.imei,
        }
        payload["hashData"] = self._generate_hash_data(payload)
        # [LOG] 상세 Request 정보 출력
        _LOGGER.debug(
            "[Zigbang LOGIN REQUEST]\nMethod: %s\nURL: %s\nParams: %s\nBody: %s",
            "PUT", uri, None, json.dumps(payload, indent=2, ensure_ascii=False) if payload else "None"
        )

        # 로그인은 무한루프 방지를 위해 직접 호출
        async with session.put(f"{self.base_url}{uri}", json=payload, headers=self._get_headers()) as response:
            res_text = await response.text()
            _LOGGER.debug("[Zigbang LOGIN RESPONSE] %s: %s", response.status, res_text)
            if response.status == 200:
                data = json.loads(res_text)
                if data.get("result"):
                    self.auth_token = data.get("authToken")
                    self.auth_code = data.get("authCode")
                    self.member_id = data.get("memberId")
                    return True
            return False

    async def fetch_app_ver(self, session: aiohttp.ClientSession):
        uri = "/v20/appsetting/getappver"
        params = {"createDate": self._get_timestamp()}
        data = await self.async_request("GET", uri, session, params=params, loginRetry=False)
        if data and "AppVersionList" in data:
            for app in data["AppVersionList"]:
                if app.get("osTypeCd") == "ADR":
                    self.app_ver = app.get("osAppVer")
                    break

    async def fetch_doorlock_list(self, session: aiohttp.ClientSession):
        uri = "/v20/doorlockctrl/membersdoorlocklist"
        params = {
            "memberId": self.member_id,
            "createDate": self._get_timestamp(),
            "favoriteYn": "A"
        }
        data = await self.async_request("GET", uri, session, params=params)
        return data.get("doorlockVOList", []) if data else []

    async def control_unlock(self, session: aiohttp.ClientSession, device_id: str) -> bool:
        """도어락 열기 제어 (v20/doorlockctrl/open)"""
        if not self.member_id:
            _LOGGER.error("[Zigbang] memberId가 없어 제어 명령을 보낼 수 없습니다.")
            return False

        uri = "/v20/doorlockctrl/open"
        # 주신 명세 기반 페이로드 구성
        body = {
            "createDate": self._get_timestamp(),
            "deviceId": device_id,
            "open": True,
            "isSecurityMode": False,
            "memberId": self.member_id,
            "securityModeRptEndDt": "",
            "securityModeRptStartDt": "",
        }

        # 해시 데이터 추가
        body["hashData"] = self._generate_hash_data(body)

        # PUT 메서드로 요청
        data = await self.async_request("PUT", uri, session, body=body)

        if data and data.get("result"):
            _LOGGER.info("[Zigbang] 도어락 열기 명령 성공: %s", device_id)
            return True

        _LOGGER.error("[Zigbang] 도어락 열기 명령 실패")
        return False
