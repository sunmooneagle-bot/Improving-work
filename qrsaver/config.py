"""설정 및 파일 경로."""
import json
import os
import sys

CONFIG_VERSION = 14

DEFAULTS = {
    "config_version": CONFIG_VERSION,
    "window_keyword": "AMIS",          # AMIS 창 제목에 포함된 글자
    "field_offset": None,              # 검사번호 칸 위치 [x, y] (AMIS 창 왼쪽 위 기준)
    "idle_seconds": 5.0,               # 사용자가 이 시간 이상 입력이 없을 때만 작업
    "load_wait": 2.0,                  # 검사번호 입력+Enter 후 조회 대기
    "save_wait": 2.0,                  # F9 후 저장 대기
    "item_interval": 1.0,              # 항목 사이 간격
    "input_method": "uia",             # uia | paste | unicode | keys | message
    "screen_code": "VSPSSPR059S",      # 병리결과입력 화면 ID
    "uia_screen_id": "VSPSSPR059S",    # 화면 컨테이너 AutomationId (병리결과입력 화면)
    "uia_field_id": "txtExamRcepNo",   # 검사번호 입력창 AutomationId (헤더 검사번호 칸)
    "key_send": "auto",                # Enter/F9 전송: auto | message | keyboard
    "check_default": False,            # 저장 전 기본값(Negative) 선택 확인 - 기본값이 자동 설정되므로 끔
    "default_name": "Negative for malignant cells",   # 저장 전 선택돼 있어야 하는 라디오버튼 이름 (여러 개면 쉼표)
    "clear_method": "home_end",        # home_end | ctrl_a | backspace
    "press_enter": True,               # 번호 입력 후 Enter 로 조회 (QR 스캐너처럼 번호 + Enter)
    "check_loaded": True,              # F9 전 화면에 해당 검사번호가 조회됐는지 확인
    "loaded_check": "grid",            # grid: 목록(표) 셀에서만 확인(권장) | any: 입력칸 외 모든 칸
    "amis_space": True,                # QR '26-S-082711' → AMIS 표기 '26-S -082711' 로 맞춤 (목록 표시/비교용)
    # QR 목록에 추가할 체크박스 컬럼: "컬럼제목=AMIS 체크박스 이름 앞부분" 을 | 로 구분
    # 목록에서 체크한 항목은 저장(F9) 전에 AMIS 해당 체크박스를 같은 상태로 맞춘 뒤 저장
    "extra_checks": "Cell block 부적합=The submitted specimen is inappropriate for the cell block",
    # GYN Vaginal 건 (목록 'Vaginal' 컬럼 체크 시): 진단 문구 'Cervicovaginal :' → 'Vaginal :',
    # 'Presence of endocervical / transformation zone' 라디오 선택 해제(한 번 더 클릭) 후 저장
    # URINE 탭 라디오 변경 컬럼: "컬럼제목=클릭할 라디오 이름 앞부분[@그룹]" 을 | 로 구분
    # 같은 @그룹 컬럼은 목록에서 하나만 체크됨 (Instrumented urine 10~20 / <10)
    "radio_actions": ("Urine <30ml=Urine volume < 30 ml|UC absent=Urothelial cells absent|"
                      "Inst 10~20=10 ~ 20 cell@inst|Inst <10=< 10 cell@inst"),
    "vaginal_col": "Vaginal",
    "vaginal_text_from": "Cervicovaginal",
    "vaginal_text_to": "Vaginal :",
    "vaginal_radio": "Presence of endocervical",
    "f9_keyboard": True,               # F9 는 사람이 누르는 것과 같은 실제 키보드로 (AMIS 를 앞으로 가져옴)
    "uia_input": "replay",             # replay: QR 원문을 태그하듯 그대로 입력(권장) | set: 값 직접 설정 | type: 키보드 입력
    "type_method": "keys",             # 키보드 입력 방식: keys(실제 키 = 스캐너와 동일, 권장) | unicode
    "type_delay_ms": 40,               # 글자 사이 간격(ms) - 너무 빠르면 AMIS 가 일부 글자를 놓침
    "type_raw_qr": True,               # 입력칸에 QR 원래 형태(공백 없음, 26-S-082711)로 넣음 (처음 방식)
    "save_key": "F9",
    "auto_close_dialogs": True,        # 확인/알림창 Enter 로 자동 처리 (stop_on_popup 이 꺼져 있을 때만)
    "stop_on_popup": False,            # (사용 안 함) 팝업이 뜨면 작업 전체 중지
    # '아니오' 를 누르고 다음 건으로 넘어갈 팝업 ('+' 로 묶인 글자가 모두 있으면 해당) - 이미 저장된 건
    "no_popups": "저장된 결과입니다+다시 저장",
    "dialog_wait": 1.5,                # F9 후 '저장된 결과입니다' 등 팝업을 기다리는 최대 시간(초)
    "avg_sec_per_item": 15.0,          # 1건 평균 처리시간(초) - 작업할 때마다 자동 갱신, 예상 소요시간 계산에 사용
    "delete_menu_name": "일괄삭제",
    # 일괄 삭제 타이밍(초) - 설정 탭 '일괄 삭제 타이밍' 에서 조정
    "del_load_wait": 2.0,              # 검사번호 입력+Enter 후 조회 대기
    "del_action_wait": 0.5,            # Action 버튼 누른 뒤 메뉴가 펼쳐질 때까지 대기
    "del_menu_timeout": 3.0,           # '일괄삭제' 메뉴를 찾는 최대 시간
    "del_confirm_wait": 4.0,           # 확인창(예/아니오)이 뜰 때까지 최대 대기
    "del_after_wait": 4.0,             # '예' 누른 뒤 완료/오류 알림창 확인 대기
    "del_item_interval": 1.0,          # 삭제 항목 사이 간격     # 일괄 삭제 탭: Action 메뉴에서 누를 항목 이름
    "action_button_name": "Action",                # F9 후 팝업이 뜰 때까지 기다리는 최대 시간(초)
    # 목록 체크 컬럼 순서 (쉼표 구분, 여기 없는 컬럼은 뒤에)
    "check_order": "Urine <30ml,Cell block 부적합,Vaginal,UC absent,Inst 10~20,Inst <10",
    # 검사코드표 엑셀 (프로그램 폴더 기준, A열 처방코드 / B열 처방영문명). 없으면 내장 표 사용
    "exam_code_file": "검사코드.xlsx",
    "limit_checks_by_exam": True,      # QR 검사코드의 검체 종류에 맞는 체크 칸만 활성화
    # 검체 분류: "분류=검사명에 들어 있는 글자(쉼표 구분)" 을 | 로 구분 (대소문자 무시)
    "exam_categories": ("urine=urine,bladder irrigation|"
                        "inst=washed urine,bladder irrigation|"
                        "gyn=cervical,vaginal,endometrial|"
                        "cellblock=cell block"),
    # 체크 칸별로 활성화할 검체 분류: "컬럼제목=분류" 를 | 로 구분 (여기 없는 칸은 항상 활성)
    "check_categories": ("Urine <30ml=urine|UC absent=urine|Inst 10~20=inst|Inst <10=inst|"
                         "Vaginal=gyn|Cell block 부적합=cellblock"),
    "always_on_top": True,             # 프로그램 창(큰 화면)을 항상 위에 표시
    "mini_compact": False,             # 축소창을 작업화면 미리보기 없이 작게             # 팝업(확인/알림창)이 뜨면 닫지 않고 그대로 두고 작업 전체를 중지
    "fail_keywords": "실패,오류,에러,error,없습니다,존재하지,권한,잘못",
    # 무시할 알림 (쉼표로 구분, '+' 로 묶인 글자가 모두 들어 있으면 무시하고 건드리지 않음)
    # 병리결과입력에서 번호를 조회하면 옆의 결과조회 화면이 따라 조회되며 우하단에 약 3초 뜨는 안내창
    "ignore_popups": "VSPSSPR061S+결과내용이 없습니다",
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


def parse_extra_checks(text):
    """'제목=이름앞부분|제목2=이름앞부분2' → [(제목, 이름앞부분), ...]"""
    out = []
    for part in str(text or "").split("|"):
        if "=" in part:
            hdr, prefix = part.split("=", 1)
            if hdr.strip() and prefix.strip():
                out.append((hdr.strip(), prefix.strip()))
    return out


def parse_radio_actions(text):
    """'제목=라디오이름앞부분@그룹|...' → [(제목, 이름앞부분, 그룹 또는 ''), ...]"""
    out = []
    for part in str(text or "").split("|"):
        if "=" not in part:
            continue
        hdr, rest = part.split("=", 1)
        prefix, _, group = rest.partition("@")
        if hdr.strip() and prefix.strip():
            out.append((hdr.strip(), prefix.strip(), group.strip()))
    return out


def data_path(name):
    return os.path.join(app_dir(), name)


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(data_path("settings.json"), encoding="utf-8") as f:
            saved = json.load(f)
        cfg.update({k: v for k, v in saved.items() if k in DEFAULTS})
        for k in ("uia_screen_id", "uia_field_id"):   # 비어 있으면 기본 ID 사용
            if not cfg.get(k):
                cfg[k] = DEFAULTS[k]
        if int(saved.get("config_version", 1) or 1) < 4:
            cfg["press_enter"] = True   # v1.3.4: 입력 후 Enter 로 조회하는 흐름으로 변경
        if int(saved.get("config_version", 1) or 1) < 6:
            cfg["type_method"] = "keys"  # v1.3.8: unicode 입력 시 26-C-053447 → 26-C-000534 로 조회되는 문제
        if int(saved.get("config_version", 1) or 1) < 5:
            cfg["uia_input"] = "type"   # v1.3.7: 값 직접 설정 시 AMIS 조회 실패 → 스캐너와 같은 키보드 입력
            cfg["key_send"] = "auto"
        if int(saved.get("config_version", 1) or 1) < 7:
            cfg["uia_input"] = "set"     # v1.4.0: 조회는 처음 방식(값 직접 설정, Enter 없음)으로 복귀
            cfg["press_enter"] = False
            cfg["type_raw_qr"] = True
        if int(saved.get("config_version", 1) or 1) < 8:
            cfg["press_enter"] = True    # v1.4.2: 값 설정 후 Enter 를 보내야 조회됨
        if int(saved.get("config_version", 1) or 1) < 11:
            cfg["uia_input"] = "replay"  # v1.5.0: 스캐너가 친 QR 원문(예: '26-C -053447')을 그대로 다시 태그
            cfg["press_enter"] = True
        if int(saved.get("config_version", 1) or 1) < 12:
            cfg["check_default"] = False  # 라디오버튼은 기본값이 자동 설정되므로 확인하지 않고 저장
        if int(saved.get("config_version", 1) or 1) < 13:
            cfg["stop_on_popup"] = False  # 팝업 시 작업 중지 취소
        if int(saved.get("config_version", 1) or 1) < 14:
            if float(cfg.get("dialog_wait", 1.5)) >= 4.0:
                cfg["dialog_wait"] = 1.5     # v2.3.1: 매 건 4초씩 기다리던 것을 줄임
        cfg["config_version"] = CONFIG_VERSION
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
