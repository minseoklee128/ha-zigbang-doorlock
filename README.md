# **🏠 Home Assistant Zigbang Doorlock Integration**

이 통합 구성요소(Custom Component)는 **직방(구 삼성 SDS) 스마트 도어락**을 Home Assistant와 연동하여 상태 모니터링, 배터리 관리, 원격 제어를 가능하게 합니다. 공식 앱의 기능을 HA 내에서 자동화 및 대시보드로 확장할 수 있습니다.

---

### **✨ 주요 기능**

*   **실시간 상태 동기화**: 도어락의 잠금/해제 상태를 실시간으로 모니터링하며 HA의 `lock` 엔티티와 동기화합니다.
*   **원격 보안 제어**: HA 대시보드 및 서비스 호출을 통해 안전하게 문을 열 수(Unlock) 있습니다.
*   **지능형 배터리 관리**: 배터리 잔량을 별도의 센서(`sensor`) 엔티티로 제공하여 교체 시기를 푸시 알림으로 설정할 수 있습니다.
*   **정밀한 출입 이력 분석**: 지문, 카드, 앱, 내부 수동 개폐 등 출입 수단과 사용자 정보를 엔티티의 속성(Attributes) 데이터로 상세히 제공합니다.
*   **자동 세션 복구**: API 인증 만료 시 자동으로 재로그인을 수행하여 끊김 없는 연결성을 유지합니다.
*   **타임존 자동 보정**: 서버의 UTC 시간을 한국 표준시(KST) 및 사용자의 지역 시간대에 맞춰 자동으로 변환합니다.

---

### **📂 디렉토리 구조**

```text
custom_components/zigbang_doorlock/
├── __init__.py      # 데이터 업데이트 코디네이터 및 통합 구성요소 초기화
├── api.py           # 직방 클라우드 서버와의 REST API 통신 로직
├── const.py         # 도메인, 기본 설정값 등 상수 정의
├── lock.py          # 도어락 잠금/해제 기능 엔티티 구현
├── sensor.py        # 배터리 잔량 및 상태 센서 엔티티 구현
└── manifest.json    # 통합 구성요소 메타데이터 및 의존성 정의
```

---

### **🚀 설치 및 설정**

#### **1. 수동 설치**
1. Home Assistant의 설정 디렉토리(`config/`) 내부의 `custom_components/` 폴더로 이동합니다. (폴더가 없으면 생성하세요.)
2. `custom_components/zigbang_doorlock/` 폴더를 생성하고 Repo 내 `custom_components/zigbang_doorlock/` 모든 파일을 해당 경로에 복사합니다.
3. Home Assistant를 **재시작**합니다.

#### **2. YAML 설정 (Configuration)**
`configuration.yaml` 파일에 아래 내용을 추가하고 사용자 정보를 입력합니다.

```yaml
# zigbang_doorlock 설정 예시
zigbang_doorlock:
  username: "YOUR_ZIGBANG_ID"        # 직방 앱 로그인 이메일 계정
  password: "YOUR_ZIGBANG_PASSWORD"  # 직방 앱 비밀번호
  imei: "YOUR_DEVICE_IMEI"           # (선택 사항) 스마트폰의 IMEI 값
```

---

### **💡 IMEI 설정 가이드**

직방 API 보안 정책상 **동일 계정에서 새로운 IMEI로 로그인할 경우 기존 기기는 로그아웃** 처리됩니다.

*   **공존 모드 (추천)**: 현재 사용 중인 스마트폰 앱의 IMEI 값을 확인하여 입력하세요. 앱과 HA가 동일한 기기로 인식되어 양쪽 모두 로그인이 유지됩니다.
*   **독립 모드**: 별도의 계정을 사용하거나 앱 로그아웃이 상관없다면 `imei` 항목을 비워두세요. 시스템이 자동으로 고유한 무작위 값을 생성합니다.

---

### **🤖 자동화 활용 예시**

새로운 출입 이벤트가 발생할 때 사용자 이름을 포함하여 스마트폰으로 푸시 알림을 보내는 자동화 스크립트입니다.

```yaml
alias: "[보안] 현관문 실시간 출입 알림"
description: "출입 수단과 이름을 구분하여 알림을 발송합니다."
trigger:
  - platform: state
    entity_id: lock.zigbang_doorlock
    attribute: event_id  # 새로운 출입 이벤트 발생 시 트리거
action:
  - variables:
      msg_text: "{{ state_attr(trigger.entity_id, 'last_event_msg') }}"
      msg_code: "{{ state_attr(trigger.entity_id, 'last_event_code') }}"
      # 메시지에서 사용자 이름 추출 (예: '홍길동'님이 문을 열었습니다 -> 홍길동)
      user_name: >-
        {% if msg_text.count("'") >= 2 %}
          {{ msg_text.split("'")[1] }}
        {% elif '(' in msg_text %}
          {{ msg_text.split('(')[1].split(')')[0] }}
        {% else %}
          가족
        {% endif %}
      # 출입 유형에 따른 메시지 포맷팅
      friendly_msg: >-
        {% if "622_OUT" in msg_code %}
          내부에서 수동으로 문을 열고 나갔습니다.
        {% else %}
          {{ user_name }}님이 인증을 통해 입실하였습니다.
        {% endif %}
    service: notify.mobile_app_your_smartphone
    data:
      title: "🏠 도어락 알림"
      message: "{{ friendly_msg }}"
      data:
        group: "doorlock-events"
        clickAction: "/lovelace/security"
```

---

### **⚖️ 면책 조항 (Disclaimer)**

*   본 프로젝트는 개인이 직방 API를 분석하여 제작한 **비공식(Unofficial)** 통합 구성요소입니다.
*   직방(Zigbang) 측의 API 사정이나 정책 변경에 따라 기능이 제한되거나 중단될 수 있습니다.
*   과도한 API 요청(Polling)은 계정 일시 차단의 원인이 될 수 있으므로 주의하십시오.
*   본 소프트웨어 사용으로 인해 발생하는 기기 오작동, 보안 사고 등 어떠한 결과에 대해서도 개발자는 책임을 지지 않습니다.
