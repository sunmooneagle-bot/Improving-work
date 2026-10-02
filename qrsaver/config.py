"""설정 및 파일 경로."""
import json
import os
import sys

DEFAULTS = {
    "window_keyword": "AMIS",          # AMIS 창 제목에 포함된 글자
    "field_offset": None,              # 검사번호 칸 위치 [x, y] (AMIS 창 왼쪽 위 기준)
    "idle_seconds": 5.0,               # 사용자가 이 시간 이상 입력이 없을 때만 작업
    "load_wait": 2.0,                  # 검사번호 입력+Enter 후 조회 대기
    "save_wait": 2.0,                  # F9 후 저장 대기
    "item_interval": 1.0,              # 항목 사이 간격
    "input_method": "uia",             # uia | paste | unicode | keys | message
    "screen_code": "VSPSSPR059S",      # 병리결과입력 화면 ID
    "uia_screen_id": "",               # 화면 컨테이너 AutomationId (UI 요소 찾기로 자동 저장)
    "uia_field_id": "",                # 검사번호 입력창 AutomationId (UI 요소 찾기로 자동 저장)
    "key_send": "auto",                # Enter/F9 전송: auto | message | keyboard
    "check_default": True,             # 저장 전 기본값(Negative) 선택 여부 확인
    "default_name": "Negative for malignant cells",
    "clear_method": "home_end",        # home_end | ctrl_a | backspace
    "press_enter": True,               # 입력 후 Enter 로 조회
    "save_key": "F9",
    "auto_close_dialogs": True,        # 확인/알림창 Enter 로 자동 처리
    "fail_keywords": "실패,오류,에러,error,없습니다,존재하지,권한,잘못",
    "restore_focus": True,             # 작업 후 원래 쓰던 창으로 복귀
    "max_retries": 1,
    "fix_hangul": True,                # 한글 상태로 스캔된 값(ㅊ→C) 자동 보정
    "uppercase": True,
    "preview_interval_ms": 800,
    "mini_geometry": "",
}


def app_dir():
    base = os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                           else os.path.abspath(sys.argv[0] or __file__))
    if os.access(base, os.W_OK):
        return base
    alt = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AMIS_QR_Saver")
    os.makedirs(alt, exist_ok=True)
    return alt


def data_path(name):
    return os.path.join(app_dir(), name)


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(data_path("settings.json"), encoding="utf-8") as f:
            saved = json.load(f)
        cfg.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    try:
        with open(data_path("settings.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False
