"""UI Automation (AutomationId) 로 AMIS 화면 요소를 직접 찾는 모듈.

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
