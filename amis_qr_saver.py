# -*- coding: utf-8 -*-
"""AMIS QR 일괄저장 - 단일 실행 파일 (tools/make_single.py 로 자동 생성, 직접 수정하지 마세요)

실행:  python amis_qr_saver.py      (콘솔 없이: pythonw amis_qr_saver.py)
필요:  pip install pillow uiautomation
"""
import sys
import types

_SOURCES = {}

_SOURCES['__init__'] = r'''"""AMIS 병리결과 QR 일괄저장 도우미."""
__version__ = "1.3.0"
'''

_SOURCES['config'] = r'''"""설정 및 파일 경로."""
import json
import os
import sys

CONFIG_VERSION = 3

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
    "uia_screen_id": "",               # 화면 컨테이너 AutomationId (UI 요소 찾기로 자동 저장)
    "uia_field_id": "",                # 검사번호 입력창 AutomationId (UI 요소 찾기로 자동 저장)
    "key_send": "auto",                # Enter/F9 전송: auto | message | keyboard
    "check_default": True,             # 저장 전 기본값(Negative) 선택 여부 확인
    "default_name": "Negative for malignant cells",
    "clear_method": "home_end",        # home_end | ctrl_a | backspace
    "press_enter": False,              # 입력 후 Enter 전송 (AMIS 는 입력만으로 조회되므로 기본 꺼짐)
    "check_loaded": True,              # F9 전 화면에 해당 검사번호가 조회됐는지 확인
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
        if int(saved.get("config_version", 1) or 1) < 3:
            cfg["press_enter"] = False  # v1.3: Enter 불필요
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


def normalize_code(raw, fix_hangul=True, uppercase=True):
    """스캔된 문자열을 검사번호로 정리 (앞뒤 공백/개행 제거, 내부 공백은 유지)."""
    code = raw.replace("\r", "").replace("\n", "").replace("\t", "").strip()
    if fix_hangul:
        code = hangul_to_qwerty(code)
    if uppercase:
        code = code.upper()
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
    __slots__ = ("id", "code", "status", "time", "note", "tries", "added")

    def __init__(self, id, code, status=WAIT, time="", note="", tries=0, added=""):
        self.id = id
        self.code = code
        self.status = status
        self.time = time
        self.note = note
        self.tries = tries
        self.added = added

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
    def add(self, code):
        """추가된 Item 반환, 이미 목록에 있으면 None."""
        with self.lock:
            if any(i.code == code for i in self.items):
                return None
            item = Item(self._next_id, code, added=time.strftime("%H:%M:%S"))
            self._next_id += 1
            self.items.append(item)
        self.save()
        return item

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


def find_window(keyword):
    """제목에 keyword 가 포함된 (자기 자신 제외) 가장 큰 최상위 창."""
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


def type_keys(text):
    """가상 키 코드로 입력 (한글 IME 상태의 영향을 받을 수 있음)."""
    if not IS_WINDOWS:
        return
    for ch in text:
        res = user32.VkKeyScanW(ch)
        if res == -1:
            type_unicode(ch)
            continue
        vk, shift = res & 0xFF, (res >> 8) & 1
        seq = []
        if shift:
            seq.append(_key_input(KEY_CODES["SHIFT"], False))
        seq += [_key_input(vk, False), _key_input(vk, True)]
        if shift:
            seq.append(_key_input(KEY_CODES["SHIFT"], True))
        _send(seq)
        time.sleep(0.015)


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


def is_edit_like(hwnd):
    return "edit" in class_name(hwnd).lower()


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
    return auto._AutomationClient.instance().IUIAutomation


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
    if not fid:
        return None, screen
    field = _find_first(screen or root, PROP_AUTOMATION_ID, fid)
    return field, screen


def _norm(t):
    return "".join((t or "").split()).upper()


def find_showing(root, code, exclude=None, limit=800):
    """root 안에서 (exclude 제외) 값이나 이름에 code 가 표시된 Edit/Text/DataItem 요소."""
    if root is None:
        return None
    target = _norm(code)
    cli = _client()
    cond = cli.CreateOrCondition(
        cli.CreateOrCondition(cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50004),
                              cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50020)),
        cli.CreatePropertyCondition(PROP_CONTROL_TYPE, 50029))
    arr = root.Element.FindAll(TREE_DESCENDANTS, cond)
    if not arr:
        return None
    ex = exclude.Element if exclude is not None else None
    for i in range(min(arr.Length, limit)):
        el = arr.GetElement(i)
        if ex is not None and _safe(lambda: cli.CompareElements(el, ex), 0):
            continue
        c = _wrap(el)
        if c is None:
            continue
        if target in _norm(_safe(lambda: c.Name)) or target in _norm(get_value(c)):
            return c
    return None


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
'''

