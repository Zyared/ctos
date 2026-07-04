import math
import random
import time
import tkinter as tk

from ctos.config import IDLE_TIMEOUT_MS, MUSIC_FILE
from ctos.modules.registry import DEFAULT_MODULE_FACTORIES, Factory
from ctos.services.sound_service import SoundService
from ctos.ui import theme as T
from ctos.utils.tk_helpers import after_cancel_safe, draw_corner_frame
from ctos.ui.viewport import Viewport

_MODULE_STATES = {
    "BRUTEFORCE": "bruteforce",
    "ZERO-DAY": "zero_day",
}


class CtOSApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("CtOS")
        self.root.configure(bg="black")
        self.fullscreen = True
        self.root.attributes("-fullscreen", True)

        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.bind("<Return>", self.enter_pressed)

        self.canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.text = "МИВЛГУ"

        self.state = "intro"

        self.is_exiting = False

        # ==== АНИМИРОВАННЫЙ ФОН ====
        self.bg_step = 70          # размер клеточки (как в твоём draw_grid_background)
        self.bg_offset = 0.0       # текущее смещение по диагонали
        self.bg_anim_job = None    # after-job анимации фона


        self.music_enabled = True
        self.music_file = MUSIC_FILE
        self.sound_service = SoundService()
        self.sounds = self.sound_service.sounds
        self.module_factories: dict[str, Factory | None] = dict(DEFAULT_MODULE_FACTORIES)

        # флаги и джобы для графа
        self.graph_active = False
        self.graph_motion_job = None
        self.graph_edges_job = None
        self.graph_jobs = []

        self.glitch_active = True  # гличи ТОЛЬКО на заставке
        self.global_glitch_job = None

        # джоб для глича МИВЛГУ
        self.mivlgu_job = None

        self.idle_timeout = IDLE_TIMEOUT_MS
        self.idle_job = None

        self.loader_active = False
        self._module_launch_lock = False

        self.grid_pulse_active = False
        self._grid_pulse_job = None
        self._grid_pulses: list[dict] = []
        self._wd_grid_step = T.WD_GRID_STEP

        self._hud_profiler_job = None
        self._hud_feed_job = None
        self._hud_map_job = None
        self._map_circle_ids: list[int] = []
        self._map_label_ids: list[int] = []
        self._map_subtitle = None
        self._profiler_index = 0
        self._feed_index = 0
        self._map_active = 0
        self._last_hover_sound_ts = 0.0
        self._exit_flash_pending = False

        # отслеживаем активность пользователя
        self.root.bind_all("<Motion>", self.reset_idle_timer)
        self.root.bind_all("<Key>", self.reset_idle_timer)
        self.root.bind_all("<Button>", self.reset_idle_timer)

        self.reset_idle_timer()

        self.draw_menu()
        self.schedule_next_glitch()

    def _refresh_viewport(self) -> None:
        self.vp = Viewport.from_canvas(self.canvas, self.root)
        self.w = self.vp.w
        self.h = self.vp.h

    # ================= МЕНЮ С ГЛИЧЕМ (ЗАСТАВКА) =================
    def draw_menu(self):
        self._refresh_viewport()
        self.state = "intro"
        self.center_x = self.w // 2
        vp = self.vp
        start_y = self.h // 2 - vp.px(420)

        logo = [
"                                         -+#%%%%%%%#*-                                          ",
"                                     +@%=.           .=#@*.                                     ",
"                                  =@*                     +@+                                   ",
"                                *@-                         :@*                                 ",
"                              :@-   =                     -   :@=                               ",
"                             #@     @%                   =@-    %@                              ",
"                            %#      @@+                 :@@-     *@                             ",
"                           *@       @-@-      #@@       @+@-      %%                            ",
"                           @.       @ :@     @* .@-    #* %-       @:                           ",
"                          *#        @  +%  :@:    @#  +%  %-       *%                           ",
"                          #-        @   ###%       *@#@   %-       .@                           ",
"                          #-        @   :@%         =@+   %-        @                           ",
"                          #=        @  :@@@.        %@@+  %-       :@                           ",
"                          +@        @ +@@*@@*+++++*@@#%@%.%-       %#                           ",
"                           @:       @@#    %#     -@.   +@@:       @                            ",
"                           -@       @-      @-    @=     :@:      @+                            ",
"                            =@              :@   #%              @*                             ",
"                             :@:             +@ :@             .@-                              ",
"                               %@             @%@:            #@                                ",
"                                 @%            @*           *@:                                 ",
"                                   *@+                   =%#                                    ",
"                                      +%%*=.       .-*%%+.                                      ",
"                                           :-+++++-:                                            "
        ]

        y = start_y
        for line in logo:
            self.canvas.create_text(self.center_x, y, text=line,
                                    fill="#8f8f8f", font=vp.consolas(9), anchor="center")
            y += vp.px(16)

        self.logo_y = y + vp.px(50)
        self.base_logo = self.canvas.create_text(
            self.center_x, self.logo_y,
            text=self.text,
            fill="white",
            font=vp.arial_black(90),
            anchor="center"
        )

        self.ctos_tagline = self.canvas.create_text(
            self.center_x, self.logo_y + vp.px(80),
            text="CtOS // CENTRAL OPERATING SYSTEM",
            fill="#d0d0d0",
            font=vp.consolas(22, bold=True)
        )

        self.ctos_subtitle = self.canvas.create_text(
            self.center_x, self.logo_y + vp.px(120),
            text="МИВЛГУ — ИНФОРМАЦИОННАЯ БЕЗОПАСНОСТЬ",
            fill="#bfbfbf",
            font=vp.consolas(18, bold=True)
        )

        self.sub = self.canvas.create_text(
            self.center_x, self.logo_y + vp.px(170),
            text="Press Enter",
            fill="#dddddd",
            font=vp.consolas(22)
        )

        self.hint = self.canvas.create_text(
            self.center_x, self.h - vp.px(40),
            text="ENTER — ПРОДОЛЖИТЬ   F11 — ПОЛНЫЙ ЭКРАН   ESC — ВЫХОД",
            fill="#555555",
            font=vp.consolas(14)
        )
        self.is_exiting = False
        self.spawn_random_glitch()

    def reset_idle_timer(self, event=None):
        # если мы уже в заставке — не заводим таймер
        if self.glitch_active:
            return

        after_cancel_safe(self.root, self.idle_job)
        self.idle_job = self.root.after(self.idle_timeout, self.on_idle_timeout)

    def on_idle_timeout(self):
        # защита от повторных срабатываний
        if self.glitch_active:
            return

        # имитируем нажатие EXIT
        self.reboot_to_intro()

    def spawn_random_glitch(self):
        if not self.glitch_active:
            return
        # звук при каждом гличе
        random.choice(self.sounds["glitch"]).play()

        w, h = self.w, self.h

        glitch_type = random.choice([
            "slice", "block", "noise", "error", "override", "blackout", "flicker"
        ])

        vp = self.vp
        if glitch_type == "slice":
            y = random.randint(0, h)
            height = random.randint(vp.px(6), vp.px(18))
            offset = random.randint(-vp.px(100), vp.px(100))

            rect = self.canvas.create_rectangle(
                0, y, w, y + height,
                fill=random.choice(["#ffffff", "#48bfff", "#ff0000"]),
                outline="",
                tags="screen_glitch"
            )
            self.canvas.move(rect, offset, 0)

        elif glitch_type == "block":
            x = random.randint(0, w)
            y = random.randint(0, h)
            size = random.randint(vp.px(20), vp.px(80))

            self.canvas.create_rectangle(
                x, y,
                x + size, y + size,
                fill=random.choice(["#ff0033", "#48bfff", "#ffffff", "#ff4444"]),
                outline="",
                tags="screen_glitch"
            )

        elif glitch_type == "noise":
            for _ in range(random.randint(50, 150)):
                px = random.randint(0, w)
                py = random.randint(0, h)
                d = max(1, vp.px(2))
                self.canvas.create_rectangle(
                    px, py, px + d, py + d,
                    fill=random.choice(["#ffffff", "#48bfff", "#ff0033"]),
                    outline="",
                    tags="screen_glitch"
                )

        elif glitch_type == "error":
            self.sounds["error"].play()
            msg = random.choice([
                "ACCESS DENIED",
                "MEMORY CORRUPTED",
                "SYSTEM FAILURE",
                "KERNEL EXCEPTION",
                "DATA LOSS",
                "STACK OVERFLOW",
                "FATAL ERROR"
            ])

            self.canvas.create_text(
                random.randint(vp.px(150), w - vp.px(150)),
                random.randint(vp.px(100), h - vp.px(100)),
                text=msg,
                fill="#ff0033",
                font=vp.consolas(14, bold=True),
                tags="screen_glitch"
            )

        elif glitch_type == "override":
            self.canvas.create_text(
                w // 2,
                h // 2,
                text="SYSTEM OVERRIDE",
                fill="#ff2222",
                font=vp.consolas(36, bold=True),
                tags="screen_glitch"
            )

        elif glitch_type == "blackout":
            rect = self.canvas.create_rectangle(
                0, 0, w, h,
                fill="black",
                outline="",
                tags="screen_glitch"
            )

        elif glitch_type == "flicker":
            self.sounds["flicker"].play()
            rect = self.canvas.create_rectangle(
                0, 0, w, h,
                fill=random.choice(["#100000", "#001820", "#001010"]),
                outline="",
                tags="screen_glitch"
            )

        # удалить глюки быстро
        self.root.after(random.randint(100, 260),
                        lambda: self.canvas.delete("screen_glitch"))

        # запуск следующего
        self.global_glitch_job = self.root.after(
            random.randint(350, 1200),
            self.spawn_random_glitch
        )



    # ================= ГЛИЧ ЗАСТАВКИ =================
    def schedule_next_glitch(self):
        self.glitch_job = self.root.after(random.randint(2000, 3000), self.start_glitch)

    def start_glitch(self):
        self.glitch_frames = random.randint(3, 6)
        self.run_glitch_frame()

    def run_glitch_frame(self):
        if self.glitch_frames <= 0:
            self.canvas.delete("glitch")
            self.schedule_next_glitch()
            return

        self.canvas.delete("glitch")
        vp = self.vp
        top = self.logo_y - vp.px(45)
        bottom = self.logo_y + vp.px(45)

        for _ in range(random.randint(1, 3)):
            slice_y = random.randint(top, bottom)
            slice_h = random.randint(vp.px(6), vp.px(14))
            shift_x = random.randint(-vp.px(25), vp.px(25))
            color = random.choice(["#ffffff", "#dddddd", "#bbbbbb"])

            self.canvas.create_text(
                self.center_x + shift_x, self.logo_y,
                text=self.text,
                fill=color,
                font=vp.arial_black(90),
                anchor="center",
                tags="glitch"
            )

            self.canvas.create_rectangle(
                0, slice_y - slice_h // 2,
                self.w, slice_y + slice_h // 2,
                fill="black", tags="glitch"
            )

        self.glitch_frames -= 1
        self.root.after(90, self.run_glitch_frame)

    # ================= ENTER -> ЗАГРУЗКА =================
    def enter_pressed(self, event=None):
        # ENTER работает ТОЛЬКО на заставке
        if self.state != "intro":
            return

        self.state = "boot"  # переходим в загрузку

        # выключаем все гличи
        self.stop_all_glitches()

        after_cancel_safe(self.root, self.global_glitch_job)
        self.global_glitch_job = None

        # чистим экран
        self.canvas.delete("all")

        # загружаем систему
        self.start_boot()

    # ================= ЗАГРУЗКА ОС =================
    def start_boot(self):
        self._refresh_viewport()
        self.sounds["boot"].play()
        self.console = tk.Text(
            self.root, bg="black", fg="#bdbdbd",
            font=self.vp.consolas(12), insertbackground="white",
            bd=0, highlightthickness=0, padx=0, pady=0,
            wrap="none", spacing1=0, spacing2=0, spacing3=0
        )
        self.console.place(x=0, y=0, relwidth=1, relheight=1)
        self.console.config(state="disabled")
        self.state = "boot"

        self.boot_lines = [
            "CtOS Bootloader v2.03",
            "Copyright (C) CtOS Corporation",
            "",
            "[ OK ] Initializing kernel modules",
            "[ OK ] Loading system libraries",
            "[ OK ] Mounting devices",
            "[ OK ] Loading virtual memory system",
            "[ OK ] Initializing cryptography engine",
            "[ OK ] Starting system daemon",
            "[ OK ] Scanning hardware devices",
            "[ OK ] Starting security services",
            "[ OK ] Launching firewall core",
            "[ OK ] Loading exploit framework",
            "[ OK ] Enabling network interfaces",
            "[ OK ] Starting intrusion detector",
            "[ OK ] Loading intelligence scripts",
            "[ OK ] Initializing surveillance module",
            "[ OK ] Mounting /dev/root",
            "[ OK ] Preparing runtime environment",
            "[ OK ] Cleaning temporary buffers",
            "[ OK ] Synchronizing clocks",
            "[ OK ] Checking disk integrity",
            "[ OK ] Activating kernel hooks",
            "[ OK ] Starting background services",
            "[ OK ] Final system check",
            "",
            "System successfully started.",
            "Switching to interactive mode...",
            "",
            "CtOS READY. LOADING INTERFACE..."
        ]

        self.line_index = 0
        self.print_next_line()

    def print_next_line(self):
        if self.line_index >= len(self.boot_lines):
            self.root.after(3000, self.show_main_ctos)
            return

        self.console.config(state="normal")
        self.console.insert("end", self.boot_lines[self.line_index] + "\n")
        self.console.see("end")
        self.console.config(state="disabled")

        self.line_index += 1
        self.root.after(random.randint(80, 160), self.print_next_line)

    # ================= ГЛАВНЫЙ ЭКРАН CtOS =================
    def show_main_ctos(self):
        self.console.destroy()
        self.canvas.delete("all")
        self._refresh_viewport()
        self.draw_grid_background()
        self.state = "main"
        self.start_grid_pulse_animation()
        self.draw_ctos_ui()
        self.start_system_monitor()
        self.schedule_mivlgu_glitch()
        self.force_mivlgu_top()
        self.stop_all_glitches()
        self.glitch_active = False
        self.canvas.delete("screen_glitch")
        self.reset_idle_timer()

    def _stop_hud_rotations(self) -> None:
        after_cancel_safe(self.root, self._hud_profiler_job)
        self._hud_profiler_job = None
        after_cancel_safe(self.root, self._hud_feed_job)
        self._hud_feed_job = None
        after_cancel_safe(self.root, self._hud_map_job)
        self._hud_map_job = None
        self._map_circle_ids.clear()
        self._map_label_ids.clear()
        self._map_subtitle = None
        self.canvas.delete("main_hud")

    def stop_main_menu_bg_anim(self) -> None:
        self.grid_pulse_active = False
        after_cancel_safe(self.root, self._grid_pulse_job)
        self._grid_pulse_job = None
        self._grid_pulses.clear()
        self.canvas.delete("grid_pulse")
        self._stop_hud_rotations()

    def _grid_neighbors(self, ix: int, iy: int) -> list[tuple[int, int]]:
        """Соседи по всем линиям сетки: ортогональ + диагонали (как X в ячейках)."""
        out: list[tuple[int, int]] = []
        for dx, dy in (
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (-1, -1), (1, -1), (-1, 1),
        ):
            nx, ny = ix + dx, iy + dy
            if self._pulse_ix0 <= nx <= self._pulse_ix1 and self._pulse_iy0 <= ny <= self._pulse_iy1:
                out.append((nx, ny))
        return out

    def _random_pulse_edge(self) -> tuple[tuple[int, int], tuple[int, int]]:
        for _ in range(120):
            ix = random.randint(self._pulse_ix0, self._pulse_ix1)
            iy = random.randint(self._pulse_iy0, self._pulse_iy1)
            nbs = self._grid_neighbors(ix, iy)
            if nbs:
                return (ix, iy), random.choice(nbs)
        return (self._pulse_ix0, self._pulse_iy0), (self._pulse_ix0 + 1, self._pulse_iy0)

    def start_grid_pulse_animation(self) -> None:
        self.stop_main_menu_bg_anim()
        self.grid_pulse_active = True
        step = self._wd_grid_step
        w, h = self.w, self.h
        margin = step * 3
        self._pulse_ix0 = int((-margin) // step) - 1
        self._pulse_ix1 = int((w + margin) // step) + 2
        self._pulse_iy0 = int((-margin) // step) - 1
        self._pulse_iy1 = int((h + margin) // step) + 2

        colors = T.PULSE_COLORS
        tail = 0.13
        for _ in range(T.GRID_PULSE_COUNT):
            i1, i2 = self._random_pulse_edge()
            line_id = self.canvas.create_line(
                0, 0, 1, 1,
                fill=random.choice(colors),
                width=self.vp.wid(1),
                tags=("grid_pulse",),
            )
            self._grid_pulses.append(
                {
                    "i1": i1,
                    "i2": i2,
                    "t": random.random() * 0.4,
                    "speed": random.uniform(0.028, 0.062),
                    "tail": tail + random.uniform(-0.02, 0.03),
                    "line_id": line_id,
                }
            )
        self._tick_grid_pulses()

    def _pulse_segment_coords(
        self, i1: tuple[int, int], i2: tuple[int, int], t: float, tail: float
    ) -> tuple[float, float, float, float]:
        s = self._wd_grid_step
        ax, ay = i1[0] * s, i1[1] * s
        bx, by = i2[0] * s, i2[1] * s
        t0 = max(0.0, t - tail)
        x1 = ax + (bx - ax) * t0
        y1 = ay + (by - ay) * t0
        x2 = ax + (bx - ax) * t
        y2 = ay + (by - ay) * t
        return x1, y1, x2, y2

    def _tick_grid_pulses(self) -> None:
        if not self.grid_pulse_active or self.state != "main":
            return
        if not self.canvas.find_withtag("grid_pulse"):
            return
        for p in self._grid_pulses:
            p["t"] += p["speed"]
            if p["t"] >= 1.0:
                i2 = p["i2"]
                prev = p["i1"]
                nbs = [n for n in self._grid_neighbors(*i2) if n != prev]
                if not nbs:
                    nbs = self._grid_neighbors(*i2)
                if not nbs:
                    p["i1"], p["i2"] = self._random_pulse_edge()
                    p["t"] = 0.0
                else:
                    p["i1"] = i2
                    p["i2"] = random.choice(nbs)
                    p["t"] = 0.0
            x1, y1, x2, y2 = self._pulse_segment_coords(
                p["i1"], p["i2"], min(1.0, p["t"]), p["tail"]
            )
            self.canvas.coords(p["line_id"], x1, y1, x2, y2)

        self._grid_pulse_job = self.root.after(T.GRID_PULSE_MS, self._tick_grid_pulses)

    def draw_grid_background(self):
        """
        Статичный фон Watch Dogs: сетка + X в ячейках + точки.
        «Световые» бегущие полосы — отдельно, см. start_grid_pulse_animation.
        """
        w, h = self.w, self.h
        step = self.vp.px(T.WD_GRID_STEP)
        self._wd_grid_step = max(8, step)
        margin = step * 3

        self.canvas.create_rectangle(0, 0, w, h, fill=T.GRID_BG, outline="", tags=("bg_base",))

        c_hv = T.GRID_HV
        c_diag = T.GRID_DIAG
        c_dot = T.GRID_DOT
        lw = self.vp.wid(1)
        dot_r = max(1, self.vp.px(1))

        x_min = -margin
        x_max = w + margin
        y_min = -margin
        y_max = h + margin

        ix0 = x_min // step - 1
        ix1 = x_max // step + 2
        iy0 = y_min // step - 1
        iy1 = y_max // step + 2

        for ix in range(ix0, ix1 + 1):
            x = ix * step
            self.canvas.create_line(x, y_min, x, y_max, fill=c_hv, width=lw, tags=("grid_bg",))

        for iy in range(iy0, iy1 + 1):
            y = iy * step
            self.canvas.create_line(x_min, y, x_max, y, fill=c_hv, width=lw, tags=("grid_bg",))

        for ix in range(ix0, ix1):
            for iy in range(iy0, iy1):
                x0 = ix * step
                y0 = iy * step
                self.canvas.create_line(
                    x0, y0, x0 + step, y0 + step, fill=c_diag, width=lw, tags=("grid_bg",),
                )
                self.canvas.create_line(
                    x0 + step, y0, x0, y0 + step, fill=c_diag, width=lw, tags=("grid_bg",),
                )

        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                x0 = ix * step
                y0 = iy * step
                self.canvas.create_oval(
                    x0 - dot_r, y0 - dot_r, x0 + dot_r, y0 + dot_r,
                    fill=c_dot, outline="", tags=("grid_bg",),
                )


    def _draw_hub_logo(self, cx: int, cy: int) -> None:
        """Центральный знак поверх рёбер графа + маска, чтобы линии не «резали» глиф."""
        vp = self.vp
        r = vp.px(160)
        r_mask = vp.px(156)
        self.canvas.create_oval(
            cx - r_mask, cy - r_mask, cx + r_mask, cy + r_mask,
            fill=T.GRID_BG, outline="", tags=("hub_logo",),
        )
        self.canvas.create_oval(
            cx - r - vp.px(3), cy - r - vp.px(3), cx + r + vp.px(3), cy + r + vp.px(3),
            outline=T.LOGO_OUTER, width=vp.wid(1), tags=("hub_logo",),
        )
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=T.LOGO_RING, width=vp.wid(2), tags=("hub_logo",),
        )
        self.canvas.create_line(
            cx - vp.px(70), cy + vp.px(50),
            cx - vp.px(30), cy - vp.px(60),
            cx, cy + vp.px(10),
            cx + vp.px(30), cy - vp.px(60),
            cx + vp.px(70), cy + vp.px(50),
            fill=T.LOGO_MARK, width=vp.wid(4), tags=("hub_logo",),
        )

    def _raise_hub_logo(self) -> None:
        if self.canvas.find_withtag("hub_logo"):
            self.canvas.tag_raise("hub_logo")

    def draw_ctos_ui(self):
        self._refresh_viewport()
        w, h = self.w, self.h
        vp = self.vp
        cx = w // 2
        cy = h // 2

        # Центр графа (логотип рисуем после рёбер — иначе пунктир «режет» знак)
        self.menu_center_x = cx
        self.menu_center_y = cy

        # СЛЕВА СВЕРХУ — HUD (ctOS)
        self.sys_text = self.canvas.create_text(
            vp.px(20), vp.px(20), anchor="nw",
            text="CtOS // CORE STATUS\n──────────────────\nInitializing...",
            fill=T.HUD_TITLE, font=vp.consolas(11),
        )

        # ВНИЗУ СПРАВА — МИВЛГУ (объект для глича)
        self.mivlgu_x = w - vp.px(20)
        self.mivlgu_y = h - vp.px(20)

        self.mivlgu_text = self.canvas.create_text(
            self.mivlgu_x, self.mivlgu_y,
            anchor="se",
            text="МИВЛГУ",
            fill=T.HUD_MIVLGU,
            font=vp.arial_black(22),
            tags=("mivlgu",)
        )

        # ===== МЕНЮ-ГРАФ ПО СЕРЕДИНЕ =====
        self.draw_exploit_menu()
        self._draw_hud_widgets(w, h)
        self.force_mivlgu_top()

        # ===== КНОПКА EXIT (справа сверху) =====
        bx = w - vp.px(140)
        by = vp.px(20)

        self.exit_btn = self.canvas.create_rectangle(
            bx, by,
            bx + vp.px(120), by + vp.px(40),
            outline=T.EXIT_OUTLINE,
            width=vp.wid(2),
            fill=T.EXIT_FILL,
            tags=("exit_btn",),
        )

        self.exit_txt = self.canvas.create_text(
            bx + vp.px(60), by + vp.px(20),
            text="EXIT",
            fill=T.EXIT_TEXT,
            font=vp.consolas(14, bold=True),
            tags=("exit_btn",),
        )

        # hover эффект
        for item in (self.exit_btn, self.exit_txt):
            self.canvas.tag_bind(item, "<Enter>", lambda e: self.canvas.itemconfig(self.exit_btn, fill=T.EXIT_FILL_HOVER))
            self.canvas.tag_bind(item, "<Leave>", lambda e: self.canvas.itemconfig(self.exit_btn, fill=T.EXIT_FILL))
            self.canvas.tag_bind(item, "<Button-1>", lambda e: self.exit_main_with_flash())

        self._draw_hub_logo(cx, cy)

        if self.canvas.find_withtag("main_hud"):
            self.canvas.tag_raise("main_hud")
        self._raise_hub_logo()
        self.canvas.tag_raise("mivlgu")
        self.canvas.tag_raise("exit_btn")

    def exit_main_with_flash(self, event=None):
        if self.state != "main" or self.is_exiting or self._exit_flash_pending:
            return
        self.sound_service.play_ui_click()
        self._exit_flash_pending = True
        self._exit_flash_step = 0
        self._run_exit_flash()

    def _run_exit_flash(self):
        if self._exit_flash_step >= 8:
            self.reboot_to_intro()
            return
        if self.state != "main":
            self._exit_flash_pending = False
            return
        try:
            alt = self._exit_flash_step % 2 == 1
            self.canvas.itemconfig(
                self.sys_text,
                fill=T.HUD_TITLE
                if alt
                else random.choice(["#ffffff", "#ff3355", "#aee6ff"]),
            )
        except tk.TclError:
            self._exit_flash_pending = False
            return
        try:
            self.sounds["flicker"].play()
        except KeyError:
            pass
        self._exit_flash_step += 1
        self.root.after(75, self._run_exit_flash)

    def _draw_hud_widgets(self, w: int, h: int) -> None:
        self._stop_hud_rotations()
        self._profiler_index = 0
        self._feed_index = 0
        self._map_active = 0
        self._map_circle_ids = []
        vp = self.vp

        py = h - vp.px(268)
        px0, px1 = vp.px(14), vp.px(356)
        draw_corner_frame(
            self.canvas, px0, py, px1, h - vp.px(18),
            outline=T.MENU_NODE_OUTLINE, frame_width=vp.wid(1),
            bracket_len=vp.px(14), bracket_width=vp.wid(2), tags=("main_hud",),
        )
        self.canvas.create_text(
            vp.px(22), py + vp.px(8), anchor="nw",
            text="PROFILER // TARGET LOCK",
            fill=T.HUD_TITLE, font=vp.consolas(10, bold=True),
            tags=("main_hud",),
        )
        self.canvas.create_text(
            vp.px(22), py + vp.px(26), anchor="nw",
            text="────────────────────────────",
            fill=T.HUD_MAP_DIM, font=vp.consolas(8),
            tags=("main_hud",),
        )
        self._profiler_body = self.canvas.create_text(
            vp.px(24), py + vp.px(44), anchor="nw",
            text="",
            fill="#aee6ff", font=vp.consolas(9),
            width=vp.px(320),
            justify="left",
            tags=("main_hud",),
        )
        self._refresh_profiler_body()

        # my0 держим ниже кнопки EXIT (by=20..60 design px) — иначе панель карты
        # заезжает под кнопку и её верхний правый угол обрезается.
        mx0, my0 = w - vp.px(432), vp.px(68)
        mx1, my1 = w - vp.px(128), vp.px(244)
        draw_corner_frame(
            self.canvas, mx0, my0, mx1, my1,
            outline=T.MENU_NODE_OUTLINE, frame_width=vp.wid(1),
            bracket_len=vp.px(12), bracket_width=vp.wid(2), tags=("main_hud",),
        )
        self.canvas.create_text(
            mx0 + vp.px(8), my0 + vp.px(6), anchor="nw",
            text=T.MAP_TITLE,
            fill=T.HUD_TITLE, font=vp.consolas(9, bold=True),
            tags=("main_hud",),
        )
        self._map_subtitle = self.canvas.create_text(
            mx0 + vp.px(8), my0 + vp.px(26), anchor="nw",
            text="",
            fill=T.HUD_MAP_ACCENT, font=vp.consolas(8),
            width=mx1 - mx0 - vp.px(16),
            justify="left",
            tags=("main_hud",),
        )
        pad = vp.px(12)
        aw = mx1 - mx0 - pad * 2
        ah = my1 - my0 - pad * 2 - vp.px(44)
        bx0 = mx0 + pad
        by0 = my0 + pad + vp.px(44)
        for sx0, sy0, sx1, sy1 in T.MAP_STREETS:
            self.canvas.create_line(
                bx0 + sx0 * aw,
                by0 + sy0 * ah,
                bx0 + sx1 * aw,
                by0 + sy1 * ah,
                fill=T.HUD_MAP_STREET,
                width=vp.wid(1),
                dash=vp.dash(2, 5),
                tags=("main_hud",),
            )
        for ia, ib in T.MAP_EDGES:
            a = T.MAP_NODES[ia]
            b = T.MAP_NODES[ib]
            ax = bx0 + a[0] * aw
            ay = by0 + a[1] * ah
            bx_ = bx0 + b[0] * aw
            by_ = by0 + b[1] * ah
            self.canvas.create_line(
                ax, ay, bx_, by_,
                fill=T.GRAPH_EDGE, width=vp.wid(1), dash=vp.dash(*T.GRAPH_EDGE_DASH), tags=("main_hud",),
            )
        for i, (nx, ny, code, _dname) in enumerate(T.MAP_NODES):
            mcx = bx0 + nx * aw
            mcy = by0 + ny * ah
            dot = vp.px(5)
            cid = self.canvas.create_oval(
                mcx - dot, mcy - dot, mcx + dot, mcy + dot,
                outline=T.MENU_NODE_OUTLINE, width=vp.wid(1), fill="#1a3d4d", tags=("main_hud",),
            )
            self._map_circle_ids.append(cid)
            lid = self.canvas.create_text(
                mcx + vp.px(9), mcy,
                anchor="w",
                text=code,
                fill=T.HUD_MAP_DIM,
                font=vp.consolas(8, bold=True),
                tags=("main_hud",),
            )
            self._map_label_ids.append(lid)
        self._apply_map_highlight()

        fy = h - vp.px(28)
        self._feed_text = self.canvas.create_text(
            w - vp.px(24), fy, anchor="se",
            text="",
            fill="#89c4d4", font=vp.consolas(9),
            width=vp.px(420),
            justify="right",
            tags=("main_hud",),
        )
        self._refresh_feed_text()

        self._hud_profiler_job = self.root.after(T.PROFILER_ROTATE_MS, self._tick_profiler)
        self._hud_feed_job = self.root.after(T.FEED_ROTATE_MS, self._tick_feed)
        self._hud_map_job = self.root.after(T.MAP_PULSE_MS, self._tick_map)

    def _refresh_profiler_body(self) -> None:
        row = T.PROFILER_ROWS[self._profiler_index]
        txt = (
            f"{row[0]}  //  {row[1]}\n"
            f"{row[2]}\n"
            f"{row[3]}\n"
            f"{row[4]}"
        )
        try:
            self.canvas.itemconfig(self._profiler_body, text=txt)
        except tk.TclError:
            pass

    def _tick_profiler(self) -> None:
        self._hud_profiler_job = None
        if self.state != "main" or not self.canvas.find_withtag("main_hud"):
            return
        self._profiler_index = (self._profiler_index + 1) % len(T.PROFILER_ROWS)
        self._refresh_profiler_body()
        self._hud_profiler_job = self.root.after(T.PROFILER_ROTATE_MS, self._tick_profiler)

    def _refresh_feed_text(self) -> None:
        n = len(T.FEED_LINES)
        a = T.FEED_LINES[self._feed_index % n]
        b = T.FEED_LINES[(self._feed_index + 1) % n]
        txt = f"{a}\n{b}"
        try:
            self.canvas.itemconfig(self._feed_text, text=txt)
        except tk.TclError:
            pass

    def _tick_feed(self) -> None:
        self._hud_feed_job = None
        if self.state != "main" or not self.canvas.find_withtag("main_hud"):
            return
        self._feed_index = (self._feed_index + 1) % len(T.FEED_LINES)
        self._refresh_feed_text()
        self._hud_feed_job = self.root.after(T.FEED_ROTATE_MS, self._tick_feed)

    def _apply_map_highlight(self) -> None:
        vp = self.vp
        for i, cid in enumerate(self._map_circle_ids):
            active = i == self._map_active
            self.canvas.itemconfig(
                cid,
                fill="#00e5ff" if active else "#1a3d4d",
                outline=T.MENU_HOVER_OUTLINE if active else T.MENU_NODE_OUTLINE,
                width=vp.wid(2) if active else vp.wid(1),
            )
        for i, lid in enumerate(self._map_label_ids):
            active = i == self._map_active
            self.canvas.itemconfig(
                lid,
                fill=T.HUD_TITLE if active else T.HUD_MAP_DIM,
            )
        if self._map_subtitle is not None:
            _nx, _ny, _code, dname = T.MAP_NODES[self._map_active]
            risk = (self._map_active * 7 + 11) % 24 + 6
            try:
                self.canvas.itemconfig(
                    self._map_subtitle,
                    text=f"{T.MAP_RISK_PREFIX}: {dname} // EST. RISK {risk}%",
                )
            except tk.TclError:
                pass

    def _tick_map(self) -> None:
        self._hud_map_job = None
        if self.state != "main" or not self.canvas.find_withtag("main_hud"):
            return
        self._map_active = (self._map_active + 1) % len(T.MAP_NODES)
        self._apply_map_highlight()
        self._hud_map_job = self.root.after(T.MAP_PULSE_MS, self._tick_map)

    # ================= МЕНЮ КАК ГРАФ (Obsidian-style) =================
    def draw_exploit_menu(self):
        cx, cy = self.menu_center_x, self.menu_center_y
        vp = self.vp
        self._graph_r = vp.px(42)
        self._graph_hit_pad = vp.px(4)
        self._graph_label_dy = vp.px(60)

        # ----- Описание узлов (дизайн в «логических» px 1920×1080) -----
        self.graph_nodes = [
            {"name": "BRUTEFORCE",       "pos": (-360, -120), "icon": "☠"},
            {"name": "SOCIAL ENG.",      "pos": (400, -160),  "icon": "☺"},
            {"name": "NETWORK SNIFFER",  "pos": (420, 200),   "icon": "⌁"},
            {"name": "PHISHING",         "pos": (-420, 220),  "icon": "⚓"},
            {"name": "ZERO-DAY",         "pos": (0,   -340),  "icon": "≡"},
            {"name": "DATA EXFIL",       "pos": (50,  360),   "icon": "▣"},
        ]

        # ----- Связи между узлами -----
        self.graph_edges = self.generate_random_edges()

        self.node_drawables = []
        self.edge_drawables = []

        # ----- Линии (edges) — «данные» ctOS, без smooth (дешевле для CPU) -----
        for a, b in self.graph_edges:
            pa = self.graph_nodes[a]["pos"]
            pb = self.graph_nodes[b]["pos"]
            x1 = cx + vp.px(pa[0])
            y1 = cy + vp.px(pa[1])
            x2 = cx + vp.px(pb[0])
            y2 = cy + vp.px(pb[1])
            line = self.canvas.create_line(
                x1, y1, x2, y2,
                fill=T.GRAPH_EDGE, width=vp.wid(1), dash=vp.dash(*T.GRAPH_EDGE_DASH),
            )
            self.edge_drawables.append(line)

        # ----- Узлы (nodes) -----
        r = self._graph_r
        hpad = self._graph_hit_pad
        ldy = self._graph_label_dy
        for i, node in enumerate(self.graph_nodes):
            x = cx + vp.px(node["pos"][0])
            y = cy + vp.px(node["pos"][1])

            # Невидимый хитбокс (чтобы кликалась вся область)
            hitbox = self.canvas.create_oval(
                x - r - hpad, y - r - hpad,
                x + r + hpad, y + r + hpad,
                outline="", fill="black"
            )

            circ = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                outline=T.MENU_NODE_OUTLINE, width=vp.wid(2), fill=T.MENU_NODE_FILL,
            )
            ico = self.canvas.create_text(
                x, y,
                text=node["icon"],
                fill=T.MENU_ICON,
                font=vp.consolas(26, bold=True),
            )
            label = self.canvas.create_text(
                x, y + ldy,
                text=node["name"],
                fill=T.MENU_LABEL,
                font=vp.consolas(10, bold=True),
            )

            # бинды — на всё (hitbox, круг, иконка, подпись)
            for item in (hitbox, circ, ico, label):
                self.canvas.tag_bind(item, "<Enter>",    lambda e, i=i: self.node_hover(i))
                self.canvas.tag_bind(item, "<Leave>",    lambda e, i=i: self.node_leave(i))
                self.canvas.tag_bind(item, "<Button-1>", lambda e, i=i: self.node_click(i))

            self.node_drawables.append({
                "hitbox": hitbox,
                "circ": circ,
                "ico": ico,
                "label": label,
                "x": x,
                "y": y
            })

        self.graph_active = True
        self.start_graph_motion()
        job = self.root.after(3500, self.reshuffle_graph)
        self.graph_jobs.append(job)
        self.graph_edges_job = job

    def generate_random_edges(self):
        edges = set()
        count = random.randint(6, 10)

        while len(edges) < count:
            a = random.randint(0, 5)
            b = random.randint(0, 5)
            if a != b:
                edges.add(tuple(sorted((a, b))))

        return list(edges)

    def reshuffle_graph(self):
        # удалить старые линии
        for line in self.edge_drawables:
            self.canvas.delete(line)

        # новые связи
        self.graph_edges = self.generate_random_edges()
        self.edge_drawables = []

        # перерисовать новые линии
        vp = self.vp
        for a, b in self.graph_edges:
            x1, y1 = self.node_drawables[a]["x"], self.node_drawables[a]["y"]
            x2, y2 = self.node_drawables[b]["x"], self.node_drawables[b]["y"]

            line = self.canvas.create_line(
                x1, y1,
                x2, y2,
                fill=T.GRAPH_EDGE,
                width=vp.wid(1),
                dash=vp.dash(*T.GRAPH_EDGE_DASH),
            )
            self.edge_drawables.append(line)

        if self.graph_active:
            job = self.root.after(random.randint(3000, 4000), self.reshuffle_graph)
            self.graph_jobs.append(job)
            self.graph_edges_job = job

        self._raise_hub_logo()

    # ----- Ховер узла -----
    def node_hover(self, idx):
        now = time.monotonic()
        if now - self._last_hover_sound_ts > 0.18:
            self.sound_service.play_ui_hover()
            self._last_hover_sound_ts = now
        self.canvas.itemconfig(
            self.node_drawables[idx]["circ"],
            outline=T.MENU_HOVER_OUTLINE,
            width=self.vp.wid(3),
            fill=T.MENU_HOVER_FILL,
        )
        self.canvas.itemconfig(self.node_drawables[idx]["ico"], fill=T.MENU_HOVER_ICON)
        self.canvas.itemconfig(self.node_drawables[idx]["label"], fill=T.MENU_HOVER_LABEL)

    def node_leave(self, idx):
        self.canvas.itemconfig(
            self.node_drawables[idx]["circ"],
            outline=T.MENU_NODE_OUTLINE,
            width=self.vp.wid(2),
            fill=T.MENU_NODE_FILL,
        )
        self.canvas.itemconfig(self.node_drawables[idx]["ico"], fill=T.MENU_ICON)
        self.canvas.itemconfig(self.node_drawables[idx]["label"], fill=T.MENU_LABEL)

    # ----- Клик по узлу -----
    def node_click(self, idx):
        if self.state != "main":
            return
        if self.loader_active or self._module_launch_lock:
            return
        name = self.graph_nodes[idx]["name"]
        factory = self.module_factories.get(name)
        if factory is None:
            self.show_overlay_message(f"{name}\nMODULE NOT INSTALLED", "#aaaaaa")
            return
        self.sound_service.play_ui_click()
        self._module_launch_lock = True
        self.sounds["glitchy_exploit"].play()
        self.show_watchdogs_loader(lambda n=name, f=factory: self._launch_module_safe(n, f))

    def _draw_mivlgu_watermark(self) -> None:
        self._refresh_viewport()
        vp = self.vp
        self.mivlgu_x = self.w - vp.px(20)
        self.mivlgu_y = self.h - vp.px(20)
        self.mivlgu_text = self.canvas.create_text(
            self.mivlgu_x,
            self.mivlgu_y,
            anchor="se",
            text="МИВЛГУ",
            fill="white",
            font=vp.arial_black(22),
            tags=("mivlgu",),
        )

    def _launch_module_safe(self, module_name: str, factory: Factory) -> None:
        try:
            self._run_module(module_name, factory)
        finally:
            self._module_launch_lock = False

    def _run_module(self, module_name: str, factory: Factory) -> None:
        self.stop_graph()
        state = _MODULE_STATES.get(module_name)
        if state is not None:
            self.state = state
        self.canvas.delete("all")
        self._draw_mivlgu_watermark()
        factory(self.canvas, self.root, self.return_to_menu)
        self.schedule_mivlgu_glitch()
        self.force_mivlgu_top()

    # ----- Движение графа (лёгкое дрожание) -----
    def start_graph_motion(self):
        s = self.vp.scale
        self.graph_phase = [random.uniform(0, 6.28) for _ in self.node_drawables]
        self.graph_amp = [random.uniform(0.8, 1.8) * s for _ in self.node_drawables]
        self.update_graph_motion()

    def update_graph_motion(self):
        if not self.graph_active:
            return

        r = getattr(self, "_graph_r", self.vp.px(42))
        hpad = getattr(self, "_graph_hit_pad", self.vp.px(4))
        ldy = getattr(self, "_graph_label_dy", self.vp.px(60))

        # Обновляем позиции узлов
        for i, node in enumerate(self.node_drawables):
            self.graph_phase[i] += 0.032
            dx = math.sin(self.graph_phase[i]) * self.graph_amp[i]
            dy = math.cos(self.graph_phase[i]) * self.graph_amp[i]

            x = node["x"] + dx
            y = node["y"] + dy

            self.canvas.coords(node["hitbox"], x - r - hpad, y - r - hpad, x + r + hpad, y + r + hpad)
            self.canvas.coords(node["circ"],   x - r,     y - r,     x + r,     y + r)
            self.canvas.coords(node["ico"],    x,         y)
            self.canvas.coords(node["label"],  x,         y + ldy)

        # Перерисовываем линии между ними
        for idx, (a, b) in enumerate(self.graph_edges):
            na = self.node_drawables[a]
            nb = self.node_drawables[b]
            ca = self.canvas.coords(na["ico"])
            cb = self.canvas.coords(nb["ico"])
            if len(ca) < 2 or len(cb) < 2:
                continue
            ax, ay = ca[0], ca[1]
            bx, by = cb[0], cb[1]
            self.canvas.coords(self.edge_drawables[idx], ax, ay, bx, by)

        if self.graph_active:
            job = self.root.after(T.GRAPH_MOTION_MS, self.update_graph_motion)
            self.graph_jobs.append(job)
            self.graph_motion_job = job

    # ===== ПОЛУПРОЗРАЧНОЕ СООБЩЕНИЕ В ЦЕНТРЕ =====
    def show_overlay_message(self, text, color):
        self._refresh_viewport()
        w, h = self.w, self.h
        vp = self.vp

        panel = self.canvas.create_rectangle(
            w // 2 - vp.px(320), h // 2 - vp.px(80),
            w // 2 + vp.px(320), h // 2 + vp.px(80),
            fill="#05080c", outline="#3b3b3b", width=vp.wid(2)
        )

        msg = self.canvas.create_text(
            w // 2, h // 2,
            text=text,
            fill=color,
            font=vp.consolas(22, bold=True),
            justify="center"
        )

        self.canvas.after(2400, lambda: (self.canvas.delete(panel),
                                         self.canvas.delete(msg)))

    def stop_graph(self):
        self.graph_active = False

        for job in self.graph_jobs:
            after_cancel_safe(self.root, job)
        self.graph_jobs.clear()

        after_cancel_safe(self.root, self.graph_motion_job)
        self.graph_motion_job = None

        after_cancel_safe(self.root, self.graph_edges_job)
        self.graph_edges_job = None

    def return_to_menu(self):
        # возврат из модуля сценария в главное меню CtOS
        self.stop_main_menu_bg_anim()
        self._module_launch_lock = False
        self.loader_active = False
        self.graph_active = False
        self.graph_jobs.clear()
        self.canvas.delete("all")
        self._refresh_viewport()
        # Вход в модуль сопровождается loader'ом (лого + прогресс + глитч),
        # а выход раньше был мгновенным обрубком. Короткий деглитч делает
        # переход симметричным.
        self._play_return_glitch(frames=4)

    def _play_return_glitch(self, frames: int) -> None:
        self.canvas.delete("return_glitch")
        w, h = self.w, self.h
        vp = self.vp
        self.canvas.create_rectangle(0, 0, w, h, fill="black", outline="", tags=("return_glitch",))
        if frames <= 0:
            self.canvas.delete("return_glitch")
            self._finish_return_to_menu()
            return
        for _ in range(random.randint(2, 4)):
            y = random.randint(0, h)
            height = random.randint(vp.px(4), vp.px(14))
            offset = random.randint(-vp.px(60), vp.px(60))
            rect = self.canvas.create_rectangle(
                0, y, w, y + height,
                fill=random.choice([T.MENU_NODE_OUTLINE, "#ffffff", "#0f2a38"]),
                outline="",
                tags=("return_glitch",),
            )
            self.canvas.move(rect, offset, 0)
        try:
            self.sounds["flicker"].play()
        except KeyError:
            pass
        self.root.after(70, lambda: self._play_return_glitch(frames - 1))

    def _finish_return_to_menu(self) -> None:
        self.canvas.delete("all")
        self.draw_grid_background()
        self.state = "main"
        self.start_grid_pulse_animation()
        self.draw_ctos_ui()
        self.start_system_monitor()
        self.schedule_mivlgu_glitch()
        self.force_mivlgu_top()

    # ================= МОНИТОРИНГ СИСТЕМЫ =================
    def start_system_monitor(self):
        self.system_messages = [
            "Integrity check: OK",
            "Exploit engine ready",
            "Target nodes detected",
            "Firewall bypass loaded",
            "Encryption synced",
            "Network trace active",
            "Memory scan running",
            "Telemetry stream online",
            "Remote access available"
        ]
        self.update_monitor()

    def update_monitor(self):
        msg = (
            "CtOS CORE STATUS\n"
            "-----------------\n"
            f"{random.choice(self.system_messages)}\n"
            f"CPU: {random.randint(10, 90)}%\n"
            f"RAM: {random.randint(20, 95)}%\n"
            f"Packets: {random.randint(500, 5000)}\n"
            "Security: ACTIVE"
        )
        self.canvas.itemconfig(self.sys_text, text=msg)
        self.root.after(1200, self.update_monitor)

    # ========= ГЛИЧ ДЛЯ МИВЛГУ ВНИЗУ =========
    def schedule_mivlgu_glitch(self):
        after_cancel_safe(self.root, self.mivlgu_job)
        self.mivlgu_job = None

        self.mivlgu_job = self.root.after(
            random.randint(3000, 6000),
            self.start_mivlgu_glitch
        )

    def start_mivlgu_glitch(self):
        if self.state != "main":
            return
        self.mivlgu_frames = random.randint(2, 4)
        self.run_mivlgu_glitch_frame()
        self.force_mivlgu_top()

    def run_mivlgu_glitch_frame(self):
        if self.state != "main":
            return
        if self.mivlgu_frames <= 0:
            try:
                self.canvas.itemconfig(self.mivlgu_text, fill=T.HUD_MIVLGU)
            except tk.TclError:
                pass
            self.schedule_mivlgu_glitch()
            return

        try:
            self.canvas.itemconfig(
                self.mivlgu_text,
                fill=random.choice([T.HUD_MIVLGU, "#e8fdff", T.HUD_MIVLGU, "#a8d8e8"]),
            )
        except tk.TclError:
            pass

        self.mivlgu_frames -= 1
        self.root.after(80, self.run_mivlgu_glitch_frame)
        self.force_mivlgu_top()

    def force_mivlgu_top(self):
        if self.canvas.find_withtag("mivlgu"):
            self.canvas.tag_raise("mivlgu")
        self._raise_hub_logo()
        if self.canvas.find_withtag("exit_btn"):
            self.canvas.tag_raise("exit_btn")

    # ================= FULLSCREEN =================
    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def exit_fullscreen(self, event=None):
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)

    def show_watchdogs_loader(self, callback):
        if self.loader_active:
            self._module_launch_lock = False
            return
        self.stop_main_menu_bg_anim()
        self.loader_active = True
        self.canvas.delete("all")

        self._refresh_viewport()
        w, h = self.w, self.h
        vp = self.vp

        ascii_logo = [
            "   ██████╗ ████████╗ ██████╗ ███████╗ ",
            "  ██╔════╝ ╚══██╔══╝██╔═══██╗██╔════╝ ",
            "  ██║         ██║   ██║   ██║███████╗ ",
            "  ██║         ██║   ██║   ██║╚════██║ ",
            "  ╚██████╗    ██║   ╚██████╔╝███████║ ",
            "   ╚═════╝    ╚═╝    ╚═════╝ ╚══════╝ ",
            "       CENTRAL OPERATING SYSTEM      "
        ]

        self.logo_objects = []
        start_y = h // 2 - vp.px(160)

        for i, line in enumerate(ascii_logo):
            t = self.canvas.create_text(
                w // 2, start_y + i * vp.px(22),
                text=line,
                fill="#9ef",
                font=vp.consolas(14, bold=True)
            )
            self.logo_objects.append(t)

        self.loading_text = self.canvas.create_text(
            w // 2, start_y + vp.px(260),
            text="INITIALIZING CtOS MODULE...",
            fill="#48bfff",
            font=vp.consolas(14, bold=True)
        )

        # Progress Bar Frame
        self.pb_y = start_y + vp.px(300)
        self._loader_pb_half = vp.px(240)
        self._loader_pb_h = vp.px(18)
        self._loader_pb_inner = vp.px(238)
        self.canvas.create_rectangle(
            w // 2 - self._loader_pb_half, self.pb_y,
            w // 2 + self._loader_pb_half, self.pb_y + self._loader_pb_h,
            outline="#48bfff", width=vp.wid(2)
        )

        # Progress Fill
        self.pb_fill = self.canvas.create_rectangle(
            w // 2 - self._loader_pb_inner, self.pb_y + vp.px(2),
            w // 2 - self._loader_pb_inner, self.pb_y + vp.px(16),
            fill="#48bfff", width=0
        )

        self.loader_progress = 0

        self.animate_watchdogs_glitch()
        self.animate_loader(callback)

    def animate_watchdogs_glitch(self):
        if not self.loader_active:
            return
        j = max(1, self.vp.px(3))

        for obj in self.logo_objects:
            if random.random() < 0.15:
                dx = random.randint(-j, j)
                dy = random.randint(-max(1, self.vp.px(2)), max(1, self.vp.px(2)))
                self.canvas.move(obj, dx, dy)

            if random.random() < 0.08:
                self.canvas.itemconfig(obj, fill=random.choice(["#9ef", "#ffffff", "#48bfff"]))

        self.root.after(100, self.animate_watchdogs_glitch)

    def animate_loader(self, callback):
        if not self.loader_active:
            return

        self.loader_progress += random.randint(2, 5)
        percent = min(100, self.loader_progress)

        inner = getattr(self, "_loader_pb_inner", self.vp.px(238))
        full = inner * 2
        fill_width = int(full * (percent / 100))
        dy2 = self.vp.px(2)
        dy16 = self.vp.px(16)

        self.canvas.coords(
            self.pb_fill,
            self.w // 2 - inner,
            self.pb_y + dy2,
            self.w // 2 - inner + fill_width,
            self.pb_y + dy16
        )

        self.canvas.itemconfig(self.loading_text, text=f"LOADING MODULE... {percent}%")

        if percent >= 100:
            self.loader_active = False
            self.root.after(400, callback)
            return

        self.root.after(200, lambda: self.animate_loader(callback))


    def reboot_to_intro(self):
        self._exit_flash_pending = False
        # стоп системы
        self.stop_main_menu_bg_anim()
        self.graph_active = False
        self.glitch_active = False
        self.state = "shutdown"

        for job in self.graph_jobs:
            after_cancel_safe(self.root, job)
        self.graph_jobs.clear()

        after_cancel_safe(self.root, self.graph_motion_job)
        self.graph_motion_job = None

        after_cancel_safe(self.root, self.graph_edges_job)
        self.graph_edges_job = None

        after_cancel_safe(self.root, self.idle_job)
        self.idle_job = None

        if self.is_exiting:
            return

        self.is_exiting = True

        # запускаем эффект выхода

        self.root.after(1500, lambda: self.sounds["exit"].play())
        self.root.after(3500, lambda: self.sounds["digital_error"].play())
        self.play_shutdown_effect()

    def play_shutdown_effect(self):
        self.shutdown_stage = 0
        self.root.after(1500, self.shutdown_stage1)

    def shutdown_stage1(self):
        self.shutdown_stage = 1
        self.shutdown_light_glitches(2)  # 2 редких глича

    def shutdown_light_glitches(self, count):
        if count <= 0:
            self.root.after(50, self.shutdown_stage2)
            return

        self.spawn_single_shutdown_glitch()
        self.root.after(600, lambda: self.shutdown_light_glitches(count - 1))

    def shutdown_stage2(self):
        self.shutdown_frames = 10
        self.shutdown_power = 50
        self.shutdown_intense_glitch()

    def shutdown_intense_glitch(self):
        if self.shutdown_frames <= 0:
            self.canvas.delete("shutdown")
            self.show_watchdogs_reboot()
            return

        self._refresh_viewport()
        w, h = self.w, self.h
        vp = self.vp

        for _ in range(self.shutdown_power):
            x = random.randint(0, w)
            y = random.randint(0, h)
            dx = random.randint(vp.px(60), vp.px(180))
            dy = random.randint(vp.px(10), vp.px(60))

            self.canvas.create_rectangle(
                x, y, x + dx, y + dy,
                fill=random.choice(["#ff0033", "#ffffff", "#48bfff"]),
                outline="",
                tags="shutdown"
            )

        if random.random() < 0.4:
            self.canvas.create_text(
                random.randint(vp.px(200), w - vp.px(200)),
                random.randint(vp.px(120), h - vp.px(120)),
                text=random.choice(["ERROR", "SYSTEM CRASH", "ACCESS LOST"]),
                fill="#ff0033",
                font=vp.consolas(20, bold=True),
                tags="shutdown"
            )

        self.shutdown_frames -= 1
        self.root.after(180, self.shutdown_intense_glitch)

    def spawn_single_shutdown_glitch(self):
        self._refresh_viewport()
        w, h = self.w, self.h
        vp = self.vp

        x = random.randint(0, w - vp.px(120))
        y = random.randint(0, h - vp.px(30))

        self.canvas.create_rectangle(
            x, y, x + random.randint(vp.px(80), vp.px(160)), y + random.randint(vp.px(10), vp.px(25)),
            fill=random.choice(["#ff0033", "#ffffff"]),
            outline="",
            tags="shutdown"
        )

        self.root.after(
            250,
            lambda: self.canvas.delete("shutdown")
        )

    def show_watchdogs_reboot(self):
        self.canvas.delete("all")

        self._refresh_viewport()
        w, h = self.w, self.h
        vp = self.vp

        # чёрный фон
        self.canvas.create_rectangle(0, 0, w, h, fill="black", outline="")

        # красное лого CtOS
        self.canvas.create_text(
            w // 2, h // 2 - vp.px(60),
            text="CtOS",
            fill="#ff0033",
            font=vp.arial_black(64)
        )

        # надпись REBOOT
        self.reboot_text = self.canvas.create_text(
            w // 2, h // 2 + vp.px(30),
            text="REBOOTING SYSTEM",
            fill="#ff0033",
            font=vp.consolas(20, bold=True)
        )

        self.root.after(3000, self.return_to_intro)



    def run_shutdown_glitch(self):
        if self.shutdown_frames <= 0:
            self.canvas.delete("shutdown")
            self.show_blackout()
            return

        self._refresh_viewport()
        w, h = self.w, self.h
        vp = self.vp

        glitch_count = self.shutdown_power * random.randint(6, 12)

        for _ in range(glitch_count):
            x = random.randint(0, w)
            y = random.randint(0, h)
            dx = random.randint(vp.px(80), vp.px(240))
            dy = random.randint(vp.px(20), vp.px(70))

            self.canvas.create_rectangle(
                x, y, x + dx, y + dy,
                fill=random.choice(["#ff0022", "#ffffff", "#48bfff", "#ff3355"]),
                outline="",
                tags="shutdown"
            )

        # сообщения усиливаются со временем
        if random.random() < 0.35:
            msg = random.choice([
                "SYSTEM FAILURE",
                "MEMORY COLLAPSE",
                "CORE DISCONNECT",
                "SESSION LOST",
                "CRITICAL ERROR",
                "ACCESS VIOLATION",
                "POWER LOSS",
                "NO SIGNAL"
            ])
            fs = random.randint(18, 28)
            self.canvas.create_text(
                random.randint(vp.px(200), w - vp.px(200)),
                random.randint(vp.px(100), h - vp.px(120)),
                text=msg,
                fill="#ff3333",
                font=vp.consolas(fs, bold=True),
                tags="shutdown"
            )

        self.shutdown_power += 1  # каждый кадр всё жестче
        self.shutdown_frames -= 1

        self.root.after(140, self.run_shutdown_glitch)  # было ~100 → замедлили для драматизма

    def show_blackout(self):
        self.canvas.delete("shutdown")
        self.canvas.delete("all")

        self._refresh_viewport()
        w, h = self.w, self.h

        # ЧЁРНЫЙ ЭКРАН
        self.canvas.create_rectangle(
            0, 0,
            w,
            h,
            fill="black",
            outline=""
        )

        # пауза перед возвратом
        self.root.after(1300, self.return_to_intro)

    def return_to_intro(self):
        self.stop_all_glitches()
        self.canvas.delete("all")
        self.glitch_active = True
        self.state = "intro"

        # возвращаем заставку
        self.draw_menu()
        self.schedule_next_glitch()

    def stop_all_glitches(self):
        self.glitch_active = False

        after_cancel_safe(self.root, getattr(self, "global_glitch_job", None))
        self.global_glitch_job = None

        after_cancel_safe(self.root, getattr(self, "glitch_job", None))
        self.glitch_job = None

        self.canvas.delete("screen_glitch")
        self.canvas.delete("glitch")

    def start_music(self) -> None:
        self.sound_service.start_background_music(self.music_enabled)

