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
