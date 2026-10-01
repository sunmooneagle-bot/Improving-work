"""Win32 API 래퍼 (ctypes 사용, 외부 의존성 없음).

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

    INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
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
    # 대체 방법: Alt 키 입력으로 포그라운드 잠금 해제
    _send([_key_input(KEY_CODES["ALT"], False), _key_input(KEY_CODES["ALT"], True)])
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
