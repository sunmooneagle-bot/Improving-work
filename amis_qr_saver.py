# -*- coding: utf-8 -*-
"""결과입력 자동 프로그램 (AMIS 병리결과입력 QR 일괄저장) - 단일 실행 파일 (tools/make_single.py 로 자동 생성, 직접 수정하지 마세요)

실행:  python amis_qr_saver.py      (콘솔 없이: pythonw amis_qr_saver.py)
필요:  pip install pillow uiautomation
"""
import sys
import types

_SOURCES = {}

_SOURCES['__init__'] = r'''"""결과입력 자동 프로그램 - AMIS 병리결과 QR 일괄저장 도우미."""
__version__ = "2.3.1"
'''

_SOURCES['config'] = r'''"""설정 및 파일 경로."""
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
'''

_SOURCES['hangul'] = r'''"""QR 스캐너 입력 보정.

QR 스캐너는 키보드처럼 동작하므로 한/영 상태가 '한글'이면
'26-C -053637' 이 '26-ㅊ -053637' 처럼 들어온다. 두벌식 자판 기준으로
한글을 원래 영문 키로 되돌린다.
"""
import re

_CHO = ["r", "R", "s", "e", "E", "f", "a", "q", "Q", "t", "T", "d", "w", "W",
        "c", "z", "x", "v", "g"]
_JUNG = ["k", "o", "i", "O", "j", "p", "u", "P", "h", "hk", "ho", "hl", "y",
         "n", "nj", "np", "nl", "b", "m", "ml", "l"]
_JONG = ["", "r", "R", "rt", "s", "sw", "sg", "e", "f", "fr", "fa", "fq", "ft",
         "fx", "fv", "fg", "a", "q", "qt", "t", "T", "d", "w", "c", "z", "x",
         "v", "g"]
# 호환 자모 U+3131(ㄱ) ~ U+3163(ㅣ)
_COMPAT = ("r R rt s sw sg e E f fr fa fq ft fx fv fg a q Q qt t T d w W c z x v g "
           "k o i O j p u P h hk ho hl y n nj np nl b m ml l").split()


def hangul_to_qwerty(text):
    out = []
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            idx = code - 0xAC00
            out.append(_CHO[idx // 588] + _JUNG[(idx % 588) // 28] + _JONG[idx % 28])
        elif 0x3131 <= code <= 0x3163:
            out.append(_COMPAT[code - 0x3131])
        else:
            out.append(ch)
    return "".join(out)


_AMIS_RE = re.compile(r"^(\d{2})-([A-Za-z]{1,2})\s*-\s*(\d{3,})$")


def amis_format(code):
    """검사번호를 AMIS 화면 표기로 통일: '26-S-082711' / '26-S  - 082711' → '26-S -082711'.
    형식이 다르면 그대로 둔다."""
    m = _AMIS_RE.match((code or "").strip())
    if not m:
        return code
    return "%s-%s -%s" % (m.group(1), m.group(2).upper(), m.group(3))


def normalize_code(raw, fix_hangul=True, uppercase=True, amis_space=True):
    """스캔된 문자열을 검사번호로 정리 (앞뒤 공백/개행 제거).
    amis_space=True 면 QR 의 '26-S-082711' 을 AMIS 표기 '26-S -082711' 로 바꾼다."""
    code = raw.replace("\r", "").replace("\n", "").replace("\t", "").strip()
    if fix_hangul:
        code = hangul_to_qwerty(code)
    if uppercase:
        code = code.upper()
    if amis_space:
        code = amis_format(code)
    return code


_PATTERN = re.compile(r"^\d{2}-[A-Z]{1,2}\s*-\s*\d{3,}$")


def looks_like_accession(code):
    """'26-C -053637' 같은 검사번호 형식인지 (경고 표시용)."""
    return bool(_PATTERN.match(code))
'''

_SOURCES['models'] = r'''"""QR 태그 목록 (작업 큐) - 파일로 자동 저장되어 프로그램을 다시 켜도 유지된다."""
import json
import os
import threading
import time

WAIT, RUN, DONE, FAIL = "대기중", "진행중", "저장완료", "저장실패"


class Item:
    __slots__ = ("id", "code", "status", "time", "note", "tries", "added", "raw", "checks")

    def __init__(self, id, code, status=WAIT, time="", note="", tries=0, added="", raw="", checks=None):
        self.id = id
        self.code = code
        self.status = status
        self.time = time
        self.note = note
        self.tries = tries
        self.added = added
        self.raw = raw        # QR 스캐너가 실제로 친 원문 (예: '26-C -053447') - 저장 시 그대로 다시 입력
        self.checks = dict(checks) if isinstance(checks, dict) else {}   # 목록 체크박스 {컬럼제목: True/False}

    def to_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


class Store:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self.items = []
        self._next_id = 1
        self.load()

    # ------------------------------------------------------------ 파일
    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        for d in data:
            item = Item(**{k: d.get(k, "") for k in Item.__slots__ if k in d})
            if item.status == RUN:
                item.status = WAIT
            item.tries = int(item.tries or 0)
            self.items.append(item)
        self._next_id = max([i.id for i in self.items], default=0) + 1

    def save(self):
        with self.lock:
            data = [i.to_dict() for i in self.items]
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass

    # ------------------------------------------------------------ 조작
    def add(self, code, raw=""):
        """추가된 Item 반환, 이미 목록에 있으면 None. raw = QR 원문."""
        with self.lock:
            if any(i.code == code for i in self.items):
                return None
            item = Item(self._next_id, code, added=time.strftime("%H:%M:%S"), raw=raw)
            self._next_id += 1
            self.items.append(item)
        self.save()
        return item

    def set_checks(self, item_id, values):
        """대기중 항목의 여러 체크 상태를 한 번에 설정 (values: {제목: bool})."""
        with self.lock:
            for i in self.items:
                if i.id == item_id and i.status == WAIT:
                    i.checks.update(values)
                    break
            else:
                return False
        self.save()
        return True

    def toggle_check(self, item_id, key):
        """대기중 항목의 목록 체크박스 켜기/끄기. 바뀐 상태 반환 (대기중이 아니면 None)."""
        with self.lock:
            for i in self.items:
                if i.id == item_id:
                    if i.status != WAIT:
                        return None
                    i.checks[key] = not i.checks.get(key, False)
                    val = i.checks[key]
                    break
            else:
                return None
        self.save()
        return val

    def get(self, item_id):
        with self.lock:
            for i in self.items:
                if i.id == item_id:
                    return i
        return None

    def remove(self, ids):
        ids = set(ids)
        with self.lock:
            self.items = [i for i in self.items if i.id not in ids or i.status == RUN]
        self.save()

    def clear(self, statuses=None):
        with self.lock:
            self.items = [i for i in self.items
                          if i.status == RUN or (statuses is not None and i.status not in statuses)]
        self.save()

    def update(self, item, **kw):
        with self.lock:
            for k, v in kw.items():
                setattr(item, k, v)
            if kw.get("status") in (DONE, FAIL):
                item.time = time.strftime("%H:%M:%S")
        self.save()

    def reset(self, ids=None, statuses=(FAIL,)):
        """지정 항목(또는 해당 상태 전체)을 다시 대기중으로."""
        with self.lock:
            for i in self.items:
                if i.status == RUN:
                    continue
                if (ids is not None and i.id in ids) or (ids is None and i.status in statuses):
                    i.status, i.tries, i.note, i.time = WAIT, 0, "", ""
        self.save()

    def next_pending(self):
        with self.lock:
            for i in self.items:
                if i.status == WAIT:
                    return i
        return None

    def counts(self):
        with self.lock:
            c = {WAIT: 0, RUN: 0, DONE: 0, FAIL: 0}
            for i in self.items:
                c[i.status] = c.get(i.status, 0) + 1
            c["total"] = len(self.items)
            return c

    def snapshot(self):
        with self.lock:
            return list(self.items)
'''

_SOURCES['win32'] = r'''"""Win32 API 래퍼 (ctypes 사용, 외부 의존성 없음).

AMIS 창 찾기/활성화, 키보드·마우스 입력, 유휴시간 측정, 확인창 탐지,
창 화면 캡처(미리보기용)를 담당한다. Windows 가 아닌 환경에서는
GUI 개발/테스트를 위해 아무 동작도 하지 않는 대체 함수가 동작한다.
"""
import sys
import time
import ctypes

IS_WINDOWS = sys.platform == "win32"

KEY_CODES = {
    "ENTER": 0x0D, "TAB": 0x09, "ESC": 0x1B, "BACK": 0x08, "SPACE": 0x20,
    "DELETE": 0x2E, "HOME": 0x24, "END": 0x23, "INSERT": 0x2D,
    "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    "CTRL": 0x11, "SHIFT": 0x10, "ALT": 0x12,
    "A": 0x41, "C": 0x43, "S": 0x53, "V": 0x56,
}
KEY_CODES.update({"F%d" % i: 0x6F + i for i in range(1, 13)})
EXTENDED_KEYS = {0x2E, 0x24, 0x23, 0x2D, 0x25, 0x26, 0x27, 0x28, 0x21, 0x22}

TICK_MASK = 0xFFFFFFFF


def tick_diff(a, b):
    """GetTickCount 값 a - b (32bit 순환 고려). b 가 더 나중이면 음수."""
    d = (a - b) & TICK_MASK
    return d if d < 0x80000000 else d - 0x100000000


if IS_WINDOWS:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    ULONG_PTR = ctypes.c_size_t

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _sig(fn, args, res=wintypes.BOOL):
        fn.argtypes = args
        fn.restype = res

    _sig(user32.SendInput, (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int), wintypes.UINT)
    _sig(user32.GetLastInputInfo, (ctypes.POINTER(LASTINPUTINFO),))
    _sig(kernel32.GetTickCount, (), wintypes.DWORD)
    _sig(kernel32.GetCurrentProcessId, (), wintypes.DWORD)
    _sig(kernel32.GetCurrentThreadId, (), wintypes.DWORD)
    _sig(user32.EnumWindows, (WNDENUMPROC, wintypes.LPARAM))
    _sig(user32.EnumChildWindows, (wintypes.HWND, WNDENUMPROC, wintypes.LPARAM))
    _sig(user32.GetWindowTextLengthW, (wintypes.HWND,), ctypes.c_int)
    _sig(user32.GetWindowTextW, (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int), ctypes.c_int)
    _sig(user32.GetClassNameW, (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int), ctypes.c_int)
    _sig(user32.IsWindow, (wintypes.HWND,))
    _sig(user32.IsWindowVisible, (wintypes.HWND,))
    _sig(user32.IsIconic, (wintypes.HWND,))
    _sig(user32.GetWindowThreadProcessId, (wintypes.HWND, ctypes.POINTER(wintypes.DWORD)), wintypes.DWORD)
    _sig(user32.GetWindowRect, (wintypes.HWND, ctypes.POINTER(wintypes.RECT)))
    _sig(user32.GetForegroundWindow, (), wintypes.HWND)
    _sig(user32.SetForegroundWindow, (wintypes.HWND,))
    _sig(user32.BringWindowToTop, (wintypes.HWND,))
    _sig(user32.ShowWindow, (wintypes.HWND, ctypes.c_int))
    _sig(user32.GetAncestor, (wintypes.HWND, wintypes.UINT), wintypes.HWND)
    _sig(user32.GetWindow, (wintypes.HWND, wintypes.UINT), wintypes.HWND)
    _sig(user32.AttachThreadInput, (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL))
    _sig(user32.GetCursorPos, (ctypes.POINTER(wintypes.POINT),))
    _sig(user32.SetCursorPos, (ctypes.c_int, ctypes.c_int))
    _sig(user32.MapVirtualKeyW, (wintypes.UINT, wintypes.UINT), wintypes.UINT)
    _sig(user32.VkKeyScanW, (wintypes.WCHAR,), ctypes.c_short)
    _sig(user32.GetWindowDC, (wintypes.HWND,), wintypes.HDC)
    _sig(user32.ReleaseDC, (wintypes.HWND, wintypes.HDC), ctypes.c_int)
    _sig(user32.PrintWindow, (wintypes.HWND, wintypes.HDC, wintypes.UINT))
    _sig(user32.OpenClipboard, (wintypes.HWND,))
    _sig(user32.CloseClipboard, ())
    _sig(user32.EmptyClipboard, ())
    _sig(user32.IsClipboardFormatAvailable, (wintypes.UINT,))
    _sig(user32.GetClipboardData, (wintypes.UINT,), wintypes.HANDLE)
    _sig(user32.SetClipboardData, (wintypes.UINT, wintypes.HANDLE), wintypes.HANDLE)
    _sig(kernel32.GlobalAlloc, (wintypes.UINT, ctypes.c_size_t), wintypes.HGLOBAL)
    _sig(kernel32.GlobalLock, (wintypes.HGLOBAL,), wintypes.LPVOID)
    _sig(kernel32.GlobalUnlock, (wintypes.HGLOBAL,))
    _sig(kernel32.GlobalFree, (wintypes.HGLOBAL,), wintypes.HGLOBAL)
    _sig(gdi32.CreateCompatibleDC, (wintypes.HDC,), wintypes.HDC)
    _sig(gdi32.CreateCompatibleBitmap, (wintypes.HDC, ctypes.c_int, ctypes.c_int), wintypes.HBITMAP)
    _sig(gdi32.SelectObject, (wintypes.HDC, wintypes.HGDIOBJ), wintypes.HGDIOBJ)
    _sig(gdi32.DeleteObject, (wintypes.HGDIOBJ,))
    _sig(gdi32.DeleteDC, (wintypes.HDC,))
    _sig(gdi32.BitBlt, (wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                        wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD))
    _sig(gdi32.GetDIBits, (wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                           wintypes.LPVOID, ctypes.POINTER(BITMAPINFO), wintypes.UINT), ctypes.c_int)

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    _sig(user32.ScreenToClient, (wintypes.HWND, ctypes.POINTER(wintypes.POINT)))
    _sig(user32.ChildWindowFromPointEx, (wintypes.HWND, wintypes.POINT, wintypes.UINT), wintypes.HWND)
    _sig(user32.SendMessageTimeoutW, (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                      wintypes.UINT, wintypes.UINT, ctypes.POINTER(ULONG_PTR)), wintypes.LPARAM)
    _sig(user32.PostMessageW, (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM))
    _sig(user32.SetFocus, (wintypes.HWND,), wintypes.HWND)
    _sig(user32.GetFocus, (), wintypes.HWND)
    _sig(user32.IsWindowEnabled, (wintypes.HWND,))
    _sig(user32.GetKeyState, (ctypes.c_int,), ctypes.c_short)
    _sig(kernel32.OpenProcess, (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD), wintypes.HANDLE)
    _sig(kernel32.CloseHandle, (wintypes.HANDLE,))
    _sig(kernel32.GetCurrentProcess, (), wintypes.HANDLE)
    _sig(kernel32.QueryFullProcessImageNameW, (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                               ctypes.POINTER(wintypes.DWORD)))
    _sig(advapi32.OpenProcessToken, (wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)))
    _sig(advapi32.GetTokenInformation, (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD,
                                        ctypes.POINTER(wintypes.DWORD)))
    _sig(shell32.ShellExecuteW, (wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                 wintypes.LPCWSTR, ctypes.c_int), wintypes.HINSTANCE)

    INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
    CWP_SKIPINVISIBLE, CWP_SKIPTRANSPARENT = 0x1, 0x4
    WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH = 0x000C, 0x000D, 0x000E
    WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102
    SMTO_ABORTIFHUNG = 0x2
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    TOKEN_QUERY = 0x0008
    TokenElevation = 20
    KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x1, 0x2, 0x4
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x2, 0x4
    GA_ROOT, GW_OWNER = 2, 4
    SW_RESTORE = 9
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x2
    PW_RENDERFULLCONTENT = 0x2
    SRCCOPY = 0x00CC0020


def set_dpi_aware():
    """마우스 좌표가 실제 화면 픽셀과 일치하도록 DPI 인식 모드를 켠다."""
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ---------------------------------------------------------------- 시간/유휴
def get_tick():
    if not IS_WINDOWS:
        return int(time.monotonic() * 1000) & TICK_MASK
    return kernel32.GetTickCount()


def get_last_input_tick():
    """시스템 전체에서 마지막 키보드/마우스 입력이 있었던 시각(GetTickCount 기준)."""
    if not IS_WINDOWS:
        return 0
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    user32.GetLastInputInfo(ctypes.byref(info))
    return info.dwTime


# ---------------------------------------------------------------- 창
def _window_text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_window_pid(hwnd):
    if not IS_WINDOWS or not hwnd:
        return 0
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _top_windows():
    result = []

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            result.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return result


def get_window_rect(hwnd):
    if not IS_WINDOWS or not hwnd:
        return (0, 0, 0, 0)
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


AMIS_CLASS_PREFIX = "WindowsForms10."   # AMIS(WinForms) 창 클래스. VS Code/브라우저(Chrome_WidgetWin_1) 등은 제외


def find_window(keyword):
    """제목에 keyword 가 포함된 (자기 자신 제외) 가장 큰 최상위 'WinForms' 창.
    클래스로 거르지 않으면 제목에 'amis' 가 들어간 VS Code·탐색기 창(예: amis_qr_saver.py)을 AMIS 로 착각한다."""
    if not IS_WINDOWS or not keyword:
        return None
    own_pid = kernel32.GetCurrentProcessId()
    best, best_area = None, -1
    kw = keyword.lower()
    for hwnd in _top_windows():
        if user32.GetWindow(hwnd, GW_OWNER):
            continue
        if get_window_pid(hwnd) == own_pid:
            continue
        if not class_name(hwnd).startswith(AMIS_CLASS_PREFIX):
            continue
        if kw not in _window_text(hwnd).lower():
            continue
        l, t, r, b = get_window_rect(hwnd)
        area = (r - l) * (b - t)
        if user32.IsIconic(hwnd):
            area = 1  # 최소화된 창도 후보로는 인정
        if area > best_area:
            best, best_area = hwnd, area
    return best


def window_title(hwnd):
    return _window_text(hwnd) if IS_WINDOWS and hwnd else ""


def is_window(hwnd):
    return bool(IS_WINDOWS and hwnd and user32.IsWindow(hwnd))


def get_foreground():
    return user32.GetForegroundWindow() if IS_WINDOWS else None


def is_foreground(hwnd):
    if not IS_WINDOWS or not hwnd:
        return False
    fg = user32.GetForegroundWindow()
    return bool(fg) and (fg == hwnd or user32.GetAncestor(fg, GA_ROOT) == hwnd)


def activate(hwnd):
    """창을 맨 앞으로 가져온다. 성공 여부 반환."""
    if not IS_WINDOWS or not hwnd or not user32.IsWindow(hwnd):
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.2)
    if is_foreground(hwnd):
        return True
    fg = user32.GetForegroundWindow()
    cur_tid = kernel32.GetCurrentThreadId()
    fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    tgt_tid = user32.GetWindowThreadProcessId(hwnd, None)
    attached = []
    for tid in {fg_tid, tgt_tid}:
        if tid and tid != cur_tid and user32.AttachThreadInput(cur_tid, tid, True):
            attached.append(tid)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        for tid in attached:
            user32.AttachThreadInput(cur_tid, tid, False)
    time.sleep(0.1)
    if is_foreground(hwnd):
        return True
    # 대체 방법: 움직임 0 마우스 입력으로 포그라운드 잠금 해제
    # (Alt 키를 쓰면 AMIS 메뉴바가 활성화돼 이후 키 입력이 칸에 안 들어갈 수 있음)
    nudge = INPUT()
    nudge.type = INPUT_MOUSE
    _send([nudge])
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.1)
    return is_foreground(hwnd)


def list_popups(pid, exclude=None):
    """해당 프로세스의 (메인 창을 제외한) 보이는 최상위 창 목록."""
    if not IS_WINDOWS or not pid:
        return []
    return [h for h in _top_windows() if h != exclude and get_window_pid(h) == pid]


def is_dialog_like(hwnd):
    if not IS_WINDOWS:
        return False
    return _class_name(hwnd) == "#32770" or bool(user32.GetWindow(hwnd, GW_OWNER))


def get_all_text(hwnd):
    """창 제목 + 자식 컨트롤 텍스트 (메시지 박스 내용 확인용)."""
    if not IS_WINDOWS or not hwnd:
        return ""
    texts = [_window_text(hwnd)]

    def cb(child, _):
        t = _window_text(child)
        if t:
            texts.append(t)
        return True

    user32.EnumChildWindows(hwnd, WNDENUMPROC(cb), 0)
    return " ".join(t.strip() for t in texts if t.strip())


# ---------------------------------------------------------------- 입력
def _key_input(vk, up, scan=0, unicode=False):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    flags = KEYEVENTF_KEYUP if up else 0
    if unicode:
        inp.u.ki.wVk = 0
        inp.u.ki.wScan = scan
        flags |= KEYEVENTF_UNICODE
    else:
        inp.u.ki.wVk = vk
        inp.u.ki.wScan = user32.MapVirtualKeyW(vk, 0)
        if vk in EXTENDED_KEYS:
            flags |= KEYEVENTF_EXTENDEDKEY
    inp.u.ki.dwFlags = flags
    return inp


def _send(inputs):
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def press(key, mods=()):
    """key: 'F9', 'ENTER', 'A' 등. mods: ('CTRL',) 등."""
    if not IS_WINDOWS:
        return
    vk = KEY_CODES[key.upper()]
    mod_vks = [KEY_CODES[m.upper()] for m in mods]
    seq = [_key_input(m, False) for m in mod_vks]
    seq += [_key_input(vk, False), _key_input(vk, True)]
    seq += [_key_input(m, True) for m in reversed(mod_vks)]
    _send(seq)
    time.sleep(0.05)


def type_unicode(text):
    if not IS_WINDOWS:
        return
    for ch in text:
        _send([_key_input(0, False, ord(ch), True), _key_input(0, True, ord(ch), True)])
        time.sleep(0.015)


def caps_lock_on():
    return bool(IS_WINDOWS and user32.GetKeyState(0x14) & 1)


def ime_english(hwnd):
    """hwnd 입력칸의 한/영 상태를 영문으로 (QR 스캐너가 한글 상태일 때 'ㅊ' 이 들어가는 것 방지). 최선 시도."""
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        imm = ctypes.WinDLL("imm32")
        imm.ImmGetDefaultIMEWnd.argtypes = (wintypes.HWND,)
        imm.ImmGetDefaultIMEWnd.restype = wintypes.HWND
        ime = imm.ImmGetDefaultIMEWnd(hwnd)
        if not ime:
            return False
        _send_msg(ime, 0x0283, 0x0002, 0)   # WM_IME_CONTROL, IMC_SETCONVERSIONMODE, 영문(0)
        return True
    except Exception:
        return False


def type_keys(text, delay=0.04):
    """실제 가상 키로 입력 (QR 스캐너와 같은 방식). 글자 사이 delay 초. CapsLock 이 켜져 있어도 대소문자 유지."""
    if not IS_WINDOWS:
        return
    caps = caps_lock_on()
    for ch in text:
        res = user32.VkKeyScanW(ch)
        if res == -1:
            type_unicode(ch)
            continue
        vk, shift = res & 0xFF, (res >> 8) & 1
        if caps and ch.isalpha():
            shift ^= 1
        seq = []
        if shift:
            seq.append(_key_input(KEY_CODES["SHIFT"], False))
        seq += [_key_input(vk, False), _key_input(vk, True)]
        if shift:
            seq.append(_key_input(KEY_CODES["SHIFT"], True))
        _send(seq)
        time.sleep(delay)


def get_cursor_pos():
    if not IS_WINDOWS:
        return (0, 0)
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return (p.x, p.y)


def set_cursor_pos(x, y):
    if IS_WINDOWS:
        user32.SetCursorPos(int(x), int(y))


def click(x, y):
    if not IS_WINDOWS:
        return
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    down, up = INPUT(), INPUT()
    down.type = up.type = INPUT_MOUSE
    down.u.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
    up.u.mi.dwFlags = MOUSEEVENTF_LEFTUP
    _send([down, up])
    time.sleep(0.05)


# ---------------------------------------------------------------- 클립보드
def _open_clipboard():
    for _ in range(10):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.05)
    return False


def get_clipboard_text():
    if not IS_WINDOWS or not _open_clipboard():
        return None
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return None
        p = kernel32.GlobalLock(h)
        try:
            return ctypes.wstring_at(p) if p else None
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text):
    if not IS_WINDOWS or not _open_clipboard():
        return False
    try:
        user32.EmptyClipboard()
        data = ctypes.create_unicode_buffer(text)
        size = ctypes.sizeof(data)
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not h:
            return False
        p = kernel32.GlobalLock(h)
        ctypes.memmove(p, data, size)
        kernel32.GlobalUnlock(h)
        if not user32.SetClipboardData(CF_UNICODETEXT, h):
            kernel32.GlobalFree(h)
            return False
        return True
    finally:
        user32.CloseClipboard()


# ---------------------------------------------------------------- 캡처
def capture_window(hwnd):
    """창 내용을 (width, height, BGRX bytes) 로 반환. 다른 창에 가려져 있어도 캡처 시도."""
    if not IS_WINDOWS or not hwnd or not user32.IsWindow(hwnd) or user32.IsIconic(hwnd):
        return None
    l, t, r, b = get_window_rect(hwnd)
    w, h = r - l, b - t
    if w <= 0 or h <= 0:
        return None
    hdc_win = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    old = gdi32.SelectObject(hdc_mem, hbmp)
    try:
        if not user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT):
            gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_win, 0, 0, SRCCOPY)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)
        return (w, h, buf.raw)
    finally:
        gdi32.SelectObject(hdc_mem, old)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_win)


# ---------------------------------------------------------------- 컨트롤 / 메시지
def class_name(hwnd):
    return _class_name(hwnd) if IS_WINDOWS and hwnd else ""


def control_at(root_hwnd, sx, sy):
    """화면 좌표 (sx, sy) 에 있는 root 창의 가장 안쪽 자식 컨트롤 (다른 창에 가려져 있어도 동작)."""
    if not IS_WINDOWS or not root_hwnd:
        return None
    h = root_hwnd
    for _ in range(30):
        pt = wintypes.POINT(int(sx), int(sy))
        user32.ScreenToClient(h, ctypes.byref(pt))
        child = user32.ChildWindowFromPointEx(h, pt, CWP_SKIPINVISIBLE | CWP_SKIPTRANSPARENT)
        if not child or child == h:
            break
        h = child
    return h


def is_visible(hwnd):
    return bool(IS_WINDOWS and hwnd and user32.IsWindowVisible(hwnd))


_Z_HOLD = [0.0]


def hold_z(secs):
    """secs 초 동안 프로그램 창을 AMIS 위로 올리지 않음 (실제 마우스 클릭 중)."""
    _Z_HOLD[0] = time.monotonic() + secs


def z_held():
    return time.monotonic() < _Z_HOLD[0]


def own_windows():
    """이 프로그램의 화면에 보이는 최상위 창들."""
    if not IS_WINDOWS:
        return []
    pid = kernel32.GetCurrentProcessId()
    return [h for h in _top_windows() if get_window_pid(h) == pid]


def is_topmost(hwnd):
    return bool(IS_WINDOWS and hwnd and user32.GetWindowLongW(wintypes.HWND(hwnd), -20) & 0x8)


def set_z(hwnd, after):
    """after: -1 항상위, -2 항상위 해제, 1 맨 아래 (활성화/이동/크기 변경 없음)."""
    if IS_WINDOWS and hwnd:
        user32.SetWindowPos(wintypes.HWND(hwnd), wintypes.HWND(after), 0, 0, 0, 0, 0x0013)


def is_edit_like(hwnd):
    return "edit" in class_name(hwnd).lower()


# ---------------------------------------------------------------- MDI 화면 (AMIS 안의 화면 탭)
WM_MDIACTIVATE, WM_MDIGETACTIVE = 0x0222, 0x0229


def find_children_by_text(parent, names, visible_only=True):
    """parent 아래 모든 자식 창 중 글자가 names 중 하나인 창 핸들들 (Win32, 매우 빠름)."""
    if not IS_WINDOWS or not parent:
        return []
    want = set(names)
    out = []

    def cb(h, _):
        if (not visible_only or user32.IsWindowVisible(h)) and _window_text(h).strip() in want:
            out.append(h)
        return True

    user32.EnumChildWindows(parent, WNDENUMPROC(cb), 0)
    return out


def parent_of(hwnd):
    return user32.GetAncestor(hwnd, 1) if IS_WINDOWS and hwnd else 0   # GA_PARENT


def find_mdi_child(main_hwnd, code):
    """AMIS 안의 화면(MDI 자식 창) 중 제목에 code(예: VSPSSPR059S)가 들어간 창.
    뒤에 깔려 있거나 숨겨진(탭 뒤) 화면도 찾는다."""
    if not IS_WINDOWS or not main_hwnd or not code:
        return None
    code = code.lower()
    clients = []

    def cb(h, _):
        if "MDICLIENT" in class_name(h).upper():
            clients.append(h)
        return True

    user32.EnumChildWindows(main_hwnd, WNDENUMPROC(cb), 0)
    for mc in clients:
        h = user32.GetWindow(mc, 5)          # GW_CHILD
        while h:
            if code in _window_text(h).lower():
                return h
            h = user32.GetWindow(h, 2)       # GW_HWNDNEXT
    return None


def is_iconic(hwnd):
    return bool(IS_WINDOWS and hwnd and user32.IsIconic(hwnd))


def show_no_activate(hwnd):
    """최소화된 창을 원래 크기로 (포커스는 가져오지 않음)."""
    if IS_WINDOWS and hwnd:
        user32.ShowWindow(hwnd, 4)           # SW_SHOWNOACTIVATE
        time.sleep(0.3)


def mdi_client_of(child):
    """AMIS 화면(MDI 자식 창)의 부모 MDICLIENT. 아니면 None."""
    if not IS_WINDOWS or not child:
        return None
    p = user32.GetAncestor(child, 1)  # GA_PARENT
    return p if p and "MDICLIENT" in class_name(p).upper() else None


def mdi_active(child):
    """child 와 같은 MDICLIENT 에서 현재 활성화된 화면 핸들."""
    mc = mdi_client_of(child)
    if not mc:
        return None
    return _send_msg(mc, WM_MDIGETACTIVE, 0, 0) or None


def mdi_activate(child, tries=3):
    """AMIS 안에서 해당 화면(예: 병리결과입력)을 활성 화면으로 만든다. 확인까지 성공해야 True.
    Enter/F9 같은 단축키는 '활성 화면'이 처리하므로, 결과조회 화면이 활성이면 그쪽에서 동작한다."""
    mc = mdi_client_of(child)
    if not mc:
        return False
    for _ in range(tries):
        if int(_send_msg(mc, WM_MDIGETACTIVE, 0, 0) or 0) == int(child):
            return True
        _send_msg(mc, WM_MDIACTIVATE, int(child), 0)
        time.sleep(0.2)
    return int(_send_msg(mc, WM_MDIGETACTIVE, 0, 0) or 0) == int(child)


def _send_msg(hwnd, msg, wparam, lparam, timeout=2000):
    res = ULONG_PTR()
    ok = user32.SendMessageTimeoutW(hwnd, msg, wparam, lparam, SMTO_ABORTIFHUNG, timeout, ctypes.byref(res))
    return res.value if ok else None


def get_control_text(hwnd):
    """WM_GETTEXT 로 컨트롤 내용 읽기 (실패 시 None)."""
    if not IS_WINDOWS or not hwnd:
        return None
    n = _send_msg(hwnd, WM_GETTEXTLENGTH, 0, 0)
    if n is None:
        return None
    buf = ctypes.create_unicode_buffer(int(n) + 2)
    if _send_msg(hwnd, WM_GETTEXT, int(n) + 2, ctypes.addressof(buf)) is None:
        return None
    return buf.value


def set_control_text(hwnd, text):
    if not IS_WINDOWS or not hwnd:
        return False
    buf = ctypes.create_unicode_buffer(text)
    return bool(_send_msg(hwnd, WM_SETTEXT, 0, ctypes.addressof(buf)))


def focus_control(hwnd):
    """다른 프로세스의 컨트롤에 키보드 포커스를 준다 (창을 앞으로 가져오지 않음)."""
    if not IS_WINDOWS or not hwnd:
        return False
    cur_tid = kernel32.GetCurrentThreadId()
    tgt_tid = user32.GetWindowThreadProcessId(hwnd, None)
    if not user32.AttachThreadInput(cur_tid, tgt_tid, True):
        return False
    try:
        user32.SetFocus(hwnd)
        return user32.GetFocus() == hwnd
    finally:
        user32.AttachThreadInput(cur_tid, tgt_tid, False)


def post_key(hwnd, key, char=None):
    """키보드 장치를 거치지 않고 WM_KEYDOWN/WM_CHAR/WM_KEYUP 메시지를 직접 보낸다."""
    if not IS_WINDOWS or not hwnd:
        return False
    vk = KEY_CODES[key.upper()]
    scan = user32.MapVirtualKeyW(vk, 0)
    ext = (1 << 24) if vk in EXTENDED_KEYS else 0
    down = 1 | (scan << 16) | ext
    up = down | (1 << 30) | (1 << 31)
    ok = user32.PostMessageW(hwnd, WM_KEYDOWN, vk, down)
    if char is not None:
        user32.PostMessageW(hwnd, WM_CHAR, ord(char), down)
    user32.PostMessageW(hwnd, WM_KEYUP, vk, up)
    return bool(ok)


# ---------------------------------------------------------------- 권한 / 프로세스
def process_path(pid):
    if not IS_WINDOWS or not pid:
        return ""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(h)


def _token_elevated(proc_handle):
    tok = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(proc_handle, TOKEN_QUERY, ctypes.byref(tok)):
        return None
    try:
        val = wintypes.DWORD()
        size = wintypes.DWORD()
        if not advapi32.GetTokenInformation(tok, TokenElevation, ctypes.byref(val),
                                            ctypes.sizeof(val), ctypes.byref(size)):
            return None
        return bool(val.value)
    finally:
        kernel32.CloseHandle(tok)


def is_self_elevated():
    if not IS_WINDOWS:
        return False
    return bool(_token_elevated(kernel32.GetCurrentProcess()))


def is_process_elevated(pid):
    """True/False, 확인 불가(보통 상대가 관리자 권한일 때)면 None."""
    if not IS_WINDOWS or not pid:
        return None
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        return _token_elevated(h)
    finally:
        kernel32.CloseHandle(h)


def restart_as_admin():
    """현재 프로그램을 관리자 권한으로 다시 실행 (UAC 창 표시). 성공 시 True."""
    if not IS_WINDOWS:
        return False
    import os
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, ""
    else:
        exe = sys.executable
        if exe.lower().endswith("python.exe"):
            alt = exe[:-10] + "pythonw.exe"
            if os.path.exists(alt):
                exe = alt
        params = '"%s"' % os.path.abspath(sys.argv[0])
    r = shell32.ShellExecuteW(None, "runas", exe, params, os.getcwd(), 1)
    return (r or 0) > 32
'''