_SOURCES['worker'] = r'''"""자동 저장 작업 스레드.

목록의 '대기중' 항목을 하나씩 꺼내서
  AMIS 활성화 → 검사번호 칸 클릭 → 번호 입력 → Enter(조회) → F9(저장)
순서로 처리한다. 사용자가 키보드/마우스를 쓰는 동안은 멈추고, 설정한
시간(기본 5초) 이상 입력이 없을 때만 진행한다.
"""
import threading
import time

from . import uia
from . import win32 as w
from .models import WAIT, RUN, DONE, FAIL

# 프로그램이 직접 보낸 입력 이후 이 시간(ms)보다 늦게 들어온 입력은 사용자 입력으로 본다.
INJECT_MARGIN_MS = 250


class UserActive(Exception):
    """작업 도중 사용자 입력이 감지됨 → 해당 항목은 대기로 돌리고 다시 기다린다."""


class StepError(Exception):
    """처리 실패 (재시도 대상)."""


class Worker(threading.Thread):
    def __init__(self, store, cfg, emit):
        super().__init__(daemon=True)
        self.store = store
        self.cfg = cfg
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
        self.emit("phase", text=text)

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

                if not self.wait_idle():
                    continue

                hwnd = w.find_window(self.cfg.get("window_keyword", "AMIS"))
                if not hwnd:
                    self.phase("AMIS 창을 찾을 수 없음 · 대기")
                    self.emit("amis", found=False)
                    self.sleep(2)
                    continue
                self.emit("amis", found=True)

                self.store.update(item, status=RUN, note="")
                self.emit("item", id=item.id)
                try:
                    self.process(item, hwnd)
                except UserActive:
                    self.store.update(item, status=WAIT, note="사용자 작업 감지 → 대기")
                    self.log("[%s] 사용자 입력 감지, 잠시 멈춥니다." % item.code, "warn")
                except StepError as e:
                    tries = item.tries + 1
                    retries = int(self.cfg.get("max_retries", 1))
                    if tries > retries:
                        self.store.update(item, status=FAIL, tries=tries, note=str(e))
                        self.log("[%s] 저장실패: %s" % (item.code, e), "error")
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
                    self.log("[%s] 저장완료" % item.code, "ok")
                self.emit("item", id=item.id)
                self.sleep(self.cfg.get("item_interval", 1.0))
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
            err = self.handle_dialogs(pid, hwnd, baseline)
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
        baseline = set(w.list_popups(pid, exclude=hwnd))

        self.phase("병리결과입력 화면 찾기")
        field, screen = uia.find_field(hwnd, cfg)
        if field is None:
            where = "화면(%s)" % cfg.get("screen_code") if screen is None else "입력창"
            raise StepError("%s 을(를) 찾지 못했습니다 – 병리결과입력 화면이 열려 있는지 확인" % where)

        fhwnd = uia.native_handle(field)
        mode = cfg.get("key_send", "auto")
        use_msg = mode == "message" or (mode == "auto" and fhwnd)
        if use_msg and not fhwnd:
            raise StepError("입력창에 창 핸들이 없어 메시지 전송 불가 → Enter/F9 전송을 '키보드'로 변경")

        prev_fg, prev_pos, activated = w.get_foreground(), w.get_cursor_pos(), False
        try:
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
                uia.focus(field)
            if not uia.set_value(field, item.code):
                raise StepError("입력창에 값을 넣지 못했습니다 (%s)" % uia.describe(field))
            self.sleep(0.15)
            value = uia.get_value(field)
            norm = lambda t: "".join((t or "").split()).upper()
            if value is not None and norm(item.code) not in norm(value):
                raise StepError("검사번호가 입력되지 않았습니다 (입력창 값: '%s')" % value[:30])

            if cfg.get("press_enter", False):
                self.send_key(fhwnd if use_msg else None, "ENTER", "\r")
            self.phase("조회 대기")
            self.sleep(cfg.get("load_wait", 2.0))
            if not use_msg:
                self.check_user()
            err = self.handle_dialogs(pid, hwnd, baseline)
            if err:
                raise StepError("조회 오류: " + err)

            if cfg.get("check_loaded", True):
                self.check_loaded(screen or uia.control_from_handle(hwnd), field, item.code)
            if cfg.get("check_default", True):
                self.check_default_selected(screen or uia.control_from_handle(hwnd))

            if not use_msg:
                if not w.is_foreground(hwnd):
                    w.activate(hwnd)
                    self.mark()
                    self.sleep(0.2)
                self.check_user()
            self.phase("저장 (%s)" % cfg.get("save_key", "F9"))
            self.send_key(fhwnd if use_msg else None, cfg.get("save_key", "F9"))
            self.sleep(cfg.get("save_wait", 2.0))
            err = self.handle_dialogs(pid, hwnd, baseline)
            if err:
                raise StepError("저장 오류: " + err)
        finally:
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
            if uia.find_showing(root, code, exclude=field) is not None:
                return
            if time.monotonic() >= deadline or self.stop_event.is_set():
                raise StepError("화면에 %s 가 조회되지 않아 저장하지 않았습니다" % code)
            self.sleep(0.5)

    def check_default_selected(self, root):
        name = (self.cfg.get("default_name") or "").strip()
        if not name:
            return
        ctrl = uia.find_by_name(root, name)
        if ctrl is None:
            raise StepError("'%s' 항목을 화면에서 찾지 못해 저장하지 않았습니다" % name)
        if uia.is_checked(ctrl) is False:
            raise StepError("'%s' 가 선택되어 있지 않아 저장하지 않았습니다" % name)

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
        err = self.handle_dialogs(pid, hwnd, baseline)
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

    def handle_dialogs(self, pid, main_hwnd, baseline):
        """새로 뜬 확인/알림창을 처리. 실패로 판단되면 그 메시지를 반환."""
        keywords = [k.strip().lower() for k in str(self.cfg.get("fail_keywords", "")).split(",")
                    if k.strip()]
        for _ in range(6):
            dialogs = [h for h in w.list_popups(pid, exclude=main_hwnd)
                       if h not in baseline and w.is_dialog_like(h)]
            if not dialogs:
                return None
            h = dialogs[0]
            text = w.get_all_text(h) or "(내용 없음)"
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
        return "확인창이 닫히지 않습니다"
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
    "bg": "#f2f2f2",
    "panel": "#ffffff",
    "line": "#b9c3c9",
    "titlebar": "#7f9db2",       # 최상단 AMIS 3.0 바
    "header": "#e9ecee",         # 화면 제목줄
    "teal": "#5b9c9e",           # DIAGNOSIS 바, 선택행
    "teal_dark": "#3f7f86",
    "accent": "#c8ee3c",         # 검사번호 형광 노랑
    "blue": "#cfe6f6",           # '접수' 칸
    "sub": "#e6e6d6",            # 'Specimen adequacy' 소제목
    "grid_head": "#eaeaea",
    "red": "#d92b2b",
    "pink": "#f4b9b9",
    "text": "#222222",
    "muted": "#6b6b6b",
    "btn": "#f4f4f4",
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


def _btn(parent, text, cmd, bg=None, fg=None, width=None, bold=False, **kw):
    b = tk.Button(parent, text=text, command=cmd, font=F_B if bold else F,
                  bg=bg or C["btn"], fg=fg or C["text"], activebackground=bg or "#e2e2e2",
                  activeforeground=fg or C["text"], relief="solid", bd=1,
                  highlightthickness=0, cursor="hand2", padx=8, pady=2, **kw)
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
        self.events = queue.Queue()
        self.worker = None
        self.mini = None
        self.photos = {}
        self.current_code = None
        self.log_dir = data_path("logs")
        os.makedirs(self.log_dir, exist_ok=True)

        root.title("AMIS QR 일괄저장 v%s" % __version__)
        root.geometry("1240x780")
        root.minsize(980, 620)
        root.configure(bg=C["bg"])
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._init_style()
        self._build()
        self.reload_tree()
        self.update_summary()

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
        s.configure("Treeview", font=F, rowheight=24, background=C["panel"],
                    fieldbackground=C["panel"], bordercolor=C["line"])
        s.configure("Treeview.Heading", font=F, background=C["grid_head"],
                    foreground=C["text"], relief="solid", borderwidth=1)
        s.map("Treeview", background=[("selected", C["teal"])], foreground=[("selected", "white")])
        s.configure("TNotebook", background=C["bg"], borderwidth=0, tabmargins=(2, 4, 2, 0))
        s.configure("TNotebook.Tab", font=F, padding=(12, 3), background="#e4e4e4",
                    foreground=C["text"], bordercolor=C["line"])
        s.map("TNotebook.Tab", background=[("selected", C["panel"])],
              foreground=[("selected", C["teal_dark"])])
        s.configure("AMIS.Horizontal.TProgressbar", troughcolor="#e4e7e9",
                    background=C["teal"], bordercolor=C["line"], lightcolor=C["teal"],
                    darkcolor=C["teal_dark"], thickness=16)
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
        tk.Label(top, text="│  QR 일괄저장", bg=C["titlebar"], fg="#eef3f6", font=F).pack(side="left")
        self.amis_lbl = tk.Label(top, text="AMIS 연결 확인중…", bg=C["titlebar"], fg="white", font=F)
        self.amis_lbl.pack(side="right", padx=10)

        # --- 화면 제목줄 ----------------------------------------------
        hdr = tk.Frame(root, bg=C["header"], highlightbackground=C["line"], highlightthickness=1)
        hdr.pack(fill="x", padx=4, pady=(4, 0))
        tk.Label(hdr, text="QR일괄저장[VSPSQRB01S]  [ 검사의뢰서 QR 태그 → 기본값 저장(F9) ]",
                 bg=C["header"], fg=C["text"], font=F_B).pack(side="left", padx=6, pady=3)
        self.clock_lbl = tk.Label(hdr, text="", bg=C["header"], fg=C["muted"], font=F)
        self.clock_lbl.pack(side="right", padx=8)

        # --- 상단 정보줄 (형광 검사번호 / 접수 칸 / 건수 / 버튼) ---------
        info = tk.Frame(root, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        info.pack(fill="x", padx=4, pady=(0, 0))

        self.code_lbl = tk.Label(info, text="--", bg=C["accent"], fg="#111",
                                 font=(FONT_NAME, 22, "bold"), width=13, anchor="w", padx=8)
        self.code_lbl.pack(side="left", padx=(4, 2), pady=4, ipady=2)
        self.phase_lbl = tk.Label(info, text="대기", bg=C["blue"], fg="#16425b",
                                  font=(FONT_NAME, 11, "bold"), width=24, anchor="w", padx=8)
        self.phase_lbl.pack(side="left", padx=2, pady=4, fill="y")

        counts = tk.Frame(info, bg=C["panel"])
        counts.pack(side="left", padx=10)
        self.count_vars = {}
        for col, (key, label, color) in enumerate([("total", "전체", C["text"]), (DONE, "저장완료", "#2e7d32"),
                                                  (WAIT, "대기중", "#555"), (FAIL, "저장실패", C["red"])]):
            tk.Label(counts, text=label, bg=C["panel"], fg=color, font=F).grid(row=0, column=col, padx=4)
            v = tk.StringVar(value="0")
            tk.Label(counts, textvariable=v, bg="white", fg=color, font=(FONT_NAME, 12, "bold"),
                     width=5, relief="solid", bd=1).grid(row=1, column=col, padx=4)
            self.count_vars[key] = v

        btns = tk.Frame(info, bg=C["panel"])
        btns.pack(side="right", padx=6)
        self.start_btn = _btn(btns, "▶ 시작", self.start, bg=C["teal"], fg="white", bold=True, width=8)
        self.start_btn.pack(side="left", padx=2)
        self.pause_btn = _btn(btns, "Ⅱ 일시정지", self.pause, width=9)
        self.pause_btn.pack(side="left", padx=2)
        self.stop_btn = _btn(btns, "■ 정지", self.stop, width=6)
        self.stop_btn.pack(side="left", padx=2)
        self._build_action_button(btns).pack(side="left", padx=(8, 2))

        # --- QR 입력줄 -------------------------------------------------
        qr = tk.Frame(root, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        qr.pack(fill="x", padx=4)
        tk.Label(qr, text="QR 태그", bg=C["panel"], font=F_B).pack(side="left", padx=(8, 4), pady=5)
        self.qr_var = tk.StringVar()
        self.qr_entry = tk.Entry(qr, textvariable=self.qr_var, font=(FONT_NAME, 13, "bold"), width=22,
                                 relief="solid", bd=1, bg="#fffde8", highlightthickness=2,
                                 highlightcolor=C["accent"], highlightbackground=C["line"])
        self.qr_entry.pack(side="left", padx=4, pady=5, ipady=2)
        for seq in ("<Return>", "<KP_Enter>", "<Tab>"):
            self.qr_entry.bind(seq, self.on_qr_enter)
        _btn(qr, "추가", lambda: self.on_qr_enter(None)).pack(side="left", padx=2)
        self.qr_msg = tk.Label(qr, text="QR코드를 태그하면 아래 목록에 추가됩니다.", bg=C["panel"],
                               fg=C["red"], font=F)
        self.qr_msg.pack(side="left", padx=10)
        _btn(qr, "실패항목 재시도", self.retry_failed, bg=C["pink"], fg=C["red"]).pack(side="right", padx=6)

        # --- 진행률 ----------------------------------------------------
        prog = tk.Frame(root, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        prog.pack(fill="x", padx=4)
        tk.Label(prog, text="작업진행", bg=C["panel"], font=F_B).pack(side="left", padx=(8, 6), pady=5)
        self.progress = ttk.Progressbar(prog, style="AMIS.Horizontal.TProgressbar", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True, padx=4, pady=5)
        self.prog_lbl = tk.Label(prog, text="0 / 0  (0%)", bg=C["panel"], font=F_B, width=16)
        self.prog_lbl.pack(side="left", padx=6)

        # --- 본문: 좌 (목록/설정/로그) | 우 (작업화면) -------------------
        body = tk.PanedWindow(root, orient="horizontal", bg=C["bg"], sashwidth=5, bd=0)
        body.pack(fill="both", expand=True, padx=4, pady=4)

        left = tk.Frame(body, bg=C["bg"])
        self.nb = ttk.Notebook(left)
        self.nb.pack(fill="both", expand=True)
        self.nb.add(self._build_list_tab(self.nb), text="QR 리스트")
        self.nb.add(self._build_settings_tab(self.nb), text="설정")
        self.nb.add(self._build_log_tab(self.nb), text="작업 로그")
        body.add(left, minsize=520, width=640)

        right = tk.Frame(body, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        body.add(right, minsize=300)
        rh = tk.Frame(right, bg=C["teal"])
        rh.pack(fill="x")
        tk.Label(rh, text="☑ 작업 화면 (AMIS 실시간)", bg=C["teal"], fg="white", font=F_B).pack(
            side="left", padx=6, pady=3)
        _btn(rh, "축소창 ▣", self.open_mini, bg="#ffffff").pack(side="right", padx=4, pady=2)
        self.preview_cv = tk.Canvas(right, bg="#dfe4e7", highlightthickness=0, width=300, height=200)
        self.preview_cv.pack(fill="both", expand=True, padx=4, pady=4)
        self.show_preview_text("AMIS 화면을 불러오는 중…" if Image else
                               "미리보기를 사용하려면 Pillow 설치가 필요합니다\n(pip install pillow)")
        self.preview_info = tk.Label(right, text="", bg=C["panel"], fg=C["muted"], font=F, anchor="w")
        self.preview_info.pack(fill="x", padx=6, pady=(0, 4))

        # --- 상태바 ----------------------------------------------------
        self.status_lbl = tk.Label(root, text="준비", bg="#e7e7e7", fg=C["text"], font=F, anchor="w",
                                   relief="sunken", bd=1)
        self.status_lbl.pack(fill="x", side="bottom")

        self.tick_clock()

    def _build_action_button(self, parent):
        mb = tk.Menubutton(parent, text="Action ▾", font=F, bg=C["btn"], relief="solid", bd=1,
                           activebackground="#e2e2e2", padx=10, pady=3, cursor="hand2")
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
        sub = tk.Label(bar, text=" 검사의뢰서 QR 태그 목록 ", bg=C["sub"], fg=C["text"], font=F_B)
        sub.pack(side="left", padx=4)
        _btn(bar, "전체삭제", lambda: self.clear_items(None)).pack(side="right", padx=2)
        _btn(bar, "완료정리", lambda: self.clear_items((DONE,))).pack(side="right", padx=2)
        _btn(bar, "삭제", self.delete_selected).pack(side="right", padx=2)
        _btn(bar, "대기로", self.reset_selected).pack(side="right", padx=2)

        cols = ("no", "code", "status", "time", "note")
        tf = tk.Frame(f, bg=C["panel"])
        tf.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="extended")
        for c, text, width, anchor in [("no", "No", 44, "center"), ("code", "검사번호", 150, "center"),
                                       ("status", "상태", 100, "center"), ("time", "처리시각", 80, "center"),
                                       ("note", "비고", 240, "w")]:
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, anchor=anchor, stretch=(c == "note"))
        for st, (_, bg, fg) in STATUS_STYLE.items():
            self.tree.tag_configure(st, background=bg, foreground=fg)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Button-3>", self.on_tree_menu)

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
        for i, (key, text) in enumerate([("press_enter", "입력 후 Enter 전송 (보통 불필요)"),
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
        raw = self.qr_var.get()
        self.qr_var.set("")
        code = normalize_code(raw, self.cfg.get("fix_hangul", True), self.cfg.get("uppercase", True))
        if not code:
            return "break"
        item = self.store.add(code)
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

    def _row_values(self, idx, item):
        return (idx, item.code, STATUS_STYLE[item.status][0], item.time or "", item.note or "")

    def insert_row(self, item):
        idx = len(self.tree.get_children()) + 1
        self.tree.insert("", "end", iid=str(item.id), values=self._row_values(idx, item), tags=(item.status,))

    def reload_tree(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.store.snapshot():
            self.insert_row(item)

    def refresh_row(self, item_id):
        item = self.store.get(item_id)
        iid = str(item_id)
        if item is None or not self.tree.exists(iid):
            return
        idx = self.tree.index(iid) + 1
        self.tree.item(iid, values=self._row_values(idx, item), tags=(item.status,))
        if item.status == RUN:
            self.tree.see(iid)

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
                    self.code_lbl.config(text=d["code"] or "--")
                    if self.mini:
                        self.mini.set_code(d["code"])
                elif kind == "state":
                    self.on_state(d["state"])
                elif kind == "amis":
                    self.set_amis(d["found"])
                elif kind == "call":
                    d["fn"](*d.get("args", ()))
        except queue.Empty:
            pass
        self.root.after(100, self.poll_events)

    def on_state(self, state):
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
                    add("  %s%s%s" % ("  " * min(i, 10), uia.describe(a), "   ◀ 화면" if a is screen else ""))
                aid = (ctrl.AutomationId if ctrl is not None else "") or ""
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
                add("검사번호 입력창(ID '%s'): %s" % (self.cfg.get("uia_field_id"), uia.describe(field)))
                if field is not None:
                    add("  현재 값: '%s' · 창 핸들 %s → Enter/F9 %s" % (
                        uia.get_value(field) or "", uia.native_handle(field) or "없음",
                        "백그라운드 전송 가능" if uia.native_handle(field) else "키보드 전송 필요"))
                name = self.cfg.get("default_name")
                if name:
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
            for key in ("idle_seconds", "load_wait", "save_wait", "item_interval"):
                new[key] = max(0.0, float(self.vars[key].get()))
            new["idle_seconds"] = max(1.0, new["idle_seconds"])
            new["max_retries"] = max(0, int(float(self.vars["max_retries"].get())))
        except ValueError:
            if not silent:
                messagebox.showerror("오류", "숫자 설정값을 확인해 주세요.", parent=self.root)
            return False
        for key in ("window_keyword", "fail_keywords", "screen_code", "uia_field_id", "uia_screen_id",
                    "default_name"):
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
        win.title("QR 일괄저장 - 축소창")
        win.configure(bg=C["panel"])
        win.attributes("-topmost", True)
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
        tk.Label(hdr, text="AMIS 3.0 · QR 일괄저장", bg=C["titlebar"], fg="white", font=F_B).pack(
            side="left", padx=6, pady=2)

        top = tk.Frame(win, bg=C["panel"])
        top.pack(fill="x", padx=4, pady=4)
        self.code_lbl = tk.Label(top, text="--", bg=C["accent"], font=(FONT_NAME, 15, "bold"), width=14,
                                 anchor="w", padx=6)
        self.code_lbl.pack(side="left")
        self.phase_lbl = tk.Label(top, text="", bg=C["blue"], fg="#16425b", font=F_B, anchor="w", padx=4)
        self.phase_lbl.pack(side="left", fill="both", expand=True, padx=(4, 0))

        ph = tk.Frame(win, bg=C["teal"])
        ph.pack(fill="x", padx=4)
        tk.Label(ph, text="☑ 작업 화면", bg=C["teal"], fg="white", font=F_B).pack(side="left", padx=4)
        self.preview = tk.Label(win, bg="#dfe4e7", fg=C["muted"], font=F, text="화면 불러오는 중…",
                                width=self.PREVIEW[0], height=self.PREVIEW[1])
        # 픽셀 단위 크기 고정을 위해 이미지 없는 상태에서도 빈 이미지 사용
        self._blank = tk.PhotoImage(width=self.PREVIEW[0], height=self.PREVIEW[1])
        self.preview.config(image=self._blank, compound="center")
        self.preview.pack(padx=4, pady=(0, 4))

        pf = tk.Frame(win, bg=C["panel"])
        pf.pack(fill="x", padx=4)
        self.bar = ttk.Progressbar(pf, style="AMIS.Horizontal.TProgressbar", maximum=100)
        self.bar.pack(side="left", fill="x", expand=True)
        self.pct_lbl = tk.Label(pf, text="0%", bg=C["panel"], font=F_B, width=12)
        self.pct_lbl.pack(side="left")
        self.count_lbl = tk.Label(win, text="", bg=C["panel"], font=F, anchor="w")
        self.count_lbl.pack(fill="x", padx=6)

        bf = tk.Frame(win, bg=C["panel"])
        bf.pack(fill="x", padx=4, pady=4)
        self.start_btn = _btn(bf, "▶ 시작", app.start, bg=C["teal"], fg="white", bold=True)
        self.start_btn.pack(side="left")
        self.pause_btn = _btn(bf, "Ⅱ 일시정지", app.pause)
        self.pause_btn.pack(side="left", padx=2)
        _btn(bf, "■ 정지", app.stop).pack(side="left")
        _btn(bf, "큰 화면 ▢", app.close_mini).pack(side="right")

    def preview_size(self):
        return self.PREVIEW

    def set_preview(self, photo):
        if photo is None:
            self.preview.config(image=self._blank, text="AMIS 창을 찾을 수 없습니다")
        else:
            self.preview.config(image=photo, text="")

    def set_code(self, code):
        self.code_lbl.config(text=code or "--")

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


def main():
    w.set_dpi_aware()
    root = tk.Tk()
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
