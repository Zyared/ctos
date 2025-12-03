import tkinter as tk
import random
import math
import subprocess
from BruteforceModule import BruteforceModule
from NetworkSnifferModule import NetworkSnifferModule
import pygame
import os
from DataExfilModule import DataExfilModule
from ZeroDownModule import ZeroDownModule

class CtOSMenu:
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


        # MUSIC
        self.music_enabled = True
        self.music_file = os.path.join(os.path.dirname(__file__), "music.mp3")

        # SOUND SYSTEM
        pygame.mixer.init()
        self.sounds = {}

        base = os.path.join(os.path.dirname(__file__), "sound")

        self.sounds["glitch"] = [
            pygame.mixer.Sound(os.path.join(base, "glitch1.wav")),
            pygame.mixer.Sound(os.path.join(base, "glitch2.mp3")),
            pygame.mixer.Sound(os.path.join(base, "glitch3.mp3")),
            pygame.mixer.Sound(os.path.join(base, "glitch4.mp3")),
            pygame.mixer.Sound(os.path.join(base, "glitch5.mp3")),
        ]
        self.sounds["error"] = pygame.mixer.Sound(os.path.join(base, "error.mp3"))
        self.sounds["flicker"] = pygame.mixer.Sound(os.path.join(base, "flicker.mp3"))
        self.sounds["boot"] = pygame.mixer.Sound(os.path.join(base, "boot.wav"))
        self.sounds["exit"] = pygame.mixer.Sound(os.path.join(base, "exit.mp3"))
        self.sounds["digital_error"] = pygame.mixer.Sound(os.path.join(base, "digital_error.mp3"))
        self.sounds["glitchy_exploit"] = pygame.mixer.Sound(os.path.join(base, "glitchy_exploit.mp3"))

        # громкость
        for s in self.sounds["glitch"]:
            s.set_volume(0.05)

        self.sounds["error"].set_volume(0.05)
        self.sounds["flicker"].set_volume(0.05)
        self.sounds["boot"].set_volume(0.8)
        self.sounds["exit"].set_volume(0.4)
        self.sounds["glitchy_exploit"].set_volume(0.4)
        self.sounds["digital_error"].set_volume(0.4)

        # флаги и джобы для графа
        self.graph_active = False
        self.graph_motion_job = None
        self.graph_edges_job = None
        self.graph_jobs = []

        self.glitch_active = True  # гличи ТОЛЬКО на заставке
        self.global_glitch_job = None

        # джоб для глича МИВЛГУ
        self.mivlgu_job = None

        # ===== IDLE TIMER =====
        self.idle_timeout = 300000  # 2 минуты
        self.idle_job = None

        # отслеживаем активность пользователя
        self.root.bind_all("<Motion>", self.reset_idle_timer)
        self.root.bind_all("<Key>", self.reset_idle_timer)
        self.root.bind_all("<Button>", self.reset_idle_timer)

        self.reset_idle_timer()

        self.draw_menu()
        self.schedule_next_glitch()



    # ================= МЕНЮ С ГЛИЧЕМ (ЗАСТАВКА) =================
    def draw_menu(self):
        self.w = self.canvas.winfo_screenwidth()
        self.h = self.canvas.winfo_screenheight()
        self.state = "intro"
        self.center_x = self.w // 2
        start_y = self.h // 2 - 420

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
                                    fill="#8f8f8f", font=("Consolas", 9), anchor="center")
            y += 16

        self.logo_y = y + 50
        self.base_logo = self.canvas.create_text(
            self.center_x, self.logo_y,
            text=self.text,
            fill="white",
            font=("Arial Black", 90),
            anchor="center"
        )

        self.ctos = self.canvas.create_text(
            self.center_x, self.logo_y + 80,
            text="CtOS // CENTRAL OPERATING SYSTEM",
            fill="#d0d0d0",
            font=("Consolas", 22, "bold")
        )

        self.ctos = self.canvas.create_text(
            self.center_x, self.logo_y + 120,
            text="МИВЛГУ — ИНФОРМАЦИОННАЯ БЕЗОПАСНОСТЬ",
            fill="#bfbfbf",
            font=("Consolas", 18, "bold")
        )

        self.sub = self.canvas.create_text(
            self.center_x, self.logo_y + 170,
            text="Press Enter",
            fill="#dddddd",
            font=("Consolas", 22)
        )

        self.hint = self.canvas.create_text(
            self.center_x, self.h - 40,
            text="ENTER — ПРОДОЛЖИТЬ   F11 — ПОЛНЫЙ ЭКРАН   ESC — ВЫХОД",
            fill="#555555",
            font=("Consolas", 14)
        )
        self.is_exiting = False
        self.spawn_random_glitch()

    def reset_idle_timer(self, event=None):
        # если мы уже в заставке — не заводим таймер
        if self.glitch_active:
            return

        if self.idle_job:
            try:
                self.root.after_cancel(self.idle_job)
            except:
                pass

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

        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        glitch_type = random.choice([
            "slice", "block", "noise", "error", "override", "blackout", "flicker"
        ])

        if glitch_type == "slice":
            y = random.randint(0, h)
            height = random.randint(6, 18)
            offset = random.randint(-100, 100)

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
            size = random.randint(20, 80)

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
                self.canvas.create_rectangle(
                    px, py, px + 2, py + 2,
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
                random.randint(150, w - 150),
                random.randint(100, h - 100),
                text=msg,
                fill="#ff0033",
                font=("Consolas", 14, "bold"),
                tags="screen_glitch"
            )

        elif glitch_type == "override":
            self.canvas.create_text(
                w // 2,
                h // 2,
                text="SYSTEM OVERRIDE",
                fill="#ff2222",
                font=("Consolas", 36, "bold"),
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
        top = self.logo_y - 45
        bottom = self.logo_y + 45

        for _ in range(random.randint(1, 3)):
            slice_y = random.randint(top, bottom)
            slice_h = random.randint(6, 14)
            shift_x = random.randint(-25, 25)
            color = random.choice(["#ffffff", "#dddddd", "#bbbbbb"])

            self.canvas.create_text(
                self.center_x + shift_x, self.logo_y,
                text=self.text,
                fill=color,
                font=("Arial Black", 90),
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

        # отменяем глобальный глич
        if self.global_glitch_job:
            try:
                self.root.after_cancel(self.global_glitch_job)
            except:
                pass
            self.global_glitch_job = None

        # чистим экран
        self.canvas.delete("all")

        # загружаем систему
        self.start_boot()

    # ================= ЗАГРУЗКА ОС =================
    def start_boot(self):
        self.sounds["boot"].play()
        self.console = tk.Text(
            self.root, bg="black", fg="#bdbdbd",
            font=("Consolas", 12), insertbackground="white",
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
        self.draw_grid_background()
        self.draw_ctos_ui()
        self.start_system_monitor()
        self.schedule_mivlgu_glitch()
        self.force_mivlgu_top()
        self.stop_all_glitches()
        self.glitch_active = False
        self.canvas.delete("screen_glitch")
        self.state = "main"
        self.reset_idle_timer()


    def draw_grid_background(self):
        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()
        step = 70  # размер квадрата
        line_w = 2  # толщина линий

        # ===== ЧЁРНАЯ БАЗА =====
        self.canvas.create_rectangle(
            0, 0, w, h,
            fill="#05070b",
            outline=""
        )

        # ===== ОСНОВНАЯ СЕТКА =====
        for x in range(0, w, step):
            self.canvas.create_line(x, 0, x, h, fill="#1c1c1c", width=line_w)
        for y in range(0, h, step):
            self.canvas.create_line(0, y, w, y, fill="#1c1c1c", width=line_w)

        # ===== ДИАГОНАЛИ ТОЛЬКО В КАЖДОМ КВАДРАТЕ =====
        for x in range(0, w, step):
            for y in range(0, h, step):
                self.canvas.create_line(
                    x, y,
                    x + step, y + step,
                    fill="#111111", width=1
                )
                self.canvas.create_line(
                    x + step, y,
                    x, y + step,
                    fill="#111111", width=1
                )


    def draw_ctos_ui(self):
        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()
        cx = w // 2
        cy = h // 2

        # ЛОГОТИП
        r = 160
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="white", width=3)
        self.canvas.create_line(
            cx - 70, cy + 50,
            cx - 30, cy - 60,
            cx,      cy + 10,
            cx + 30, cy - 60,
            cx + 70, cy + 50,
            fill="white", width=4
        )

        # Сохраняем центр для графа
        self.menu_center_x = cx
        self.menu_center_y = cy

        # СЛЕВА СВЕРХУ — СИСТЕМА
        self.sys_text = self.canvas.create_text(
            20, 20, anchor="nw",
            text="CtOS CORE STATUS\n-----------------\nInitializing...",
            fill="#e0e0e0", font=("Consolas", 11)
        )

        # ВНИЗУ СПРАВА — МИВЛГУ (объект для глича)
        self.mivlgu_x = w - 20
        self.mivlgu_y = h - 20

        self.mivlgu_text = self.canvas.create_text(
            self.mivlgu_x, self.mivlgu_y,
            anchor="se",
            text="МИВЛГУ",
            fill="white",
            font=("Arial Black", 22),
            tags=("mivlgu",)
        )

        # ===== МЕНЮ-ГРАФ ПО СЕРЕДИНЕ =====
        self.draw_exploit_menu()
        self.force_mivlgu_top()

        # ===== КНОПКА EXIT (справа сверху) =====
        bx = self.canvas.winfo_screenwidth() - 140
        by = 20

        self.exit_btn = self.canvas.create_rectangle(
            bx, by,
            bx + 120, by + 40,
            outline="#ff4444",
            width=2
        )

        self.exit_txt = self.canvas.create_text(
            bx + 60, by + 20,
            text="EXIT",
            fill="#ff4444",
            font=("Consolas", 14, "bold")
        )

        # hover эффект
        for item in (self.exit_btn, self.exit_txt):
            self.canvas.tag_bind(item, "<Enter>", lambda e: self.canvas.itemconfig(self.exit_btn, fill="#300000"))
            self.canvas.tag_bind(item, "<Leave>", lambda e: self.canvas.itemconfig(self.exit_btn, fill=""))
            self.canvas.tag_bind(item, "<Button-1>", lambda e: self.reboot_to_intro())

    # ================= МЕНЮ КАК ГРАФ (Obsidian-style) =================
    def draw_exploit_menu(self):
        cx, cy = self.menu_center_x, self.menu_center_y

        # ----- Описание узлов -----
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

        # ----- Линии (edges) -----
        for a, b in self.graph_edges:
            x1, y1 = cx + self.graph_nodes[a]["pos"][0], cy + self.graph_nodes[a]["pos"][1]
            x2, y2 = cx + self.graph_nodes[b]["pos"][0], cy + self.graph_nodes[b]["pos"][1]
            line = self.canvas.create_line(
                x1, y1, x2, y2,
                fill="#2a6a8a", width=1, smooth=True
            )
            self.edge_drawables.append(line)

        # ----- Узлы (nodes) -----
        r = 42
        for i, node in enumerate(self.graph_nodes):
            x = cx + node["pos"][0]
            y = cy + node["pos"][1]

            # Невидимый хитбокс (чтобы кликалась вся область)
            hitbox = self.canvas.create_oval(
                x - r - 4, y - r - 4,
                x + r + 4, y + r + 4,
                outline="", fill="black"
            )

            circ = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                outline="white", width=2, fill=""
            )
            ico = self.canvas.create_text(
                x, y,
                text=node["icon"],
                fill="white",
                font=("Consolas", 26, "bold")
            )
            label = self.canvas.create_text(
                x, y + 60,
                text=node["name"],
                fill="#9aa7b1",
                font=("Consolas", 11, "bold")
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
        for a, b in self.graph_edges:
            x1, y1 = self.node_drawables[a]["x"], self.node_drawables[a]["y"]
            x2, y2 = self.node_drawables[b]["x"], self.node_drawables[b]["y"]

            line = self.canvas.create_line(
                x1, y1,
                x2, y2,
                fill="#2a6a8a",
                width=1,
                smooth=True
            )
            self.edge_drawables.append(line)

        if self.graph_active:
            job = self.root.after(random.randint(3000, 4000), self.reshuffle_graph)
            self.graph_jobs.append(job)
            self.graph_edges_job = job

    # ----- Ховер узла -----
    def node_hover(self, idx):
        self.canvas.itemconfig(self.node_drawables[idx]["circ"], outline="#48bfff", width=3)
        self.canvas.itemconfig(self.node_drawables[idx]["ico"],  fill="#9ee8ff")
        self.canvas.itemconfig(self.node_drawables[idx]["label"], fill="#9ee8ff")

    def node_leave(self, idx):
        self.canvas.itemconfig(self.node_drawables[idx]["circ"], outline="white", width=2)
        self.canvas.itemconfig(self.node_drawables[idx]["ico"],  fill="white")
        self.canvas.itemconfig(self.node_drawables[idx]["label"], fill="#9aa7b1")

    # ----- Клик по узлу -----
    def node_click(self, idx):
        name = self.graph_nodes[idx]["name"]
        if name == "BRUTEFORCE":
            self.sounds["glitchy_exploit"].play()
            self.show_watchdogs_loader(self.launch_bruteforce)
        elif name == "NETWORK SNIFFER":
            self.sounds["glitchy_exploit"].play()
            self.show_watchdogs_loader(self.launch_sniffer)
        elif name == "DATA EXFIL":
            self.sounds["glitchy_exploit"].play()
            self.show_watchdogs_loader(self.launch_exfil)
        elif name == "ZERO-DAY":
            self.sounds["glitchy_exploit"].play()
            self.show_watchdogs_loader(self.launch_zero_day)
        else:
            self.show_overlay_message(f"{name}\nMODULE NOT INSTALLED", "#aaaaaa")

    def launch_zero_day(self):
        # остановить граф-меню
        self.stop_graph()
        self.state = "zero_day"

        # очистить сцену
        self.canvas.delete("all")

        # нарисовать МИВЛГУ внизу справа
        self.mivlgu_x = self.canvas.winfo_screenwidth() - 20
        self.mivlgu_y = self.canvas.winfo_screenheight() - 20

        self.mivlgu_text = self.canvas.create_text(
            self.mivlgu_x, self.mivlgu_y,
            anchor="se",
            text="МИВЛГУ",
            fill="white",
            font=("Arial Black", 22),
            tags=("mivlgu",)
        )

        # 🔹 запускаем ZeroDownModule (мини-игра Zero-Day)
        # у него вся логика стартует прямо в __init__, .start() НЕ нужен
        self.zero_day = ZeroDownModule(self.canvas, self.root, self.return_to_menu)

        # включаем глич для МИВЛГУ
        self.schedule_mivlgu_glitch()
        self.force_mivlgu_top()

    def launch_exfil(self):
        self.stop_graph()
        self.canvas.delete("all")

        self.mivlgu_x = self.canvas.winfo_screenwidth() - 20
        self.mivlgu_y = self.canvas.winfo_screenheight() - 20

        self.mivlgu_text = self.canvas.create_text(
            self.mivlgu_x, self.mivlgu_y,
            anchor="se",
            text="МИВЛГУ",
            fill="white",
            font=("Arial Black", 22),
            tags=("mivlgu",)
        )

        self.data_exfil = DataExfilModule(self.canvas, self.root, self.return_to_menu)
        self.data_exfil.start()

        self.schedule_mivlgu_glitch()
        self.force_mivlgu_top()

    def launch_sniffer(self):
        self.stop_graph()
        self.canvas.delete("all")

        self.mivlgu_x = self.canvas.winfo_screenwidth() - 20
        self.mivlgu_y = self.canvas.winfo_screenheight() - 20

        self.mivlgu_text = self.canvas.create_text(
            self.mivlgu_x, self.mivlgu_y,
            anchor="se",
            text="МИВЛГУ",
            fill="white",
            font=("Arial Black", 22),
            tags=("mivlgu",)
        )

        self.sniffer = NetworkSnifferModule(self.canvas, self.root, self.return_to_menu)
        self.sniffer.start()

        self.schedule_mivlgu_glitch()
        self.force_mivlgu_top()

    # ----- Движение графа (лёгкое дрожание) -----
    def start_graph_motion(self):
        self.graph_phase = [random.uniform(0, 6.28) for _ in self.node_drawables]
        self.graph_amp   = [random.randint(1, 3)      for _ in self.node_drawables]
        self.update_graph_motion()

    def update_graph_motion(self):
        if not self.graph_active:
            return

        # Обновляем позиции узлов
        for i, node in enumerate(self.node_drawables):
            self.graph_phase[i] += 0.02
            dx = math.sin(self.graph_phase[i]) * self.graph_amp[i]
            dy = math.cos(self.graph_phase[i]) * self.graph_amp[i]

            x = node["x"] + dx
            y = node["y"] + dy
            r = 42

            self.canvas.coords(node["hitbox"], x - r - 4, y - r - 4, x + r + 4, y + r + 4)
            self.canvas.coords(node["circ"],   x - r,     y - r,     x + r,     y + r)
            self.canvas.coords(node["ico"],    x,         y)
            self.canvas.coords(node["label"],  x,         y + 60)

        # Перерисовываем линии между ними
        for idx, (a, b) in enumerate(self.graph_edges):
            na = self.node_drawables[a]
            nb = self.node_drawables[b]
            ax, ay = self.canvas.coords(na["ico"])[0:2]
            bx, by = self.canvas.coords(nb["ico"])[0:2]
            self.canvas.coords(self.edge_drawables[idx], ax, ay, bx, by)

        if self.graph_active:
            job = self.root.after(40, self.update_graph_motion)
            self.graph_jobs.append(job)
            self.graph_motion_job = job

    # ===== ПОЛУПРОЗРАЧНОЕ СООБЩЕНИЕ В ЦЕНТРЕ =====
    def show_overlay_message(self, text, color):
        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        panel = self.canvas.create_rectangle(
            w // 2 - 320, h // 2 - 80,
            w // 2 + 320, h // 2 + 80,
            fill="#05080c", outline="#3b3b3b", width=2
        )

        msg = self.canvas.create_text(
            w // 2, h // 2,
            text=text,
            fill=color,
            font=("Consolas", 22, "bold"),
            justify="center"
        )

        self.canvas.after(2400, lambda: (self.canvas.delete(panel),
                                         self.canvas.delete(msg)))

    # ===== BRUTEFORCE (запуск безопасного симулятора) =====
    def launch_bruteforce(self):
        # полностью останавливаем граф
        self.stop_graph()
        self.state = "bruteforce"

        # чистим сцену
        self.canvas.delete("all")

        # сразу рисуем МИВЛГУ внизу справа и запустим для него глич
        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()
        self.mivlgu_x = w - 20
        self.mivlgu_y = h - 20
        self.mivlgu_text = self.canvas.create_text(
            self.mivlgu_x, self.mivlgu_y,
            anchor="se",
            text="МИВЛГУ",
            fill="white",
            font=("Arial Black", 22),
            tags=("mivlgu",)
        )

        # запускаем модуль брутфорса (он рисует свою UI на том же canvas)
        self.bruteforce = BruteforceModule(self.canvas, self.root, self.return_to_menu)
        self.bruteforce.start()

        # запускаем глич для МИВЛГУ и поднимаем текст наверх
        self.schedule_mivlgu_glitch()
        self.force_mivlgu_top()

    def stop_graph(self):
        self.graph_active = False

        # отменяем все отложенные задачи графа
        for job in self.graph_jobs:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self.graph_jobs.clear()

        if self.graph_motion_job:
            try:
                self.root.after_cancel(self.graph_motion_job)
            except Exception:
                pass
            self.graph_motion_job = None

        if self.graph_edges_job:
            try:
                self.root.after_cancel(self.graph_edges_job)
            except Exception:
                pass
            self.graph_edges_job = None

    def return_to_menu(self):
        # возврат из Bruteforce в главное меню CtOS
        self.canvas.delete("all")
        self.graph_active = False
        self.graph_jobs.clear()
        self.draw_grid_background()
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
        # перед новым запуском на всякий случай отменим старый
        if self.mivlgu_job:
            try:
                self.root.after_cancel(self.mivlgu_job)
            except Exception:
                pass
            self.mivlgu_job = None

        self.mivlgu_job = self.root.after(
            random.randint(3000, 6000),
            self.start_mivlgu_glitch
        )

    def start_mivlgu_glitch(self):
        self.mivlgu_frames = random.randint(2, 4)
        self.run_mivlgu_glitch_frame()
        self.force_mivlgu_top()

    def run_mivlgu_glitch_frame(self):
        if self.mivlgu_frames <= 0:
            self.canvas.delete("mivlgu_glitch")
            self.schedule_mivlgu_glitch()
            return

        self.canvas.delete("mivlgu_glitch")

        for _ in range(random.randint(1, 2)):
            dy = random.randint(-6, 6)
            dx = random.randint(-12, 12)

            self.canvas.create_text(
                self.mivlgu_x + dx,
                self.mivlgu_y + dy,
                text="МИВЛГУ",
                fill=random.choice(["#ffffff", "#cccccc", "#bbbbbb"]),
                font=("Arial Black", 22),
                anchor="se",
                tags=("mivlgu_glitch",)
            )

        self.mivlgu_frames -= 1
        self.root.after(80, self.run_mivlgu_glitch_frame)
        self.force_mivlgu_top()

    def force_mivlgu_top(self):
        # реально поднимаем текст и глич МИВЛГУ поверх остального
        if self.canvas.find_withtag("mivlgu"):
            self.canvas.tag_raise("mivlgu")
        if self.canvas.find_withtag("mivlgu_glitch"):
            self.canvas.tag_raise("mivlgu_glitch")

    # ================= FULLSCREEN =================
    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def exit_fullscreen(self, event=None):
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)

    def show_watchdogs_loader(self, callback):
        self.canvas.delete("all")

        self.w = self.canvas.winfo_screenwidth()
        self.h = self.canvas.winfo_screenheight()

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
        start_y = self.h // 2 - 160

        for i, line in enumerate(ascii_logo):
            t = self.canvas.create_text(
                self.w // 2, start_y + i * 22,
                text=line,
                fill="#9ef",
                font=("Consolas", 14, "bold")
            )
            self.logo_objects.append(t)

        self.loading_text = self.canvas.create_text(
            self.w // 2, start_y + 260,
            text="INITIALIZING CtOS MODULE...",
            fill="#48bfff",
            font=("Consolas", 14, "bold")
        )

        # Progress Bar Frame
        self.pb_y = start_y + 300
        self.canvas.create_rectangle(
            self.w // 2 - 240, self.pb_y,
            self.w // 2 + 240, self.pb_y + 18,
            outline="#48bfff", width=2
        )

        # Progress Fill
        self.pb_fill = self.canvas.create_rectangle(
            self.w // 2 - 238, self.pb_y + 2,
            self.w // 2 - 238, self.pb_y + 16,
            fill="#48bfff", width=0
        )

        self.loader_progress = 0
        self.loader_active = True

        self.animate_watchdogs_glitch()
        self.animate_loader(callback)

    def animate_watchdogs_glitch(self):
        if not self.loader_active:
            return

        for obj in self.logo_objects:
            if random.random() < 0.15:
                dx = random.randint(-3, 3)
                dy = random.randint(-2, 2)
                self.canvas.move(obj, dx, dy)

            if random.random() < 0.08:
                self.canvas.itemconfig(obj, fill=random.choice(["#9ef", "#ffffff", "#48bfff"]))

        self.root.after(100, self.animate_watchdogs_glitch)

    def animate_loader(self, callback):
        if not self.loader_active:
            return

        self.loader_progress += random.randint(2, 5)
        percent = min(100, self.loader_progress)

        fill_width = int(476 * (percent / 100))

        self.canvas.coords(
            self.pb_fill,
            self.w // 2 - 238,
            self.pb_y + 2,
            self.w // 2 - 238 + fill_width,
            self.pb_y + 16
        )

        self.canvas.itemconfig(self.loading_text, text=f"LOADING MODULE... {percent}%")

        if percent >= 100:
            self.loader_active = False
            self.root.after(400, callback)
            return

        self.root.after(200, lambda: self.animate_loader(callback))


    def reboot_to_intro(self):
        # стоп системы
        self.graph_active = False
        self.glitch_active = False
        self.state = "shutdown"

        # отмена всех задач графа
        for job in self.graph_jobs:
            try:
                self.root.after_cancel(job)
            except:
                pass
        self.graph_jobs.clear()

        if self.graph_motion_job:
            try:
                self.root.after_cancel(self.graph_motion_job)
            except:
                pass
            self.graph_motion_job = None

        if self.graph_edges_job:
            try:
                self.root.after_cancel(self.graph_edges_job)
            except:
                pass
            self.graph_edges_job = None

        # сбрасываем idle
        if self.idle_job:
            try:
                self.root.after_cancel(self.idle_job)
            except:
                pass
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

        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        for _ in range(self.shutdown_power):
            x = random.randint(0, w)
            y = random.randint(0, h)
            dx = random.randint(60, 180)
            dy = random.randint(10, 60)

            self.canvas.create_rectangle(
                x, y, x + dx, y + dy,
                fill=random.choice(["#ff0033", "#ffffff", "#48bfff"]),
                outline="",
                tags="shutdown"
            )

        if random.random() < 0.4:
            self.canvas.create_text(
                random.randint(200, w - 200),
                random.randint(120, h - 120),
                text=random.choice(["ERROR", "SYSTEM CRASH", "ACCESS LOST"]),
                fill="#ff0033",
                font=("Consolas", 20, "bold"),
                tags="shutdown"
            )

        self.shutdown_frames -= 1
        self.root.after(180, self.shutdown_intense_glitch)

    def spawn_single_shutdown_glitch(self):
        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        x = random.randint(0, w - 120)
        y = random.randint(0, h - 30)

        self.canvas.create_rectangle(
            x, y, x + random.randint(80, 160), y + random.randint(10, 25),
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

        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        # чёрный фон
        self.canvas.create_rectangle(0, 0, w, h, fill="black", outline="")

        # красное лого CtOS
        self.canvas.create_text(
            w // 2, h // 2 - 60,
            text="CtOS",
            fill="#ff0033",
            font=("Arial Black", 64)
        )

        # надпись REBOOT
        self.reboot_text = self.canvas.create_text(
            w // 2, h // 2 + 30,
            text="REBOOTING SYSTEM",
            fill="#ff0033",
            font=("Consolas", 20, "bold")
        )

        self.root.after(3000, self.return_to_intro)



    def run_shutdown_glitch(self):
        if self.shutdown_frames <= 0:
            self.canvas.delete("shutdown")
            self.show_blackout()
            return

        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        glitch_count = self.shutdown_power * random.randint(6, 12)

        for _ in range(glitch_count):
            x = random.randint(0, w)
            y = random.randint(0, h)
            dx = random.randint(80, 240)
            dy = random.randint(20, 70)

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
            self.canvas.create_text(
                random.randint(200, w - 200),
                random.randint(100, h - 120),
                text=msg,
                fill="#ff3333",
                font=("Consolas", random.randint(18, 28), "bold"),
                tags="shutdown"
            )

        self.shutdown_power += 1  # каждый кадр всё жестче
        self.shutdown_frames -= 1

        self.root.after(140, self.run_shutdown_glitch)  # было ~100 → замедлили для драматизма

    def show_blackout(self):
        self.canvas.delete("shutdown")
        self.canvas.delete("all")

        # ЧЁРНЫЙ ЭКРАН
        self.canvas.create_rectangle(
            0, 0,
            self.canvas.winfo_screenwidth(),
            self.canvas.winfo_screenheight(),
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

        if hasattr(self, "global_glitch_job") and self.global_glitch_job:
            try:
                self.root.after_cancel(self.global_glitch_job)
            except:
                pass
            self.global_glitch_job = None

        if hasattr(self, "glitch_job"):
            try:
                self.root.after_cancel(self.glitch_job)
            except:
                pass

        self.canvas.delete("screen_glitch")
        self.canvas.delete("glitch")

    def start_music(self):
        if not self.music_enabled:
            print("Music disabled")
            return

        try:
            print("Music path:", self.music_file)
            pygame.mixer.init()
            pygame.mixer.music.load(self.music_file)
            pygame.mixer.music.set_volume(0.22)
            pygame.mixer.music.play(-1)
            print("Music STARTED")

        except Exception as e:
            print("Music ERROR:", e)


if __name__ == "__main__":
    root = tk.Tk()
    app = CtOSMenu(root)
    app.start_music()
    root.mainloop()