_SOURCES['uia'] = r'''"""UI Automation (AutomationId) 로 AMIS 화면 요소를 직접 찾는 모듈.

좌표 대신 병리결과입력[VSPSSPR059S] 화면 안의 검사번호 입력창을
AutomationId 로 찾기 때문에 창 위치/크기/해상도가 바뀌어도 정확하다.
`pip install uiautomation` 필요 (없으면 이 기능만 비활성화).
"""
import contextlib

try:
    import uiautomation as auto
except Exception:  # 미설치 또는 Windows 아님
    auto = None

TREE_DESCENDANTS = 4
PROP_CONTROL_TYPE = 30003
PROP_NAME = 30005
PROP_AUTOMATION_ID = 30011
PAT_VALUE = 10002
PAT_SELECTION_ITEM = 10010
PAT_TOGGLE = 10015
PAT_LEGACY = 10018


def available():
    return auto is not None


@contextlib.contextmanager
def thread_init():
    """작업 스레드에서 UIA 를 쓰기 위한 COM 초기화."""
    if auto is None:
        yield
        return
    with auto.UIAutomationInitializerInThread():
        yield


def _client():
    # uiautomation 2.x 는 패키지 구조라 '_' 로 시작하는 이름이 최상위에 노출되지 않음
    mod = getattr(auto, "uiautomation", auto)
    return mod._AutomationClient.instance().IUIAutomation


def _wrap(element):
    return auto.Control.CreateControlFromElement(element) if element else None


def _find_first(root, prop, value):
    cond = _client().CreatePropertyCondition(prop, value)
    return _wrap(root.Element.FindFirst(TREE_DESCENDANTS, cond))


def _find_all(root, prop, value, limit=200):
    cond = _client().CreatePropertyCondition(prop, value)
    arr = root.Element.FindAll(TREE_DESCENDANTS, cond)
    out = []
    if arr:
        for i in range(min(arr.Length, limit)):
            c = _wrap(arr.GetElement(i))
            if c is not None:
                out.append(c)
    return out


def _safe(fn, default=""):
    try:
        v = fn()
        return default if v is None else v
    except Exception:
        return default


# ---------------------------------------------------------------- 정보
def describe(c):
    if c is None:
        return "(없음)"
    return "[%s] Name='%s' AutomationId='%s' Class='%s' HWND=%s" % (
        _safe(lambda: c.ControlTypeName), _safe(lambda: c.Name)[:60], _safe(lambda: c.AutomationId),
        _safe(lambda: c.ClassName), _safe(lambda: c.NativeWindowHandle, 0))


def ancestors(c, limit=25):
    out = []
    p = _safe(lambda: c.GetParentControl(), None)
    while p is not None and len(out) < limit:
        out.append(p)
        p = _safe(lambda: p.GetParentControl(), None)
    return out


def control_from_point(x, y):
    return auto.ControlFromPoint(int(x), int(y)) if auto else None


def control_from_handle(hwnd):
    return auto.ControlFromHandle(hwnd) if auto and hwnd else None


def pick_screen(ctrl, screen_code):
    """요소의 조상 중 화면(병리결과입력[VSPSSPR059S]) 컨테이너를 고른다."""
    code = (screen_code or "").lower()
    chain = ancestors(ctrl)
    if code:
        for a in chain:
            if code in _safe(lambda: a.Name).lower() or code in _safe(lambda: a.AutomationId).lower():
                return a
    return None


# ---------------------------------------------------------------- 찾기
def find_screen(root, cfg):
    """설정된 화면 컨테이너 (AutomationId 우선, 없으면 이름에 화면 코드 포함)."""
    sid = cfg.get("uia_screen_id")
    if sid:
        s = _find_first(root, PROP_AUTOMATION_ID, sid)
        if s is not None:
            return s
    code = (cfg.get("screen_code") or "").lower()
    if not code:
        return None
    # 이름 부분 일치는 조건식으로 안 되므로 상위 몇 단계만 직접 탐색 (그리드 셀까지 내려가지 않게)
    level = [root]
    for _ in range(8):
        nxt = []
        for c in level:
            for ch in _safe(lambda: c.GetChildren(), []):
                if code in _safe(lambda: ch.Name).lower() or code in _safe(lambda: ch.AutomationId).lower():
                    return ch
                nxt.append(ch)
        level = nxt[:400]
        if not level:
            break
    return None


def find_field(hwnd, cfg):
    """(검사번호 입력창, 화면 컨테이너) 반환. 못 찾으면 (None, screen)."""
    root = control_from_handle(hwnd)
    if root is None:
        return None, None
    screen = find_screen(root, cfg)
    fid = cfg.get("uia_field_id")
    if not fid or screen is None:
        # 화면(병리결과입력)을 못 찾으면 AMIS 전체에서 찾지 않는다.
        # txtExamRcepNo 는 병리과결과조회[VSPSSPR061S] 등 다른 화면에도 있어 엉뚱한 화면에 입력될 수 있음
        return None, screen
    field = _find_first(screen, PROP_AUTOMATION_ID, fid)
    return field, screen


def _norm(t):
    return "".join((t or "").split()).upper()


def _rect(c):
    r = _safe(lambda: c.BoundingRectangle, None)
    if r is None:
        return None
    try:
        return (r.left, r.top, r.right, r.bottom)
    except Exception:
        return None


def _inside(inner, outer):
    if not inner or not outer:
        return False
    return (inner[0] >= outer[0] - 2 and inner[1] >= outer[1] - 2
            and inner[2] <= outer[2] + 2 and inner[3] <= outer[3] + 2)


def find_showing(root, code, exclude=None, limit=800, grid_only=False):
    """root 안에서 code 가 표시된 요소 (조회 완료 확인용).
    - exclude(검사번호 입력칸)와 그 '안쪽' 편집상자는 제외 (입력한 값이 그대로 보이므로 증거가 안 됨)
    - grid_only=True 면 목록(표) 셀(DataItem)만, 값이 검사번호와 정확히 같은 셀만 인정
    - 비교는 공백 무시/대문자 ('26-S-082711' == '26-S -082711')"""
    if root is None:
        return None
    target = _norm(code)
    cli = _client()
    if grid_only:
        cond = cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50029)
    else:
        cond = cli.CreateOrCondition(
            cli.CreateOrCondition(cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50004),
                                  cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50020)),
            cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50029))
    arr = root.Element.FindAll(TREE_DESCENDANTS, cond)
    if not arr:
        return None
    ex = exclude.Element if exclude is not None else None
    ex_rect = _rect(exclude) if exclude is not None else None
    for i in range(min(arr.Length, limit)):
        el = arr.GetElement(i)
        if ex is not None and _safe(lambda: cli.CompareElements(el, ex), 0):
            continue
        c = _wrap(el)
        if c is None:
            continue
        if _inside(_rect(c), ex_rect):
            continue
        val = _norm(get_value(c))
        if grid_only:
            if val == target:
                return c
        elif target in _norm(_safe(lambda: c.Name)) or target in val:
            return c
    return None


def showing_report(root, code, exclude=None, limit=1500):
    """조회 확인 실패 시 원인 파악용: 검사번호가 보이는 모든 요소(입력칸 영역 제외)와 표 셀 개수."""
    if root is None:
        return 0, []
    target = _norm(code)
    cli = _client()
    cond = cli.CreateOrCondition(
        cli.CreateOrCondition(cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50004),
                              cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50020)),
        cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50029))
    arr = root.Element.FindAll(TREE_DESCENDANTS, cond)
    if not arr:
        return 0, []
    ex_rect = _rect(exclude) if exclude is not None else None
    n_items, hits, loaded = 0, [], []
    for i in range(min(arr.Length, limit)):
        c = _wrap(arr.GetElement(i))
        if c is None or _inside(_rect(c), ex_rect):
            continue
        ctype = _safe(lambda: c.ControlTypeName)
        val = get_value(c) or ""
        name = _safe(lambda: c.Name)
        if ctype == "DataItemControl":
            n_items += 1
            if name.startswith("검사번호") and val and val not in loaded:
                loaded.append(val)     # 실제로 화면에 조회돼 있는 검사번호
        if target in _norm(val) or target in _norm(name):
            hits.append("%s id='%s' name='%s' 값='%s'" % (ctype, _safe(lambda: c.AutomationId),
                                                          name[:25], val[:40]))
    if loaded:
        hits.append("※ 지금 표에 조회돼 있는 검사번호: " + ", ".join(loaded[:5]))
    return n_items, hits[:11]


def find_checkbox(root, prefix, limit=400):
    """이름이 prefix 로 시작하는 체크박스 (공백/대소문자 무시)."""
    if root is None or not prefix:
        return None
    want = " ".join(prefix.split()).lower()
    for c in _find_all(root, PROP_CONTROL_TYPE, 50002, limit):
        name = " ".join((_safe(lambda: c.Name) or "").split()).lower()
        if name.startswith(want):
            return c
    return None


def _flat(t):
    return " ".join((t or "").split()).lower()


def find_by_prefix(root, ctype, prefix, by_value=False, limit=600):
    """컨트롤 종류(ctype: 50004 Edit, 50013 RadioButton ...) 중 이름(또는 값)이 prefix 로 시작하는 첫 요소."""
    if root is None or not prefix:
        return None
    want = _flat(prefix)
    for c in _find_all(root, PROP_CONTROL_TYPE, ctype, limit):
        text = get_value(c) if by_value else _safe(lambda: c.Name)
        if _flat(text).startswith(want):
            return c
    return None


def _key(t):
    t = (t or "").lower()
    for a, b in (("∼", "~"), ("〜", "~"), ("～", "~"), ("＜", "<"), ("＞", ">"), ("&lt;", "<"), ("&gt;", ">")):
        t = t.replace(a, b)
    return "".join(t.split())


def find_radio(root, prefix, limit=800):
    """이름이 prefix 로 시작하는 라디오버튼 (공백·전각 기호 무시: '10 ~ 20 cell' == '10~20cell')."""
    if root is None or not prefix:
        return None
    want = _key(prefix)
    for c in _find_all(root, PROP_CONTROL_TYPE, 50013, limit):
        if _key(_safe(lambda: c.Name)).startswith(want):
            return c
    return None


def all_text(c, limit=60):
    """창 이름 + 안쪽 글자(Text 요소 이름) - Win32 로 글자가 안 읽히는 팝업용."""
    if c is None:
        return ""
    parts = [_safe(lambda: c.Name) or ""]
    for e in _find_all(c, PROP_CONTROL_TYPE, 50020, limit):
        t = _safe(lambda: e.Name) or ""
        if t and t not in parts:
            parts.append(t)
    return " ".join(p.strip() for p in parts if p.strip())


def has_button(c, names):
    for n in names:
        b = find_by_prefix(c, 50000, n)
        if b is not None:
            return b
    return None


def find_visible(root, name, limit=200):
    """이름이 name 인(없으면 name 으로 시작하는) 화면에 보이는 요소."""
    if root is None or not name:
        return None
    for c in _find_all(root, PROP_NAME, name, limit):
        if not _safe(lambda: c.IsOffscreen, False):
            return c
    want = _flat(name)
    for ctype in (50000, 50011, 50007, 50025, 50033):   # Button, MenuItem, ListItem, Custom, Pane
        for c in _find_all(root, PROP_CONTROL_TYPE, ctype, limit):
            if _flat(_safe(lambda: c.Name)).startswith(want) and not _safe(lambda: c.IsOffscreen, False):
                return c
    return None


def visible_buttons(root, names, limit=10):
    """root 아래에서 화면에 보이는 이름이 names 중 하나인 버튼들."""
    out = []
    if root is None:
        return out
    for n in names:
        for c in _find_all(root, PROP_NAME, n, limit):
            if _safe(lambda: c.ControlTypeName) == "ButtonControl" and not _safe(lambda: c.IsOffscreen, False):
                out.append(c)
    return out


def dialog_of(btn):
    """버튼이 들어 있는 창(가장 가까운 WindowControl, 없으면 바로 위 요소)."""
    for a in ancestors(btn, 6):
        if _safe(lambda: a.ControlTypeName) == "WindowControl":
            return a
    return _safe(lambda: btn.GetParentControl(), None)


def invoke(c):
    """버튼 누르기 (InvokePattern → LegacyIAccessible 기본동작). 성공 여부."""
    if c is None:
        return False
    p = _safe(lambda: c.GetPattern(10000), None)   # InvokePattern
    if p is not None:
        try:
            p.Invoke(waitTime=0)
            return True
        except Exception:
            pass
    p = _safe(lambda: c.GetPattern(PAT_LEGACY), None)
    if p is not None:
        try:
            p.DoDefaultAction(waitTime=0)
            return True
        except Exception:
            pass
    return False


def click(c):
    """사람처럼 실제 마우스로 요소 가운데를 클릭 (AMIS 를 앞으로 가져온 뒤 사용). 성공 여부."""
    if c is None or _safe(lambda: c.IsOffscreen, False):
        return False
    try:
        c.Click(simulateMove=False, waitTime=0.1)
        return True
    except Exception:
        return False


def toggle(c):
    """체크박스 상태 바꾸기 (TogglePattern → LegacyIAccessible 기본동작). 성공 여부."""
    p = _safe(lambda: c.GetPattern(PAT_TOGGLE), None)
    if p is not None:
        try:
            p.Toggle(waitTime=0)
            return True
        except Exception:
            pass
    p = _safe(lambda: c.GetPattern(PAT_LEGACY), None)
    if p is not None:
        try:
            p.DoDefaultAction(waitTime=0)
            return True
        except Exception:
            pass
    return False


def find_by_name(root, name):
    return _find_first(root, PROP_NAME, name) if root is not None and name else None


def list_edits(root, limit=60):
    return _find_all(root, PROP_CONTROL_TYPE, 50004, limit)


# ---------------------------------------------------------------- 값 / 상태
def get_value(c):
    if c is None:
        return None
    for pid in (PAT_VALUE, PAT_LEGACY):
        p = _safe(lambda: c.GetPattern(pid), None)
        if p is not None:
            v = _safe(lambda: p.Value, None)
            if v is not None:
                return v
    return None


def set_value(c, text):
    """ValuePattern → LegacyIAccessible 순으로 값 설정. 성공 여부."""
    for pid in (PAT_VALUE, PAT_LEGACY):
        p = _safe(lambda: c.GetPattern(pid), None)
        if p is None:
            continue
        try:
            p.SetValue(text, waitTime=0)
            return True
        except Exception:
            continue
    return False


def is_checked(c):
    """체크/선택 상태: True/False, 알 수 없으면 None."""
    if c is None:
        return None
    p = _safe(lambda: c.GetPattern(PAT_TOGGLE), None)
    if p is not None:
        st = _safe(lambda: p.ToggleState, None)
        if st is not None:
            return st == 1
    p = _safe(lambda: c.GetPattern(PAT_SELECTION_ITEM), None)
    if p is not None:
        v = _safe(lambda: p.IsSelected, None)
        if v is not None:
            return bool(v)
    p = _safe(lambda: c.GetPattern(PAT_LEGACY), None)
    if p is not None:
        st = _safe(lambda: p.State, None)
        if st is not None:
            return bool(st & 0x10)  # STATE_SYSTEM_CHECKED
    return None


def focus(c):
    return bool(_safe(lambda: c.SetFocus(), False))


def native_handle(c):
    return int(_safe(lambda: c.NativeWindowHandle, 0) or 0)


def inner_edit(c):
    """입력칸(txtExamRcepNo) 안에서 실제로 키 입력을 받는 편집상자(창 핸들 있는 Edit).
    Enter/F9 메시지는 바깥 틀이 아니라 이 상자로 보내야 AMIS 가 반응한다. 없으면 c 자신."""
    if c is None:
        return None
    for e in _find_all(c, PROP_CONTROL_TYPE, 50004, 10):
        if native_handle(e):
            return e
    return c


def default_names(text):
    return [n.strip() for n in (text or "").split(",") if n.strip()]
'''

