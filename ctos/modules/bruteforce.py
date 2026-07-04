import math
import random
import string
import tkinter as tk

from ctos import bruteforce_config as C
from ctos.ui import theme as T
from ctos.ui.viewport import Viewport
from ctos.utils.tk_helpers import draw_corner_frame


class BruteforceModule:
    def __init__(self, canvas, root, on_exit):
        self.canvas = canvas
        self.root = root
        self.on_exit = on_exit
        self.is_alive = True

        self.target_password = C.TARGET_PASSWORD

        self.networks = [dict(x) for x in C.NETWORKS]
        for n in self.networks:
            n.setdefault("target", False)

        self.logs = []
        self.ready = False
        self.idx = 0
        self.attempt = 0
        self.max_attempts = 80
        self._attempt_delay_ms = 100
        self.phase_idx = 0
        self.dict_profile = C.DEFAULT_PROFILE

        self.net_nodes = []
        self.net_edges = []
        self.net_phase = []
        self.net_amp = []
        self.net_active = False

        self.attack_active = False
        self.attack_flash = False
        self.attack_target_name = None
        self.attack_success = False
        self._exit_in_progress = False

        self.info_visible = False
        self.info_page = 0
        self.info_overlay = None
        self.info_focus = None
        self.info_box = None
        self.info_title = None
        self.info_text = None
        self.info_counter = None
        self.info_big_panel = None
        self.info_big_text = None
        self.info_targets: dict[str, int] = {}

        self._bf_wave_phase = 0.0
        self._ambient_progress = 0
        self._bf_sig_bars: list[int] = []
        self._bf_load_bars: list[int] = []
        self._bf_strip_y1 = 84
        self._pb_scan_phase = 0.0
        self.pb_scan: int | None = None

        self._wifi_phase = 0.0
        self._wifi_arcs: list[int] = []
        self._wifi_sig_bars: list[int] = []
        self._wifi_dot: int | None = None
        self._wifi_radii: tuple[int, int, int] = (36, 52, 72)
        self._wifi_bars_offset = 95
        self._wifi_arc_widths = (5, 6, 7)

    # ================== START ==================
    def start(self):
        self.build_ui()
        self.restore_mivlgu()
        self.calculate_log_limit()  # до simulate и scan
        self.start_scan()
        self.simulate_signal()

    # ================== UI ==================
    def build_ui(self):
        self.canvas.delete("all")

        vp = self.vp = Viewport.from_canvas(self.canvas, self.root)
        self.w = vp.w
        self.h = vp.h
        self._bf_strip_y1 = vp.px(84)
        self._ambient_progress = 0
        self._bf_wave_phase = 0.0

        self._draw_ambient_background()

        # header
        self.canvas.create_text(
            self.w // 2, vp.px(35),
            text="CtOS  //  BRUTEFORCE (SIMULATION)",
            fill=T.BF_TEXT_BRIGHT, font=vp.consolas(20, bold=True)
        )

        # BACK
        self.back = self.canvas.create_rectangle(
            vp.px(30), vp.px(20), vp.px(140), vp.px(60),
            outline=T.BF_ACCENT, width=vp.wid(2), fill="")
        self.back_t = self.canvas.create_text(
            vp.px(85), vp.px(40), text="BACK", fill=T.BF_ACCENT, font=vp.consolas(12, bold=True)
        )
        for i in (self.back, self.back_t):
            self.canvas.tag_bind(i, "<Button-1>", lambda e: self.exit())
            self.canvas.tag_bind(i, "<Enter>", lambda e: self._topbar_hover(self.back, self.back_t, True))
            self.canvas.tag_bind(i, "<Leave>", lambda e: self._topbar_hover(self.back, self.back_t, False))

        # INFO
        self.info_btn = self.canvas.create_rectangle(
            vp.px(150), vp.px(20), vp.px(270), vp.px(60),
            outline=T.BF_ACCENT, width=vp.wid(2), fill="")
        self.info_btn_t = self.canvas.create_text(
            vp.px(210), vp.px(40), text="INFO", fill=T.BF_ACCENT, font=vp.consolas(12, bold=True)
        )
        for i in (self.info_btn, self.info_btn_t):
            self.canvas.tag_bind(i, "<Button-1>", lambda e: self.toggle_info())
            self.canvas.tag_bind(i, "<Enter>", lambda e: self._topbar_hover(self.info_btn, self.info_btn_t, True))
            self.canvas.tag_bind(i, "<Leave>", lambda e: self._topbar_hover(self.info_btn, self.info_btn_t, False))

        # NETWORK PANEL (ниже ambient‑полосы 58–84)
        self.panel_net_rect = draw_corner_frame(
            self.canvas, vp.px(40), vp.px(92), vp.px(380), self.h - vp.px(120),
            outline=T.BF_PANEL_OUTLINE, fill=T.BF_PANEL_BG, frame_width=vp.wid(2),
            bracket_len=vp.px(14), bracket_width=vp.wid(2),
        )
        self.canvas.create_text( vp.px(60), vp.px(102), anchor="nw", text="AVAILABLE NETWORKS:",
                                fill=T.BF_HEADER, font=vp.consolas(12, bold=True))

        self.network_items = []
        self.network_rects = []

        base = vp.px(138)
        line = vp.px(32)

        for i, net in enumerate(self.networks):
            y = base + i * line

            rect = self.canvas.create_rectangle(
                vp.px(50), y - vp.px(3), vp.px(370), y + vp.px(20),
                outline="", fill=T.BF_PANEL_BG
            )
            text = self.canvas.create_text(
                vp.px(60), y, anchor="nw",
                text=f"[..] {net['ssid']}  {net['signal']} dBm",
                fill=T.BF_TEXT_DIM, font=vp.consolas(11)
            )

            self.canvas.tag_bind(rect, "<Enter>",  lambda e, i=i: self.hover_on(i))
            self.canvas.tag_bind(text, "<Enter>",  lambda e, i=i: self.hover_on(i))
            self.canvas.tag_bind(rect, "<Leave>",  lambda e, i=i: self.hover_off(i))
            self.canvas.tag_bind(text, "<Leave>",  lambda e, i=i: self.hover_off(i))
            self.canvas.tag_bind(rect, "<Button-1>", lambda e, i=i: self.select(i))
            self.canvas.tag_bind(text, "<Button-1>", lambda e, i=i: self.select(i))

            self.network_rects.append(rect)
            self.network_items.append(text)

        profile_y = base + len(self.networks) * line + vp.px(8)
        self.canvas.create_text(
            vp.px(60), profile_y, anchor="nw",
            text="DICT PROFILE (sim):",
            fill=T.BF_HEADER, font=vp.consolas(10, bold=True),
        )
        pfy = profile_y + vp.px(22)
        self.prof_fast_r = self.canvas.create_rectangle(
            vp.px(52), pfy, vp.px(198), pfy + vp.px(28),
            outline=T.BF_ACCENT, width=vp.wid(2), fill=T.BF_PANEL_BG,
        )
        self.prof_fast_t = self.canvas.create_text(
            vp.px(125), pfy + vp.px(14),
            text="FAST",
            fill=T.BF_ACCENT, font=vp.consolas(10, bold=True),
        )
        self.prof_deep_r = self.canvas.create_rectangle(
            vp.px(208), pfy, vp.px(364), pfy + vp.px(28),
            outline=T.BF_PANEL_OUTLINE, width=vp.wid(1), fill=T.BF_PANEL_BG,
        )
        self.prof_deep_t = self.canvas.create_text(
            vp.px(286), pfy + vp.px(14),
            text="DEEP",
            fill=T.BF_TEXT_DIM, font=vp.consolas(10, bold=True),
        )
        for item in (self.prof_fast_r, self.prof_fast_t):
            self.canvas.tag_bind(item, "<Button-1>", lambda e: self.set_dict_profile("fast"))
            self.canvas.tag_bind(item, "<Enter>", lambda e: self._profile_hover("fast", True))
            self.canvas.tag_bind(item, "<Leave>", lambda e: self._profile_hover("fast", False))
        for item in (self.prof_deep_r, self.prof_deep_t):
            self.canvas.tag_bind(item, "<Button-1>", lambda e: self.set_dict_profile("deep"))
            self.canvas.tag_bind(item, "<Enter>", lambda e: self._profile_hover("deep", True))
            self.canvas.tag_bind(item, "<Leave>", lambda e: self._profile_hover("deep", False))

        # LOG PANEL (фон Wi‑Fi под текстом лога)
        self.panel_log_rect = draw_corner_frame(
            self.canvas, vp.px(410), vp.px(92), self.w - vp.px(40), self.h - vp.px(120),
            outline=T.BF_PANEL_OUTLINE, fill=T.BF_PANEL_BG, frame_width=vp.wid(2),
            bracket_len=vp.px(16), bracket_width=vp.wid(2),
        )
        self._draw_wifi_watermark()
        self.canvas.create_text(vp.px(430), vp.px(102), anchor="nw", text="ATTACK LOG:",
                                fill=T.BF_HEADER, font=vp.consolas(12, bold=True))

        self.logbox = self.canvas.create_text(
            vp.px(430), vp.px(132),
            anchor="nw",
            text="",
            fill=T.BF_TEXT,
            font=vp.consolas(11),
            width=self.w - vp.px(480),
            justify="left"
        )
        # Wi‑Fi водяной знак рисуем фоном под текстом лога.
        self.canvas.tag_lower("bf_wifi")

        # ================= NETWORK MAP PANEL =================
        # 444, а не 420: у PHONE (pos x=-160, r=22) кружок на 2px вылезал за
        # левую границу панели, и узел ещё «дышит» — animate_network_map()
        # добавляет к позиции синус/косинус-дрожание амплитудой до 1.6*scale px,
        # так что нужен запас больше просто статического зазора. 444 проверено
        # с запасом (>=3px) даже в худшем случае дрожания на широком диапазоне
        # разрешений/масштабов (0.4x — 2.0x).
        map_x1 = self.w - vp.px(444)
        map_y1 = vp.px(112)
        map_x2 = self.w - vp.px(60)
        map_y2 = self.h - vp.px(180)

        self.panel_map_rect = draw_corner_frame(
            self.canvas, map_x1, map_y1, map_x2, map_y2,
            outline=T.BF_PANEL_OUTLINE, fill=T.BF_MAP_BG, frame_width=vp.wid(2),
            bracket_len=vp.px(12), bracket_width=vp.wid(2),
        )

        self.canvas.create_text(
            (map_x1 + map_x2) // 2, map_y1 + vp.px(15),
            text="NETWORK MAP",
            fill=T.BF_HEADER,
            font=vp.consolas(11, bold=True)
        )

        self.network_center = (
            (map_x1 + map_x2) // 2,
            (map_y1 + map_y2) // 2 + vp.px(20)
        )

        self.draw_network_map()

        # PROGRESS BAR (CtOS style)
        self.pb_y = self.h - vp.px(85)

        self.pb_frame = self.canvas.create_rectangle(
            vp.px(40), self.pb_y, self.w - vp.px(40), self.pb_y + vp.px(22),
            outline=T.BF_PANEL_OUTLINE, width=vp.wid(2)
        )

        self.pb_fill = self.canvas.create_rectangle(
            vp.px(42), self.pb_y + vp.px(2), vp.px(42), self.pb_y + vp.px(20),
            fill=T.BF_ACCENT, width=0
        )

        # Тонкий «скан» поверх заливки — как будто сквозь бар бежит сигнал.
        self.pb_scan = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#eaffff", stipple="gray25", outline="",
        )

        self.pb_text = self.canvas.create_text(
            self.w // 2, self.pb_y + vp.px(11),
            text="PROGRESS: 0%",
            fill=T.BF_HEADER,
            font=vp.consolas(10, bold=True)
        )

        self.canvas.tag_lower("bf_ambient")
        self._tick_ambient_wave()
        self._tick_wifi_icon()
        self._tick_progress_scan()

        self.info_targets = {
            "NETWORKS": self.panel_net_rect,
            "PROFILE": self.prof_fast_r,
            "LOG": self.panel_log_rect,
            "MAP": self.panel_map_rect,
            "PROGRESS": self.pb_frame,
            "INFO": self.info_btn,
        }

    def _draw_wifi_watermark(self) -> None:
        vp = self.vp
        log_x1, log_y1 = vp.px(410), vp.px(92)
        log_x2, log_y2 = self.w - vp.px(40), self.h - vp.px(120)
        cx = (log_x1 + log_x2) / 2
        panel_w = log_x2 - log_x1
        panel_h = log_y2 - log_y1
        # Крупный водяной знак, центр панели (как фон под логом)
        r3 = int(min(panel_h * 0.34, panel_w * 0.20, 118))
        r3 = max(r3, 72)
        r2 = int(r3 * 0.68)
        r1 = int(r3 * 0.42)
        vc = (log_y1 + log_y2) / 2
        base = vc + r3
        self._wifi_cx = cx
        self._wifi_base_y = base
        self._wifi_radii = (r1, r2, r3)
        self._wifi_arc_widths = (vp.wid(5), vp.wid(6), vp.wid(7))
        self._wifi_bars_offset = int(r3 * 0.72) + vp.px(12)
        dim = "#0f1822"
        self._wifi_arcs = []
        for ri, r in enumerate((r1, r2, r3)):
            a = self.canvas.create_arc(
                cx - r, base - 2 * r, cx + r, base,
                start=180,
                extent=-180,
                style=tk.ARC,
                outline=dim,
                width=self._wifi_arc_widths[ri] if ri < len(self._wifi_arc_widths) else vp.wid(5),
                tags=("bf_wifi",),
            )
            self._wifi_arcs.append(a)
        dr = max(vp.px(6), r1 // 3)
        self._wifi_dot = self.canvas.create_oval(
            cx - dr, base - dr - vp.px(4), cx + dr, base + vp.px(4),
            fill=dim,
            outline="",
            tags=("bf_wifi",),
        )
        self._wifi_sig_bars = []
        bw = max(vp.px(10), r1 // 2)
        gap = max(vp.px(12), r1 // 3)
        # Центрируем группу сигнальных полос относительно центра панели лога.
        group_w = 4 * bw + 3 * gap
        bx = cx - group_w / 2
        for i in range(4):
            h = int(vp.px(16) + i * vp.px(12))
            bid = self.canvas.create_rectangle(
                bx + i * (bw + gap),
                base - h,
                bx + i * (bw + gap) + bw,
                base,
                fill=dim,
                outline="",
                tags=("bf_wifi", "bf_wifi_sig"),
            )
            self._wifi_sig_bars.append(bid)

    def _wifi_palette(self) -> tuple[str, str, str]:
        """Всегда тускло: выглядит как слой под текстом лога."""
        p = self._ambient_progress / 100.0
        if self.attack_success:
            return "#1a2e28", "#152820", "#12261c"
        if self.attack_active:
            # Зелёный -> красный, но приглушённые значения (не ярко).
            # t=0..1 по прогрессу атаки.
            t = max(0.0, min(1.0, p))
            gr, gg, gb = 28, 82, 46   # green (dim)
            rr, rg, rb = 86, 26, 26  # red   (dim)
            r = int(gr + (rr - gr) * t)
            g = int(gg + (rg - gg) * t)
            b = int(gb + (rb - gb) * t)
            arc = f"#{r:02x}{g:02x}{b:02x}"
            # Для полос делаем чуть темнее, чтобы оставалось фоном.
            dr = int(r * 0.72)
            dg = int(g * 0.72)
            db = int(b * 0.72)
            bar_base = f"#{dr:02x}{dg:02x}{db:02x}"
            return arc, arc, bar_base
        if self.ready:
            return "#1a2832", "#15222c", "#121c26"
        return "#141e28", "#121a24", "#0f1820"

    def _tick_wifi_icon(self) -> None:
        if not self.is_alive:
            return
        self._wifi_phase += 0.18
        t = self._wifi_phase
        arc_c, dot_c, bar_base = self._wifi_palette()
        pulse = 0.92 + 0.08 * (0.5 + 0.5 * math.sin(t))
        widths = getattr(self, "_wifi_arc_widths", (5, 6, 7))
        for i, aid in enumerate(self._wifi_arcs):
            w0 = float(widths[i] if i < len(widths) else 5)
            self.canvas.itemconfig(aid, outline=arc_c, width=max(1, int(w0 * pulse)))
        if self._wifi_dot is not None:
            self.canvas.itemconfig(self._wifi_dot, fill=dot_c)
        lvl = 1
        if self.attack_success:
            lvl = 4
        elif self.attack_active:
            lvl = 1 + int(3 * (self._ambient_progress / 100.0) ** 0.7)
        elif self.ready:
            lvl = 2 + int(1.5 * (0.5 + 0.5 * math.sin(t)))
        else:
            lvl = 1 + int(random.random() * 1.5)
        lvl = max(1, min(4, lvl))
        base = self._wifi_base_y
        vp = self.vp
        r1 = self._wifi_radii[0] if self._wifi_radii else vp.px(36)
        bw = max(vp.px(10), r1 // 2)
        gap = max(vp.px(12), r1 // 3)
        # Центрируем группу полос относительно центра арок.
        group_w = 4 * bw + 3 * gap
        bx = self._wifi_cx - group_w / 2
        for i, bid in enumerate(self._wifi_sig_bars):
            h = int(vp.px(16) + i * vp.px(12))
            active = i < lvl
            col = bar_base if active else "#070c10"
            if active and self.attack_active:
                col = bar_base if self._ambient_progress > i * 22 else "#121a22"
            self.canvas.itemconfig(bid, fill=col)
            x0 = bx + i * (bw + gap)
            x1 = x0 + bw
            self.canvas.coords(
                bid,
                x0,
                base - (h if active else vp.px(6)),
                x1,
                base,
            )
        self.root.after(220, self._tick_wifi_icon)

    def _draw_ambient_background(self) -> None:
        w, h = self.w, self.h
        vp = self.vp
        sy0, sy1 = vp.px(58), self._bf_strip_y1
        self.canvas.create_rectangle(
            0, 0, w, h,
            fill=T.BF_AMBIENT_BG, outline="", tags=("bf_ambient",),
        )
        self.canvas.create_rectangle(
            vp.px(40), sy0, w - vp.px(40), sy1,
            fill=T.BF_AMBIENT_STRIP,
            outline=T.BF_AMBIENT_STRIP_OUTLINE,
            width=vp.wid(1),
            tags=("bf_ambient",),
        )
        self.canvas.create_text(
            vp.px(52), (sy0 + sy1) // 2,
            anchor="w",
            text="RF SCAN (sim)",
            fill=T.BF_AMBIENT_LABEL,
            font=vp.consolas(8),
            tags=("bf_ambient",),
        )
        self.canvas.create_text(
            w // 2, (sy0 + sy1) // 2,
            text="AMBIENT NETWORKS  //  ATTACK LOAD (sim)",
            fill=T.BF_AMBIENT_LABEL,
            font=vp.consolas(8),
            tags=("bf_ambient",),
        )
        x0, x1 = vp.px(158), w // 2 - vp.px(28)
        n_sig = 28
        step = max(3.0, (x1 - x0) / max(1, n_sig))
        self._bf_sig_bars = []
        for i in range(n_sig):
            xa = x0 + i * step
            bw = min(step - 1.5, float(vp.px(5)))
            bid = self.canvas.create_rectangle(
                xa, sy1 - vp.px(4), xa + bw, sy1 - vp.px(4),
                fill=T.BF_WAVE_BAR_SIG,
                outline="",
                tags=("bf_ambient", "bf_wave_sig"),
            )
            self._bf_sig_bars.append(bid)
        x0b, x1b = w // 2 + vp.px(24), w - vp.px(52)
        n_ld = 12
        stepb = max(4.0, (x1b - x0b) / max(1, n_ld))
        self._bf_load_bars = []
        for j in range(n_ld):
            xb = x0b + j * stepb
            bw = min(stepb - 1.5, float(vp.px(8)))
            bid = self.canvas.create_rectangle(
                xb, sy1 - vp.px(4), xb + bw, sy1 - vp.px(4),
                fill=T.BF_WAVE_BAR_LOAD,
                outline="",
                tags=("bf_ambient", "bf_wave_load"),
            )
            self._bf_load_bars.append(bid)

    def _tick_ambient_wave(self) -> None:
        if not self.is_alive:
            return
        sy1 = self._bf_strip_y1
        yb = sy1 - max(1, self.vp.px(3))
        self._bf_wave_phase += 0.14
        t = self._bf_wave_phase
        for i, bid in enumerate(self._bf_sig_bars):
            h = 5 + int(
                17
                * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(t + i * 0.38)))
                * random.uniform(0.88, 1.0)
            )
            h = max(4, min(24, h))
            x0, _, x1, _ = self.canvas.coords(bid)
            self.canvas.coords(bid, x0, yb - h, x1, yb)
        fill = self._ambient_progress / 100.0
        for i, bid in enumerate(self._bf_load_bars):
            seg = (i + 1) / max(1, len(self._bf_load_bars))
            base = 0.25 + 0.75 * fill
            h = 3 + int(
                15
                * base
                * (0.65 + 0.35 * (0.5 + 0.5 * math.sin(t * 1.7 + i * 0.9)))
            )
            if seg > fill + 0.05:
                h = max(2, int(5 * random.random()))
            hot = fill > 0.45 and seg <= fill + 0.08
            self.canvas.itemconfig(
                bid,
                fill=T.BF_WAVE_BAR_LOAD_HOT if hot else T.BF_WAVE_BAR_LOAD,
            )
            h = max(3, min(20, h))
            x0, _, x1, _ = self.canvas.coords(bid)
            self.canvas.coords(bid, x0, yb - h, x1, yb)
        self.root.after(200, self._tick_ambient_wave)

    def toggle_info(self) -> None:
        if self.info_visible:
            self.hide_info()
        else:
            self.start_info_tour()

    def start_info_tour(self) -> None:
        self.info_visible = True
        self.info_page = 0
        self.show_info_step()

    def _wrap_text_to_box(self, text: str, max_chars: int = 50) -> str:
        import textwrap

        lines: list[str] = []
        for block in text.split("\n"):
            wrapped = textwrap.wrap(block, max_chars) or [""]
            lines.extend(wrapped)
        return "\n".join(lines)

    def show_info_step(self) -> None:
        self.clear_info()

        key, raw_text = C.INFO_PAGES[self.info_page]
        if key == "FINAL":
            self.show_big_theory_panels()
            return

        text = self._wrap_text_to_box(raw_text, 50)
        w, h = self.w, self.h
        vp = self.vp

        self.info_overlay = self.canvas.create_rectangle(
            0, 0, w, h, fill="black", stipple="gray50"
        )

        target = self.info_targets.get(key)
        if not target:
            self.next_info()
            return

        bb = self.canvas.bbox(target)
        if not bb:
            self.next_info()
            return
        x1, y1, x2, y2 = bb

        self.info_focus = self.canvas.create_rectangle(
            x1 - vp.px(6), y1 - vp.px(6), x2 + vp.px(6), y2 + vp.px(6),
            outline=T.BF_ACCENT, width=vp.wid(2),
        )

        BOX_W = vp.px(420)
        PADDING = vp.px(16)
        TITLE_H = vp.px(32)
        FOOTER_H = vp.px(26)
        lines = text.count("\n") + 1
        LINE_H = vp.px(18)
        BODY_H = lines * LINE_H
        BOX_H = TITLE_H + BODY_H + FOOTER_H + vp.px(14)

        gap = vp.px(20)
        # Справа от подсвеченного элемента, иначе слева.
        box_x = x2 + gap if x2 + gap + BOX_W <= w - gap else x1 - BOX_W - gap
        # Широкие панели (LOG, PROGRESS) занимают почти всю ширину экрана —
        # там оба варианта выталкивают окно за левый край и текст обрезается.
        # Прижимаем окно к видимой области.
        box_x = max(gap, min(box_x, w - BOX_W - gap))
        box_y = min(y1, h - BOX_H - gap)
        # Не даём окну INFO залезать на нижнюю прогресс-линию.
        pb_bb = self.canvas.bbox(self.pb_frame)
        if pb_bb:
            pb_top = pb_bb[1]
            max_box_y = pb_top - BOX_H - vp.px(10)
            box_y = min(box_y, max_box_y)
        box_y = max(0, box_y)

        self.info_box = self.canvas.create_rectangle(
            box_x, box_y, box_x + BOX_W, box_y + BOX_H,
            fill="#05080c", outline=T.BF_ACCENT, width=vp.wid(2),
        )

        self.info_title = self.canvas.create_text(
            box_x + BOX_W // 2,
            box_y + vp.px(16),
            text=key,
            fill=T.BF_ACCENT,
            font=vp.consolas(13, bold=True),
        )

        self.info_text = self.canvas.create_text(
            box_x + PADDING,
            box_y + TITLE_H,
            anchor="nw",
            text=text,
            fill="#aee6ff",
            width=BOX_W - PADDING * 2,
            font=vp.consolas(11),
            justify="left",
        )

        self.info_counter = self.canvas.create_text(
            box_x + BOX_W // 2,
            box_y + BOX_H - vp.px(12),
            text=f"{self.info_page + 1}/{len(C.INFO_PAGES)}  (CLICK)",
            fill=T.BF_ACCENT,
            font=vp.consolas(9, bold=True),
        )

        for obj in (self.info_overlay, self.info_box, self.info_text):
            self.canvas.tag_bind(obj, "<Button-1>", self.next_info)

        for obj in (
            self.info_overlay,
            self.info_focus,
            self.info_box,
            self.info_text,
            self.info_counter,
            self.info_title,
        ):
            self.canvas.tag_raise(obj)

        if self.canvas.find_withtag("mivlgu"):
            self.canvas.tag_raise("mivlgu")

    def show_big_theory_panels(self) -> None:
        self.clear_info()
        w, h = self.w, self.h
        vp = self.vp

        self.info_overlay = self.canvas.create_rectangle(
            0, 0, w, h, fill="#000510", stipple="gray50"
        )

        x1, y1 = w // 2 - vp.px(440), h // 2 - vp.px(220)
        x2, y2 = w // 2 + vp.px(440), h // 2 + vp.px(220)
        self.info_big_panel = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill="#040608", outline=T.BF_ACCENT, width=vp.wid(2),
        )

        body = self._wrap_text_to_box(C.INFO_FINAL_THEORY + C.EDUCATION_APPEND, 72)
        self.info_big_text = self.canvas.create_text(
            w // 2,
            h // 2,
            text=body,
            fill="#b8e8ff",
            font=vp.consolas(12),
            width=x2 - x1 - vp.px(48),
            justify="left",
        )

        self.info_counter = self.canvas.create_text(
            w // 2,
            h - vp.px(40),
            text="CLICK TO EXIT INFO",
            fill=T.BF_ACCENT,
            font=vp.consolas(11, bold=True),
        )

        for obj in (
            self.info_overlay,
            self.info_big_panel,
            self.info_big_text,
            self.info_counter,
        ):
            self.canvas.tag_bind(obj, "<Button-1>", self.hide_info)

        self.canvas.tag_raise(self.info_overlay)
        for item in (self.info_big_panel, self.info_big_text, self.info_counter):
            self.canvas.tag_raise(item)

        if self.canvas.find_withtag("mivlgu"):
            self.canvas.tag_raise("mivlgu")

    def next_info(self, e=None) -> None:
        self.info_page += 1
        if self.info_page >= len(C.INFO_PAGES):
            self.hide_info()
        else:
            self.show_info_step()

    def clear_info(self) -> None:
        for attr in (
            "info_title",
            "info_overlay",
            "info_focus",
            "info_box",
            "info_text",
            "info_counter",
            "info_big_panel",
            "info_big_text",
        ):
            obj = getattr(self, attr, None)
            if obj:
                self.canvas.delete(obj)
                setattr(self, attr, None)

    def hide_info(self, event=None) -> None:
        self.clear_info()
        self.info_visible = False

    def update_progress(self, percent):
        percent = max(0, min(100, percent))
        self._ambient_progress = percent
        vp = self.vp
        full_width = self.w - vp.px(84)
        new_width = int(full_width * (percent / 100))
        left = vp.px(42)

        self.canvas.coords(
            self.pb_fill,
            left,
            self.pb_y + vp.px(2),
            left + new_width,
            self.pb_y + vp.px(20)
        )

        self.canvas.itemconfig(self.pb_text, text=f"PROGRESS: {percent}%")

    def _tick_progress_scan(self) -> None:
        if not self.is_alive:
            return
        self._pb_scan_phase += 0.06
        vp = self.vp
        fx0, fy0, fx1, fy1 = self.canvas.coords(self.pb_fill)
        width = fx1 - fx0
        scan_w = min(vp.px(26), max(0, width))
        if width < vp.px(6):
            self.canvas.coords(self.pb_scan, 0, 0, 0, 0)
        else:
            span = max(0.0, width - scan_w)
            phase = (math.sin(self._pb_scan_phase) + 1) / 2
            sx = fx0 + phase * span
            self.canvas.coords(self.pb_scan, sx, fy0, sx + scan_w, fy1)
        self.root.after(70, self._tick_progress_scan)

    def calculate_log_limit(self):
        vp = self.vp
        panel_top = vp.px(132)
        panel_bottom = self.h - vp.px(260)
        panel_height = panel_bottom - panel_top
        line_height = vp.px(16)
        self.log_max_lines = max(4, int(panel_height / line_height))

    # ================== HOVER ==================
    def _topbar_hover(self, rect, label, entering: bool) -> None:
        vp = self.vp
        if entering:
            self.canvas.itemconfig(rect, fill=T.BF_BUTTON_HOVER, outline=T.HOVER_OUTLINE, width=vp.wid(3))
            self.canvas.itemconfig(label, fill=T.TEXT_BRIGHT)
        else:
            self.canvas.itemconfig(rect, fill="", outline=T.BF_ACCENT, width=vp.wid(2))
            self.canvas.itemconfig(label, fill=T.BF_ACCENT)

    def hover_on(self, idx):
        if not self.ready:
            return
        self.canvas.itemconfig(self.network_rects[idx], fill="#13384a")

    def hover_off(self, idx):
        self.canvas.itemconfig(self.network_rects[idx], fill=T.BF_PANEL_BG)

    def set_dict_profile(self, key: str) -> None:
        if key not in C.DICT_PROFILES:
            return
        self.dict_profile = key
        active = T.BF_ACCENT
        dim = T.BF_PANEL_OUTLINE
        vp = self.vp
        if key == "fast":
            self.canvas.itemconfig(self.prof_fast_r, outline=active, width=vp.wid(2))
            self.canvas.itemconfig(self.prof_fast_t, fill=active)
            self.canvas.itemconfig(self.prof_deep_r, outline=dim, width=vp.wid(1))
            self.canvas.itemconfig(self.prof_deep_t, fill=T.BF_TEXT_DIM)
        else:
            self.canvas.itemconfig(self.prof_deep_r, outline=active, width=vp.wid(2))
            self.canvas.itemconfig(self.prof_deep_t, fill=active)
            self.canvas.itemconfig(self.prof_fast_r, outline=dim, width=vp.wid(1))
            self.canvas.itemconfig(self.prof_fast_t, fill=T.BF_TEXT_DIM)

    def _profile_hover(self, key: str, entering: bool) -> None:
        if self.dict_profile == key:
            return
        r = self.prof_fast_r if key == "fast" else self.prof_deep_r
        t = self.prof_fast_t if key == "fast" else self.prof_deep_t
        if entering:
            self.canvas.itemconfig(r, fill=T.BF_BUTTON_HOVER, outline=T.HOVER_OUTLINE)
            self.canvas.itemconfig(t, fill=T.TEXT_BRIGHT)
        else:
            self.canvas.itemconfig(r, fill=T.BF_PANEL_BG, outline=T.BF_PANEL_OUTLINE)
            self.canvas.itemconfig(t, fill=T.BF_TEXT_DIM)

    # ================== LOG ==================
    def log(self, text):
        self.logs.append(text)
        if len(self.logs) > self.log_max_lines:
            self.logs = self.logs[-self.log_max_lines:]

        self.canvas.itemconfig(self.logbox, text="\n".join(self.logs))
        self.canvas.update_idletasks()

    def draw_network_map(self):
        cx, cy = self.network_center
        vp = self.vp
        self._net_map_r = vp.px(22)
        self._net_label_dy = vp.px(34)

        self.net_devices = [
            {"name": "YOU", "pos": (0, 0), "icon": "👤", "role": "attacker"},

            {"name": "ROUTER", "pos": (-130, -80), "icon": "📡", "role": "node"},
            {"name": "PHONE", "pos": (-160, 90), "icon": "📱", "role": "node"},
            {"name": "LAPTOP", "pos": (140, 110), "icon": "💻", "role": "node"},

            {"name": "CAMERA", "pos": (150, -60), "icon": "📷", "role": "node"},
            {"name": "SMART TV", "pos": (0, 160), "icon": "📺", "role": "node"},
            {"name": "NAS", "pos": (0, -170), "icon": "🗄", "role": "node"},
        ]

        self.net_nodes = []
        self.net_edges = []
        self.net_phase = []
        self.net_amp = []

        # линии
        for i in range(1, len(self.net_devices)):
            x1 = cx
            y1 = cy
            px, py = self.net_devices[i]["pos"]
            x2 = cx + vp.px(px)
            y2 = cy + vp.px(py)

            line = self.canvas.create_line(
                x1, y1, x2, y2,
                fill=T.BF_MAP_LINE, width=vp.wid(1)
            )
            self.net_edges.append(line)

        # узлы
        r = self._net_map_r
        ldy = self._net_label_dy
        for dev in self.net_devices:
            px, py = dev["pos"]
            x = cx + vp.px(px)
            y = cy + vp.px(py)

            color = T.BF_ACCENT

            circ = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                outline=color, width=vp.wid(2)
            )

            ico = self.canvas.create_text(
                x, y,
                text=dev["icon"],
                fill=color,
                font=vp.consolas(18)
            )

            txt = self.canvas.create_text(
                x, y + ldy,
                text=dev["name"],
                fill="#9ecfe0",
                font=vp.consolas(9, bold=True)
            )

            self.net_nodes.append({
                "circ": circ,
                "ico": ico,
                "txt": txt,
                "x": x,
                "y": y,
                "dev_name": dev["name"],
            })

            self.net_phase.append(random.uniform(0, 6.28))
            self.net_amp.append(random.uniform(0.6, 1.6) * vp.scale)

        self.net_active = True
        self.animate_network_map()

    def animate_network_map(self):
        if not self.net_active:
            return

        r = getattr(self, "_net_map_r", self.vp.px(22))
        ldy = getattr(self, "_net_label_dy", self.vp.px(34))

        for i, node in enumerate(self.net_nodes):
            self.net_phase[i] += 0.02
            dx = math.sin(self.net_phase[i]) * self.net_amp[i]
            dy = math.cos(self.net_phase[i]) * self.net_amp[i]

            x = node["x"] + dx
            y = node["y"] + dy

            self.canvas.coords(node["circ"], x - r, y - r, x + r, y + r)
            self.canvas.coords(node["ico"], x, y)
            self.canvas.coords(node["txt"], x, y + ldy)

        # перерисуем линии
        cx, cy = self.network_center

        for idx in range(len(self.net_edges)):
            node = self.net_nodes[idx + 1]
            ax = self.canvas.coords(node["ico"])[0]
            ay = self.canvas.coords(node["ico"])[1]

            self.canvas.coords(self.net_edges[idx], cx, cy, ax, ay)

        self.root.after(40, self.animate_network_map)

    # ================== SCAN ==================
    def start_scan(self):
        self.log("SAFE MODE ENABLED")
        self.log("No real Wi-Fi attack is performed.")
        self.log("")
        self.log("Starting simulated scan...")
        self.idx = 0
        self.scan_step()

    def scan_step(self):
        if self.idx >= len(self.networks):
            self.log("")
            self.log("Scan completed.")
            self.log("Select network to start simulation.")
            self.ready = True
            return

        net = self.networks[self.idx]
        self.canvas.itemconfig(
            self.network_items[self.idx],
            text=f"[OK] {net['ssid']}   {net['signal']} dBm",
            fill=T.BF_TEXT_BRIGHT
        )
        self.log(f"Found SSID: {net['ssid']}")
        self.idx += 1
        self.root.after(350, self.scan_step)

    # ================== SELECT ==================
    def select(self, idx):
        if not self.ready:
            self.log("Please wait for scan.")
            return
        if self.attack_active:
            self.log("[SYSTEM] Simulation already running — wait for completion or press BACK.")
            return

        for r in self.network_rects:
            self.canvas.itemconfig(r, outline="", width=self.vp.wid(1))

        self.canvas.itemconfig(self.network_rects[idx], outline=T.BF_ACCENT, width=self.vp.wid(2))

        net = self.networks[idx]
        self.log("")
        self.log(f"TARGET SELECTED: {net['ssid']}")
        prof = C.get_profile(self.dict_profile)
        self.log(str(prof["label"]))

        possible = ["ROUTER", "PHONE", "LAPTOP"]
        self.attack_target_name = random.choice(possible)
        self.log(f"ATTACK VECTOR: {self.attack_target_name}")

        self._highlight_router_on_map(net["ssid"])
        self.start_attack(net)

    def _highlight_router_on_map(self, ssid: str) -> None:
        if not self.net_nodes:
            return
        short = (ssid[:18] + "…") if len(ssid) > 18 else ssid
        for node in self.net_nodes:
            if node.get("dev_name") == "ROUTER":
                self.canvas.itemconfig(
                    node["txt"],
                    text=f"ROUTER\n[{short}]",
                    fill=T.BF_TEXT_BRIGHT,
                )
                break

    # ================== ATTACK ==================
    def start_attack(self, net):
        self.current = net
        self.attempt = 0
        self.phase_idx = 0
        self.log("")
        self.log("Handshake pipeline (simulated) — educational only.")
        self.attack_active = True
        self.attack_success = False
        self.update_progress(4)
        self.animate_attack_nodes()
        self.root.after(280, self.attack_phase_chain)

    def attack_phase_chain(self) -> None:
        if not self.is_alive or not self.attack_active:
            return
        if self.phase_idx >= len(C.HANDSHAKE_PHASES):
            self.log("[DICT] Starting PSK candidate pass (simulation only).")
            self.begin_bruteforce_attempts()
            return
        self.log(C.HANDSHAKE_PHASES[self.phase_idx])
        pct = 10 + self.phase_idx * 7
        self.update_progress(min(32, pct))
        self.phase_idx += 1
        self.root.after(420, self.attack_phase_chain)

    def begin_bruteforce_attempts(self) -> None:
        if not self.is_alive or not self.attack_active:
            return
        p = C.get_profile(self.dict_profile)
        self.max_attempts = int(p["max_attempts"])
        self._attempt_delay_ms = int(p["delay_ms"])
        self.attempt = 0
        self.attack_step()

    def attack_step(self):
        if self.attempt >= self.max_attempts:
            self.success() if self.current.get("target") else self.fail()
            return

        fake = "".join(random.choice(string.ascii_letters + "0123456789") for _ in range(10))
        self.log(f"[TRY {self.attempt:03d}] {fake}  → denied")

        span = max(1, self.max_attempts - 1)
        progress = 35 + int((self.attempt / span) * 65)
        self.update_progress(min(100, progress))

        self.attempt += 1
        self.root.after(self._attempt_delay_ms, self.attack_step)

    def success(self):
        self.log("")
        self.log(f"KEY FOUND: {self.target_password}")
        self.log("AUTHENTICATION SUCCESSFUL")
        self.log("")
        self.log("[LINK] Establishing session with router...")
        self.log("[LINK] Authentication token issued.")
        self.log("[LINK] Privilege level: ADMIN")
        self.log("[LINK] Secure channel: ESTABLISHED")
        self.log("")

        self.files = [
            "config_backup.bin",
            "password_store.db",
            "routing_table.dat",
            "dhcp_leases.txt",
            "firewall_rules.conf",
            "users_dump.json",
            "vpn_keys.enc"
        ]

        self.file_index = 0

        self.attack_success = True

        if self.is_alive:
            self.root.after(1200, self.download_next_file)

    def fail(self):
        self.log("")
        self.log("Password not found (simulation).")
        self.log(random.choice(C.FAIL_REASONS_NON_TARGET))
        self.log("Simulation finished. No real Wi-Fi traffic was sent.")
        self.update_progress(0)
        self.attack_active = False
        self.attack_success = False

    def animate_attack_nodes(self):
        if not self.attack_active:
            return

        self.attack_flash = not self.attack_flash

        for node in self.net_nodes:
            dev_name = node.get("dev_name", "")

            if dev_name == "YOU":
                color = T.BF_TEXT_BRIGHT if self.attack_flash else T.BF_ACCENT

            elif dev_name == self.attack_target_name:
                if self.attack_success:
                    color = "#22ff66"
                else:
                    color = "#ff3333" if self.attack_flash else "#ffaaaa"

            else:
                color = T.BF_MAP_LINE

            self.canvas.itemconfig(node["circ"], outline=color)
            self.canvas.itemconfig(node["ico"], fill=color)

        self.root.after(450, self.animate_attack_nodes)

    def download_next_file(self):
        if self.file_index >= len(self.files):
            self.log("")
            self.log("[DOWNLOAD] All files extracted successfully.")
            self.log("[SESSION] Terminating session.")
            if self.is_alive:
                self.root.after(1000, self.show_education_popup)
            return

        file = self.files[self.file_index]
        self.download_percent = 0
        self.current_file = file

        self.log(f"[DOWNLOAD] {file} ...")
        self.root.after(200, self.download_step)

    def download_step(self):
        self.download_percent += random.randint(8, 20)

        if self.download_percent >= 100:
            self.download_percent = 100
            self.log(f"[DOWNLOAD] {self.current_file} ... {self.download_percent}% [OK]")
            self.file_index += 1
            self.root.after(500, self.download_next_file)
            return

        self.log(f"[DOWNLOAD] {self.current_file} ... {self.download_percent}%")
        self.root.after(180, self.download_step)
        self.update_progress(100)

    # ============ EDUCATION POPUP (SCROLLABLE) ============
    def show_education_popup(self):
        if not self.is_alive:
            return
        vp = self.vp
        # затемнение + панель
        self.canvas.create_rectangle(
            0, 0, self.w, self.h,
            fill="#000000", stipple="gray50", tags="edu"
        )

        x1 = self.w // 2 - vp.px(420)
        y1 = self.h // 2 - vp.px(270)
        x2 = self.w // 2 + vp.px(420)
        y2 = self.h // 2 + vp.px(270)

        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline=T.BF_ACCENT, width=vp.wid(2), fill=T.BF_EDU_BG,
            tags="edu"
        )

        self.canvas.create_text(
            (x1 + x2) // 2, y1 + vp.px(25),
            text="SECURITY EDUCATION MODULE",
            fill=T.BF_ACCENT,
            font=vp.consolas(16, bold=True),
            tags="edu"
        )

        # рамка под текст
        tx1 = x1 + vp.px(20)
        ty1 = y1 + vp.px(60)
        tx2 = x2 - vp.px(20)
        ty2 = y2 - vp.px(80)

        self.canvas.create_rectangle(
            tx1, ty1, tx2, ty2,
            outline=T.BF_PANEL_OUTLINE, width=vp.wid(1), fill=T.BF_EDU_PANEL,
            tags="edu"
        )

        # Text + Scrollbar как объекты CANVAS
        self.edu_text = tk.Text(
            self.canvas,
            font=vp.consolas(11),
            bg=T.BF_EDU_PANEL,
            fg="#cceeff",
            wrap="word",
            relief="flat",
            insertbackground=T.BF_ACCENT
        )
        self.edu_scroll = tk.Scrollbar(
            self.canvas,
            orient="vertical",
            command=self.edu_text.yview
        )
        self.edu_text.configure(yscrollcommand=self.edu_scroll.set)

        self.edu_text.insert("1.0", self.get_education_text())
        self.edu_text.config(state="disabled")

        # размещаем через create_window, чтобы они были поверх канвы
        self.canvas.create_window(
            tx1 + vp.px(5),
            ty1 + vp.px(5),
            anchor="nw",
            window=self.edu_text,
            width=(tx2 - tx1) - vp.px(30),
            height=(ty2 - ty1) - vp.px(10),
            tags="edu"
        )

        self.canvas.create_window(
            tx2 - vp.px(18),
            ty1 + vp.px(5),
            anchor="nw",
            window=self.edu_scroll,
            height=(ty2 - ty1) - vp.px(10),
            tags="edu"
        )

        # кнопка CLOSE
        bx1 = (x1 + x2) // 2 - vp.px(100)
        bx2 = (x1 + x2) // 2 + vp.px(100)
        by1 = y2 - vp.px(45)
        by2 = y2 - vp.px(15)

        btn = self.canvas.create_rectangle(
            bx1, by1, bx2, by2,
            outline=T.BF_ACCENT, width=vp.wid(2),
            tags="edu"
        )
        txt = self.canvas.create_text(
            (bx1 + bx2) // 2, (by1 + by2) // 2,
            text="CLOSE",
            fill=T.BF_ACCENT,
            font=vp.consolas(12, bold=True),
            tags="edu"
        )

        for i in (btn, txt):
            self.canvas.tag_bind(i, "<Button-1>", lambda e: self.close_education())
            self.canvas.tag_bind(i, "<Enter>", lambda e: self.canvas.itemconfig(btn, fill=T.BF_BUTTON_HOVER))
            self.canvas.tag_bind(i, "<Leave>", lambda e: self.canvas.itemconfig(btn, fill=""))

        self.canvas.tag_raise("edu")
        self.canvas.tag_raise("mivlgu")

    def close_education(self):
        if getattr(self, "_edu_closed", False):
            return
        self._edu_closed = True
        # уничтожаем виджеты и всё, что помечено тегом edu
        try:
            self.edu_text.destroy()
            self.edu_scroll.destroy()
        except Exception:
            pass
        self.canvas.delete("edu")
        self.canvas.tag_raise("mivlgu")

    def get_education_text(self):
        body = (
            "⚠ ЧТО МОЖЕТ СДЕЛАТЬ ЗЛОУМЫШЛЕННИК:\n\n"
            "• Перехватывать логины, пароли, переписку\n"
            "• Получать доступ к аккаунтам\n"
            "• Подменять сайты (DNS-фишинг)\n"
            "• Атаковать другие устройства сети\n"
            "• Устанавливать трояны и шпионские программы\n"
            "• Использовать интернет жертвы\n"
            "• Управлять «умными» устройствами\n"
            "• Похищать документы и файлы\n"
            "• Подменять обновления ПО\n\n"
            "🛡 КАК ЗАЩИТИТЬСЯ:\n\n"
            "• Используйте пароли от 12 символов и длинее\n"
            "• Меняйте пароль роутера по умолчанию\n"
            "• Отключайте WPS\n"
            "• Используйте только WPA2 / WPA3\n"
            "• Регулярно обновляйте прошивку\n"
            "• Делайте гостевые сети для гостей и IoT\n"
            "• Проверяйте список подключённых устройств\n"
            "• В общественных Wi-Fi не вводите пароли и не заходите в банк\n"
            "• Используйте VPN и антивирус\n\n"
            "👨‍💻 ЗАЧЕМ ЭТО ДЕЛАЮТ ПЕНТЕСТЕРЫ:\n\n"
            "• Ищут реальные уязвимости до злоумышленников\n"
            "• Помогают предотвратить настоящие атаки\n"
            "• Проверяют настройки и архитектуру безопасности\n"
            "• Обучают администраторов и сотрудников\n"
            "• Защищают бизнес и данные клиентов\n"
            "• Помогают выполнять требования стандартов ИБ\n\n"
            "⚠ ЕСЛИ ЭТО СМОГЛА ПРОГРАММА — ЭТО СМОЖЕТ И ЧЕЛОВЕК.\n"
            "Позаботьтесь о защите своей сети.\n"
        )
        return body + C.EDUCATION_APPEND

    # ================== EXIT ==================
    def exit(self):
        if self._exit_in_progress:
            return
        self._exit_in_progress = True
        self.is_alive = False  # ⛔ модуль мёртв
        self.attack_active = False
        self.net_active = False

        if self.info_visible:
            self.hide_info()

        try:
            self.edu_text.destroy()
            self.edu_scroll.destroy()
        except Exception:
            pass

        self.canvas.delete("all")
        self.on_exit()

    # ================== MIVLGU GLITCH ==================
    def restore_mivlgu(self):
        vp = self.vp
        self.mivlgu = self.canvas.create_text(
            self.w - vp.px(20), self.h - vp.px(20),
            anchor="se",
            text="МИВЛГУ",
            fill=T.HUD_MIVLGU,
            font=vp.arial_black(22),
            tags="mivlgu"
        )
        self.animate_mivlgu()

    def animate_mivlgu(self):
        if not self.is_alive:
            return
        vp = self.vp
        j = vp.px(10)
        k = vp.px(6)
        dx = random.randint(-j, j)
        dy = random.randint(-k, k)

        glitch = self.canvas.create_text(
            self.w - vp.px(20) + dx,
            self.h - vp.px(20) + dy,
            anchor="se",
            text="МИВЛГУ",
            fill=random.choice(["#ffffff", "#cccccc", "#bbbbbb"]),
            font=vp.arial_black(22),
            tags="mivlgu"
        )

        self.canvas.tag_raise("mivlgu")
        self.canvas.after(70, lambda: self.canvas.delete(glitch))
        self.root.after(random.randint(2500, 5000), self.animate_mivlgu)

    # ================== SIGNAL SIM ==================
    def simulate_signal(self):
        if not self.is_alive:
            return
        for i, net in enumerate(self.networks):
            delta = random.randint(-2, 2)
            net["signal"] += delta
            net["signal"] = max(-90, min(-30, net["signal"]))

            status = "[OK]" if i < self.idx else "[..]"
            color = T.BF_TEXT_BRIGHT if i < self.idx else T.BF_TEXT_DIM

            self.canvas.itemconfig(
                self.network_items[i],
                text=f"{status} {net['ssid']}   {net['signal']} dBm",
                fill=color
            )

        self.root.after(1500, self.simulate_signal)
