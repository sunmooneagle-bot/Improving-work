"""AMIS 3.0 화면 스타일의 메인 창 / 축소창."""
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from . import __version__
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

INPUT_METHODS = [("paste", "붙여넣기 (권장)"), ("unicode", "문자 직접입력"), ("keys", "키보드 키입력")]
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
        outer = tk.Frame(parent, bg=C["panel"])
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

        # 1. AMIS 창 / 위치
        inner = section("AMIS 창 / 검사번호 칸 위치")
        v = tk.StringVar(value=self.cfg["window_keyword"])
        self.vars["window_keyword"] = v
        row(inner, 0, "창 제목 포함 글자", tk.Entry(inner, textvariable=v, width=20, relief="solid", bd=1),
            "예) AMIS")
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
        row(inner, 0, "검사번호 입력 방식", self.input_cb, "한/영 상태와 무관하게 입력되는 붙여넣기 권장")
        self.clear_cb = ttk.Combobox(inner, state="readonly", width=20, values=[t for _, t in CLEAR_METHODS])
        self.clear_cb.set(dict(CLEAR_METHODS).get(self.cfg["clear_method"], CLEAR_METHODS[0][1]))
        row(inner, 1, "기존 내용 지우기", self.clear_cb)
        self.savekey_cb = ttk.Combobox(inner, state="readonly", width=8,
                                       values=["F9", "F6"] + ["F%d" % i for i in range(1, 13) if i not in (6, 9)])
        self.savekey_cb.set(self.cfg["save_key"])
        row(inner, 2, "저장 키", self.savekey_cb, "Action ▸ 저장 [F9]")
        checks = tk.Frame(inner, bg=C["panel"])
        checks.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))
        for i, (key, text) in enumerate([("press_enter", "입력 후 Enter 로 조회"),
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
        return outer

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
        if not self.cfg.get("field_offset"):
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
        self.log("검사번호 칸 위치 지정: %s" % self._offset_text())

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
        for key in ("window_keyword", "fail_keywords"):
            new[key] = self.vars[key].get().strip()
        for key in ("press_enter", "auto_close_dialogs", "restore_focus", "fix_hangul", "uppercase"):
            new[key] = bool(self.vars[key].get())
        new["input_method"] = {t: k for k, t in INPUT_METHODS}.get(self.input_cb.get(), "paste")
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
        if not messagebox.askyesno("기본값", "검사번호 칸 위치를 제외한 설정을 기본값으로 되돌릴까요?",
                                   parent=self.root):
            return
        for k, v in DEFAULTS.items():
            if k in self.vars:
                self.vars[k].set(v if not isinstance(v, float) else self._fmt(v))
        self.input_cb.set(dict(INPUT_METHODS)[DEFAULTS["input_method"]])
        self.clear_cb.set(dict(CLEAR_METHODS)[DEFAULTS["clear_method"]])
        self.savekey_cb.set(DEFAULTS["save_key"])
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

    def on_close(self):
        if self.worker_alive():
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