_SOURCES['worker'] = r'''"""자동 저장 작업 스레드.

목록의 '대기중' 항목을 하나씩 꺼내서
  AMIS 활성화 → 검사번호 칸 클릭 → 번호 입력 → Enter(조회) → F9(저장)
순서로 처리한다. 사용자가 키보드/마우스를 쓰는 동안은 멈추고, 설정한
시간(기본 5초) 이상 입력이 없을 때만 진행한다.
"""
import os
import re
import threading
import time

from . import uia
from . import win32 as w
from .hangul import amis_format
from .models import WAIT, RUN, DONE, FAIL

# 프로그램이 직접 보낸 입력 이후 이 시간(ms)보다 늦게 들어온 입력은 사용자 입력으로 본다.
INJECT_MARGIN_MS = 250


class UserActive(Exception):
    """작업 도중 사용자 입력이 감지됨 → 해당 항목은 대기로 돌리고 다시 기다린다."""


class StepError(Exception):
    """처리 실패 (재시도 대상)."""


class AlreadySaved(Exception):
    """'저장된 결과입니다. 다시 저장하시겠습니까?' → 아니오 → 다음 건."""


class PopupStop(Exception):
    """AMIS 에 팝업이 떠서 작업 전체를 중지 (팝업은 닫지 않고 그대로 둠)."""

    def __init__(self, text, after_save=False):
        super().__init__(text)
        self.text = text
        self.after_save = after_save


class Worker(threading.Thread):
    def __init__(self, store, cfg, emit, mode="save"):
        super().__init__(daemon=True)
        self.store = store
        self.cfg = cfg
        self.mode = mode          # save: 저장(F9) / delete: Action ▸ 일괄삭제
        self.emit = emit
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.inject_tick = w.get_tick()
        self.user_tick = w.get_last_input_tick()

    # ------------------------------------------------------------ 제어
    def stop(self):
        self.stop_event.set()

    def pause(self):
        self.pause_event.set()

    def resume(self):
        self.pause_event.clear()

    @property
    def paused(self):
        return self.pause_event.is_set()

    # ------------------------------------------------------------ 보조
    def phase(self, text):
        now = time.monotonic()
        st = getattr(self, "_steps", None)
        if st is not None:
            if st["name"]:
                st["list"].append((st["name"], now - st["t"]))
            st["name"], st["t"] = text, now
        self.emit("phase", text=text)

    def _steps_begin(self):
        self._steps = {"name": "", "t": time.monotonic(), "list": [], "start": time.monotonic()}

    def _steps_report(self, code):
        st = getattr(self, "_steps", None)
        if not st:
            return
        now = time.monotonic()
        if st["name"]:
            st["list"].append((st["name"], now - st["t"]))
        total = now - st["start"]
        slow = [(n, d) for n, d in st["list"] if d >= 0.8]
        detail = " · ".join("%s %.1f" % (n, d) for n, d in slow) or "단계별 0.8초 미만"
        self.log("   ⏱ %s %.1f초  (%s)" % (code, total, detail), "info")
        self._steps = None

    def log(self, text, level="info"):
        self.emit("log", text=text, level=level)

    def mark(self):
        """방금 프로그램이 입력을 보냈음을 기록 (사용자 입력과 구분)."""
        time.sleep(0.03)
        self.inject_tick = w.get_tick()

    def user_input_since_mark(self):
        li = w.get_last_input_tick()
        return w.tick_diff(li, self.inject_tick) > INJECT_MARGIN_MS

    def user_idle_ms(self):
        li = w.get_last_input_tick()
        if w.tick_diff(li, self.inject_tick) > INJECT_MARGIN_MS:
            self.user_tick = li
        return max(0, w.tick_diff(w.get_tick(), self.user_tick))

    def check_user(self):
        if self.user_input_since_mark():
            self.user_tick = w.get_last_input_tick()
            raise UserActive()

    def sleep(self, sec):
        end = time.monotonic() + max(0.0, float(sec))
        while time.monotonic() < end:
            if self.stop_event.is_set():
                return
            time.sleep(0.05)

    def wait_idle(self):
        """사용자가 idle_seconds 동안 입력이 없을 때 True. 정지/일시정지 시 False."""
        last_shown = None
        while not self.stop_event.is_set() and not self.paused:
            need = float(self.cfg.get("idle_seconds", 5)) * 1000
            idle = self.user_idle_ms()
            if idle >= need:
                return True
            remain = int((need - idle) / 1000 + 0.999)
            if remain != last_shown:
                self.phase("사용자 사용중 · %d초 후 진행" % remain)
                last_shown = remain
            time.sleep(0.2)
        return False

    # ------------------------------------------------------------ 메인 루프
    def run(self):
        with uia.thread_init():
            self._run()

    def _run(self):
        self.emit("state", state="running")
        self.log("자동 저장을 시작합니다.")
        finished = False
        try:
            while not self.stop_event.is_set():
                if self.paused:
                    self.emit("state", state="paused")
                    self.phase("일시정지")
                    while self.paused and not self.stop_event.is_set():
                        time.sleep(0.2)
                    self.emit("state", state="running")
                    continue

                item = self.store.next_pending()
                if item is None:
                    finished = True
                    break
                self.emit("current", code=item.code)

                t_idle = time.monotonic()
                if not self.wait_idle():
                    continue
                idle_wait = time.monotonic() - t_idle
                if idle_wait >= 1.0:
                    self.log("   ⏳ 사용자 사용 중이라 %.0f초 기다렸다가 시작" % idle_wait, "info")

                hwnd = w.find_window(self.cfg.get("window_keyword", "AMIS"))
                if not hwnd:
                    self.phase("AMIS 창을 찾을 수 없음 · 대기")
                    self.emit("amis", found=False)
                    self.sleep(2)
                    continue
                self.emit("amis", found=True)

                self.store.update(item, status=RUN, note="")
                self.emit("item", id=item.id)
                self._steps_begin()
                try:
                    self.process(item, hwnd)
                except AlreadySaved as e:
                    self.store.update(item, status=DONE, note="이미 저장된 결과 → '아니오' (다시 저장 안 함)")
                    self.log("[%s] '저장된 결과입니다' 팝업 → '아니오' 누르고 다음 건 진행" % item.code, "warn")
                    path = self.record_already_saved(item, str(e))
                    if path:
                        self.log("   기록: %s" % path, "info")
                except PopupStop as e:
                    if e.after_save:
                        note = "저장(F9) 후 팝업 → 작업 중지 · 저장 여부 AMIS 에서 확인: %s" % e.text[:80]
                    else:
                        note = "팝업 발생 → 작업 중지 (저장 안 함): %s" % e.text[:80]
                    self.store.update(item, status=FAIL, tries=item.tries + 1, note=note)
                    self.log("[%s] %s" % (item.code, note), "error")
                    self.emit("item", id=item.id)
                    self.emit("popup", text=e.text, code=item.code, after_save=e.after_save)
                    self.stop_event.set()
                    break
                except UserActive:
                    self.store.update(item, status=WAIT, note="사용자 작업 감지 → 대기")
                    self.log("[%s] 사용자 입력 감지, 잠시 멈춥니다." % item.code, "warn")
                except StepError as e:
                    tries = item.tries + 1
                    retries = int(self.cfg.get("max_retries", 1))
                    if tries > retries:
                        self.store.update(item, status=FAIL, tries=tries, note=str(e))
                        self.log("[%s] %s: %s" % (item.code, "삭제실패" if self.mode == "delete" else "저장실패", e),
                                 "error")
                    else:
                        self.store.update(item, status=WAIT, tries=tries,
                                          note="재시도 대기 (%s)" % e)
                        self.log("[%s] 실패, 재시도 예정: %s" % (item.code, e), "warn")
                except Exception as e:  # 예기치 못한 오류도 항목 실패로 기록하고 계속
                    self.store.update(item, status=FAIL, tries=item.tries + 1,
                                      note="예외: %s" % e)
                    self.log("[%s] 예외: %r" % (item.code, e), "error")
                else:
                    self.store.update(item, status=DONE, note="")
                    self.log("[%s] %s" % (item.code, "일괄삭제 완료" if self.mode == "delete" else "저장완료"), "ok")
                self._steps_report(item.code)
                self.emit("item", id=item.id)
                self.sleep(self.cfg.get("del_item_interval" if self.mode == "delete" else "item_interval", 1.0))
        finally:
            self.emit("current", code=None)
            self.emit("state", state="done" if finished else "stopped")
            self.log("모든 항목 처리가 끝났습니다." if finished else "작업을 멈췄습니다.")

    # ------------------------------------------------------------ 한 건 처리
    def process(self, item, hwnd):
        cfg = self.cfg
        if cfg.get("input_method") == "uia":
            return self.process_by_uia(item, hwnd)
        offset = cfg.get("field_offset")
        if not offset:
            raise StepError("검사번호 칸 위치가 설정되지 않았습니다 (설정 탭)")

        pid = w.get_window_pid(hwnd)
        baseline = set(w.list_popups(pid, exclude=hwnd))
        if cfg.get("input_method") == "message":
            return self.process_by_message(item, hwnd, pid, baseline, offset)
        prev_fg = w.get_foreground()
        prev_pos = w.get_cursor_pos()
        try:
            self.phase("AMIS 창 활성화")
            if not w.activate(hwnd):
                raise StepError("AMIS 창을 앞으로 가져오지 못했습니다")
            self.mark()
            self.sleep(0.3)
            self.check_user()

            self.phase("검사번호 입력")
            left, top, _, _ = w.get_window_rect(hwnd)
            fx, fy = left + offset[0], top + offset[1]
            w.click(fx, fy)
            self.mark()
            self.sleep(0.2)
            self.clear_field()
            self.input_text(item.code)
            self.mark()
            self.sleep(0.1)
            self.verify_input(w.control_at(hwnd, fx, fy), item.code)
            self.check_user()

            if cfg.get("press_enter", False):
                w.press("ENTER")
                self.mark()
            self.phase("조회 대기")
            self.sleep(cfg.get("load_wait", 2.0))
            self.check_user()
            err = self.handle_dialogs(pid, hwnd, baseline)
            if err:
                raise StepError("조회 오류: " + err)

            if not w.is_foreground(hwnd):
                w.activate(hwnd)
                self.mark()
                self.sleep(0.2)
            self.check_user()

            self.phase("저장 (%s)" % cfg.get("save_key", "F9"))
            w.press(cfg.get("save_key", "F9"))
            self.mark()
            self.sleep(cfg.get("save_wait", 2.0))
            err = self.handle_dialogs(pid, hwnd, baseline, after_save=True)
            if err:
                raise StepError("저장 오류: " + err)
        finally:
            if (cfg.get("restore_focus", True) and prev_fg and prev_fg != hwnd
                    and w.is_window(prev_fg) and not self.user_input_since_mark()):
                w.activate(prev_fg)
                w.set_cursor_pos(*prev_pos)
                self.mark()

    # ------------------------------------------------------------ UI Automation 방식
    def process_by_uia(self, item, hwnd):
        """병리결과입력 화면의 검사번호 입력창을 AutomationId 로 찾아 입력 → Enter → (기본값 확인) → F9."""
        cfg = self.cfg
        if not uia.available():
            raise StepError("uiautomation 모듈이 없습니다 (pip install uiautomation)")
        if not cfg.get("uia_field_id"):
            raise StepError("검사번호 입력창 AutomationId 가 없습니다 → 설정 ▸ [UI 요소 찾기]")
        pid = w.get_window_pid(hwnd)
        self.clear_leftover_popups(pid, hwnd)
        baseline = set(h for h in w.list_popups(pid, exclude=hwnd) if not w.is_dialog_like(h))

        self.phase("병리결과입력 화면 찾기")
        if w.is_iconic(hwnd):                 # AMIS 가 최소화돼 있으면 원래 크기로
            self.log("AMIS 가 최소화되어 있어 원래 크기로 복원합니다.", "info")
            w.show_no_activate(hwnd)
        field, screen = uia.find_field(hwnd, cfg)
        if field is None or uia._safe(lambda: field.IsOffscreen, False):
            # 병리결과입력 화면이 다른 화면 뒤(또는 탭 뒤)에 있는 경우 → 앞으로 전환 후 다시 찾기
            code = cfg.get("uia_screen_id") or cfg.get("screen_code") or "VSPSSPR059S"
            child = w.find_mdi_child(hwnd, code)
            if child:
                self.phase("병리결과입력 화면 앞으로 전환")
                self.log("병리결과입력 화면이 뒤에 있어 앞으로 전환합니다.", "info")
                if w.is_iconic(child):
                    w.show_no_activate(child)
                w.mdi_activate(child)
                for _ in range(10):
                    self.sleep(0.3)
                    field, screen = uia.find_field(hwnd, cfg)
                    if field is not None and not uia._safe(lambda: field.IsOffscreen, False):
                        break
        if field is None:
            where = "화면(%s)" % cfg.get("screen_code") if screen is None else "입력창"
            raise StepError("%s 을(를) 찾지 못했습니다 – AMIS 에 병리결과입력 화면이 열려 있는지 확인" % where)

        key_target = uia.inner_edit(field)
        fhwnd = uia.native_handle(key_target) or uia.native_handle(field)
        mode = cfg.get("key_send", "auto")
        replay = cfg.get("uia_input", "replay") == "replay"
        typing = replay or cfg.get("uia_input", "replay") == "type"
        # 키보드 입력 방식이면 Enter/F9 도 실제 키보드로 (사람이 직접 누르는 것과 동일)
        use_msg = (not typing) and (mode == "message" or (mode == "auto" and fhwnd))
        if use_msg and not fhwnd:
            raise StepError("입력창에 창 핸들이 없어 메시지 전송 불가 → Enter/F9 전송을 '키보드'로 변경")

        screen_hwnd = uia.native_handle(screen) if screen is not None else 0
        if not screen_hwnd or not w.mdi_client_of(screen_hwnd):
            raise StepError("병리결과입력 화면의 창 핸들을 찾지 못했습니다 (화면 전환 불가)")
        prev_mdi = w.mdi_active(screen_hwnd)

        def ensure_screen(step):
            """결과조회 등 다른 화면이 활성이면 병리결과입력으로 전환. 실패하면 이 건은 저장하지 않음."""
            if not w.mdi_activate(screen_hwnd):
                raise StepError("%s 전에 병리결과입력 화면을 활성화하지 못해 중단했습니다" % step)

        prev_fg, prev_pos, activated = w.get_foreground(), w.get_cursor_pos(), False
        try:
            self.phase("병리결과입력 화면 활성화")
            ensure_screen("검사번호 입력")
            self.phase("검사번호 입력")
            if not use_msg:
                if not w.activate(hwnd):
                    raise StepError("AMIS 창을 앞으로 가져오지 못했습니다")
                activated = True
                self.mark()
                self.sleep(0.2)
                self.check_user()
            if use_msg:
                w.focus_control(fhwnd)   # 창을 앞으로 가져오지 않고 포커스만
            else:
                uia.focus(key_target)
            if typing:
                # QR 스캐너가 하는 것과 똑같이: 칸 비우기 → 글자 입력 (→ 아래에서 Enter)
                # 값을 직접 설정하면 칸에는 보이지만 AMIS 내부 조회값이 안 바뀌어 '결과내용이 없습니다' 가 뜸
                self.sleep(0.1)
                self.check_user()
                if replay:
                    # QR 태그와 똑같이: 칸 전체 선택 → 스캐너가 쳤던 원문 그대로 → (아래에서) Enter
                    w._send_msg(fhwnd, 0x00B1, 0, -1)       # EM_SETSEL 전체 선택
                    self.sleep(0.05)
                else:
                    self.clear_field()
                w.ime_english(fhwnd)
                if replay:
                    typed = item.raw or amis_format(item.code)   # 예전 목록(원문 없음)은 AMIS 표기로
                else:
                    typed = "".join(item.code.split()) if cfg.get("type_raw_qr", True) else item.code
                if cfg.get("type_method", "keys") == "keys":
                    w.type_keys(typed, max(0.01, float(cfg.get("type_delay_ms", 40)) / 1000.0))
                else:
                    w.type_unicode(typed)
                self.mark()
            else:
                # 처음 방식: QR 원래 값(공백 없음)을 입력칸에 직접 설정 → AMIS 가 입력만으로 조회
                code_in = "".join(item.code.split()) if cfg.get("type_raw_qr", True) else amis_format(item.code)
                # 입력 전에 입력칸의 기존 값을 전체 선택 (EM_SETSEL 0, -1) → 새 번호로 통째로 바뀌게
                if fhwnd:
                    w._send_msg(fhwnd, 0x00B1, 0, -1)
                    self.sleep(0.05)
                if not uia.set_value(field, code_in):
                    raise StepError("입력창에 값을 넣지 못했습니다 (%s)" % uia.describe(field))
            self.sleep(0.25)
            value = uia.get_value(field)
            norm = lambda t: "".join((t or "").split()).upper()
            if value is None or norm(value) != norm(item.code):
                # 정확히 같을 때만 Enter (일부 글자 누락·한글 입력·이전 값 잔류 시 조회하지 않음)
                raise StepError("입력칸 값이 검사번호와 달라 조회하지 않았습니다 (입력창 값: '%s')" % (value or "")[:30])

            if cfg.get("press_enter", False):
                ensure_screen("Enter(조회)")
                if not use_msg:
                    uia.focus(key_target)
                self.send_key(fhwnd if use_msg else None, "ENTER", "\r")
            self.phase("조회 대기")
            self.sleep(cfg.get("del_load_wait" if self.mode == "delete" else "load_wait", 2.0))
            if not use_msg:
                self.check_user()
            err = self.handle_dialogs(pid, hwnd, baseline)
            if err:
                raise StepError("조회 오류: " + err)

            if cfg.get("check_loaded", True) or self.mode == "delete":
                self.check_loaded(screen or uia.control_from_handle(hwnd), field, item.code)
            if self.mode == "delete":
                activated = self.do_bulk_delete(screen, hwnd, pid, baseline, item) or activated
                return
            if cfg.get("check_default", True):
                self.check_default_selected(screen or uia.control_from_handle(hwnd))
            self.apply_extra_checks(screen or uia.control_from_handle(hwnd), item)
            if item.checks.get(cfg.get("vaginal_col", "Vaginal")):
                activated = self.apply_vaginal(screen or uia.control_from_handle(hwnd), hwnd) or activated
            activated = self.apply_radio_actions(screen or uia.control_from_handle(hwnd), item, hwnd) or activated

            if not use_msg:
                if not w.is_foreground(hwnd):
                    w.activate(hwnd)
                    self.mark()
                    self.sleep(0.2)
                self.check_user()
            ensure_screen("저장(F9)")
            f9_msg = use_msg and not cfg.get("f9_keyboard", True)
            if not f9_msg:
                if not w.is_foreground(hwnd):
                    if not w.activate(hwnd):
                        raise StepError("AMIS 창을 앞으로 가져오지 못해 저장(F9)하지 않았습니다")
                    activated = True
                    self.mark()
                    self.sleep(0.2)
                self.check_user()
                ensure_screen("저장(F9)")
                uia.focus(key_target)
                self.sleep(0.1)
            self.phase("저장 (%s)" % cfg.get("save_key", "F9"))
            self.send_key(fhwnd if f9_msg else None, cfg.get("save_key", "F9"))
            self.sleep(cfg.get("save_wait", 2.0))
            err = self.handle_dialogs(pid, hwnd, baseline, after_save=True)
            if err:
                raise StepError("저장 오류: " + err)
        finally:
            # 원래 보던 AMIS 화면(예: 결과조회)으로 되돌림 - 사용자가 그사이 입력하지 않았을 때만
            if (cfg.get("restore_focus", True) and prev_mdi and int(prev_mdi) != int(screen_hwnd)
                    and not self.user_input_since_mark()):
                w.mdi_activate(prev_mdi)
            if (activated and cfg.get("restore_focus", True) and prev_fg and prev_fg != hwnd
                    and w.is_window(prev_fg) and not self.user_input_since_mark()):
                w.activate(prev_fg)
                w.set_cursor_pos(*prev_pos)
                self.mark()

    def send_key(self, target_hwnd, key, char=None):
        """target_hwnd 가 있으면 메시지로(백그라운드), 없으면 실제 키 입력으로."""
        if target_hwnd:
            w.post_key(target_hwnd, key, char)
        else:
            w.press(key)
            self.mark()

    def check_loaded(self, root, field, code):
        """입력창 말고 화면의 다른 곳(병리번호 칸, 목록 등)에 검사번호가 표시돼야 조회된 것으로 본다.
        조회가 안 됐는데 F9 를 누르면 이전 검사가 다시 저장될 수 있으므로 반드시 확인한다."""
        deadline = time.monotonic() + 5.0
        while True:
            grid_only = self.cfg.get("loaded_check", "grid") == "grid"
            if uia.find_showing(root, code, exclude=field, grid_only=grid_only) is not None:
                return
            if time.monotonic() >= deadline or self.stop_event.is_set():
                try:
                    n_items, hits = uia.showing_report(root, code, exclude=field)
                    self.log("  ↳ 조회 확인 실패 상세: 입력칸 값 '%s' · 표 셀 %d개 · 번호가 보이는 곳 %d곳"
                             % ((uia.get_value(field) or "")[:30], n_items, len(hits)), "warn")
                    for h in hits:
                        self.log("     - " + h, "warn")
                except Exception as e:
                    self.log("  ↳ 상세 확인 오류: %r" % e, "warn")
                where = "목록(표)" if self.cfg.get("loaded_check", "grid") == "grid" else "화면"
                raise StepError("%s에 %s 가 조회되지 않아 저장하지 않았습니다" % (where, code))
            self.sleep(0.5)

    def apply_radio_actions(self, root, item, hwnd):
        """목록에서 체크한 라디오 변경(URINE: <30ml, UC absent, Instrumented 10~20 / <10)을 적용.
        사람처럼 해당 라디오를 실제 클릭(같은 묶음의 기존 선택은 AMIS 가 자동 해제) → 선택됐는지 확인.
        찾지 못하거나 선택되지 않으면 저장하지 않음. AMIS 를 앞으로 가져왔으면 True."""
        from .config import parse_radio_actions
        todo = [(h, p) for h, p, _ in parse_radio_actions(self.cfg.get("radio_actions")) if item.checks.get(h)]
        if not todo:
            return False
        activated = False
        for hdr, prefix in todo:
            radio = uia.find_radio(root, prefix)
            if radio is None:
                raise StepError("'%s' 라디오버튼(%s)을 찾지 못해 저장하지 않았습니다 (URINE 건이 맞는지 확인)"
                                % (hdr, prefix))
            if uia.is_checked(radio) is True:
                continue
            if not w.is_foreground(hwnd):
                if not w.activate(hwnd):
                    raise StepError("AMIS 창을 앞으로 가져오지 못해 '%s' 를 적용하지 않았습니다" % hdr)
                activated = True
                self.mark()
                self.sleep(0.2)
            self.check_user()
            self.phase("라디오 변경: %s" % hdr)
            ok = self.real_click(radio)
            if not ok:
                raise StepError("'%s' 라디오를 클릭하지 못해 저장하지 않았습니다 (화면에 보이는지 확인)" % hdr)
            if uia.is_checked(radio) is not True:
                raise StepError("'%s' 가 선택되지 않아 저장하지 않았습니다" % hdr)
            self.log("  %s 선택 확인" % hdr, "info")
        return activated

    def apply_vaginal(self, root, hwnd):
        """GYN Vaginal 건: 진단 문구를 'Vaginal :' 로 바꾸고 Presence 라디오를 해제. 확인 실패 시 저장하지 않음.
        사람이 하는 것과 같이 실제 키 입력/마우스 클릭을 쓰므로 AMIS 를 앞으로 가져온다. 가져왔으면 True."""
        cfg = self.cfg
        to_text = cfg.get("vaginal_text_to", "Vaginal :")
        activated = False
        if not w.is_foreground(hwnd):
            if not w.activate(hwnd):
                raise StepError("AMIS 창을 앞으로 가져오지 못해 Vaginal 처리를 하지 않았습니다")
            activated = True
            self.mark()
            self.sleep(0.2)
        self.check_user()

        # 1) 진단 문구 Cervicovaginal : → Vaginal :
        edit = uia.find_by_prefix(root, 50004, to_text, by_value=True)
        if edit is None:
            edit = uia.find_by_prefix(root, 50004, cfg.get("vaginal_text_from", "Cervicovaginal"), by_value=True)
            if edit is None:
                raise StepError("진단 문구 칸('Cervicovaginal :')을 찾지 못해 저장하지 않았습니다")
            self.phase("Vaginal: 진단 문구 변경")
            uia.focus(edit)
            self.sleep(0.1)
            eh = uia.native_handle(edit)
            if eh:
                w._send_msg(eh, 0x00B1, 0, -1)       # EM_SETSEL 전체 선택
            else:
                w.press("A", ("CTRL",))
            w.ime_english(eh)
            w.type_keys(to_text, max(0.01, float(cfg.get("type_delay_ms", 40)) / 1000.0))
            self.mark()
            self.sleep(0.2)
        if uia._flat(uia.get_value(edit)) != uia._flat(to_text):
            raise StepError("진단 문구가 '%s' 로 바뀌지 않아 저장하지 않았습니다 (현재: '%s')"
                            % (to_text, (uia.get_value(edit) or "")[:30]))

        # 2) Presence of endocervical / transformation zone 라디오 해제 (선택돼 있으면 한 번 더 클릭)
        radio = uia.find_by_prefix(root, 50013, cfg.get("vaginal_radio", "Presence of endocervical"))
        if radio is None:
            raise StepError("'Presence of endocervical' 라디오버튼을 찾지 못해 저장하지 않았습니다")
        if uia.is_checked(radio):
            self.phase("Vaginal: Presence 라디오 해제")
            ok = self.real_click(radio)
            if not ok:
                raise StepError("Presence 라디오버튼을 클릭하지 못해 저장하지 않았습니다 (화면에 보이는지 확인)")
        if uia.is_checked(radio) is not False:
            raise StepError("Presence 라디오버튼이 해제되지 않아 저장하지 않았습니다")
        self.log("  Vaginal 처리: 문구 '%s', Presence 해제 확인" % to_text, "info")
        return activated

    def apply_extra_checks(self, root, item):
        """목록에서 지정한 체크박스 상태를 AMIS 화면에 똑같이 맞춘다. 맞추지 못하면 저장하지 않음."""
        from .config import parse_extra_checks
        for hdr, prefix in parse_extra_checks(self.cfg.get("extra_checks")):
            want = bool(item.checks.get(hdr, False))
            ctrl = uia.find_checkbox(root, prefix)
            if ctrl is None:
                if want:
                    raise StepError("'%s' 체크박스를 화면에서 찾지 못해 저장하지 않았습니다" % hdr)
                continue
            st = uia.is_checked(ctrl)
            if st is None:
                raise StepError("'%s' 체크박스 상태를 읽지 못해 저장하지 않았습니다" % hdr)
            if st != want:
                self.phase("체크박스 %s: %s" % (hdr, "체크" if want else "해제"))
                uia.toggle(ctrl)
                self.sleep(0.3)
                if uia.is_checked(ctrl) != want:
                    raise StepError("'%s' 체크박스를 %s하지 못해 저장하지 않았습니다"
                                    % (hdr, "체크" if want else "해제"))
                self.log("  %s → %s" % (hdr, "체크함" if want else "해제함"), "info")

    def check_default_selected(self, root):
        """조회 후 기본 라디오버튼(예: Negative for malignant cells)이 선택돼 있어야 저장.
        이름은 쉼표로 여러 개 지정 가능 (진단 탭마다 문구가 다를 때) - 하나라도 선택돼 있으면 통과."""
        names = uia.default_names(self.cfg.get("default_name"))
        if not names:
            return
        found, unchecked = [], []
        for name in names:
            ctrl = uia.find_by_name(root, name)
            if ctrl is None:
                continue
            found.append(name)
            st = uia.is_checked(ctrl)
            if st is True:
                return
            if st is False:
                unchecked.append(name)
        if not found:
            raise StepError("기본 라디오버튼(%s)을 화면에서 찾지 못해 저장하지 않았습니다" % ", ".join(names))
        if unchecked and len(unchecked) == len(found):
            raise StepError("기본 라디오버튼(%s)이 선택되어 있지 않아 저장하지 않았습니다" % ", ".join(unchecked))

    def process_by_message(self, item, hwnd, pid, baseline, offset):
        """창을 앞으로 가져오지 않고 메시지를 직접 보내는 방식 (키보드 보안 프로그램 영향 없음)."""
        cfg = self.cfg
        left, top, _, _ = w.get_window_rect(hwnd)
        ctrl = w.control_at(hwnd, left + offset[0], top + offset[1])
        if not ctrl or ctrl == hwnd:
            raise StepError("검사번호 칸 컨트롤을 찾지 못했습니다 (위치 재지정 필요)")

        self.phase("검사번호 입력 (메시지)")
        w.focus_control(ctrl)
        if not w.set_control_text(ctrl, item.code):
            raise StepError("검사번호 칸에 값을 넣지 못했습니다 [%s]" % w.class_name(ctrl))
        self.sleep(0.1)
        self.verify_input(ctrl, item.code)

        if cfg.get("press_enter", False):
            w.post_key(ctrl, "ENTER", "\r")
        self.phase("조회 대기")
        self.sleep(cfg.get("load_wait", 2.0))
        err = self.handle_dialogs(pid, hwnd, baseline)
        if err:
            raise StepError("조회 오류: " + err)

        self.phase("저장 (%s, 메시지)" % cfg.get("save_key", "F9"))
        w.post_key(ctrl, cfg.get("save_key", "F9"))
        self.sleep(cfg.get("save_wait", 2.0))
        err = self.handle_dialogs(pid, hwnd, baseline, after_save=True)
        if err:
            raise StepError("저장 오류: " + err)

    def verify_input(self, ctrl, code):
        """일반 입력칸(Edit)이면 실제로 번호가 들어갔는지 읽어서 확인한다."""
        if not ctrl or not w.is_edit_like(ctrl):
            return
        text = w.get_control_text(ctrl)
        if text is None:
            return
        norm = lambda t: "".join(t.split()).upper()
        if norm(code) not in norm(text):
            raise StepError("검사번호가 입력되지 않았습니다 (칸 내용: '%s') → [진단] 결과 확인" % text[:30])

    def clear_field(self):
        method = self.cfg.get("clear_method", "home_end")
        if method == "ctrl_a":
            w.press("A", ("CTRL",))
            w.press("BACK")
        elif method == "backspace":
            w.press("END")
            for _ in range(30):
                w.press("BACK")
        else:
            w.press("HOME")
            w.press("END", ("SHIFT",))
            w.press("BACK")
        self.mark()

    def input_text(self, text):
        method = self.cfg.get("input_method", "paste")
        if method == "paste":
            backup = w.get_clipboard_text()
            if not w.set_clipboard_text(text):
                w.type_unicode(text)
                return
            w.press("V", ("CTRL",))
            time.sleep(0.3)
            if backup is not None:
                w.set_clipboard_text(backup)
        elif method == "keys":
            w.type_keys(text)
        else:
            w.type_unicode(text)

    def record_already_saved(self, item, text):
        """'저장된 결과입니다' 팝업이 뜬 검사번호를 날짜별 CSV 에 누적 기록 (엑셀로 열림)."""
        from .config import data_path
        try:
            folder = data_path("logs")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, "이미저장_%s.csv" % time.strftime("%Y%m%d"))
            new = not os.path.exists(path)
            with open(path, "a", encoding="utf-8-sig", newline="") as f:
                if new:
                    f.write("시각,검사번호,팝업 내용\r\n")
                f.write('%s,%s,"%s"\r\n' % (time.strftime("%Y-%m-%d %H:%M:%S"), item.code,
                                           " ".join(text.split()).replace('"', "'")))
            return path
        except OSError as e:
            self.log("   기록 실패: %s" % e, "error")
            return None

    def _closed(self, h, secs=1.5, btn=None):
        """창(h)이 닫혔는지. 창 핸들이 없으면 버튼이 화면에서 사라졌는지로 판단."""
        for _ in range(int(secs * 10)):
            self.sleep(0.1)
            if h:
                if not w.is_window(h) or not w.is_visible(h):
                    return True
            elif btn is not None and uia._safe(lambda: btn.IsOffscreen, True):
                return True
        return False

    def press_button(self, h, btn):
        """팝업 h 의 버튼 btn 을 누르고 팝업이 닫혔는지 확인.
        AMIS(DevExpress) 메시지창은 Invoke 가 안 먹는 경우가 있어 3가지 방법을 차례로 시도."""
        if btn is None:
            return False
        if not h:
            h = uia.native_handle(btn)
        name = uia._safe(lambda: btn.Name) or "?"
        # 1) UI 자동화 Invoke
        if uia.invoke(btn) and self._closed(h, btn=btn):
            return True
        # 2) 실제 마우스 클릭
        if (not h) or (w.is_window(h) and w.is_visible(h)):
            w.activate(h)
            self.sleep(0.15)
            if self.real_click(btn) and self._closed(h, btn=btn):
                return True
        # 3) 그 버튼에 포커스 → Space (포커스된 버튼 누르기, 다른 버튼이 눌릴 위험 없음)
        if (not h) or (w.is_window(h) and w.is_visible(h)):
            w.activate(h)
            self.sleep(0.15)
            uia.focus(btn)
            self.sleep(0.15)
            if uia._safe(lambda: btn.HasKeyboardFocus, False):
                w.press("SPACE")
                self.mark()
                if self._closed(h, 2.0, btn=btn):
                    return True
            else:
                self.log("   '%s' 버튼에 포커스를 줄 수 없어 Space 생략" % name, "warn")
        self.log("   '%s' 버튼을 눌렀지만 창이 닫히지 않음" % name, "error")
        return False

    def press_no(self, h, btn=None):
        """팝업 h 의 '아니오' 버튼을 누르고 팝업이 닫혔는지 확인."""
        if btn is None:
            btn = uia.has_button(uia.control_from_handle(h), self.NO_NAMES)
        return self.press_button(h, btn)

    def real_click(self, ctrl):
        """실제 마우스 클릭. 프로그램 창(항상 위)이 가리지 않게 잠시 맨 아래로 내렸다가 되돌린다."""
        w.hold_z(3.0)
        mine = w.own_windows()
        tops = [h for h in mine if w.is_topmost(h)]
        for h in mine:
            w.set_z(h, -2)
            w.set_z(h, 1)
        try:
            pos = w.get_cursor_pos()
            ok = uia.click(ctrl)
            self.mark()
            self.sleep(0.3)
            w.set_cursor_pos(*pos)
            return ok
        finally:
            for h in tops:
                w.set_z(h, -1)
            w.hold_z(0)

    NO_NAMES = ("아니오", "아니요", "No")

    def popup_text(self, h):
        """팝업 글자: Win32 + UIA 를 합쳐서 (DevExpress 메시지창은 Win32 로 본문이 안 읽힐 수 있음)."""
        t1 = w.get_all_text(h) or ""
        t2 = uia.all_text(uia.control_from_handle(h)) if uia.available() else ""
        return " ".join(x for x in (t1, t2) if x).strip() or "(내용 없음)"

    YES_NAMES = ("예", "예(Y)", "Yes")

    def find_yesno(self, pid, main_hwnd, baseline=()):
        """예/아니오 창 찾기. 반환 dict(h, text, yes, no) 또는 None.
        1) AMIS 의 새 최상위 창 중 '아니오' 버튼이 있는 창 (대화상자 판정과 무관)
        2) AMIS 메인 창 안에 그려진 메시지창 (최상위 창이 아니라 목록에 안 잡히는 경우)"""
        if not uia.available():
            return None
        for h in w.list_popups(pid, exclude=main_hwnd):
            if h in baseline:
                continue
            d = uia.control_from_handle(h)
            no = uia.has_button(d, self.NO_NAMES)
            if no is not None and not uia._safe(lambda: no.IsOffscreen, False):
                return {"h": h, "text": self.popup_text(h), "no": no,
                        "yes": uia.has_button(d, self.YES_NAMES)}
        # AMIS 창 안에 그려진 메시지창: Win32 로 '아니오' 글자 버튼을 찾고, 같은 부모에 '예' 가 있을 때만
        # (예전 UI 자동화 전체 탐색은 AMIS 화면 요소가 많아 한 번에 수 초씩 걸렸음)
        for no_h in w.find_children_by_text(main_hwnd, self.NO_NAMES):
            box = w.parent_of(no_h)
            for _ in range(3):
                if not box:
                    break
                yes_hs = w.find_children_by_text(box, self.YES_NAMES)
                if yes_hs:
                    no = uia.control_from_handle(no_h)
                    yes = uia.control_from_handle(yes_hs[0])
                    dlg = uia.control_from_handle(box)
                    text = (uia.all_text(dlg, 20) or w.get_all_text(box) or "").strip() or "(내용 없음)"
                    return {"h": box, "text": text, "no": no, "yes": yes}
                box = w.parent_of(box)
        return None

    def _popups(self, pid, main_hwnd, baseline, ignored):
        out = []
        ignore_rules = [[t.strip().lower() for t in rule.split("+") if t.strip()]
                        for rule in str(self.cfg.get("ignore_popups", "")).split(",") if rule.strip()]
        for h in w.list_popups(pid, exclude=main_hwnd):
            if h in baseline or h in ignored or not w.is_dialog_like(h):
                continue
            t = self.popup_text(h).lower()
            if any(rule and all(tok in t for tok in rule) for rule in ignore_rules):
                ignored.add(h)      # 자동으로 사라지는 안내창: 건드리지 않음
                self.log("안내창 무시: %s" % t[:60], "info")
                continue
            out.append(h)
        return out

    def handle_dialogs(self, pid, main_hwnd, baseline, after_save=False, wait=None):
        """새로 뜬 팝업 처리. 실패로 판단되면 그 메시지를 반환.
        - '예/아니오' 창: 절대 Enter(=예) 를 누르지 않고 '아니오'. '저장된 결과입니다' 면 AlreadySaved.
        - 확인(OK) 창: Enter 로 닫고, 실패 문구가 있으면 실패.
        - F9 후(after_save)에는 팝업이 늦게 뜰 수 있어 dialog_wait 초 동안 기다린다."""
        keywords = [k.strip().lower() for k in str(self.cfg.get("fail_keywords", "")).split(",") if k.strip()]
        no_rules = [[t.strip().lower() for t in rule.split("+") if t.strip()]
                    for rule in str(self.cfg.get("no_popups", "")).split(",") if rule.strip()]
        ignored = set()
        if wait is None:
            wait = float(self.cfg.get("dialog_wait", 4.0)) if after_save else 0.0
        wait_until = time.monotonic() + wait
        handled = 0
        while True:
            yn = self.find_yesno(pid, main_hwnd, baseline)
            if yn is not None:
                handled += 1
                if handled > 6:
                    return "팝업이 계속 닫히지 않습니다"
                text, low = yn["text"], yn["text"].lower()
                already = any(rule and all(tok in low for tok in rule) for rule in no_rules)
                if not already and after_save and len(low.replace("vspsspr059s", "").strip()) < 25:
                    already = True          # F9 직후 본문을 못 읽은 예/아니오 창 = '저장된 결과입니다'
                self.log("확인창(예/아니오): %s → [아니오]" % text, "warn")
                if not self.press_button(yn["h"], yn["no"]):
                    raise StepError("예/아니오 팝업에서 '아니오'를 누르지 못했습니다: %s" % text[:60])
                if already:
                    raise AlreadySaved(text)
                raise StepError("예/아니오 팝업 → '아니오' (저장 안 함): %s" % text[:80])
            dialogs = self._popups(pid, main_hwnd, baseline, ignored)
            if not dialogs:
                if handled or time.monotonic() >= wait_until:
                    return None
                time.sleep(0.2)
                continue
            h = dialogs[0]
            handled += 1
            if handled > 6:
                return "팝업이 계속 닫히지 않습니다"
            text = self.popup_text(h)
            dlg = uia.control_from_handle(h) if uia.available() else None
            no_btn = uia.has_button(dlg, self.NO_NAMES) if dlg is not None else None
            if no_btn is not None:
                low = text.lower()
                already = any(rule and all(tok in low for tok in rule) for rule in no_rules)
                # 글자를 못 읽어도 F9 직후 병리결과입력 화면의 예/아니오 창이면 '저장된 결과입니다' 로 본다
                if not already and after_save and "vspsspr059s" in low:
                    title = (w.get_all_text(h) or "").split("]")[0].lower() + "]"
                    rest = low.replace(title, "").replace("예", "").replace("아니오", "").strip()
                    if len(rest) < 5:       # 본문 글자를 못 읽은 경우
                        already = True
                self.log("확인창(예/아니오): %s → [아니오]" % text, "warn")
                if not self.press_no(h, no_btn):
                    raise StepError("예/아니오 팝업에서 '아니오'를 누르지 못했습니다: %s" % text[:60])
                if already:
                    raise AlreadySaved(text)
                raise StepError("예/아니오 팝업 → '아니오' (저장 안 함): %s" % text[:80])
            if self.cfg.get("stop_on_popup", False):
                self.log("팝업 감지: %s" % text, "error")
                raise PopupStop(text, after_save)
            failed = any(k in text.lower() for k in keywords)
            self.log("확인창: %s" % text, "warn" if failed else "info")
            if not self.cfg.get("auto_close_dialogs", True):
                return text if failed else "확인창이 떠 있습니다: " + text
            w.activate(h)
            w.press("ENTER")
            self.mark()
            self.sleep(0.6)
            if failed:
                return text

    def do_bulk_delete(self, screen, hwnd, pid, baseline, item):
        """Action ▸ 일괄삭제 → 확인창의 [검사번호] 가 이 건과 정확히 같을 때만 '예'.
        다르면 '아니오' 후 실패. AMIS 를 앞으로 가져왔으면 True."""
        cfg = self.cfg
        menu_name = cfg.get("delete_menu_name", "일괄삭제")
        activated = False
        if not w.is_foreground(hwnd):
            if not w.activate(hwnd):
                raise StepError("AMIS 창을 앞으로 가져오지 못해 삭제하지 않았습니다")
            activated = True
            self.mark()
            self.sleep(0.2)
        self.check_user()

        # 1) Action 버튼
        self.phase("일괄삭제: Action 메뉴 열기")
        btn = uia.find_visible(screen, cfg.get("action_button_name", "Action"))
        if btn is None:
            raise StepError("병리결과입력 화면에서 Action 버튼을 찾지 못해 삭제하지 않았습니다")
        if not self.real_click(btn):
            raise StepError("Action 버튼을 누르지 못해 삭제하지 않았습니다")

        # 2) 메뉴의 '일괄삭제' (메뉴는 화면 안 또는 별도 창에 뜰 수 있음)
        self.sleep(float(cfg.get("del_action_wait", 0.5)))
        menu = None
        menu_deadline = time.monotonic() + float(cfg.get("del_menu_timeout", 3.0))
        while time.monotonic() < menu_deadline:
            for h in [hwnd] + w.list_popups(pid, exclude=hwnd):
                menu = uia.find_visible(uia.control_from_handle(h), menu_name)
                if menu is not None:
                    break
            if menu is not None:
                break
            self.sleep(0.15)
        if menu is None:
            w.press("ESC")
            raise StepError("Action 메뉴에서 '%s' 을(를) 찾지 못해 삭제하지 않았습니다" % menu_name)
        self.phase("일괄삭제: 메뉴 선택")
        if not self.real_click(menu):
            w.press("ESC")
            raise StepError("'%s' 메뉴를 누르지 못해 삭제하지 않았습니다" % menu_name)

        # 3) 확인창: [검사번호] 일치 확인 후 '예'
        self.phase("일괄삭제: 확인창 확인")
        target = "".join(item.code.split()).upper()
        dlg_h, text, yes, no_btn = None, "", None, None
        deadline = time.monotonic() + float(cfg.get("del_confirm_wait", 4.0))
        while time.monotonic() < deadline and dlg_h is None:
            yn = self.find_yesno(pid, hwnd, baseline)
            if yn is not None and yn["yes"] is not None:
                dlg_h, text, yes, no_btn = yn["h"], yn["text"], yn["yes"], yn["no"]
                break
            time.sleep(0.2)
        if yes is None:
            raise StepError("일괄삭제 확인창(예/아니오)이 뜨지 않았습니다 (삭제 안 됨)")
        self.log("  일괄삭제 확인창 내용: %s" % text, "info")
        codes = ["".join(c.split()).upper() for c in re.findall(r"\[([^\]]+)\]", text)]
        if codes and target not in codes:
            self.press_button(dlg_h, no_btn)
            raise StepError("확인창의 검사번호(%s)가 이 건과 달라 '아니오' (삭제 안 함)" % ", ".join(codes))
        if not codes:
            # 확인창 글자를 못 읽은 경우: 지금 화면에 이 번호가 조회돼 있는지 다시 확인하고 진행
            field2, scr2 = uia.find_field(hwnd, cfg)
            cur = "".join((uia.get_value(field2) or "").split()).upper() if field2 is not None else ""
            if cur != target or uia.find_showing(scr2, item.code, exclude=field2, grid_only=True) is None:
                self.press_button(dlg_h, no_btn)
                raise StepError("확인창 번호를 읽지 못했고 화면 번호(%s)도 확인되지 않아 '아니오' (삭제 안 함)"
                                % (cur or "없음"))
            self.log("  확인창 번호는 못 읽었지만 화면에 %s 가 조회돼 있음을 확인" % item.code, "warn")
        self.log("  → [예]", "warn")
        if not self.press_button(dlg_h, yes):
            raise StepError("확인창의 '예'를 누르지 못했습니다 (삭제 여부 AMIS 에서 확인)")
        self.mark()

        # 4) 이후 알림창 처리 (예/아니오 창은 '아니오', 실패 문구면 실패)
        err = self.handle_dialogs(pid, hwnd, baseline, wait=float(cfg.get("del_after_wait", 4.0)))
        if err:
            raise StepError("삭제 후 알림: " + err)
        return activated

    def clear_leftover_popups(self, pid, hwnd):
        """작업 시작 전에 남아 있는 팝업 정리. 예/아니오 창은 '아니오'로 닫고, 다른 팝업이 남아 있으면 시작하지 않음.
        (남은 팝업 위에 다음 번호를 입력하면 Enter 가 '예'를 눌러 다시 저장될 수 있음)"""
        for _ in range(3):
            yn = self.find_yesno(pid, hwnd)
            if yn is not None:
                if not self.press_button(yn["h"], yn["no"]):
                    raise StepError("AMIS 에 닫히지 않은 예/아니오 팝업이 있어 시작하지 않았습니다: %s" % yn["text"][:60])
                self.log("남아 있던 예/아니오 팝업 → [아니오]: %s" % yn["text"], "warn")
                continue
            left = self._popups(pid, hwnd, set(), set())
            if not left:
                return
            h = left[0]
            text = self.popup_text(h)
            dlg = uia.control_from_handle(h) if uia.available() else None
            no_btn = uia.has_button(dlg, self.NO_NAMES) if dlg is not None else None
            if no_btn is None or not self.press_no(h, no_btn):
                raise StepError("AMIS 에 닫히지 않은 팝업이 있어 시작하지 않았습니다: %s" % text[:60])
            self.log("남아 있던 예/아니오 팝업 → [아니오]: %s" % text, "warn")
        raise StepError("AMIS 팝업이 계속 남아 있어 시작하지 않았습니다")
'''

