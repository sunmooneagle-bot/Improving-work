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
