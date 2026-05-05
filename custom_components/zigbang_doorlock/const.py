DOMAIN = "zigbang_doorlock"
ATTR_BATTERY = "battery_level"
ATTR_LOCK_STATE = "lock_state"

# 언어별 알림 타입 정의 (기본 지원: 한국어, 영어)
ALERT_TYPE = {
    "ko": {
        '622_NONE': '잠김',
        '622_IN_FGP': '열림',
        '622_IN_RFC': '열림',
        '622_OUT': '열림',
        '622_IN_SVR': '열림',
        '620': '5회 열기 실패',
        '648': '30초 열림',
        '652': '잠금 실패'
    },
    "en": {
        '622_NONE': 'Locked',
        '622_IN_FGP': 'Unlocked',
        '622_IN_RFC': 'Unlocked',
        '622_OUT': 'Unlocked',
        '622_IN_SVR': 'Unlocked',
        '620': 'Failed 5 times',
        '648': 'Open for 30s',
        '652': 'Lock failed'
    }
}

OPEN_TYPE = {
    "ko": {
        'FGP': '지문',
        'SVR': '앱',
        'RFC': '키택'
    },
    "en": {
        'FGP': 'Fingerprint',
        'SVR': 'App',
        'RFC': 'Keytag'
    }
}