_SOURCES['gui'] = r'''"""AMIS 3.0 화면 스타일의 메인 창 / 축소창."""
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from . import __version__
from . import uia
from . import win32 as w


def _uia_safe(fn, default=""):
    try:
        v = fn()
        return default if v is None else v
    except Exception:
        return default


from .config import DEFAULTS, data_path, load_config, save_config
from .hangul import looks_like_accession, normalize_code
from .models import WAIT, RUN, DONE, FAIL, Store
from .worker import Worker

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:  # 미리보기만 비활성화
    Image = None

FONT_NAME = "맑은 고딕"
F = (FONT_NAME, 9)
F_B = (FONT_NAME, 9, "bold")

# AMIS 3.0 화면에서 가져온 색상
C = {
    "bg": "#f4f6f9",
    "panel": "#ffffff",
    "line": "#e1e6ec",
    "titlebar": "#7fa2c6",       # 최상단 AMIS 3.0 바
    "header": "#eef1f5",         # 화면 제목줄
    "teal": "#4a8fdb",           # 주 강조색 (시작 버튼, 진행바, 탭 밑줄)
    "teal_dark": "#2f6fb8",
    "accent": "#e8f1fc",         # 현재 검사번호 카드
    "blue": "#e8f1fc",           # 진행 단계 카드
    "sub": "#f0f2f5",            # 소제목 칩
    "grid_head": "#f5f7fa",
    "red": "#e0453a",
    "pink": "#fde8e8",
    "text": "#1f2937",
    "muted": "#8a94a3",
    "btn": "#eef1f5",
    "btn_hover": "#e2e7ee",
    "select": "#dbeafe",
    "save": "#b9d82e",           # Action ▸ 저장[F9] 색
}

STATUS_STYLE = {
    WAIT: ("○ 대기중", "#ffffff", "#555555"),
    RUN: ("▶ 진행중", "#fff4bf", "#7a5c00"),
    DONE: ("● 저장완료", "#e3f4dc", "#2e7d32"),
    FAIL: ("✕ 저장실패", "#fde1e1", "#c62828"),
}

INPUT_METHODS = [("uia", "UI 자동화 · AutomationId (권장)"), ("paste", "붙여넣기"), ("unicode", "문자 직접입력"), ("keys", "키보드 키입력"),
                 ("message", "메시지 직접전송 (백그라운드)")]
KEY_SENDS = [("auto", "자동 (가능하면 백그라운드)"), ("message", "메시지 (백그라운드)"),
             ("keyboard", "키보드 (AMIS 앞으로)")]
TEST_TEXT = "26-T -000000"
CLEAR_METHODS = [("home_end", "Home → Shift+End 삭제"), ("ctrl_a", "Ctrl+A 삭제"),
                 ("backspace", "Backspace 반복")]


def _btn(parent, text, cmd, bg=None, fg=None, width=None, bold=False, outline=False, **kw):
    """평평한 버튼 (테두리 없음, 마우스를 올리면 살짝 진해짐). outline=True 면 흰 바탕 + 얇은 테두리."""
    base = bg or ("#ffffff" if outline else C["btn"])
    hover = C["teal_dark"] if bg == C["teal"] else (C["btn_hover"] if not bg or outline else bg)
    b = tk.Button(parent, text=text, command=cmd, font=F_B if bold else F,
                  bg=base, fg=fg or C["text"], activebackground=hover,
                  activeforeground=fg or C["text"], relief="solid" if outline else "flat",
                  bd=1 if outline else 0, highlightthickness=0, cursor="hand2", padx=14, pady=5,
                  disabledforeground="#b8c0cc", **kw)
    if outline:
        b.config(highlightbackground=C["line"])
    b.bind("<Enter>", lambda e: b["state"] != "disabled" and b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=base))
    if width:
        b.config(width=width)
    return b


class PreviewThread(threading.Thread):
    """AMIS 창을 주기적으로 캡처해 미리보기 이미지를 만든다 (GUI 멈춤 방지용 별도 스레드)."""

    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.sizes = {}          # name -> (w, h)
        self.result = None       # (dict name->PIL image, title, timestamp)
        self.lock = threading.Lock()
        self.running = True

    def run(self):
        while self.running:
            interval = max(300, int(self.app.cfg.get("preview_interval_ms", 800))) / 1000.0
            try:
                self.capture_once()
            except Exception:
                pass
            time.sleep(interval)

    def capture_once(self):
        if Image is None:
            return
        sizes = dict(self.sizes)
        if not sizes:
            return
        hwnd = w.find_window(self.app.cfg.get("window_keyword", "AMIS"))
        if not hwnd:
            with self.lock:
                self.result = ({}, None, time.time())
            return
        cap = w.capture_window(hwnd)
        if not cap:
            return
        cw, ch, raw = cap
        img = Image.frombuffer("RGB", (cw, ch), raw, "raw", "BGRX", 0, 1)
        off = self.app.cfg.get("field_offset")
        if off:
            d = ImageDraw.Draw(img)
            x, y = off
            r = max(10, cw // 120)
            d.ellipse((x - r * 3, y - r * 2, x + r * 3, y + r * 2), outline=(230, 30, 30), width=max(2, r // 3))
        images = {}
        for name, (tw, th) in sizes.items():
            if tw < 20 or th < 20:
                continue
            scale = min(tw / cw, th / ch)
            images[name] = img.resize((max(1, int(cw * scale)), max(1, int(ch * scale))), Image.BILINEAR)
        with self.lock:
            self.result = (images, w.window_title(hwnd), time.time())

    def take(self):
        with self.lock:
            r, self.result = self.result, None
        return r


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.store = Store(data_path("qr_list.json"))
        self.del_store = Store(data_path("delete_list.json"))
        self.del_worker = None
        self.events = queue.Queue()
        self.worker = None
        self.mini = None
        self.photos = {}
        self.current_code = None
        self.log_dir = data_path("logs")
        os.makedirs(self.log_dir, exist_ok=True)

        root.title("결과입력 자동 프로그램 v%s" % __version__)
        root.geometry("1240x780")
        root.minsize(980, 620)
        root.configure(bg=C["bg"])
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._init_style()
        self._build()
        self.reload_tree()
        self.update_summary()
        self._fit_window()
        self._full_min = False
        self.timer = None
        self.root.after(1000, self._time_tick)
        self.apply_on_top()
        root.bind("<Unmap>", self._on_unmap, add="+")
        root.bind("<Map>", self._on_map, add="+")

        self.preview = PreviewThread(self)
        self.preview.start()
        root.after(100, self.poll_events)
        root.after(300, self.poll_preview)
        root.after(1000, self.poll_amis)
        root.after(1500, self.check_privilege)
        self.qr_entry.focus_set()

    # ================================================================ 스타일
    def _init_style(self):
        s = ttk.Style(self.root)
        s.theme_use("clam")
        s.configure(".", font=F, background=C["bg"])
        sc = max(1.0, self.root.winfo_fpixels("1i") / 96.0)
        s.configure("Treeview", font=F, rowheight=int(28 * sc), background=C["panel"],
                    fieldbackground=C["panel"], bordercolor=C["line"], borderwidth=0,
                    lightcolor=C["line"], darkcolor=C["line"])
        s.configure("Treeview.Heading", font=F, background=C["grid_head"], foreground=C["text"],
                    relief="flat", borderwidth=0, padding=(4, int(6 * sc)))
        s.map("Treeview.Heading", background=[("active", "#eceff3")])
        s.map("Treeview", background=[("selected", C["select"])], foreground=[("selected", C["text"])])
        # 탭: 기본 탭 모양은 숨기고, 밑줄 탭을 직접 그림 (_build_tabbar)
        s.configure("Flat.TNotebook", background=C["panel"], borderwidth=0, tabmargins=0,
                    bordercolor=C["panel"], lightcolor=C["panel"], darkcolor=C["panel"])
        s.layout("Flat.TNotebook.Tab", [])
        s.configure("TNotebook", background=C["bg"], borderwidth=0, tabmargins=(2, 4, 2, 0))
        s.configure("TNotebook.Tab", font=F, padding=(12, 3), background="#eef1f5",
                    foreground=C["text"], bordercolor=C["line"])
        s.map("TNotebook.Tab", background=[("selected", C["panel"])],
              foreground=[("selected", C["teal_dark"])])
        s.configure("AMIS.Horizontal.TProgressbar", troughcolor="#eef1f5",
                    background=C["teal"], bordercolor="#eef1f5", lightcolor=C["teal"],
                    darkcolor=C["teal"], thickness=int(6 * sc))
        s.configure("TCombobox", font=F)
        s.configure("TCheckbutton", font=F, background=C["panel"])
        s.configure("TSpinbox", font=F)

    # ================================================================ 화면 구성
    def _build(self):
        root = self.root
        # --- 최상단 바 (AMIS 3.0) --------------------------------------
        top = tk.Frame(root, bg=C["titlebar"], height=26)
        top.pack(fill="x")
        tk.Label(top, text="AMIS 3.0", bg=C["titlebar"], fg="white",
                 font=(FONT_NAME, 10, "bold")).pack(side="left", padx=8)
        tk.Label(top, text="│  결과입력 자동 프로그램", bg=C["titlebar"], fg="#eef3f6", font=F).pack(side="left")
        self.amis_lbl = tk.Label(top, text="AMIS 연결 확인중…", bg=C["titlebar"], fg="white", font=F)
        self.amis_lbl.pack(side="right", padx=10)

        # --- 화면 제목줄 ----------------------------------------------
        hdr = tk.Frame(root, bg=C["header"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="결과입력 자동 프로그램  [ 검사의뢰서 QR 태그 → 병리결과입력 기본값 저장(F9) ]",
                 bg=C["header"], fg=C["text"], font=F_B).pack(side="left", padx=12, pady=8)
        self.clock_lbl = tk.Label(hdr, text="", bg=C["header"], fg=C["muted"], font=F)
        self.clock_lbl.pack(side="right", padx=12)

        # --- 상단 정보줄 (형광 검사번호 / 접수 칸 / 건수 / 버튼) ---------
        info = tk.Frame(root, bg=C["bg"])
        info.pack(fill="x", padx=12, pady=(10, 0))

        # 현재 단계 카드 (작업 중이면 검사번호 + 단계)
        card = tk.Frame(info, bg=C["blue"])
        card.pack(side="left", fill="y", ipadx=6, ipady=4)
        self.code_lbl = tk.Label(card, text="", bg=C["blue"], fg="#16425b", font=(FONT_NAME, 18, "bold"),
                                 anchor="w", padx=10)
        self.code_lbl.pack(side="left")
        self.phase_lbl = tk.Label(card, text="대기", bg=C["blue"], fg="#16425b",
                                  font=(FONT_NAME, 15, "bold"), width=22, anchor="w", padx=10)
        self.phase_lbl.pack(side="left", fill="y")

        counts = tk.Frame(info, bg=C["bg"])
        counts.pack(side="left", padx=14)
        self.count_vars = {}
        for col, (key, label, color) in enumerate([("total", "전체", C["text"]), (DONE, "저장완료", "#2e9b4f"),
                                                  (WAIT, "대기중", "#4b5563"), (FAIL, "저장실패", C["red"])]):
            cell = tk.Frame(counts, bg="white", highlightbackground=C["line"], highlightthickness=1)
            cell.grid(row=0, column=col, padx=4)
            tk.Label(cell, text=label, bg="white", fg=color, font=F).pack(padx=16, pady=(4, 0))
            v = tk.StringVar(value="0")
            tk.Label(cell, textvariable=v, bg="white", fg=color, font=(FONT_NAME, 14, "bold"),
                     width=5).pack(padx=8, pady=(0, 4))
            self.count_vars[key] = v

        btns = tk.Frame(info, bg=C["bg"])
        btns.pack(side="right")
        self.start_btn = _btn(btns, "▶ 시작", self.start, bg=C["teal"], fg="white", bold=True, width=8)
        self.start_btn.pack(side="left", padx=3, ipady=4)
        self.pause_btn = _btn(btns, "Ⅱ 일시정지", self.pause, width=9)
        self.pause_btn.pack(side="left", padx=3, ipady=4)
        self.stop_btn = _btn(btns, "■ 정지", self.stop, width=6)
        self.stop_btn.pack(side="left", padx=3, ipady=4)
        self._build_action_button(btns).pack(side="left", padx=(6, 0), ipady=4)

        # --- QR 입력줄 -------------------------------------------------
        qr = tk.Frame(root, bg=C["bg"])
        qr.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(qr, text="QR 태그", bg=C["bg"], font=F_B).pack(side="left", padx=(4, 10))
        self.qr_var = tk.StringVar()
        self.qr_entry = tk.Entry(qr, textvariable=self.qr_var, font=(FONT_NAME, 13, "bold"), width=24,
                                 relief="flat", bd=0, bg="white", highlightthickness=1,
                                 highlightcolor=C["teal"], highlightbackground="#c9d3df")
        self.qr_entry.pack(side="left", padx=4, ipady=6)
        self._placeholder(self.qr_entry, self.qr_var, "QR코드를 태그하세요")
        for seq in ("<Return>", "<KP_Enter>", "<Tab>"):
            self.qr_entry.bind(seq, self.on_qr_enter)
        _btn(qr, "추가", lambda: self.on_qr_enter(None)).pack(side="left", padx=2)
        self.qr_msg = tk.Label(qr, text="QR코드를 태그하면 아래 목록에 추가됩니다.", bg=C["bg"],
                               fg=C["red"], font=F)
        self.qr_msg.pack(side="left", padx=12)
        _btn(qr, "실패항목 재시도", self.retry_failed, bg=C["pink"], fg=C["red"]).pack(side="right", padx=4)

        # --- 진행률 ----------------------------------------------------
        prog = tk.Frame(root, bg=C["bg"])
        prog.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(prog, text="작업진행", bg=C["bg"], font=F_B).pack(side="left", padx=(4, 10))
        self.progress = ttk.Progressbar(prog, style="AMIS.Horizontal.TProgressbar", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True, padx=4)
        self.prog_lbl = tk.Label(prog, text="0 / 0  (0%)", bg=C["bg"], font=F_B, width=14)
        self.prog_lbl.pack(side="left", padx=6)
        self.time_lbl = tk.Label(prog, text="", bg=C["bg"], fg="#2f6fb8", font=F_B, anchor="w")
        self.time_lbl.pack(side="left", padx=(4, 4))

        # --- 본문: 좌 (목록/설정/로그) | 우 (작업화면) -------------------
        body = tk.PanedWindow(root, orient="horizontal", bg=C["bg"], sashwidth=8, bd=0)
        body.pack(fill="both", expand=True, padx=12, pady=10)

        left = tk.Frame(body, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        self.tabbar = tk.Frame(left, bg=C["panel"])
        self.tabbar.pack(fill="x", padx=10, pady=(4, 0))
        tk.Frame(left, bg=C["line"], height=1).pack(fill="x")
        self.nb = ttk.Notebook(left, style="Flat.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.nb.add(self._build_list_tab(self.nb), text="QR 리스트")
        self.nb.add(self._build_settings_tab(self.nb), text="설정")
        self.nb.add(self._build_log_tab(self.nb), text="작업 로그")
        self.nb.add(self._build_delete_tab(self.nb), text="일괄 삭제")
        self._build_tabbar(["QR 리스트", "설정", "작업 로그", "일괄 삭제"])
        body.add(left, minsize=520, width=max(640, getattr(self, "list_req_w", 640)))

        right = tk.Frame(body, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        body.add(right, minsize=300)
        rh = tk.Frame(right, bg=C["panel"])
        rh.pack(fill="x", padx=8, pady=(6, 4))
        _btn(rh, "축소창", self.open_mini, outline=True).pack(side="right", padx=2)
        self.ontop_var = tk.BooleanVar(value=bool(self.cfg.get("always_on_top", True)))
        tk.Checkbutton(rh, text="AMIS 위에 표시", variable=self.ontop_var, command=self.apply_on_top,
                       bg=C["panel"], fg=C["text"], selectcolor="white", activebackground=C["panel"],
                       font=F).pack(side="right", padx=6)
        tk.Label(rh, text="☑ 작업 화면 (AMIS 실시간)", bg=C["panel"], fg=C["text"], font=F, anchor="w").pack(
            side="left", padx=2, fill="x", expand=True)
        self.preview_cv = tk.Canvas(right, bg="#eceff3", highlightthickness=1,
                                    highlightbackground=C["line"], width=300, height=200)
        self.preview_cv.pack(fill="both", expand=True, padx=10, pady=(4, 6))
        self.show_preview_text("AMIS 화면을 불러오는 중…" if Image else
                               "미리보기를 사용하려면 Pillow 설치가 필요합니다\n(pip install pillow)")
        self.preview_info = tk.Label(right, text="", bg=C["panel"], fg=C["muted"], font=F, anchor="w")
        self.preview_info.pack(fill="x", padx=10, pady=(0, 8))

        # --- 상태바 ----------------------------------------------------
        self.status_lbl = tk.Label(root, text="준비", bg="#eef1f5", fg=C["text"], font=F, anchor="w",
                                   relief="flat", bd=0, padx=10, pady=4)
        self.status_lbl.pack(fill="x", side="bottom")

        self.tick_clock()

    def _build_tabbar(self, names):
        """밑줄 탭 (선택된 탭은 파란 글자 + 파란 밑줄)."""
        self.tab_items = []
        for i, name in enumerate(names):
            box = tk.Frame(self.tabbar, bg=C["panel"], cursor="hand2")
            box.pack(side="left", padx=(0, 6))
            lbl = tk.Label(box, text=name, bg=C["panel"], fg=C["muted"], font=F, padx=10, pady=6,
                           cursor="hand2")
            lbl.pack()
            bar = tk.Frame(box, bg=C["panel"], height=3)
            bar.pack(fill="x")
            for wdg in (box, lbl):
                wdg.bind("<Button-1>", lambda e, k=i: self.nb.select(k))
            self.tab_items.append((lbl, bar))
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._sync_tabbar(), add="+")
        self._sync_tabbar()

    def _sync_tabbar(self):
        try:
            cur = self.nb.index("current")
        except tk.TclError:
            return
        for i, (lbl, bar) in enumerate(self.tab_items):
            on = i == cur
            lbl.config(fg=C["teal"] if on else C["muted"], font=F_B if on else F)
            bar.config(bg=C["teal"] if on else C["panel"])

    def _placeholder(self, entry, var, text):
        """비어 있을 때 회색 안내 글자."""
        normal_font = entry.cget("font")

        def show(_=None):
            if not var.get():
                entry.config(fg="#a8b1bd", font=(FONT_NAME, 11))
                var.set(text)
                entry._ph = True

        def hide(_=None):
            if getattr(entry, "_ph", False):
                entry._ph = False
                var.set("")
                entry.config(fg=C["text"], font=normal_font)

        def on_key(e):
            if getattr(entry, "_ph", False) and (e.char and e.char.isprintable() or e.keysym in ("BackSpace", "Delete")):
                hide()

        def after_change(*_):
            if not var.get() and not getattr(entry, "_ph", False):
                entry.after(10, show)

        entry.bind("<KeyPress>", on_key, add="+")
        entry.bind("<FocusOut>", show, add="+")
        var.trace_add("write", after_change)
        entry._ph_text = text
        show()

    def _build_action_button(self, parent):
        mb = tk.Menubutton(parent, text="Action ▾", font=F, bg=C["btn"], relief="flat", bd=0,
                           activebackground=C["btn_hover"], padx=14, pady=5, cursor="hand2")
        m = tk.Menu(mb, tearoff=0, font=F)
        m.add_command(label="  자동저장 시작", command=self.start, background=C["save"])
        m.add_command(label="  일시정지 / 재개", command=self.pause)
        m.add_command(label="  정지", command=self.stop)
        m.add_separator()
        m.add_command(label="  실패항목 재시도", command=self.retry_failed)
        m.add_command(label="  선택항목 대기로 되돌리기", command=self.reset_selected)
        m.add_command(label="  선택항목 삭제", command=self.delete_selected)
        m.add_command(label="  저장완료 항목 정리", command=lambda: self.clear_items((DONE,)))
        m.add_command(label="  전체 삭제", command=lambda: self.clear_items(None))
        m.add_separator()
        m.add_command(label="  검사번호 칸 위치 지정", command=self.calibrate)
        m.add_command(label="  UI 요소 찾기 (AutomationId)", command=self.inspect_uia)
        m.add_command(label="  진단 / 입력 테스트", command=self.diagnose)
        m.add_command(label="  관리자 권한으로 다시 실행", command=self.restart_admin)
        m.add_command(label="  축소창", command=self.open_mini)
        mb.config(menu=m)
        return mb

    def _build_list_tab(self, parent):
        f = tk.Frame(parent, bg=C["panel"])
        bar = tk.Frame(f, bg=C["panel"])
        bar.pack(fill="x", pady=(4, 2))
        sub = tk.Label(bar, text="검사의뢰서 QR 태그 목록", bg=C["sub"], fg=C["text"], font=F_B, padx=10, pady=4)
        sub.pack(side="left", padx=4)
        _btn(bar, "전체삭제", lambda: self.clear_items(None)).pack(side="right", padx=3)
        _btn(bar, "완료정리", lambda: self.clear_items((DONE,))).pack(side="right", padx=3)
        self.sel_btns = [_btn(bar, "삭제", self.delete_selected), _btn(bar, "대기로", self.reset_selected)]
        for b in self.sel_btns:
            b.pack(side="right", padx=3)
            b.config(state="disabled")

        from .config import parse_extra_checks
        self.check_cols = [hdr for hdr, _ in parse_extra_checks(self.cfg.get("extra_checks"))]
        if self.cfg.get("vaginal_col"):
            self.check_cols.append(self.cfg.get("vaginal_col"))
        from .config import parse_radio_actions
        self.check_groups = {}
        for hdr, _, grp in parse_radio_actions(self.cfg.get("radio_actions")):
            self.check_cols.append(hdr)
            if grp:
                self.check_groups[hdr] = grp
        order = [x.strip() for x in str(self.cfg.get("check_order", "")).split(",") if x.strip()]
        self.check_cols.sort(key=lambda h: order.index(h) if h in order else len(order))
        legend = tk.Label(f, bg=C["panel"], fg=C["muted"], font=F, anchor="w", justify="left",
                          text="체크 칸: Urine <30ml · UC absent · Inst 10~20 · Inst <10 = URINE  ·  "
                               "Cell block 부적합 = NGYN  ·  Vaginal = GYN  (Inst 두 칸은 하나만, 체크 안 하면 기본값 저장)")
        legend.pack(fill="x", padx=6, pady=(0, 2))
        ck_ids = ["ck%d" % i for i in range(len(self.check_cols))]
        cols = ("no", "code", *ck_ids, "status", "time", "note")
        tf = tk.Frame(f, bg=C["panel"])
        tf.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="extended")
        col_specs = [("no", "No", 44, "center"), ("code", "검사번호", 150, "center")]
        col_specs += [(cid, hdr, max(90, 12 * len(hdr)), "center") for cid, hdr in zip(ck_ids, self.check_cols)]
        col_specs += [("status", "상태", 100, "center"), ("time", "처리시각", 80, "center"), ("note", "비고", 240, "w")]
        sc = max(1.0, self.root.winfo_fpixels("1i") / 96.0)      # 화면 배율(125/150%) 반영
        self.list_req_w = 0
        for c, text, width, anchor in col_specs:
            width = int(width * sc)
            self.list_req_w += width
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, minwidth=int(40 * sc), anchor=anchor, stretch=(c == "note"))
        self.list_req_w += int(40 * sc)                           # 스크롤바·여백
        for st, (_, bg, fg) in STATUS_STYLE.items():
            self.tree.tag_configure(st, background=bg, foreground=fg)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Button-3>", self.on_tree_menu)
        self.tree.bind("<Button-1>", self.on_tree_click, add="+")
        self.tree.bind("<<TreeviewSelect>>", lambda e: [b.config(state="normal" if self.tree.selection() else "disabled")
                                                        for b in self.sel_btns], add="+")
        self.empty_lbl = tk.Label(self.tree, text="📭\n표시할 데이터가 없습니다.", bg=C["panel"], fg=C["muted"],
                                  font=(FONT_NAME, 11), justify="center")
        self.tree.bind("<Configure>", lambda e: self.schedule_overlays(), add="+")
        self.tree.bind("<MouseWheel>", lambda e: self.schedule_overlays(), add="+")
        self.tree.bind("<ButtonRelease-1>", lambda e: self.schedule_overlays(), add="+")
        self._yset = sb.set
        self.tree.configure(yscrollcommand=lambda a, b: (self._yset(a, b), self.schedule_overlays()))
        self.overlays = []
        self._overlay_job = None

        self.tree_menu = tk.Menu(self.root, tearoff=0, font=F)
        self.tree_menu.add_command(label="대기중으로 되돌리기", command=self.reset_selected)
        self.tree_menu.add_command(label="삭제", command=self.delete_selected)
        return f

    def _build_settings_tab(self, parent):
        holder = tk.Frame(parent, bg=C["panel"])
        cv = tk.Canvas(holder, bg=C["panel"], highlightthickness=0)
        sb = ttk.Scrollbar(holder, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        outer = tk.Frame(cv, bg=C["panel"])
        win_id = cv.create_window((0, 0), window=outer, anchor="nw")
        outer.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win_id, width=e.width))
        wheel = lambda e: cv.yview_scroll(int(-e.delta / 120) or (-1 if e.num == 4 else 1), "units")
        holder.bind("<Enter>", lambda e: (cv.bind_all("<MouseWheel>", wheel),
                                          cv.bind_all("<Button-4>", wheel), cv.bind_all("<Button-5>", wheel)))
        holder.bind("<Leave>", lambda e: (cv.unbind_all("<MouseWheel>"),
                                          cv.unbind_all("<Button-4>"), cv.unbind_all("<Button-5>")))
        self.vars = {}

        def section(title):
            box = tk.Frame(outer, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
            box.pack(fill="x", padx=6, pady=(6, 0))
            tk.Label(box, text=" " + title, bg=C["sub"], font=F_B, anchor="w").pack(fill="x")
            inner = tk.Frame(box, bg=C["panel"])
            inner.pack(fill="x", padx=6, pady=4)
            return inner

        def row(inner, r, label, widget, hint=""):
            tk.Label(inner, text=label, bg=C["panel"], font=F, anchor="w", width=16).grid(
                row=r, column=0, sticky="w", pady=2)
            widget.grid(row=r, column=1, sticky="w", pady=2)
            if hint:
                tk.Label(inner, text=hint, bg=C["panel"], fg=C["muted"], font=F).grid(
                    row=r, column=2, sticky="w", padx=6)

        def spin(key, frm, to, inc):
            v = tk.StringVar(value=str(self.cfg[key]))
            self.vars[key] = v
            return ttk.Spinbox(inner, textvariable=v, from_=frm, to=to, increment=inc, width=7)

        def check(inner_, key, text):
            v = tk.BooleanVar(value=bool(self.cfg[key]))
            self.vars[key] = v
            return ttk.Checkbutton(inner_, text=text, variable=v)

        def entry(inner_, key, width):
            v = tk.StringVar(value=str(self.cfg.get(key) or ""))
            self.vars[key] = v
            return tk.Entry(inner_, textvariable=v, width=width, relief="solid", bd=1)

        # 0. UI 자동화 (AutomationId)
        inner = section("병리결과입력 화면 · UI 자동화 (AutomationId)")
        row(inner, 0, "창 제목 포함 글자", entry(inner, "window_keyword", 20), "예) AMIS")
        row(inner, 1, "화면 ID", entry(inner, "screen_code", 20), "병리결과입력 화면")
        row(inner, 2, "검사번호 입력창 ID", entry(inner, "uia_field_id", 28), "AutomationId")
        row(inner, 3, "화면 컨테이너 ID", entry(inner, "uia_screen_id", 28), "AutomationId (선택)")
        uf = tk.Frame(inner, bg=C["panel"])
        _btn(uf, "UI 요소 찾기", self.inspect_uia, bg=C["teal"], fg="white", bold=True).pack(side="left")
        _btn(uf, "찾기 테스트", self.test_uia).pack(side="left", padx=4)
        _btn(uf, "진단 / 입력 테스트", self.diagnose, bg=C["pink"], fg=C["red"]).pack(side="left")
        row(inner, 4, "", uf)
        tk.Label(inner, text="※ [UI 요소 찾기] 후 5초 안에 마우스를 AMIS 검사번호 입력창 위에 올려 두면 ID가 자동 저장됩니다."
                 if uia.available() else "※ uiautomation 모듈이 없습니다: pip install uiautomation",
                 bg=C["panel"], fg=C["red"], font=F, wraplength=560, justify="left").grid(
            row=5, column=0, columnspan=3, sticky="w")
        self.keysend_cb = ttk.Combobox(inner, state="readonly", width=24, values=[t for _, t in KEY_SENDS])
        self.keysend_cb.set(dict(KEY_SENDS).get(self.cfg.get("key_send"), KEY_SENDS[0][1]))
        row(inner, 6, "Enter / F9 전송", self.keysend_cb)
        dff = tk.Frame(inner, bg=C["panel"])
        check(dff, "check_default", "저장 전 기본값 선택 확인:").pack(side="left")
        entry(dff, "default_name", 28).pack(side="left", padx=4)
        dff.grid(row=7, column=0, columnspan=3, sticky="w", pady=(2, 0))
        row(inner, 8, "목록 체크박스 컬럼", entry(inner, "extra_checks", 60),
            "제목=AMIS 체크박스 이름 앞부분, 여러 개는 | 로 구분 (재시작 후 반영)")
        row(inner, 9, "목록 라디오 변경 컬럼", entry(inner, "radio_actions", 60),
            "제목=클릭할 라디오 이름 앞부분@묶음, | 로 구분 (재시작 후 반영)")

        # 1. 좌표 방식 (보조)
        inner = section("좌표 방식 (UI 자동화가 안 될 때 보조)")
        posf = tk.Frame(inner, bg=C["panel"])
        self.offset_lbl = tk.Label(posf, text=self._offset_text(), bg="white", relief="solid", bd=1,
                                   width=14, font=F)
        self.offset_lbl.pack(side="left")
        _btn(posf, "위치 지정", self.calibrate, bg=C["teal"], fg="white").pack(side="left", padx=4)
        _btn(posf, "위치 확인", self.test_position).pack(side="left")
        row(inner, 1, "검사번호 칸", posf)
        tk.Label(inner, text="※ AMIS 화면의 노란색 검사번호 칸 위치를 한 번 지정해 두면 됩니다.",
                 bg=C["panel"], fg=C["red"], font=F).grid(row=2, column=0, columnspan=3, sticky="w")

        # 2. 타이밍
        inner = section("작업 타이밍 (초)")
        row(inner, 0, "사용자 미사용 대기", spin("idle_seconds", 1, 600, 1),
            "이 시간 동안 키보드/마우스 입력이 없을 때만 진행")
        row(inner, 1, "조회 대기", spin("load_wait", 0.5, 30, 0.5), "검사번호 입력 후 화면 로딩 대기")
        row(inner, 2, "저장 대기", spin("save_wait", 0.5, 30, 0.5), "F9 저장 후 대기")
        row(inner, 3, "항목 간격", spin("item_interval", 0, 30, 0.5))
        row(inner, 4, "실패 시 재시도", spin("max_retries", 0, 5, 1), "회")
        row(inner, 5, "저장 후 팝업 대기", spin("dialog_wait", 0, 30, 0.5),
            "F9 후 '저장된 결과입니다' 팝업을 기다리는 최대 시간 (짧을수록 빠름)")

        # 일괄 삭제 타이밍
        inner = section("일괄 삭제 타이밍 (초)")
        row(inner, 0, "조회 대기", spin("del_load_wait", 0.5, 30, 0.5), "검사번호 입력 후 화면 로딩 대기")
        row(inner, 1, "Action 메뉴 대기", spin("del_action_wait", 0, 10, 0.1), "Action 버튼 누른 뒤 메뉴가 펼쳐질 때까지")
        row(inner, 2, "메뉴 찾기 최대", spin("del_menu_timeout", 0.5, 30, 0.5), "'일괄삭제' 메뉴를 찾는 최대 시간")
        row(inner, 3, "확인창 대기 최대", spin("del_confirm_wait", 0.5, 30, 0.5), "'일괄삭제 하시겠습니까?' 창이 뜰 때까지")
        row(inner, 4, "삭제 후 대기", spin("del_after_wait", 0, 30, 0.5), "'예' 누른 뒤 완료/오류 알림 확인")
        row(inner, 5, "항목 간격", spin("del_item_interval", 0, 30, 0.5), "삭제 항목 사이")

        # 3. 입력 / 저장 방식
        inner = section("입력 / 저장 방식")
        self.input_cb = ttk.Combobox(inner, state="readonly", width=20, values=[t for _, t in INPUT_METHODS])
        self.input_cb.set(dict(INPUT_METHODS).get(self.cfg["input_method"], INPUT_METHODS[0][1]))
        row(inner, 0, "검사번호 입력 방식", self.input_cb, "UI 자동화 권장 (좌표 불필요)")
        self.clear_cb = ttk.Combobox(inner, state="readonly", width=20, values=[t for _, t in CLEAR_METHODS])
        self.clear_cb.set(dict(CLEAR_METHODS).get(self.cfg["clear_method"], CLEAR_METHODS[0][1]))
        row(inner, 1, "기존 내용 지우기", self.clear_cb)
        self.savekey_cb = ttk.Combobox(inner, state="readonly", width=8,
                                       values=["F9", "F6"] + ["F%d" % i for i in range(1, 13) if i not in (6, 9)])
        self.savekey_cb.set(self.cfg["save_key"])
        row(inner, 2, "저장 키", self.savekey_cb, "Action ▸ 저장 [F9]")
        checks = tk.Frame(inner, bg=C["panel"])
        checks.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))
        for i, (key, text) in enumerate([("press_enter", "입력 후 Enter 로 조회 (권장)"),
                                         ("check_loaded", "F9 전 조회 결과 확인 (이전 검사 재저장 방지)"),
                                         ("auto_close_dialogs", "확인/알림창 자동 처리(Enter)"),
                                         ("restore_focus", "작업 후 원래 사용하던 창으로 복귀"),
                                         ("fix_hangul", "한글 상태 스캔 자동 보정 (ㅊ→C)"),
                                         ("uppercase", "검사번호 대문자 변환")]):
            check(checks, key, text).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 16))

        # 4. 실패 판단
        inner = section("저장실패 판단")
        v = tk.StringVar(value=self.cfg["fail_keywords"])
        self.vars["fail_keywords"] = v
        row(inner, 0, "실패 메시지 단어", tk.Entry(inner, textvariable=v, width=44, relief="solid", bd=1))
        tk.Label(inner, text="조회/저장 후 뜬 알림창에 위 단어(쉼표 구분)가 있으면 저장실패로 처리합니다.",
                 bg=C["panel"], fg=C["muted"], font=F).grid(row=1, column=0, columnspan=3, sticky="w")

        bf = tk.Frame(outer, bg=C["panel"])
        bf.pack(fill="x", padx=6, pady=8)
        _btn(bf, "설정 저장", self.save_settings, bg=C["save"], bold=True).pack(side="left")
        _btn(bf, "기본값", self.default_settings).pack(side="left", padx=4)
        return holder

    # ================================================================ 일괄 삭제 탭
    DEL_LABEL = {WAIT: "○ 대기중", RUN: "▶ 진행중", DONE: "● 삭제완료", FAIL: "✕ 삭제실패"}

    def _build_delete_tab(self, parent):
        f = tk.Frame(parent, bg=C["panel"])
        warn = tk.Label(f, bg="#fde1e1", fg=C["red"], font=F_B, anchor="w", justify="left", padx=8, pady=4,
                        text="⚠ 여기 목록의 검사번호는 AMIS 병리결과입력 ▸ Action ▸ '일괄삭제' 로 결과가 삭제됩니다. "
                             "되돌릴 수 없습니다.\n   확인창의 [검사번호] 가 목록 번호와 정확히 같을 때만 '예'를 누르고, "
                             "다르면 '아니오'를 누릅니다.")
        warn.pack(fill="x", padx=4, pady=(4, 2))

        qr = tk.Frame(f, bg=C["panel"])
        qr.pack(fill="x", padx=4, pady=2)
        tk.Label(qr, text="삭제할 QR 태그", bg=C["panel"], font=F_B).pack(side="left")
        self.del_qr_var = tk.StringVar()
        ent = tk.Entry(qr, textvariable=self.del_qr_var, width=24, font=(FONT_NAME, 12), relief="solid", bd=1,
                       bg="#fff0f0")
        ent.pack(side="left", padx=6)
        for seq in ("<Return>", "<KP_Enter>"):
            ent.bind(seq, self.on_del_qr_enter)
        self.del_msg = tk.Label(qr, text="", bg=C["panel"], font=F)
        self.del_msg.pack(side="left", padx=6)

        bar = tk.Frame(f, bg=C["panel"])
        bar.pack(fill="x", padx=4, pady=2)
        self.del_start_btn = _btn(bar, "▶ 삭제 시작", self.start_delete, bg=C["red"], fg="white", bold=True)
        self.del_start_btn.pack(side="left")
        _btn(bar, "■ 정지", self.stop_delete).pack(side="left", padx=4)
        _btn(bar, "전체삭제", lambda: self.clear_del_items(None)).pack(side="right", padx=2)
        _btn(bar, "완료정리", lambda: self.clear_del_items((DONE,))).pack(side="right", padx=2)
        _btn(bar, "목록에서 삭제", self.remove_del_selected).pack(side="right", padx=2)
        _btn(bar, "대기로", self.reset_del_selected).pack(side="right", padx=2)

        tf = tk.Frame(f, bg=C["panel"])
        tf.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        cols = ("no", "code", "status", "time", "note")
        self.del_tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="extended")
        for c, text, width, anchor in [("no", "No", 44, "center"), ("code", "검사번호", 150, "center"),
                                       ("status", "상태", 100, "center"), ("time", "처리시각", 80, "center"),
                                       ("note", "비고", 300, "w")]:
            self.del_tree.heading(c, text=text)
            self.del_tree.column(c, width=width, anchor=anchor, stretch=(c == "note"))
        for st, (_, bg, fg) in STATUS_STYLE.items():
            self.del_tree.tag_configure(st, background=bg, foreground=fg)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.del_tree.yview)
        self.del_tree.configure(yscrollcommand=sb.set)
        self.del_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.reload_del_tree()
        return f

    def _del_values(self, idx, item):
        return (idx, item.code, self.DEL_LABEL[item.status], item.time or "", item.note or "")

    def reload_del_tree(self):
        self.del_tree.delete(*self.del_tree.get_children())
        for i, item in enumerate(self.del_store.snapshot(), 1):
            self.del_tree.insert("", "end", iid=str(item.id), values=self._del_values(i, item), tags=(item.status,))

    def refresh_del_row(self, item_id):
        item = self.del_store.get(item_id)
        iid = str(item_id)
        if item is None or not self.del_tree.exists(iid):
            return
        self.del_tree.item(iid, values=self._del_values(self.del_tree.index(iid) + 1, item), tags=(item.status,))
        if item.status == RUN:
            self.del_tree.see(iid)

    def on_del_qr_enter(self, _event):
        raw = self.del_qr_var.get()
        self.del_qr_var.set("")
        code = normalize_code(raw, self.cfg.get("fix_hangul", True), self.cfg.get("uppercase", True),
                              self.cfg.get("amis_space", True))
        if not code:
            return "break"
        raw_qr = normalize_code(raw, self.cfg.get("fix_hangul", True), self.cfg.get("uppercase", True), False)
        item = self.del_store.add(code, raw_qr)
        if item is None:
            self.root.bell()
            self.del_msg.config(text="이미 목록에 있는 검사번호입니다: %s" % code, fg=C["red"])
        else:
            self.reload_del_tree()
            self.del_tree.see(str(item.id))
            self.del_msg.config(text="삭제 목록에 추가됨: %s" % code, fg=C["red"])
            self.log("일괄삭제 목록 추가: %s" % code)
        return "break"

    def _del_selected_ids(self):
        return [int(i) for i in self.del_tree.selection()]

    def remove_del_selected(self):
        if self.del_worker_alive():
            return
        ids = self._del_selected_ids()
        if ids:
            self.del_store.remove(ids)
            self.reload_del_tree()

    def reset_del_selected(self):
        if self.del_worker_alive():
            return
        for i in self._del_selected_ids():
            it = self.del_store.get(i)
            if it is not None and it.status == FAIL:
                self.del_store.update(it, status=WAIT, note="", tries=0)
        self.reload_del_tree()

    def clear_del_items(self, statuses):
        if self.del_worker_alive():
            return
        what = "전체 항목" if statuses is None else "삭제완료 항목"
        if messagebox.askyesno("확인", "%s을(를) 삭제 목록에서 지울까요?\n(AMIS 결과와는 상관없이 목록만 지웁니다)" % what,
                               parent=self.root):
            self.del_store.clear(statuses)
            self.reload_del_tree()

    def del_worker_alive(self):
        return self.del_worker is not None and self.del_worker.is_alive()

    def _confirm_delete(self, n):
        """되돌릴 수 없는 작업이라 '삭제' 를 직접 입력해야 시작."""
        win = tk.Toplevel(self.root)
        win.title("일괄삭제 확인")
        win.configure(bg=C["panel"])
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="AMIS 결과 %d건을 '일괄삭제' 합니다.\n되돌릴 수 없습니다.\n\n계속하려면 아래에 '삭제' 를 입력하세요." % n,
                 bg=C["panel"], fg=C["red"], font=F_B, justify="left").pack(padx=16, pady=(12, 6))
        v = tk.StringVar()
        e = tk.Entry(win, textvariable=v, width=12, font=(FONT_NAME, 12), relief="solid", bd=1)
        e.pack(pady=4)
        e.focus_set()
        ok = {"v": False}

        def go(_=None):
            ok["v"] = v.get().strip() == "삭제"
            win.destroy()

        e.bind("<Return>", go)
        bf = tk.Frame(win, bg=C["panel"])
        bf.pack(pady=(4, 12))
        _btn(bf, "확인", go, bg=C["red"], fg="white", bold=True).pack(side="left", padx=4)
        _btn(bf, "취소", win.destroy).pack(side="left", padx=4)
        self.root.wait_window(win)
        return ok["v"]

    def start_delete(self):
        if self.worker_alive() or self.del_worker_alive():
            messagebox.showwarning("작업 중", "다른 작업이 진행 중입니다. 끝난 뒤 시작하세요.", parent=self.root)
            return
        self.apply_settings(silent=True)
        if not uia.available() or not self.cfg.get("uia_field_id"):
            messagebox.showwarning("설정 필요", "UI 자동화 설정(검사번호 입력창 ID)이 필요합니다.", parent=self.root)
            return
        n = sum(1 for it in self.del_store.snapshot() if it.status == WAIT)
        if not n:
            self.del_msg.config(text="대기중인 삭제 항목이 없습니다.", fg=C["red"])
            return
        if not self._confirm_delete(n):
            self.log("일괄삭제를 취소했습니다.")
            return

        def emit_del(kind, **d):
            self.events.put(({"item": "del_item", "state": "del_state"}.get(kind, kind), d))

        self.del_worker = Worker(self.del_store, self.cfg, emit_del, mode="delete")
        self.del_worker.start()

    def stop_delete(self):
        if self.del_worker_alive():
            self.del_worker.stop()

    def _build_log_tab(self, parent):
        f = tk.Frame(parent, bg=C["panel"])
        self.log_text = tk.Text(f, font=("Consolas", 9), bg="white", relief="flat", wrap="word",
                                state="disabled")
        sb = ttk.Scrollbar(f, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)
        for tag, color in (("ok", "#2e7d32"), ("warn", "#a66b00"), ("error", C["red"]), ("info", "#333")):
            self.log_text.tag_configure(tag, foreground=color)
        return f

    # ================================================================ QR 입력 / 목록
    def on_qr_enter(self, _event):
        if getattr(self.qr_entry, "_ph", False):
            return "break"
        raw = self.qr_var.get()
        self.qr_var.set("")
        code = normalize_code(raw, self.cfg.get("fix_hangul", True), self.cfg.get("uppercase", True),
                              self.cfg.get("amis_space", True))
        if not code:
            return "break"
        raw_qr = normalize_code(raw, self.cfg.get("fix_hangul", True), self.cfg.get("uppercase", True), False)
        item = self.store.add(code, raw_qr)
        if item is None:
            self.root.bell()
            self.flash_msg("이미 목록에 있는 검사번호입니다: %s" % code, C["red"])
        else:
            self.insert_row(item)
            self.tree.see(str(item.id))
            warn = "" if looks_like_accession(code) else "  (검사번호 형식 확인 필요)"
            self.flash_msg("추가됨: %s%s" % (code, warn), "#2e7d32" if not warn else "#a66b00")
            self.log("QR 태그: %s%s" % (code, warn))
            self.update_summary()
        return "break"

    def flash_msg(self, text, color):
        self.qr_msg.config(text=text, fg=color)

    def _fit_window(self):
        """화면 구성에 필요한 크기로 창을 맞추고, 모니터보다 크면 모니터에 맞춤."""
        r = self.root
        r.update_idletasks()
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        need_w = max(r.winfo_reqwidth(), int(1240 * r.winfo_fpixels("1i") / 96.0))
        need_h = max(r.winfo_reqheight(), int(780 * r.winfo_fpixels("1i") / 96.0))
        w_, h_ = min(need_w, sw - 20), min(need_h, sh - 80)
        r.minsize(min(r.winfo_reqwidth(), sw - 20), min(r.winfo_reqheight(), sh - 80))
        r.geometry("%dx%d+%d+%d" % (w_, h_, max(0, (sw - w_) // 2), max(0, (sh - h_) // 2 - 20)))
        if need_w > sw - 20 or need_h > sh - 80:
            try:
                r.state("zoomed")
            except tk.TclError:
                pass

    def _row_values(self, idx, item):
        marks = tuple("☑" if item.checks.get(h) else "☐" for h in self.check_cols)
        return (idx, item.code, *marks, STATUS_STYLE[item.status][0], item.time or "", item.note or "")

    # 체크 칸마다 색 (체크되면 그 칸이 해당 색으로 칠해져 어느 열인지 바로 보임)
    CHECK_COLORS = ["#cfe8ff", "#ffd9b3", "#ffd1e3", "#d4f2d0", "#e3d9ff", "#fff2a8", "#d9f0f0"]

    def check_color(self, idx):
        return self.CHECK_COLORS[idx % len(self.CHECK_COLORS)]

    def schedule_overlays(self):
        if getattr(self, "_overlay_job", None):
            self.root.after_cancel(self._overlay_job)
        self._overlay_job = self.root.after(30, self.draw_overlays)

    def draw_overlays(self):
        """체크된 칸 위에 색깔 칸(☑)을 덮어 그림 (ttk 표는 칸별 색을 지원하지 않아서)."""
        self._overlay_job = None
        for lbl in self.overlays:
            lbl.destroy()
        self.overlays = []
        if self.tree.get_children():
            self.empty_lbl.place_forget()
        else:
            self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")
        if not self.check_cols:
            return
        for iid in self.tree.get_children():
            item = self.store.get(int(iid))
            if item is None:
                continue
            for idx, hdr in enumerate(self.check_cols):
                if not item.checks.get(hdr):
                    continue
                box = self.tree.bbox(iid, "ck%d" % idx)
                if not box:
                    continue
                x, y, bw, bh = box
                lbl = tk.Label(self.tree, text="☑ " + hdr, bg=self.check_color(idx), fg="#1d3557",
                               font=F_B, bd=0, cursor="hand2")
                lbl.place(x=x + 1, y=y + 1, width=bw - 2, height=bh - 2)
                lbl.bind("<Button-1>", lambda e, i=iid, k=idx: self.toggle_cell(i, k))
                lbl.bind("<MouseWheel>", lambda e: self.tree.yview_scroll(int(-e.delta / 120), "units"))
                self.overlays.append(lbl)

    def on_tree_click(self, event):
        """체크박스 컬럼 칸을 누르면 체크/해제 (대기중 항목만)."""
        if self.tree.identify_region(event.x, event.y) != "cell":
            return None
        col = self.tree.identify_column(event.x)          # '#1', '#2' ...
        iid = self.tree.identify_row(event.y)
        try:
            idx = int(col[1:]) - 3                          # No, 검사번호 다음부터 체크 컬럼
        except ValueError:
            return None
        if not iid or not (0 <= idx < len(self.check_cols)):
            return None
        self.toggle_cell(iid, idx)
        return "break"

    def toggle_cell(self, iid, idx):
        key = self.check_cols[idx]
        val = self.store.toggle_check(int(iid), key)
        if val and key in self.check_groups:       # 같은 묶음(Instrumented urine)은 하나만
            others = {k: False for k, g in self.check_groups.items() if g == self.check_groups[key] and k != key}
            if others:
                self.store.set_checks(int(iid), others)
        if val is None:
            self.log("대기중인 항목만 체크를 바꿀 수 있습니다.", "warn")
        else:
            self.refresh_row(int(iid))
            self.tree.selection_set(iid)
        self.schedule_overlays()

    def insert_row(self, item):
        idx = len(self.tree.get_children()) + 1
        self.tree.insert("", "end", iid=str(item.id), values=self._row_values(idx, item), tags=(item.status,))
        self.schedule_overlays()

    def reload_tree(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.store.snapshot():
            self.insert_row(item)
        self.schedule_overlays()

    def refresh_row(self, item_id):
        item = self.store.get(item_id)
        iid = str(item_id)
        if item is None or not self.tree.exists(iid):
            return
        idx = self.tree.index(iid) + 1
        self.tree.item(iid, values=self._row_values(idx, item), tags=(item.status,))
        if item.status == RUN:
            self.tree.see(iid)
        self.schedule_overlays()

    def selected_ids(self):
        return [int(i) for i in self.tree.selection()]

    def on_tree_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid and iid not in self.tree.selection():
            self.tree.selection_set(iid)
        self.tree_menu.tk_popup(event.x_root, event.y_root)

    def delete_selected(self):
        ids = self.selected_ids()
        if ids:
            self.store.remove(ids)
            self.reload_tree()
            self.update_summary()

    def reset_selected(self):
        ids = self.selected_ids()
        if ids:
            self.store.reset(ids=set(ids))
            self.reload_tree()
            self.update_summary()

    def retry_failed(self):
        self.store.reset(statuses=(FAIL,))
        self.reload_tree()
        self.update_summary()
        self.log("실패 항목을 대기중으로 되돌렸습니다.")

    def clear_items(self, statuses):
        what = "전체 항목" if statuses is None else "저장완료 항목"
        if not messagebox.askyesno("확인", "%s을(를) 목록에서 지울까요?" % what, parent=self.root):
            return
        self.store.clear(statuses)
        self.reload_tree()
        self.update_summary()

    def update_summary(self):
        c = self.store.counts()
        for k, v in self.count_vars.items():
            v.set(str(c.get(k, 0)))
        total = c["total"]
        finished = c[DONE] + c[FAIL]
        pct = int(finished * 100 / total) if total else 0
        self.progress["value"] = pct
        self.prog_lbl.config(text="%d / %d  (%d%%)" % (finished, total, pct))
        if self.mini:
            self.mini.update_progress(finished, total, pct, c)

    # ================================================================ 작업 제어
    def worker_alive(self):
        return self.worker is not None and self.worker.is_alive()

    def start(self):
        if self.del_worker_alive():
            messagebox.showwarning("작업 중", "일괄 삭제 작업이 진행 중입니다.", parent=self.root)
            return
        if self.worker_alive():
            if self.worker.paused:
                self.worker.resume()
                self.log("작업을 재개합니다.")
            return
        self.apply_settings(silent=True)
        if self.cfg.get("input_method") == "uia":
            if not uia.available():
                messagebox.showerror("모듈 필요", "UI 자동화를 쓰려면 uiautomation 모듈이 필요합니다.\n"
                                     "pip install uiautomation", parent=self.root)
                return
            if not self.cfg.get("uia_field_id"):
                messagebox.showwarning("입력창 ID 필요", "먼저 [설정] 탭에서 [UI 요소 찾기] 로\n"
                                       "AMIS 검사번호 입력창을 지정해 주세요.", parent=self.root)
                self.nb.select(1)
                return
        elif not self.cfg.get("field_offset"):
            messagebox.showwarning("위치 지정 필요",
                                   "먼저 [설정] 탭에서 AMIS 검사번호 칸 위치를 지정해 주세요.", parent=self.root)
            self.nb.select(1)
            return
        if self.store.next_pending() is None:
            self.flash_msg("대기중인 항목이 없습니다.", C["red"])
            return
        self.worker = Worker(self.store, self.cfg, self.emit)
        self.worker.start()

    def pause(self):
        if not self.worker_alive():
            return
        if self.worker.paused:
            self.worker.resume()
            self.log("작업을 재개합니다.")
        else:
            self.worker.pause()
            self.log("일시정지 요청.")

    def stop(self):
        if self.worker_alive():
            self.worker.stop()

    def emit(self, kind, **data):
        self.events.put((kind, data))

    def poll_events(self):
        try:
            while True:
                kind, d = self.events.get_nowait()
                if kind == "item":
                    self.refresh_row(d["id"])
                    self.update_summary()
                elif kind == "phase":
                    self.set_phase(d["text"])
                elif kind == "log":
                    self.log(d["text"], d.get("level", "info"))
                elif kind == "current":
                    self.current_code = d["code"]
                    self.code_lbl.config(text=d["code"] or "")
                    if self.mini:
                        self.mini.set_code(d["code"])
                elif kind == "state":
                    self.on_state(d["state"])
                elif kind == "amis":
                    self.set_amis(d["found"])
                elif kind == "call":
                    d["fn"](*d.get("args", ()))
                elif kind == "del_item":
                    self.refresh_del_row(d["id"])
                elif kind == "del_state":
                    running = d["state"] in ("running", "paused")
                    self.del_start_btn.config(text="● 삭제 중" if running else "▶ 삭제 시작",
                                              state="disabled" if running else "normal",
                                              disabledforeground="white")
                elif kind == "popup":
                    self.root.bell()
                    messagebox.showwarning(
                        "팝업 발생 - 작업 중지",
                        "[%s] 처리 중 AMIS 에 팝업이 떠서 작업을 중지했습니다.\n\n%s\n\n%s" % (
                            d["code"], d["text"][:300],
                            "※ 저장(F9) 이후에 뜬 팝업입니다. AMIS 에서 저장 여부를 확인해 주세요."
                            if d.get("after_save") else "※ 저장(F9) 전이라 저장되지 않았습니다."),
                        parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_events)

    # ================================================================ 소요시간 / 예상 소요시간
    @staticmethod
    def _hms(sec):
        sec = int(max(0, sec))
        h, m, s_ = sec // 3600, sec % 3600 // 60, sec % 60
        return "%d:%02d:%02d" % (h, m, s_) if h else "%d:%02d" % (m, s_)

    def _timer_state(self, state):
        """작업 시작/일시정지/재개/종료 시 시간 기록 (일시정지 시간은 소요시간에서 뺌)."""
        now = time.monotonic()
        t = getattr(self, "timer", None)
        if state == "running":
            if t is None or t.get("end"):
                c = self.store.counts()
                self.timer = {"start": now, "paused": 0.0, "pause_at": None, "end": None,
                              "done0": c[DONE] + c[FAIL]}
            elif t.get("pause_at"):
                t["paused"] += now - t["pause_at"]
                t["pause_at"] = None
        elif state == "paused" and t and not t.get("pause_at"):
            t["pause_at"] = now
        elif state in ("done", "stopped") and t and not t.get("end"):
            if t.get("pause_at"):
                t["paused"] += now - t["pause_at"]
                t["pause_at"] = None
            t["end"] = now
            elapsed = now - t["start"] - t["paused"]
            c = self.store.counts()
            n = c[DONE] + c[FAIL] - t["done0"]
            if n > 0:
                avg = elapsed / n
                self.cfg["avg_sec_per_item"] = round(avg, 1)
                save_config(self.cfg)
                self.log("총 소요시간 %s · %d건 처리 · 1건 평균 %.1f초" % (self._hms(elapsed), n, avg), "ok")
        self._time_update()

    def _time_tick(self):
        try:
            self._time_update()
        except Exception:
            pass
        self.root.after(1000, self._time_tick)

    def _time_update(self):
        c = self.store.counts()
        remain = c[WAIT] + c.get(RUN, 0)
        t = getattr(self, "timer", None)
        avg = float(self.cfg.get("avg_sec_per_item", 15.0) or 15.0)
        if t and not t.get("end"):
            now = t["pause_at"] or time.monotonic()
            elapsed = now - t["start"] - t["paused"]
            n = c[DONE] + c[FAIL] - t["done0"]
            if n > 0:
                avg = elapsed / n                       # 이번 작업의 실제 평균으로 예상
            text = "소요 %s  ·  남은 예상 %s" % (self._hms(elapsed), self._hms(avg * remain) if remain else "0:00")
            if t.get("pause_at"):
                text += "  (일시정지)"
        elif t and t.get("end"):
            text = "소요 %s" % self._hms(t["end"] - t["start"] - t["paused"])
            if remain:
                text += "  ·  남은 %d건 예상 %s" % (remain, self._hms(avg * remain))
        else:
            text = ("예상 소요 %s (%d건 × 약 %.0f초)" % (self._hms(avg * remain), remain, avg)) if remain else ""
        self.time_lbl.config(text=text)
        if self.mini:
            self.mini.set_time(text)

    def on_state(self, state):
        self._timer_state(state)
        if state == "running":
            self.start_btn.config(text="● 작업중", state="disabled", disabledforeground="white")
            self.pause_btn.config(text="Ⅱ 일시정지")
            self.status("자동 저장 진행중 – AMIS를 사용하시면 잠시 멈췄다가 %s초 후 이어서 진행합니다."
                        % self._fmt(self.cfg.get("idle_seconds")))
        elif state == "paused":
            self.pause_btn.config(text="▶ 재개")
            self.status("일시정지됨")
        else:
            self.start_btn.config(text="▶ 시작", state="normal")
            self.pause_btn.config(text="Ⅱ 일시정지")
            self.set_phase("완료" if state == "done" else "정지")
            self.status("모든 항목 처리 완료" if state == "done" else "정지됨")
            self.update_summary()
            if state == "done":
                c = self.store.counts()
                self.root.bell()
                if self.mini is None:
                    messagebox.showinfo("작업 완료", "저장완료 %d건 / 저장실패 %d건" % (c[DONE], c[FAIL]),
                                        parent=self.root)
        if self.mini:
            self.mini.on_state(state)

    def set_phase(self, text):
        self.phase_lbl.config(text=text)
        if self.mini:
            self.mini.set_phase(text)

    def status(self, text):
        self.status_lbl.config(text="  " + text)

    def log(self, text, level="info"):
        line = "[%s] %s" % (time.strftime("%H:%M:%S"), text)
        self.log_text.config(state="normal")
        self.log_text.insert("end", line + "\n", level)
        if int(self.log_text.index("end-1c").split(".")[0]) > 3000:
            self.log_text.delete("1.0", "500.0")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        try:
            with open(os.path.join(self.log_dir, time.strftime("%Y-%m-%d") + ".log"), "a",
                      encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    # ================================================================ AMIS 연결 / 미리보기
    def set_amis(self, found):
        self.amis_lbl.config(text="AMIS 연결: ● 연결됨" if found else "AMIS 연결: ○ 창 없음",
                             fg="white" if found else "#ffd6d6")

    def poll_amis(self):
        self.set_amis(bool(w.find_window(self.cfg.get("window_keyword", "AMIS"))) if w.IS_WINDOWS else False)
        self.root.after(3000, self.poll_amis)

    def poll_preview(self):
        sizes = {"main": (self.preview_cv.winfo_width(), self.preview_cv.winfo_height())}
        if self.mini:
            sizes["mini"] = self.mini.preview_size()
        self.preview.sizes = sizes
        r = self.preview.take()
        if r is not None:
            images, title, ts = r
            if not images:
                self.show_preview_text("AMIS 창을 찾을 수 없습니다.\n"
                                       "AMIS를 실행하거나 [설정]의 창 제목을 확인하세요.")
                self.photos.pop("main", None)
                if self.mini:
                    self.mini.set_preview(None)
            else:
                if "main" in images:
                    self.photos["main"] = ImageTk.PhotoImage(images["main"])
                    cv = self.preview_cv
                    cv.delete("all")
                    cv.create_image(cv.winfo_width() // 2, cv.winfo_height() // 2,
                                    image=self.photos["main"], anchor="center")
                if self.mini and "mini" in images:
                    self.photos["mini"] = ImageTk.PhotoImage(images["mini"])
                    self.mini.set_preview(self.photos["mini"])
                self.preview_info.config(text="%s  ·  갱신 %s  ·  빨간 원 = 검사번호 입력 위치"
                                         % (title, time.strftime("%H:%M:%S", time.localtime(ts))))
        self.root.after(250, self.poll_preview)

    def show_preview_text(self, text):
        cv = self.preview_cv
        cv.delete("all")
        cv.create_text(max(cv.winfo_width(), 300) // 2, max(cv.winfo_height(), 200) // 2,
                       text=text, fill=C["muted"], font=F, justify="center")

    def tick_clock(self):
        self.clock_lbl.config(text=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.tick_clock)

    # ================================================================ 위치 지정
    def _offset_text(self):
        off = self.cfg.get("field_offset")
        return "X %d, Y %d" % tuple(off) if off else "미지정"

    def calibrate(self):
        if self.worker_alive():
            messagebox.showinfo("안내", "작업을 정지한 뒤 위치를 지정해 주세요.", parent=self.root)
            return
        if not messagebox.askokcancel(
                "검사번호 칸 위치 지정",
                "[확인]을 누른 뒤 5초 안에 마우스 커서를\nAMIS 화면의 노란색 검사번호 칸 위에 올려 두세요.\n\n"
                "(클릭할 필요는 없습니다)", parent=self.root):
            return
        self._countdown(5)

    def _countdown(self, n):
        if n > 0:
            self.set_phase("위치 지정 %d…" % n)
            self.status("마우스를 AMIS 검사번호 칸 위에 올려 두세요… %d" % n)
            self.root.after(1000, self._countdown, n - 1)
            return
        x, y = w.get_cursor_pos()
        hwnd = w.find_window(self.cfg.get("window_keyword", "AMIS"))
        if not hwnd:
            self.set_phase("대기")
            messagebox.showerror("오류", "AMIS 창을 찾을 수 없습니다.", parent=self.root)
            return
        l, t, r, b = w.get_window_rect(hwnd)
        if not (l <= x < r and t <= y < b):
            self.set_phase("대기")
            messagebox.showerror("오류", "마우스가 AMIS 창 밖에 있습니다. 다시 시도해 주세요.", parent=self.root)
            return
        self.cfg["field_offset"] = [x - l, y - t]
        save_config(self.cfg)
        self.offset_lbl.config(text=self._offset_text())
        self.set_phase("위치 저장됨")
        self.status("검사번호 칸 위치가 저장되었습니다. 오른쪽 작업화면의 빨간 원을 확인하세요.")
        ctrl = w.control_at(hwnd, x, y)
        self.log("검사번호 칸 위치 지정: %s · 컨트롤 [%s] 내용 '%s'" % (
            self._offset_text(), w.class_name(ctrl), (w.get_control_text(ctrl) or "")[:30]))

    # ================================================================ UI 자동화 (AutomationId)
    def inspect_uia(self):
        if not uia.available():
            messagebox.showerror("모듈 필요", "pip install uiautomation 후 다시 실행해 주세요.", parent=self.root)
            return
        if self.worker_alive():
            messagebox.showinfo("안내", "작업을 정지한 뒤 실행해 주세요.", parent=self.root)
            return
        self.apply_settings(silent=True)
        if not messagebox.askokcancel(
                "UI 요소 찾기",
                "[확인]을 누른 뒤 5초 안에 마우스 커서를\nAMIS 병리결과입력 화면의 [검사번호 입력창] 위에 올려 두세요.\n\n"
                "(평소 QR 을 태그하는 그 입력칸입니다. 클릭할 필요는 없습니다)", parent=self.root):
            return
        self._inspect_countdown(5)

    def _inspect_countdown(self, n):
        if n > 0:
            self.set_phase("요소 찾기 %d…" % n)
            self.status("마우스를 AMIS 검사번호 입력창 위에 올려 두세요… %d" % n)
            self.root.after(1000, self._inspect_countdown, n - 1)
            return
        x, y = w.get_cursor_pos()
        self.set_phase("요소 분석 중")
        threading.Thread(target=self._inspect_thread, args=(x, y), daemon=True).start()

    def _inspect_thread(self, x, y):
        lines = []
        add = lines.append
        save = {}
        with uia.thread_init():
            try:
                ctrl = uia.control_from_point(x, y)
                add("[UI 요소 찾기] 마우스 위치 %d, %d" % (x, y))
                add("선택 요소: %s" % uia.describe(ctrl))
                add("현재 값: '%s'" % (uia.get_value(ctrl) or ""))
                screen = uia.pick_screen(ctrl, self.cfg.get("screen_code"))
                add("")
                add("[상위 요소]")
                for i, a in enumerate(uia.ancestors(ctrl)):
                    add("  %s%s%s" % ("  " * min(i, 10), uia.describe(a),
                        "   ◀ 화면" if screen is not None and _uia_safe(lambda: a.AutomationId) == _uia_safe(lambda: screen.AutomationId) else ""))
                aid = (ctrl.AutomationId if ctrl is not None else "") or ""
                ctype = _uia_safe(lambda: ctrl.ControlTypeName) if ctrl is not None else ""
                if ctrl is not None and ctype == "EditControl" and (not aid or aid.isdigit()):
                    # 입력칸 안쪽 편집상자가 잡힌 경우 → 이름 있는 상위 입력칸으로 올라감
                    for a in uia.ancestors(ctrl):
                        a_id = _uia_safe(lambda: a.AutomationId) or ""
                        if _uia_safe(lambda: a.ControlTypeName) == "EditControl" and a_id and not a_id.isdigit():
                            add("ℹ 안쪽 편집상자가 잡혀 상위 입력칸 '%s' 로 보정했습니다." % a_id)
                            aid = a_id
                            break
                    else:
                        aid = ""
                elif ctrl is not None and ctype != "EditControl":
                    add("⚠ 선택된 요소가 입력칸(EditControl)이 아닙니다: %s → 저장하지 않음" % ctype)
                    aid = ""
                elif aid.isdigit():
                    add("⚠ 숫자 ID('%s')는 실행할 때마다 바뀌는 창 번호라 저장하지 않습니다." % aid)
                    aid = ""
                add("")
                if screen is None:
                    add("⚠ 상위 요소 중 화면 ID '%s' 가 포함된 요소를 찾지 못했습니다." % self.cfg.get("screen_code"))
                if not aid:
                    add("⚠ 이 요소에는 AutomationId 가 없습니다. 입력칸 정중앙에 마우스를 두고 다시 시도하거나,")
                    add("   아래 [화면 안의 입력칸 목록] 에서 검사번호 값이 들어 있는 칸의 ID 를 직접 입력하세요.")
                else:
                    scope = screen or uia.control_from_handle(
                        w.find_window(self.cfg.get("window_keyword", "AMIS")))
                    dup = [c for c in uia.list_edits(scope, 300) if (c.AutomationId or "") == aid] if scope else []
                    if len(dup) > 1:
                        add("⚠ 같은 AutomationId 를 가진 입력칸이 %d개 있습니다 (첫 번째 것이 사용됨)." % len(dup))
                    save["uia_field_id"] = aid
                    save["uia_screen_id"] = (screen.AutomationId if screen is not None else "") or ""
                    add("✔ 저장: 검사번호 입력창 ID = '%s', 화면 컨테이너 ID = '%s'"
                        % (save["uia_field_id"], save["uia_screen_id"]))
                if screen is not None:
                    add("")
                    add("[화면 안의 입력칸 목록]")
                    for c in uia.list_edits(screen):
                        add("  %s  값='%s'" % (uia.describe(c), (uia.get_value(c) or "")[:30]))
            except Exception as e:
                add("오류: %r" % e)
        self.emit("call", fn=self._inspect_done, args=(lines, save))

    def _inspect_done(self, lines, save):
        for k, v in save.items():
            self.vars[k].set(v)
        if save:
            self.input_cb.set(dict(INPUT_METHODS)["uia"])
            self.apply_settings(silent=True)
            self.set_phase("입력창 ID 저장됨")
        else:
            self.set_phase("대기")
        self._show_report(lines, "UI 요소 찾기 결과")

    def test_uia(self):
        if not uia.available():
            messagebox.showerror("모듈 필요", "pip install uiautomation 후 다시 실행해 주세요.", parent=self.root)
            return
        self.apply_settings(silent=True)
        self.status("병리결과입력 화면에서 검사번호 입력창을 찾는 중…")
        threading.Thread(target=lambda: self.emit("call", fn=self._show_report,
                                                  args=(self._uia_report(), "찾기 테스트 결과")),
                         daemon=True).start()

    def _uia_report(self, test_input=False):
        """UI 자동화로 입력창/기본값 항목을 찾은 결과 (진단에도 사용)."""
        lines = []
        add = lines.append
        with uia.thread_init():
            try:
                hwnd = w.find_window(self.cfg.get("window_keyword", "AMIS"))
                if not hwnd:
                    return ["AMIS 창을 찾지 못했습니다."]
                field, screen = uia.find_field(hwnd, self.cfg)
                add("[UI 자동화]")
                add("화면(%s): %s" % (self.cfg.get("screen_code"), uia.describe(screen)))
                if screen is not None:
                    sh = uia.native_handle(screen)
                    act = w.mdi_active(sh) if sh else None
                    add("  현재 활성 화면: %s%s" % (w.window_title(act) if act else "(확인불가)",
                                               "  ✔ 병리결과입력" if act and int(act) == int(sh) else
                                               "  → 작업 시 병리결과입력으로 자동 전환"))
                add("검사번호 입력창(ID '%s'): %s" % (self.cfg.get("uia_field_id"), uia.describe(field)))
                if field is not None:
                    kt = uia.inner_edit(field)
                    kh = uia.native_handle(kt) or uia.native_handle(field)
                    add("  현재 값: '%s' · Enter/F9 받는 상자 핸들 %s → %s" % (
                        uia.get_value(field) or "", kh or "없음",
                        "백그라운드 전송 가능" if kh else "키보드 전송 필요"))
                    add("  입력 후 Enter 조회: %s" % ("켜짐" if self.cfg.get("press_enter", True) else "꺼짐"))
                for name in uia.default_names(self.cfg.get("default_name")):
                    d = uia.find_by_name(screen or uia.control_from_handle(hwnd), name)
                    st = uia.is_checked(d)
                    add("기본값 '%s': %s · 선택상태 %s" % (name, uia.describe(d),
                                                       {True: "선택됨", False: "선택 안 됨", None: "확인불가"}[st]))
                if test_input and field is not None:
                    before = uia.get_value(field) or ""
                    ok = uia.set_value(field, TEST_TEXT)
                    time.sleep(0.3)
                    after = uia.get_value(field) or ""
                    good = ok and "".join(TEST_TEXT.split()) in "".join(after.split()).upper()
                    uia.set_value(field, before)
                    add("입력 테스트 - UI 자동화: %s (넣은 뒤 값 '%s')" % ("성공" if good else "실패", after[:30]))
                    lines.append(("__result__", good))
            except Exception as e:
                add("오류: %r" % e)
        return lines

    # ================================================================ 권한 / 진단
    def check_privilege(self):
        """AMIS 가 관리자 권한이고 이 프로그램은 아니면, Windows 가 입력을 막는다 (UIPI)."""
        if not w.IS_WINDOWS or w.is_self_elevated():
            return
        hwnd = w.find_window(self.cfg.get("window_keyword", "AMIS"))
        if not hwnd:
            return
        if w.is_process_elevated(w.get_window_pid(hwnd)) is not False:
            self.log("AMIS 가 관리자 권한으로 실행 중인 것으로 보입니다. 이 프로그램도 관리자 권한이 필요합니다.",
                     "warn")
            if messagebox.askyesno(
                    "관리자 권한 필요",
                    "AMIS 가 관리자 권한으로 실행 중입니다.\n\n"
                    "이 경우 Windows 보안 정책 때문에 이 프로그램의 키 입력이 AMIS 에 전달되지 않습니다.\n"
                    "관리자 권한으로 다시 실행할까요?", parent=self.root):
                self.restart_admin()

    def restart_admin(self):
        if w.is_self_elevated():
            messagebox.showinfo("안내", "이미 관리자 권한으로 실행 중입니다.", parent=self.root)
            return
        if self.worker_alive():
            self.worker.stop()
        if w.restart_as_admin():
            self.on_close(force=True)
        else:
            messagebox.showerror("오류", "관리자 권한으로 실행하지 못했습니다.\n"
                                 "실행 파일을 마우스 오른쪽 버튼 → '관리자 권한으로 실행' 해 주세요.",
                                 parent=self.root)

    def diagnose(self):
        if self.worker_alive():
            messagebox.showinfo("안내", "작업을 정지한 뒤 진단해 주세요.", parent=self.root)
            return
        self.apply_settings(silent=True)
        do_test = messagebox.askyesno(
            "진단 / 입력 테스트",
            "AMIS 연결 상태와 검사번호 칸 정보를 확인합니다.\n\n"
            "입력 테스트도 할까요?\n(AMIS 검사번호 칸에 '%s' 를 방식별로 넣어 보고 바로 지웁니다.\n"
            " 테스트 중에는 키보드/마우스를 만지지 마세요.)" % TEST_TEXT, parent=self.root)
        self.status("진단 중… 키보드/마우스를 만지지 마세요.")
        threading.Thread(target=self._diagnose_thread, args=(do_test,), daemon=True).start()

    def _diagnose_thread(self, do_test):
        lines = []
        add = lines.append
        yn = lambda v: "확인불가(관리자 권한일 가능성 높음)" if v is None else ("예" if v else "아니오")
        add("[진단 시각] %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
        self_admin = w.is_self_elevated()
        add("이 프로그램 관리자 권한: %s" % yn(self_admin))
        hwnd = w.find_window(self.cfg.get("window_keyword", "AMIS"))
        if not hwnd:
            add("AMIS 창: 찾지 못함 (창 제목 포함 글자 '%s' 확인)" % self.cfg.get("window_keyword"))
            self.emit("call", fn=self._show_report, args=(lines,))
            return
        pid = w.get_window_pid(hwnd)
        amis_admin = w.is_process_elevated(pid)
        add("AMIS 창 제목: %s" % w.window_title(hwnd))
        add("AMIS 창 클래스: %s" % w.class_name(hwnd))
        add("AMIS 실행파일: %s (PID %d)" % (w.process_path(pid) or "확인불가", pid))
        add("AMIS 관리자 권한: %s" % yn(amis_admin))
        off = self.cfg.get("field_offset")
        ctrl = None
        if off:
            l, t, _, _ = w.get_window_rect(hwnd)
            fx, fy = l + off[0], t + off[1]
            ctrl = w.control_at(hwnd, fx, fy)
            add("검사번호 칸 위치: %s (화면 %d, %d)" % (self._offset_text(), fx, fy))
            add("검사번호 칸 컨트롤: [%s] %s · 현재 내용 '%s'" % (
                w.class_name(ctrl), "(입력칸 Edit)" if w.is_edit_like(ctrl) else "(일반 입력칸 아님)",
                (w.get_control_text(ctrl) or "")[:40]))
            if ctrl == hwnd:
                add("  → 칸이 별도 컨트롤로 잡히지 않습니다 (웹/자바/자체 그리기 화면일 수 있음)")
        else:
            add("검사번호 칸 위치: 미지정")

        results = {}
        if uia.available():
            add("")
            for line in self._uia_report(test_input=do_test):
                if isinstance(line, tuple):
                    results["uia"] = line[1]
                else:
                    add(line)
            add("")
        else:
            add("UI 자동화: uiautomation 모듈 없음 (pip install uiautomation)")
        if do_test and off and ctrl and ctrl != hwnd:
            readable = w.get_control_text(ctrl) is not None and w.is_edit_like(ctrl)
            for key, label in INPUT_METHODS[1:]:
                ok = self._test_method(hwnd, ctrl, fx, fy, key) if readable else None
                results[key] = ok
                add("입력 테스트 - %s: %s" % (label, {True: "성공", False: "실패", None: "확인불가(내용 읽기 불가)"}[ok]))
            self._clear_test(hwnd, ctrl, fx, fy)

        add("")
        add("[판단]")
        if not self_admin and amis_admin is not False:
            add("● AMIS 가 관리자 권한입니다 → 이 프로그램도 [Action ▸ 관리자 권한으로 다시 실행] 하세요.")
        ok_methods = [k for k, v in results.items() if v]
        if results and ok_methods:
            best = ok_methods[0]
            add("● 입력 성공 방식: %s → 설정에 자동 적용했습니다." % dict(INPUT_METHODS)[best])
            self.emit("call", fn=self._apply_method, args=(best,))
        elif results and not any(results.values()):
            add("● 모든 방식 실패: 키보드 보안 프로그램 또는 권한 문제 가능성이 큽니다. 이 진단 내용을 전달해 주세요.")
        elif not results and ctrl and ctrl != hwnd and not w.is_edit_like(ctrl):
            add("● 일반 입력칸이 아니라 결과를 자동 확인할 수 없습니다. 이 진단 내용을 전달해 주세요.")
        self.emit("call", fn=self._show_report, args=(lines,))

    def _test_method(self, hwnd, ctrl, fx, fy, method):
        cfg = dict(self.cfg, input_method=method)
        worker = Worker(self.store, cfg, lambda *a, **k: None)
        try:
            if method == "message":
                w.focus_control(ctrl)
                w.set_control_text(ctrl, "")
                w.set_control_text(ctrl, TEST_TEXT)
            else:
                w.activate(hwnd)
                time.sleep(0.3)
                w.click(fx, fy)
                time.sleep(0.2)
                worker.clear_field()
                worker.input_text(TEST_TEXT)
            time.sleep(0.3)
            text = w.get_control_text(ctrl) or ""
            return "".join(TEST_TEXT.split()) in "".join(text.split()).upper()
        except Exception:
            return False

    def _clear_test(self, hwnd, ctrl, fx, fy):
        w.set_control_text(ctrl, "")
        text = w.get_control_text(ctrl) or ""
        if text.strip():
            w.activate(hwnd)
            w.click(fx, fy)
            Worker(self.store, self.cfg, lambda *a, **k: None).clear_field()

    def _apply_method(self, method):
        self.input_cb.set(dict(INPUT_METHODS)[method])
        self.apply_settings(silent=True)

    def _show_report(self, lines, title="진단 결과"):
        text = "\n".join(lines)
        for line in lines:
            if line:
                self.log(title.split()[0] + " " + line)
        self.status("진단 완료")
        self.root.deiconify()
        self.root.lift()
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=C["panel"])
        win.transient(self.root)
        hdr = tk.Frame(win, bg=C["teal"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="☑ %s (아래 내용을 복사해서 전달해 주세요)" % title, bg=C["teal"], fg="white",
                 font=F_B).pack(side="left", padx=6, pady=3)
        t = tk.Text(win, font=(FONT_NAME, 9), width=90, height=20, wrap="word", relief="flat")
        t.insert("1.0", text)
        t.pack(fill="both", expand=True, padx=6, pady=6)
        bf = tk.Frame(win, bg=C["panel"])
        bf.pack(fill="x", padx=6, pady=(0, 6))

        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status("진단 결과를 복사했습니다.")

        _btn(bf, "복사", copy, bg=C["save"], bold=True).pack(side="left")
        _btn(bf, "닫기", win.destroy).pack(side="right")

    def test_position(self):
        off = self.cfg.get("field_offset")
        hwnd = w.find_window(self.cfg.get("window_keyword", "AMIS"))
        if not off or not hwnd:
            messagebox.showinfo("안내", "AMIS 창과 검사번호 칸 위치가 모두 필요합니다.", parent=self.root)
            return
        w.activate(hwnd)
        l, t, _, _ = w.get_window_rect(hwnd)
        w.set_cursor_pos(l + off[0], t + off[1])
        self.status("마우스가 지정된 검사번호 칸으로 이동했습니다 (클릭/입력은 하지 않음).")

    # ================================================================ 설정
    @staticmethod
    def _fmt(v):
        return ("%g" % float(v)) if v not in (None, "") else ""

    def apply_settings(self, silent=False):
        new = dict(self.cfg)
        try:
            for key in ("idle_seconds", "load_wait", "save_wait", "item_interval", "dialog_wait",
                        "del_load_wait", "del_action_wait", "del_menu_timeout", "del_confirm_wait",
                        "del_after_wait", "del_item_interval"):
                new[key] = max(0.0, float(self.vars[key].get()))
            new["idle_seconds"] = max(1.0, new["idle_seconds"])
            new["max_retries"] = max(0, int(float(self.vars["max_retries"].get())))
        except ValueError:
            if not silent:
                messagebox.showerror("오류", "숫자 설정값을 확인해 주세요.", parent=self.root)
            return False
        for key in ("window_keyword", "fail_keywords", "screen_code", "uia_field_id", "uia_screen_id",
                    "default_name", "extra_checks", "radio_actions"):
            if key in self.vars:
                new[key] = self.vars[key].get().strip()
        new["key_send"] = {t: k for k, t in KEY_SENDS}.get(self.keysend_cb.get(), "auto")
        for key in ("press_enter", "check_loaded", "auto_close_dialogs", "restore_focus", "fix_hangul", "uppercase",
                    "check_default"):
            new[key] = bool(self.vars[key].get())
        new["input_method"] = {t: k for k, t in INPUT_METHODS}.get(self.input_cb.get(), "uia")
        new["clear_method"] = {t: k for k, t in CLEAR_METHODS}.get(self.clear_cb.get(), "home_end")
        new["save_key"] = self.savekey_cb.get() or "F9"
        self.cfg.update(new)  # 작업 스레드와 같은 dict 를 공유 → 즉시 반영
        save_config(self.cfg)
        return True

    def save_settings(self):
        if self.apply_settings():
            self.status("설정이 저장되었습니다.")
            self.log("설정 저장")

    def default_settings(self):
        if not messagebox.askyesno("기본값", "검사번호 칸 위치/ID 를 제외한 설정을 기본값으로 되돌릴까요?",
                                   parent=self.root):
            return
        for k, v in DEFAULTS.items():
            if k in self.vars and k not in ("uia_field_id", "uia_screen_id"):
                self.vars[k].set(v if not isinstance(v, float) else self._fmt(v))
        self.input_cb.set(dict(INPUT_METHODS)[DEFAULTS["input_method"]])
        self.clear_cb.set(dict(CLEAR_METHODS)[DEFAULTS["clear_method"]])
        self.savekey_cb.set(DEFAULTS["save_key"])
        self.keysend_cb.set(dict(KEY_SENDS)[DEFAULTS["key_send"]])
        self.save_settings()

    # ================================================================ 항상 위 / 최소화
    def apply_on_top(self):
        """[AMIS 위] 체크: AMIS 를 쓰는 동안에만 프로그램 창이 AMIS 위에 보이고,
        다른 프로그램을 쓰면 일반 창처럼 그 프로그램 뒤로 간다."""
        self.cfg["always_on_top"] = bool(self.ontop_var.get())
        try:
            self.root.attributes("-topmost", False)
        except tk.TclError:
            pass
        if not getattr(self, "_z_started", False):
            self._z_started = True
            self._amis_pid, self._amis_check = None, 0.0
            self.root.after(300, self._z_tick)

    def _z_tick(self):
        try:
            self._z_update()
        except Exception:
            pass
        self.root.after(300, self._z_tick)

    def _z_update(self):
        mine = w.own_windows()
        if not mine:
            return
        if not self.cfg.get("always_on_top", True):
            for h in mine:
                if w.is_topmost(h):
                    w.set_z(h, -2)
            return
        if w.z_held():           # 작업 중 실제 클릭하는 동안은 건드리지 않음
            return
        now = time.monotonic()
        if now - self._amis_check > 2.0:
            self._amis_check = now
            ah = w.find_window(self.cfg.get("window_keyword", "AMIS"))
            self._amis_pid = w.get_window_pid(ah) if ah else None
        fg = w.get_foreground()
        fpid = w.get_window_pid(fg) if fg else None
        if fpid and (fpid == self._amis_pid or fpid == os.getpid()):
            for h in mine:                       # AMIS(또는 이 프로그램) 사용 중 → AMIS 위에
                if not w.is_topmost(h):
                    w.set_z(h, -1)
        else:
            for h in mine:                       # 다른 프로그램 사용 중 → 그 프로그램 바로 뒤로
                if w.is_topmost(h):
                    w.set_z(h, -2)
                    if fg:
                        w.set_z(h, fg)

    def _on_unmap(self, event):
        """큰 화면을 최소화하면 축소창으로 전환 (완전 최소화 중이면 그대로 작업표시줄로)."""
        if event.widget is self.root and self.mini is None and not self._full_min:
            self.root.after(80, lambda: self.root.state() == "iconic" and self.open_mini())

    def _on_map(self, event):
        if event.widget is self.root:
            self._full_min = False

    def full_minimize(self):
        """축소창까지 모두 숨기고 작업표시줄로 (작업은 계속). 작업표시줄 아이콘을 누르면 큰 화면으로 복귀."""
        self._full_min = True
        if self.mini:
            self.cfg["mini_geometry"] = self.mini.win.geometry()
            save_config(self.cfg)
            self.mini.win.destroy()
            self.mini = None
        self.root.iconify()

    # ================================================================ 축소창
    def open_mini(self):
        if self.mini is None:
            self.mini = MiniWindow(self)
            self.update_summary()
            self.mini.set_code(self.current_code)
            self.mini.set_phase(self.phase_lbl.cget("text"))
            self.mini.on_state("running" if self.worker_alive() and not self.worker.paused else
                               "paused" if self.worker_alive() else "stopped")
        self.root.iconify()

    def close_mini(self):
        if self.mini:
            self.cfg["mini_geometry"] = self.mini.win.geometry()
            save_config(self.cfg)
            self.mini.win.destroy()
            self.mini = None
        self.root.deiconify()
        self.root.lift()

    def on_close(self, force=False):
        if self.worker_alive() and not force:
            if not messagebox.askyesno("종료", "작업이 진행중입니다. 정지하고 종료할까요?", parent=self.root):
                return
            self.worker.stop()
        self.apply_settings(silent=True)
        self.preview.running = False
        self.store.save()
        self.root.destroy()


class MiniWindow:
    """항상 위에 떠 있는 작은 작업 현황창 (AMIS 작업화면 축소 미리보기 포함)."""

    PREVIEW = (360, 200)

    def __init__(self, app):
        self.app = app
        win = self.win = tk.Toplevel(app.root)
        win.title("결과입력 자동 프로그램 - 축소창")
        win.configure(bg=C["panel"])
        # 항상 위 여부는 App._z_update 가 관리 (AMIS 사용 중에만 위)
        try:
            win.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", app.close_mini)
        geo = app.cfg.get("mini_geometry") or ""
        if "+" in geo:
            win.geometry("+" + geo.split("+", 1)[1])
        else:
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            win.geometry("+%d+%d" % (sw - 420, sh - 440))

        hdr = tk.Frame(win, bg=C["titlebar"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="결과입력 자동 프로그램", bg=C["titlebar"], fg="white", font=F_B).pack(
            side="left", padx=6, pady=2)

        top = tk.Frame(win, bg=C["panel"])
        top.pack(fill="x", padx=4, pady=4)
        self.code_lbl = tk.Label(top, text="--", bg=C["accent"], font=(FONT_NAME, 15, "bold"), width=14,
                                 anchor="w", padx=6)
        self.code_lbl.pack(side="left")
        self.phase_lbl = tk.Label(top, text="", bg=C["blue"], fg="#16425b", font=F_B, anchor="w", padx=4)
        self.phase_lbl.pack(side="left", fill="both", expand=True, padx=(4, 0))

        ph = self.ph = tk.Frame(win, bg=C["teal"])
        ph.pack(fill="x", padx=4)
        tk.Label(ph, text="☑ 작업 화면", bg=C["teal"], fg="white", font=F_B).pack(side="left", padx=4)
        self.preview = tk.Label(win, bg="#dfe4e7", fg=C["muted"], font=F, text="화면 불러오는 중…",
                                width=self.PREVIEW[0], height=self.PREVIEW[1])
        # 픽셀 단위 크기 고정을 위해 이미지 없는 상태에서도 빈 이미지 사용
        self._blank = tk.PhotoImage(width=self.PREVIEW[0], height=self.PREVIEW[1])
        self.preview.config(image=self._blank, compound="center")
        self.preview.pack(padx=4, pady=(0, 4))

        pf = self.pf = tk.Frame(win, bg=C["panel"])
        pf.pack(fill="x", padx=4)
        self.bar = ttk.Progressbar(pf, style="AMIS.Horizontal.TProgressbar", maximum=100)
        self.bar.pack(side="left", fill="x", expand=True)
        self.pct_lbl = tk.Label(pf, text="0%", bg=C["panel"], font=F_B, width=12)
        self.pct_lbl.pack(side="left")
        self.count_lbl = tk.Label(win, text="", bg=C["panel"], font=F, anchor="w")
        self.count_lbl.pack(fill="x", padx=6)
        self.time_lbl = tk.Label(win, text="", bg=C["panel"], fg="#16425b", font=F_B, anchor="w")
        self.time_lbl.pack(fill="x", padx=6)

        bf = tk.Frame(win, bg=C["panel"])
        bf.pack(fill="x", padx=4, pady=4)
        self.start_btn = _btn(bf, "▶ 시작", app.start, bg=C["teal"], fg="white", bold=True)
        self.start_btn.pack(side="left")
        self.pause_btn = _btn(bf, "Ⅱ 일시정지", app.pause)
        self.pause_btn.pack(side="left", padx=2)
        _btn(bf, "■ 정지", app.stop).pack(side="left")
        _btn(bf, "큰 화면 ▢", app.close_mini).pack(side="right")
        _btn(bf, "_ 최소화", app.full_minimize).pack(side="right", padx=2)
        self.size_btn = _btn(bf, "작게", self.toggle_compact)
        self.size_btn.pack(side="right", padx=2)
        self.compact = False
        if app.cfg.get("mini_compact"):
            self.toggle_compact()

    def toggle_compact(self):
        """작업화면 미리보기를 숨겨 작은 창으로 / 다시 보이기."""
        self.compact = not self.compact
        if self.compact:
            self.ph.pack_forget()
            self.preview.pack_forget()
            self.size_btn.config(text="크게")
        else:
            self.ph.pack(fill="x", padx=4, before=self.pf)
            self.preview.pack(padx=4, pady=(0, 4), before=self.pf)
            self.size_btn.config(text="작게")
        self.app.cfg["mini_compact"] = self.compact

    def preview_size(self):
        return self.PREVIEW

    def set_preview(self, photo):
        if photo is None:
            self.preview.config(image=self._blank, text="AMIS 창을 찾을 수 없습니다")
        else:
            self.preview.config(image=photo, text="")

    def set_code(self, code):
        self.code_lbl.config(text=code or "--")

    def set_time(self, text):
        self.time_lbl.config(text=text)

    def set_phase(self, text):
        self.phase_lbl.config(text=text)

    def update_progress(self, finished, total, pct, c):
        self.bar["value"] = pct
        self.pct_lbl.config(text="%d/%d (%d%%)" % (finished, total, pct))
        self.count_lbl.config(text="저장완료 %d · 대기중 %d · 저장실패 %d" % (c[DONE], c[WAIT], c[FAIL]))

    def on_state(self, state):
        if state == "running":
            self.start_btn.config(text="● 작업중", state="disabled", disabledforeground="white")
            self.pause_btn.config(text="Ⅱ 일시정지")
        elif state == "paused":
            self.pause_btn.config(text="▶ 재개")
        else:
            self.start_btn.config(text="▶ 시작", state="normal")
            self.pause_btn.config(text="Ⅱ 일시정지")


# 프로그램 아이콘 (icon_white.ico) - 파일이 없어도 쓸 수 있게 내장
ICON_FILE = "icon_white.ico"
ICON_B64 = "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"


def _icon_path():
    """아이콘 파일 위치: exe/스크립트 옆 → exe 내부 → 내장 데이터를 임시 파일로."""
    import sys as _sys
    import base64 as _b64
    import tempfile as _tmp
    dirs = []
    if getattr(_sys, "frozen", False):
        dirs.append(os.path.dirname(_sys.executable))
        dirs.append(getattr(_sys, "_MEIPASS", ""))
    dirs.append(os.path.dirname(os.path.abspath(__file__)))
    for d in dirs:
        if d and os.path.isfile(os.path.join(d, ICON_FILE)):
            return os.path.join(d, ICON_FILE)
    try:
        path = os.path.join(_tmp.gettempdir(), "amis_qr_saver_icon.ico")
        if not os.path.isfile(path):
            with open(path, "wb") as f:
                f.write(_b64.b64decode(ICON_B64))
        return path
    except OSError:
        return None


def set_app_icon(root):
    """제목줄(좌측 상단)·작업표시줄 아이콘. default= 로 축소창·대화상자에도 같은 아이콘."""
    path = _icon_path()
    if not path:
        return
    try:
        root.iconbitmap(default=path)
    except tk.TclError:
        pass


def main():
    w.set_dpi_aware()
    try:
        # 작업표시줄에 python 아이콘 대신 이 프로그램 아이콘이 보이도록 별도 앱 ID 지정
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AMC.Cytology.AMISQRSaver")
    except Exception:
        pass
    root = tk.Tk()
    set_app_icon(root)
    App(root)
    root.mainloop()
'''


def _load():
    pkg = types.ModuleType("qrsaver")
    pkg.__path__ = []
    sys.modules["qrsaver"] = pkg
    for name in ['__init__', 'config', 'hangul', 'models', 'win32', 'uia', 'worker', 'gui']:
        if name == "__init__":
            mod, full = pkg, "qrsaver"
        else:
            full = "qrsaver." + name
            mod = types.ModuleType(full)
            mod.__package__ = "qrsaver"
            sys.modules[full] = mod
        mod.__file__ = __file__
        exec(compile(_SOURCES[name], "<qrsaver/%s.py>" % name, "exec"), mod.__dict__)
        if name != "__init__":
            setattr(pkg, name, mod)
    return sys.modules["qrsaver.gui"]


if __name__ == "__main__":
    _load().main()
