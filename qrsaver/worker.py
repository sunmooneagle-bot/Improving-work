"""자동 저장 작업 스레드.

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
