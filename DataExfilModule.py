import tkinter as tk
import random

class DataExfilModule:
    def __init__(self, canvas, root, exit_callback):
        self.canvas = canvas
        self.root = root
        self.exit_callback = exit_callback

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
        w = 140
        h = 40

        rect = self.canvas.create_rectangle(
            x, y, x + w, y + h,
            outline="#48bfff",
            width=2
        )

        label = self.canvas.create_text(
            x + w // 2,
            y + h // 2,
            text=text,
            fill="#48bfff",
            font=("Consolas", 12, "bold")
        )

        def on_enter(e):
            self.canvas.itemconfig(rect, fill="#0a2a44")
            self.canvas.itemconfig(label, fill="white")

        def on_leave(e):
            self.canvas.itemconfig(rect, fill="")
            self.canvas.itemconfig(label, fill="#48bfff")

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
        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        self.matrix_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#@$%&"
        self.matrix_objects = []
        self.matrix_speed = []
        self.matrix_y = []
        self.matrix_x = []

        font_size = 14
        self.matrix_font = ("Consolas", font_size)

        cols = w // font_size

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

        h = self.canvas.winfo_screenheight()

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
        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        self.canvas.create_text(30, 20, anchor="nw",
                                text="DATA EXFIL MODULE v2",
                                fill="#ff4444",
                                font=("Consolas", 18, "bold"))

        # LOG PANEL
        self.canvas.create_rectangle(30, 70, 520, h - 80, outline="#333", width=2)
        self.log_text = self.canvas.create_text(
            40, 80, anchor="nw",
            fill="#ffd0d0",
            width=460,
            font=("Consolas", 11),
            text=""
        )
        self.info_targets["LOG"] = self.log_text

        # STATS
        self.stats_text = self.canvas.create_text(
            560, h - 260, anchor="nw",
            fill="white", font=("Consolas", 12)
        )

        # PROGRESS BAR
        self.BAR_Y = h - 85
        self.progress_frame = self.canvas.create_rectangle(
            560, self.BAR_Y, 860, self.BAR_Y + 30,
            outline="#444"
        )
        self.info_targets["PROGRESS"] = self.progress_frame

        self.progress_fill = self.canvas.create_rectangle(
            562, self.BAR_Y + 2,
            562, self.BAR_Y + 28,
            fill="#48bfff", width=0
        )

        # BUTTONS
        def btn(name, y, cmd):
            rect, _ = self.create_button(w - 180, y, name, cmd)
            self.info_targets[name] = rect

        btn("START", 120, self.toggle_exfil)
        btn("ENCRYPT", 180, self.toggle_encrypt)
        btn("COMPRESS", 240, self.toggle_compress)
        btn("TOR", 300, self.toggle_tor)
        btn("INFO", 360, self.toggle_info)
        btn("BACK", 420, self.exit)

        # NODES
        self.victim_x = w // 2 - 320
        self.victim_y = h // 2

        self.attacker_x = w // 2 + 320
        self.attacker_y = h // 2

        self.host_box = self.canvas.create_rectangle(
            self.victim_x - 70, self.victim_y - 50,
            self.victim_x + 70, self.victim_y + 50,
            outline="#48bfff", width=2
        )
        self.info_targets["HOST"] = self.host_box

        self.drop_box = self.canvas.create_rectangle(
            self.attacker_x - 80, self.attacker_y - 50,
            self.attacker_x + 80, self.attacker_y + 50,
            outline="#ff4444", width=2
        )
        self.info_targets["DROP"] = self.drop_box

        self.canvas.create_line(
            self.victim_x + 70, self.victim_y,
            self.attacker_x - 80, self.attacker_y,
            fill="#555", dash=(6, 3)
        )

        self.canvas.create_text(self.victim_x, self.victim_y + 80,
                                text="CORPORATE HOST",
                                fill="#48bfff",
                                font=("Consolas", 11, "bold"))

        self.canvas.create_text(self.attacker_x, self.attacker_y + 80,
                                text="REMOTE DROP ZONE",
                                fill="#ff4444",
                                font=("Consolas", 11, "bold"))

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

    # ================= PACKETS =================
    def spawn_packet(self):
        if not self.exfil_active or not self.running:
            return

        size = random.randint(5, 35)
        speed = random.randint(30, 120)

        if self.compress:
            size //= 2
            speed *= 1.4

        if self.tor:
            speed //= 2

        y = random.randint(self.victim_y - 25, self.victim_y + 25)
        dot = self.canvas.create_oval(
            self.victim_x + 60, y - 4,
            self.victim_x + 68, y + 4,
            fill="#ff4444" if self.encrypt else "#48bfff",
            outline=""
        )

        label = self.canvas.create_text(
            self.victim_x + 50, y - 8,
            text=random.choice(self.files),
            fill="white",
            font=("Consolas", 8),
            anchor="e"
        )

        dx = (self.attacker_x - self.victim_x - 160) / speed

        self.packets.append({
            "dot": dot,
            "label": label,
            "dx": dx,
            "target_x": self.attacker_x - 90,
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
        self.canvas.itemconfig(self.stats_text,
                               text=(
                                   "SESSION STATUS\n"
                                   "-----------------\n"
                                   f"DATA STOLEN: {self.data_stolen} MB\n"
                                   f"SPEED: {self.speed} KB/s\n"
                                   f"ENCRYPT: {'ON' if self.encrypt else 'OFF'}\n"
                                   f"COMPRESS: {'ON' if self.compress else 'OFF'}\n"
                                   f"TOR: {'ON' if self.tor else 'OFF'}\n"
                                   f"RISK LEVEL: {self.risk}%\n"
                               ))

        fill = min(100, self.data_stolen)
        width = int((fill / 100) * 296)

        self.canvas.coords(self.progress_fill,
                           562, self.BAR_Y + 2,
                           562 + width, self.BAR_Y + 28)

        self.root.after(700, self.update_stats)

    # ================= INFO SYSTEM =============
    def toggle_info(self):
        if self.info_visible:
            self.hide_info()
        else:
            self.start_info_tour()

    def start_info_tour(self):
        self.info_visible = True
        self.toggle_exfil()
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

        w, h = self.canvas.winfo_screenwidth(), self.canvas.winfo_screenheight()

        self.info_overlay = self.canvas.create_rectangle(
            0, 0, w, h,
            fill="black", stipple="gray50"
        )

        target = self.info_targets.get(key)
        if not target:
            self.next_info()
            return

        x1, y1, x2, y2 = self.canvas.bbox(target)

        self.info_focus = self.canvas.create_rectangle(
            x1 - 6, y1 - 6, x2 + 6, y2 + 6,
            outline="#48bfff", width=2
        )

        BOX_W = 420
        PADDING = 16
        TITLE_H = 32
        FOOTER_H = 26

        lines = text.count("\n") + 1
        LINE_H = 18
        BODY_H = lines * LINE_H

        BOX_H = TITLE_H + BODY_H + FOOTER_H + 14

        box_x = x2 + 20 if x2 + BOX_W < w else x1 - BOX_W - 20
        box_y = min(y1, h - BOX_H - 20)

        self.info_box = self.canvas.create_rectangle(
            box_x, box_y, box_x + BOX_W, box_y + BOX_H,
            fill="#05080c", outline="#48bfff", width=2
        )

        self.info_title = self.canvas.create_text(
            box_x + BOX_W // 2,
            box_y + 16,
            text=key,
            fill="#48bfff",
            font=("Consolas", 13, "bold")
        )

        self.info_text = self.canvas.create_text(
            box_x + PADDING,
            box_y + TITLE_H,
            anchor="nw",
            text=text,
            fill="#aee6ff",
            width=BOX_W - PADDING * 2,
            font=("Consolas", 11),
            justify="left"
        )

        self.info_counter = self.canvas.create_text(
            box_x + BOX_W // 2, box_y + BOX_H - 12,
            text=f"{self.info_page + 1}/{len(self.info_pages)}  (CLICK)",
            fill="#48bfff",
            font=("Consolas", 9, "bold")
        )

        for obj in (self.info_overlay, self.info_box, self.info_text):
            self.canvas.tag_bind(obj, "<Button-1>", self.next_info)

        for obj in (self.info_overlay, self.info_focus,
                    self.info_box, self.info_text, self.info_counter, self.info_title):
            self.canvas.tag_raise(obj)

    def show_big_theory_panels(self):
        self.clear_info()
        w, h = self.canvas.winfo_screenwidth(), self.canvas.winfo_screenheight()

        self.info_overlay = self.canvas.create_rectangle(
            0, 0, w, h,
            fill="black", stipple="gray50"
        )

        self.info_big_panel1 = self.canvas.create_rectangle(
            w//2 - 460, h//2 - 200,
            w//2 - 40,  h//2 + 200,
            fill="#08090d", outline="#48bfff", width=2
        )

        self.info_big_panel2 = self.canvas.create_rectangle(
            w//2 + 40,  h//2 - 200,
            w//2 + 460, h//2 + 200,
            fill="#08090d", outline="#ff6666", width=2
        )

        self.info_big_text1 = self.canvas.create_text(
            w//2 - 250, h//2,
            text=self._wrap_text_to_box(
                "ЧТО ТАКОЕ DATA EXFIL\n\n"
                "Это скрытая утечка данных:\n\n"
                "• тайная передача файлов\n"
                "• кража информации\n"
                "• отправка на внешний сервер\n\n"
                "Используется в:\n"
                "• троянах\n"
                "• APT атаках\n"
                "• ботнетах\n"
                "• шпионских ПО", 40),
            fill="#aee6ff",
            font=("Consolas", 12),
            width=360,
            justify="left"
        )

        self.info_big_text2 = self.canvas.create_text(
            w//2 + 250, h//2,
            text=self._wrap_text_to_box(
                "КАК ЗАЩИЩАТЬСЯ\n\n"
                "• IDS / IPS\n"
                "• DLP системы\n"
                "• мониторинг трафика\n"
                "• анализ процессов\n\n"
                "• шифрование каналов\n"
                "• контроль DNS\n"
                "• сегментация сети\n\n"
                "Главное — видеть аномалии", 40),
            fill="#ffd0d0",
            font=("Consolas", 12),
            width=360,
            justify="left"
        )

        self.info_counter = self.canvas.create_text(
            w//2, h - 40,
            text="CLICK TO EXIT INFO",
            fill="#48bfff",
            font=("Consolas", 11, "bold")
        )

        for obj in (self.info_overlay,
                    self.info_big_panel1, self.info_big_text1,
                    self.info_big_panel2, self.info_big_text2,
                    self.info_counter):
            self.canvas.tag_bind(obj, "<Button-1>", self.hide_info)
            self.canvas.tag_raise(obj)

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
        self.running = False
        self.canvas.delete("all")
        self.matrix_active = False
        self.exit_callback()
