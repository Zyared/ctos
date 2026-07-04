import tkinter as tk
import random
import math

from ctos.ui import theme as T
from ctos.utils.formatting import format_speed_kbps
from ctos.ui.viewport import Viewport
from ctos.utils.tk_helpers import draw_corner_frame

# Симуляция: полная шкала прогресс-бара при таком объёме (иначе 100% за пару пакетов)
PROGRESS_BAR_FULL_MB = 1600


class DataExfilModule:
    def __init__(self, canvas, root, on_exit):
        self.canvas = canvas
        self.root = root
        self.on_exit = on_exit

        # MATRIX BACKGROUND
        self.matrix_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#@$%&"
        self.matrix_drops = []
        self.matrix_speed = []
        self.matrix_columns = []
        self.matrix_active = True

        self.running = True
        self.exfil_active = False
        self.encrypt = False
        self.compress = False
        self.tor = False

        self.progress = 0
        self.exfil_running = False

        self.data_stolen = 0
        self.speed = 0
        self.risk = 0

        self.packets = []

        self.files = [".db", ".zip", ".log", ".pdf", ".key"]
        self.max_log_lines = 20

        # INFO SYSTEM
        self.info_visible = False
        self.info_page = 0
        self.info_overlay = None
        self.info_focus = None
        self.info_box = None
        self.info_text = None
        self.info_counter = None
        self.info_big_panel1 = None
        self.info_big_panel2 = None
        self.info_big_text1 = None
        self.info_big_text2 = None
        self.info_title = None

        self.info_targets = {}

        # ===== РАСШИРЕННЫЕ СТРАНИЦЫ INFO =====
        self.info_pages = [
            ("LOG", "ЛЕНТА СОБЫТИЙ\n\n"
                    "Здесь в реальном времени отображаются события утечки данных:\n"
                    "• передача файлов\n"
                    "• срабатывание IDS\n"
                    "• аномальная активность\n\n"
                    "По этим логам в реальной жизни анализируют утечки."),

            ("HOST", "CORPORATE HOST\n\n"
                     "Это источник данных — корпоративный сервер.\n\n"
                     "В реальности здесь могут быть:\n"
                     "• базы данных клиентов\n"
                     "• финансовые отчёты\n"
                     "• пароли\n"
                     "• документы\n\n"
                     "Атака DATA EXFIL всегда начинается здесь."),

            ("DROP", "REMOTE DROP ZONE\n\n"
                     "Удалённый сервер злоумышленника.\n\n"
                     "Именно сюда передаются украденные данные.\n"
                     "После передачи они могут:\n"
                     "• продаваться\n"
                     "• использоваться для шантажа\n"
                     "• применяться для атак на другие компании"),

            ("PROGRESS", "ШКАЛА ПРОГРЕССА\n\n"
                         "Показывает объём переданных данных.\n\n"
                         "Когда шкала заполнена — утечка завершена.\n"
                         "Чем быстрее рост — тем опаснее утечка."),

            ("START", "START / STOP\n\n"
                      "Запускает или останавливает атаку.\n\n"
                      "В реальности остановка возможна только:\n"
                      "• при блокировке соединения\n"
                      "• при реагировании службы безопасности"),

            ("ENCRYPT", "ENCRYPT\n\n"
                        "Шифрует данные перед отправкой.\n\n"
                        "В реальности используется:\n"
                        "• AES\n"
                        "• TLS\n"
                        "• кастомные обфускаторы\n\n"
                        "Шифрование мешает анализу сетевого трафика."),

            ("COMPRESS", "COMPRESS\n\n"
                         "Сжимает файлы перед передачей.\n\n"
                         "Это:\n"
                         "• увеличивает скорость\n"
                         "• снижает размер трафика\n\n"
                         "Часто зловреды используют ZIP/7Z/GZIP."),

            ("TOR", "TOR ROUTE\n\n"
                    "Анонимизация маршрута передачи.\n\n"
                    "Трафик идёт:\n"
                    "• через несколько узлов\n"
                    "• меняя IP адреса\n"
                    "• уходя от прямого отслеживания"),

            ("FINAL", "ОБЩАЯ СХЕМА\n\n"
                      "DATA EXFIL = скрытая передача данных\n\n"
                      "Этапы:\n"
                      "1) Сбор данных\n"
                      "2) Сжатие\n"
                      "3) Шифрование\n"
                      "4) Отправка\n"
                      "5) Сокрытие следов\n\n"
                      "Теперь перейдём к теории."),
        ]

    # ================= BUTTON =================
    def create_button(self, x, y, text, cmd):
        vp = self.vp
        bw = vp.px(140)
        bh = vp.px(40)

        rect = self.canvas.create_rectangle(
            x, y, x + bw, y + bh,
            outline=T.ACCENT,
            width=vp.wid(2)
        )

        label = self.canvas.create_text(
            x + bw // 2,
            y + bh // 2,
            text=text,
            fill=T.ACCENT,
            font=vp.consolas(12, bold=True)
        )

        def on_enter(e):
            # ярче обводка + толще рамка + светлее текст — как у узлов графа в главном меню
            self.canvas.itemconfig(rect, fill=T.BUTTON_HOVER, outline=T.HOVER_OUTLINE, width=vp.wid(3))
            self.canvas.itemconfig(label, fill=T.TEXT_BRIGHT)

        def on_leave(e):
            self.canvas.itemconfig(rect, fill="", outline=T.ACCENT, width=vp.wid(2))
            self.canvas.itemconfig(label, fill=T.ACCENT)

        for item in (rect, label):
            self.canvas.tag_bind(item, "<Enter>", on_enter)
            self.canvas.tag_bind(item, "<Leave>", on_leave)
            self.canvas.tag_bind(item, "<Button-1>", lambda e: cmd())

        return rect, label

    # ================= START ==================
    def start(self):
        self.draw_ui()
        self.animate_packets()
        self.update_stats()
        self.init_matrix_background()
        self.animate_matrix()

    def init_matrix_background(self):
        w = self.w
        h = self.h
        vp = self.vp

        self.matrix_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#@$%&"
        self.matrix_objects = []
        self.matrix_speed = []
        self.matrix_y = []
        self.matrix_x = []

        font_size = vp.pt(14)
        self.matrix_font = ("Consolas", font_size)

        cols = max(1, w // max(1, font_size))

        for i in range(cols):
            x = i * font_size
            y = random.randint(-h, 0)
            txt = self.canvas.create_text(
                x, y,
                text=random.choice(self.matrix_chars),
                fill="#124d75",
                font=self.matrix_font
            )

            # ✅ ОБЯЗАТЕЛЬНО опустить в самый низ
            self.canvas.lower(txt)

            self.matrix_objects.append(txt)
            self.matrix_speed.append(random.randint(3, 7))
            self.matrix_y.append(y)
            self.matrix_x.append(x)

    def animate_matrix(self):
        if not self.matrix_active:
            return
        if self.info_visible:
            self.root.after(80, self.animate_matrix)
            return

        h = self.h

        for i, txt in enumerate(self.matrix_objects):
            self.matrix_y[i] += self.matrix_speed[i]

            if self.matrix_y[i] > h:
                self.matrix_y[i] = random.randint(-100, -10)
                self.canvas.itemconfig(
                    txt,
                    text=random.choice(self.matrix_chars)
                )

            self.canvas.coords(txt, self.matrix_x[i], self.matrix_y[i])

        self.root.after(80, self.animate_matrix)

    # ================= UI =====================
    def draw_ui(self):
        self.vp = Viewport.from_canvas(self.canvas, self.root)
        vp = self.vp
        w = self.w = vp.w
        h = self.h = vp.h

        self.canvas.create_text(vp.px(30), vp.px(20), anchor="nw",
                                text="DATA EXFIL MODULE v2",
                                fill=T.DANGER,
                                font=vp.consolas(18, bold=True))
        # Отсылка: терминальные «хакерские» клиенты (Uplink / Hacknet-стиль HUD)
        self.canvas.create_text(vp.px(30), vp.px(46), anchor="nw",
                                text="// SECURE CHANNEL  ·  TRACE: MASKED",
                                fill=T.SUCCESS,
                                font=vp.consolas(10))

        # LOG PANEL
        draw_corner_frame(
            self.canvas, vp.px(30), vp.px(70), vp.px(520), h - vp.px(80),
            outline=T.PANEL_OUTLINE, frame_width=vp.wid(2),
            bracket_len=vp.px(16), bracket_width=vp.wid(2),
        )
        self.log_text = self.canvas.create_text(
            vp.px(40), vp.px(80), anchor="nw",
            fill="#ffd0d0",
            width=vp.px(460),
            font=vp.consolas(11),
            text=""
        )
        self.info_targets["LOG"] = self.log_text

        # STATS (рамка в стиле терминального HUD)
        self.stats_bg = draw_corner_frame(
            self.canvas, vp.px(548), h - vp.px(288), vp.px(900), h - vp.px(100),
            outline=T.SUCCESS, fill=T.PANEL_BG, frame_width=vp.wid(1),
            bracket_len=vp.px(12), bracket_width=vp.wid(2),
        )
        self.canvas.create_text(
            vp.px(560), h - vp.px(278), anchor="nw",
            text="SESSION STATUS",
            fill=T.SUCCESS,
            font=vp.consolas(11, bold=True)
        )
        self.stats_text = self.canvas.create_text(
            vp.px(560), h - vp.px(252), anchor="nw",
            fill=T.TEXT_BRIGHT, font=vp.consolas(12)
        )

        # PROGRESS BAR
        self.BAR_Y = h - vp.px(85)
        self._bar_left = vp.px(562)
        self._bar_fill_h = vp.px(28)
        self._bar_inner_px = vp.px(296)
        self.progress_frame = draw_corner_frame(
            self.canvas, vp.px(560), self.BAR_Y, vp.px(860), self.BAR_Y + vp.px(30),
            outline=T.PANEL_OUTLINE, frame_width=vp.wid(1),
            bracket_len=vp.px(10), bracket_width=vp.wid(2),
        )
        self.info_targets["PROGRESS"] = self.progress_frame

        self.progress_fill = self.canvas.create_rectangle(
            self._bar_left, self.BAR_Y + vp.px(2),
            self._bar_left, self.BAR_Y + self._bar_fill_h,
            fill=T.ACCENT, width=0
        )

        # Тонкий «скан» поверх заливки — как будто сквозь бар бежит сигнал.
        self.progress_scan = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#eaffff", stipple="gray25", outline="",
        )
        self._progress_scan_phase = 0.0
        self._tick_progress_scan()

        # BUTTONS
        def btn(name, y, cmd):
            rect, _ = self.create_button(w - vp.px(180), y, name, cmd)
            self.info_targets[name] = rect

        btn("START", vp.px(120), self.toggle_exfil)
        btn("ENCRYPT", vp.px(180), self.toggle_encrypt)
        btn("COMPRESS", vp.px(240), self.toggle_compress)
        btn("TOR", vp.px(300), self.toggle_tor)
        btn("INFO", vp.px(360), self.toggle_info)
        btn("BACK", vp.px(420), self.exit)

        # NODES
        self.victim_x = w // 2 - vp.px(320)
        self.victim_y = h // 2

        self.attacker_x = w // 2 + vp.px(320)
        self.attacker_y = h // 2

        self.host_box = self.canvas.create_rectangle(
            self.victim_x - vp.px(70), self.victim_y - vp.px(50),
            self.victim_x + vp.px(70), self.victim_y + vp.px(50),
            outline=T.ACCENT, width=vp.wid(2)
        )
        self.info_targets["HOST"] = self.host_box

        self.drop_box = self.canvas.create_rectangle(
            self.attacker_x - vp.px(80), self.attacker_y - vp.px(50),
            self.attacker_x + vp.px(80), self.attacker_y + vp.px(50),
            outline=T.DANGER, width=vp.wid(2)
        )
        self.info_targets["DROP"] = self.drop_box

        self.canvas.create_line(
            self.victim_x + vp.px(70), self.victim_y,
            self.attacker_x - vp.px(80), self.attacker_y,
            fill="#555", dash=vp.dash(6, 3)
        )

        self.canvas.create_text(self.victim_x, self.victim_y + vp.px(80),
                                text="CORPORATE HOST",
                                fill=T.ACCENT,
                                font=vp.consolas(11, bold=True))

        self.canvas.create_text(self.attacker_x, self.attacker_y + vp.px(80),
                                text="REMOTE DROP ZONE",
                                fill=T.DANGER,
                                font=vp.consolas(11, bold=True))

        self.log("[SYSTEM] DATA EXFIL MODULE INITIALIZED", "#9eff9e")

    # ================= LOG ====================
    def log(self, msg, color="#ffd0d0"):
        lines = self.canvas.itemcget(self.log_text, "text").split("\n")
        lines.append(msg)
        self.canvas.itemconfig(self.log_text,
                               text="\n".join(lines[-self.max_log_lines:]),
                               fill=color)

    # ================= CONTROL =================
    def toggle_exfil(self):
        self.exfil_active = not self.exfil_active
        self.log(f"[EXFIL] {'STARTED' if self.exfil_active else 'STOPPED'}", "#ffaa00")
        if self.exfil_active:
            self.spawn_packet()

    def toggle_encrypt(self):
        self.encrypt = not self.encrypt
        self.log(f"[CRYPTO] {'AES ENABLED' if self.encrypt else 'DISABLED'}", "#ffaa00")

    def toggle_compress(self):
        self.compress = not self.compress
        self.log(f"[ARCHIVE] {'ZIP MODE' if self.compress else 'RAW MODE'}", "#ffaa00")

    def toggle_tor(self):
        self.tor = not self.tor
        self.log(f"[ROUTE] {'TOR ENABLED' if self.tor else 'DIRECT'}", "#ffaa00")

    def _clear_packets(self) -> None:
        for p in self.packets:
            self.canvas.delete(p["dot"])
            self.canvas.delete(p["label"])
        self.packets.clear()

    # ================= PACKETS =================
    def spawn_packet(self):
        if not self.exfil_active or not self.running or self.info_visible:
            return

        size = random.randint(5, 35)
        speed = random.randint(30, 120)

        if self.compress:
            size //= 2
            speed = int(round(speed * 1.4))

        if self.tor:
            speed = max(1, speed // 2)

        vp = self.vp
        y = random.randint(self.victim_y - vp.px(25), self.victim_y + vp.px(25))
        dot = self.canvas.create_oval(
            self.victim_x + vp.px(60), y - vp.px(4),
            self.victim_x + vp.px(68), y + vp.px(4),
            fill=T.DANGER if self.encrypt else T.ACCENT,
            outline="",
            tags=("exfil_packet",),
        )

        label = self.canvas.create_text(
            self.victim_x + vp.px(50), y - vp.px(8),
            text=random.choice(self.files),
            fill="white",
            font=vp.consolas(8),
            anchor="e",
            tags=("exfil_packet",),
        )

        dx = (self.attacker_x - self.victim_x - vp.px(160)) / speed

        self.packets.append({
            "dot": dot,
            "label": label,
            "dx": dx,
            "target_x": self.attacker_x - vp.px(90),
            "size": size,
            "speed": speed
        })

        self.root.after(random.randint(300, 600), self.spawn_packet)

    def animate_packets(self):
        if not self.running:
            return

        for p in self.packets[:]:
            self.canvas.move(p["dot"], p["dx"], 0)
            self.canvas.move(p["label"], p["dx"], 0)

            dot_x = self.canvas.coords(p["dot"])[0]

            if dot_x >= p["target_x"]:
                self.canvas.delete(p["dot"])
                self.canvas.delete(p["label"])
                self.packets.remove(p)

                self.data_stolen += p["size"]
                self.speed = p["speed"]

                if not self.encrypt and random.random() > 0.85:
                    self.risk += random.randint(1, 5)
                    self.log("[IDS] ALERT: suspicious traffic detected", "#ff3333")

                self.log(f"[FILE] {p['size']}MB exfiltrated", "#ff6666")

        self.root.after(30, self.animate_packets)

    # ================= STATS ===================
    def update_stats(self):
        self.canvas.itemconfig(
            self.stats_text,
            text=(
                f"DATA STOLEN: {self.data_stolen} MB\n"
                f"SPEED: {format_speed_kbps(self.speed)}\n"
                f"ENCRYPT: {'ON' if self.encrypt else 'OFF'}\n"
                f"COMPRESS: {'ON' if self.compress else 'OFF'}\n"
                f"TOR: {'ON' if self.tor else 'OFF'}\n"
                f"RISK LEVEL: {self.risk}%\n"
            ),
        )

        fill_pct = min(100.0, (self.data_stolen / PROGRESS_BAR_FULL_MB) * 100.0)
        inner = getattr(self, "_bar_inner_px", self.vp.px(296))
        width = int((fill_pct / 100.0) * inner)
        left = getattr(self, "_bar_left", self.vp.px(562))
        dy = self.vp.px(2)
        y2 = self.BAR_Y + getattr(self, "_bar_fill_h", self.vp.px(28))

        self.canvas.coords(
            self.progress_fill,
            left,
            self.BAR_Y + dy,
            left + width,
            y2,
        )

        self.root.after(700, self.update_stats)

    def _tick_progress_scan(self) -> None:
        if not self.running:
            return
        self._progress_scan_phase += 0.06
        vp = self.vp
        fx0, fy0, fx1, fy1 = self.canvas.coords(self.progress_fill)
        width = fx1 - fx0
        scan_w = min(vp.px(26), max(0, width))
        if width < vp.px(6):
            self.canvas.coords(self.progress_scan, 0, 0, 0, 0)
        else:
            span = max(0.0, width - scan_w)
            phase = (math.sin(self._progress_scan_phase) + 1) / 2
            sx = fx0 + phase * span
            self.canvas.coords(self.progress_scan, sx, fy0, sx + scan_w, fy1)
        self.root.after(70, self._tick_progress_scan)

    # ================= INFO SYSTEM =============
    def toggle_info(self):
        if self.info_visible:
            self.hide_info()
        else:
            self.start_info_tour()

    def start_info_tour(self):
        self.info_visible = True
        self._clear_packets()
        self.exfil_active = False
        self.info_page = 0
        self.show_info_step()

    def _wrap_text_to_box(self, text, max_chars=52):
        """
        Гарантированно НЕ даёт тексту пробивать рамки:
        - режет длинные строки
        - принудительно переносит слова
        """
        import textwrap
        lines = []
        for block in text.split("\n"):
            wrapped = textwrap.wrap(block, max_chars) or [""]
            lines.extend(wrapped)
        return "\n".join(lines)

    def show_info_step(self):
        self.clear_info()

        if self.info_pages[self.info_page][0] == "FINAL":
            self.show_big_theory_panels()
            return

        key, raw_text = self.info_pages[self.info_page]
        text = self._wrap_text_to_box(raw_text, 50)

        w, h = self.w, self.h
        vp = self.vp

        self.info_overlay = self.canvas.create_rectangle(
            0, 0, w, h,
            fill="black", stipple="gray50"
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
            outline=T.ACCENT, width=vp.wid(2)
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
        box_x = x2 + gap if x2 + gap + BOX_W <= w - gap else x1 - BOX_W - gap
        # Держим окно INFO целиком на экране (широкие цели иначе выталкивают
        # его за край и текст обрезается).
        box_x = max(gap, min(box_x, w - BOX_W - gap))
        box_y = max(0, min(y1, h - BOX_H - gap))

        self.info_box = self.canvas.create_rectangle(
            box_x, box_y, box_x + BOX_W, box_y + BOX_H,
            fill=T.INFO_BG, outline=T.ACCENT, width=vp.wid(2)
        )

        self.info_title = self.canvas.create_text(
            box_x + BOX_W // 2,
            box_y + vp.px(16),
            text=key,
            fill=T.ACCENT,
            font=vp.consolas(13, bold=True)
        )

        self.info_text = self.canvas.create_text(
            box_x + PADDING,
            box_y + TITLE_H,
            anchor="nw",
            text=text,
            fill=T.INFO_TEXT,
            width=BOX_W - PADDING * 2,
            font=vp.consolas(11),
            justify="left"
        )

        self.info_counter = self.canvas.create_text(
            box_x + BOX_W // 2, box_y + BOX_H - vp.px(12),
            text=f"{self.info_page + 1}/{len(self.info_pages)}  (CLICK)",
            fill=T.ACCENT,
            font=vp.consolas(9, bold=True)
        )

        for obj in (self.info_overlay, self.info_box, self.info_text):
            self.canvas.tag_bind(obj, "<Button-1>", self.next_info)

        for obj in (self.info_overlay, self.info_focus,
                    self.info_box, self.info_text, self.info_counter, self.info_title):
            self.canvas.tag_raise(obj)

        if self.canvas.find_withtag("mivlgu"):
            self.canvas.tag_raise("mivlgu")

    def show_big_theory_panels(self):
        self.clear_info()
        self._clear_packets()
        self.exfil_active = False
        w, h = self.w, self.h
        vp = self.vp

        self.info_overlay = self.canvas.create_rectangle(
            0, 0, w, h,
            fill="#000510", stipple="gray50"
        )

        p1x1, p1y1 = w // 2 - vp.px(460), h // 2 - vp.px(200)
        p1x2, p1y2 = w // 2 - vp.px(40), h // 2 + vp.px(200)
        self.info_big_panel1 = self.canvas.create_rectangle(
            p1x1, p1y1, p1x2, p1y2,
            fill="#040608", outline=T.SUCCESS, width=vp.wid(2)
        )

        p2x1, p2y1 = w // 2 + vp.px(40), h // 2 - vp.px(200)
        p2x2, p2y2 = w // 2 + vp.px(460), h // 2 + vp.px(200)
        self.info_big_panel2 = self.canvas.create_rectangle(
            p2x1, p2y1, p2x2, p2y2,
            fill="#040608", outline=T.DANGER, width=vp.wid(2)
        )

        body1 = self._wrap_text_to_box(
            "ЧТО ТАКОЕ DATA EXFIL\n\n"
            "Это скрытая утечка данных:\n\n"
            "• тайная передача файлов\n"
            "• кража информации\n"
            "• отправка на внешний сервер\n\n"
            "Используется в:\n"
            "• троянах\n"
            "• APT атаках\n"
            "• ботнетах\n"
            "• шпионских ПО",
            40,
        )
        self.info_big_text1 = self.canvas.create_text(
            p1x1 + vp.px(22),
            p1y1 + vp.px(24),
            anchor="nw",
            text=body1,
            fill="#b8ffe8",
            font=vp.consolas(12),
            width=p1x2 - p1x1 - vp.px(44),
            justify="left",
        )

        body2 = self._wrap_text_to_box(
            "КАК ЗАЩИЩАТЬСЯ\n\n"
            "• IDS / IPS\n"
            "• DLP системы\n"
            "• мониторинг трафика\n"
            "• анализ процессов\n\n"
            "• шифрование каналов\n"
            "• контроль DNS\n"
            "• сегментация сети\n\n"
            "Главное — видеть аномалии",
            40,
        )
        self.info_big_text2 = self.canvas.create_text(
            p2x1 + vp.px(22),
            p2y1 + vp.px(24),
            anchor="nw",
            text=body2,
            fill="#ffd6d6",
            font=vp.consolas(12),
            width=p2x2 - p2x1 - vp.px(44),
            justify="left",
        )

        self.info_counter = self.canvas.create_text(
            w // 2, h - vp.px(40),
            text="CLICK TO EXIT INFO",
            fill=T.SUCCESS,
            font=vp.consolas(11, bold=True)
        )

        for obj in (
            self.info_overlay,
            self.info_big_panel1,
            self.info_big_text1,
            self.info_big_panel2,
            self.info_big_text2,
            self.info_counter,
        ):
            self.canvas.tag_bind(obj, "<Button-1>", self.hide_info)

        # Важно: затемнение — снизу, панели и текст — НАД ним (иначе текст не виден).
        self.canvas.tag_raise(self.info_overlay)
        for item in (
            self.info_big_panel1,
            self.info_big_panel2,
            self.info_big_text1,
            self.info_big_text2,
            self.info_counter,
        ):
            self.canvas.tag_raise(item)

        if self.canvas.find_withtag("mivlgu"):
            self.canvas.tag_raise("mivlgu")

    def next_info(self, e=None):
        self.info_page += 1
        if self.info_page >= len(self.info_pages):
            self.hide_info()
        else:
            self.show_info_step()

    def clear_info(self):
        for attr in [
            "info_title",
            "info_overlay", "info_focus", "info_box", "info_text",
            "info_counter", "info_big_panel1", "info_big_panel2",
            "info_big_text1", "info_big_text2"
        ]:
            obj = getattr(self, attr, None)
            if obj:
                self.canvas.delete(obj)
                setattr(self, attr, None)

    def hide_info(self, event=None):
        self.clear_info()
        self.info_visible = False

    # ================= EXIT ===================
    def exit(self):
        if getattr(self, "_exiting", False):
            return
        self._exiting = True
        self.running = False
        self.canvas.delete("all")
        self.matrix_active = False
        self.on_exit()
