"""자동 저장 작업 스레드.

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
