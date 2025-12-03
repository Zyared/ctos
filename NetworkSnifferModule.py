import random
import tkinter as tk
import math


class NetworkSnifferModule:
    def __init__(self, canvas, root, exit_callback):
        self.canvas = canvas
        self.root = root
        self.exit_callback = exit_callback

        self.running = True
        self.paused = False
        self.mitm = False
        self.graph = True
        self.focus_node = None

        # MATRIX BACKGROUND
        self.matrix_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#@$%&"
        self.matrix_drops = []
        self.matrix_speed = []
        self.matrix_columns = []
        self.matrix_active = True

        # INFO
        self.info_visible = False
        self.info_page = 0
        self.info_overlay = None
        self.info_focus = None
        self.info_box = None
        self.info_text = None
        self.info_counter = None

        # MUSIC
        self.music_enabled = True
        self.music_file = "music.mp3"  # имя ТВОЕГО файла

        self.info_targets = {}

        self.info_pages = [
            ("SERVER",
             "Центральный сервер.\n\nВсе пакеты сходятся здесь.\n\nРеально — это:\n• веб-сервера\n• БД\n• файловые хранилища\n\nОсновная цель атак.\n"),
            ("NODE",
             "Сетевые узлы.\n\nИсточники трафика.\n\nЭто могут быть:\n• ПК\n• смартфоны\n• маршрутизаторы\n• IoT\n"),
            ("LOG",
             "Лента логов.\n\nПоказывает:\n• пакеты\n• атаки\n• подозрительные события\n\nОснова анализа безопасности.\n"),
            ("INVENTORY",
             "Обнаруженные устройства.\n\nIP адреса и MAC.\n\nИспользуется для:\n• аудита сети\n• поиска угроз\n"),
            ("SCAN", "SCAN\n\nПоиск активных устройств в сети."),
            ("MITM",
             "MITM ATTACK\n\nПерехват трафика между узлами.\n\nПозволяет:\n• читать данные\n• подменять пакеты\n"),
            ("GRAPH", "GRAPH\n\nТопология сети и связи.\n"),
            ("CLEAR", "CLEAR\n\nОчистка логов и статистики.\n"),
            ("PAUSE", "PAUSE\n\nОстановка захвата пакетов.\n"),
            ("STATS", "STATS\n\nКоличество пакетов и угроз.\n"),
            ("FINAL", "ОБЩАЯ КАРТИНА\n\nNetwork Sniffer — это инструмент.\n"
                      "В защите — помощник.\nВ атаке — оружие.\n\n"
                      "Теперь разберём RISK / PURPOSE / DEFENSE.\n")

        ]


        # DATA
        self.devices = []
        self.device_widgets = []
        self.nodes = []
        self.edges = []
        self.node_phase = []
        self.node_amp = []
        self.packets = []

        self.packet_count = 0
        self.suspicious = 0
        self.max_log_lines = 34


    # ================= START ==================
    def start(self):
        self.draw_ui()
        self.spawn_inventory_devices()
        self.spawn_graph_nodes()
        self.generate_packets()
        self.animate_packets()
        self.graph_motion()
        self.update_stats()
        self.init_matrix_background()
        self.animate_matrix()



    # ================= UI ====================
    def draw_ui(self):
        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        self.canvas.create_text(30, 20, anchor="nw",
            text="NETWORK SNIFFER MODULE",
            fill="#48bfff", font=("Consolas", 18, "bold"))

        # LOG PANEL
        self.canvas.create_rectangle(30, 70, 520, h - 80, outline="#333", width=2)
        self.log_text = self.canvas.create_text(
            40, 80, anchor="nw",
            fill="#aee6ff", width=460,
            font=("Consolas", 11), text=""
        )
        self.info_targets["LOG"] = self.log_text

        # INVENTORY
        self.canvas.create_text(560, 70, anchor="nw",
            text="DETECTED DEVICES",
            fill="#48bfff", font=("Consolas", 14, "bold"))

        self.devices_y = 110

        # STATS
        self.stats_text = self.canvas.create_text(
            560, h - 220, anchor="nw",
            fill="white", font=("Consolas", 12)
        )
        self.info_targets["STATS"] = self.stats_text

        # STATUS
        self.status_text = self.canvas.create_text(
            30, h - 40, anchor="nw",
            fill="#48bfff", font=("Consolas", 11, "bold"),
            text="STATUS: IDLE"
        )

        # BUTTONS
        self.buttons = {}

        def add_btn(name, y, cmd):
            btn, _ = self.create_button(w - 170, y, name, cmd)
            self.buttons[name] = btn
            self.info_targets[name] = btn

        add_btn("SCAN", 120, self.rescan_inventory)
        add_btn("MITM", 180, self.toggle_mitm)
        add_btn("GRAPH", 240, self.toggle_graph)
        add_btn("CLEAR", 300, self.clear_logs)
        add_btn("PAUSE", 360, self.toggle_pause)
        add_btn("INFO", 420, self.toggle_info)

        # EXIT
        self.exit_btn, _ = self.create_button(
            w - 170, 20, "EXIT", self.exit,
            outline="#ff4444", text_color="#ff4444"
        )

        # SERVER CENTER
        self.graph_center_x = w // 2 + 160
        self.graph_center_y = h // 2

        self.server = self.canvas.create_oval(
            self.graph_center_x - 30, self.graph_center_y - 30,
            self.graph_center_x + 30, self.graph_center_y + 30,
            outline="#48bfff", width=2
        )
        self.info_targets["SERVER"] = self.server

        self.canvas.create_text(
            self.graph_center_x, self.graph_center_y + 55,
            text="SERVER", fill="#48bfff",
            font=("Consolas", 10, "bold")
        )

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

    # ================= BUTTON =================
    def create_button(self, x, y, text, cmd,
                      outline="#48bfff", text_color="#48bfff"):
        r = self.canvas.create_rectangle(
            x, y, x + 130, y + 40,
            outline=outline, width=2, fill=""
        )

        t = self.canvas.create_text(
            x + 65, y + 20,
            text=text, fill=text_color,
            font=("Consolas", 13, "bold")
        )

        # ✅ фикс замыканий: передаём каждому элементу СВОЙ r
        def on_enter(e, rect=r):
            self.canvas.itemconfig(rect, fill="#102030", outline="#88d9ff")

        def on_leave(e, rect=r):
            self.canvas.itemconfig(rect, fill="", outline=outline)

        def on_click(e):
            cmd()

        for obj in (r, t):
            self.canvas.tag_bind(obj, "<Enter>", on_enter)
            self.canvas.tag_bind(obj, "<Leave>", on_leave)
            self.canvas.tag_bind(obj, "<Button-1>", on_click)

        return r, t

    # ================= INFO TOUR =================
    def toggle_info(self):
        if self.info_visible:
            self.hide_info()
        else:
            self.start_info_tour()

    def start_info_tour(self):
        self.info_visible = True
        self.info_page = 0
        self.show_info_step()

    def show_info_step(self):

        self.clear_info_elements()

        key, text = self.info_pages[self.info_page]
        w = self.canvas.winfo_screenwidth()
        h = self.canvas.winfo_screenheight()

        if key == "FINAL":
            self.show_big_theory_panels()
            return

        # затемнение
        self.info_overlay = self.canvas.create_rectangle(
            0, 0, w, h, fill="black", stipple="gray50"
        )

        target = self.info_targets.get(key)
        if not target:
            self.next_info_step()
            return

        x1, y1, x2, y2 = self.canvas.bbox(target)

        # подсветка объекта
        self.info_focus = self.canvas.create_rectangle(
            x1 - 8, y1 - 8, x2 + 8, y2 + 8,
            outline="#48bfff", width=3
        )

        BOX_W = 360
        BOX_H = 170
        OFFSET = 25

        # размещение окна (чтобы НЕ ЗАЛЕЗАЛО НА КНОПКИ)
        if x2 + BOX_W + OFFSET < w:
            box_x = x2 + OFFSET
        else:
            box_x = x1 - BOX_W - OFFSET

        box_y = y1

        if box_y + BOX_H > h:
            box_y = h - BOX_H - 20

        self.info_box = self.canvas.create_rectangle(
            box_x, box_y,
            box_x + BOX_W,
            box_y + BOX_H,
            fill="#05080c", outline="#48bfff", width=2
        )

        self.info_text = self.canvas.create_text(
            box_x + BOX_W // 2, box_y + 65,
            text=text,
            fill="#aee6ff",
            width=320,
            font=("Consolas", 13)
        )

        self.info_counter = self.canvas.create_text(
            box_x + BOX_W // 2,
            box_y + BOX_H - 15,
            text=f"{self.info_page + 1} / {len(self.info_pages)}  (CLICK)",
            fill="#48bfff",
            font=("Consolas", 9, "bold")
        )

        for obj in (self.info_overlay, self.info_box, self.info_text):
            self.canvas.tag_bind(obj, "<Button-1>", self.next_info_step)

        # поднимаем элементы тура поверх всего интерфейса и матрицы
        for obj in (self.info_overlay,
                    self.info_focus,
                    self.info_box,
                    self.info_text,
                    self.info_counter):
            self.canvas.tag_raise(obj)


    def next_info_step(self, event=None):
        self.info_page += 1
        if self.info_page >= len(self.info_pages):
            self.hide_info()
        else:
            self.show_info_step()

    def clear_info_elements(self):
        for attr in (
                "info_overlay", "info_focus", "info_box", "info_text", "info_counter",
                "info_big_panel1", "info_big_panel2",
                "info_big_text1", "info_big_text2"
        ):
            item = getattr(self, attr, None)
            if item:
                self.canvas.delete(item)
                setattr(self, attr, None)

    def hide_info(self, event=None):
        self.clear_info_elements()
        self.info_visible = False

        # ✅ вернуть пакеты под граф и инфо не перекрывать
        for p in self.packets:
            self.canvas.tag_lower(p["dot"])

    # ================= INVENTORY =================
    def spawn_inventory_devices(self):
        for b, t, _ in self.device_widgets:
            self.canvas.delete(b)
            self.canvas.delete(t)

        self.devices.clear()
        self.device_widgets.clear()

        y = self.devices_y
        for _ in range(random.randint(4, 6)):
            name = random.choice(["Router", "Laptop", "Phone", "Server"])
            ip = f"192.168.0.{random.randint(10,200)}"
            mac = self.fake_mac()

            label = f"{name} | {ip} | {mac}"

            box = self.canvas.create_rectangle(
                560, y, 940, y + 40, outline="#2a6a8a")
            txt = self.canvas.create_text(
                570, y + 20, anchor="w",
                text=label,
                fill="white", font=("Consolas", 11)
            )

            self.device_widgets.append((box, txt, label))
            self.devices.append(label)
            y += 55

        if self.device_widgets:
            self.info_targets["INVENTORY"] = self.device_widgets[0][0]

        self.log("[SYSTEM] Inventory refreshed", "#ffaa00")

    def rescan_inventory(self):
        self.spawn_inventory_devices()


    # ================= GRAPH =================
    def spawn_graph_nodes(self):
        for e in self.edges:
            self.canvas.delete(e)

        self.nodes.clear()
        self.edges.clear()
        self.node_phase.clear()
        self.node_amp.clear()

        radius = 220
        names = ["NODE-A", "NODE-B", "NODE-C", "NODE-D", "NODE-E"]

        for i, name in enumerate(names):
            ang = (2 * math.pi / len(names)) * i
            x = self.graph_center_x + radius * math.cos(ang)
            y = self.graph_center_y + radius * math.sin(ang)

            circ = self.canvas.create_oval(
                x-22, y-22, x+22, y+22, outline="white", width=2)
            lab = self.canvas.create_text(
                x, y+36, text=name,
                fill="#9aa7b1",
                font=("Consolas",10,"bold"))

            self.nodes.append({"name":name,"x":x,"y":y,"circ":circ,"label":lab})
            self.node_phase.append(random.uniform(0,6.28))
            self.node_amp.append(random.randint(1,3))

        for n in self.nodes:
            self.edges.append(self.canvas.create_line(
                n["x"], n["y"],
                self.graph_center_x, self.graph_center_y,
                fill="#2a6a8a"
            ))

        self.info_targets["NODE"] = self.nodes[0]["circ"]
        self.log("[GRAPH] Nodes online", "#9eff9e")


    # ================= MOTION ===================
    def graph_motion(self):
        if not self.running:
            return

        for i,n in enumerate(self.nodes):
            self.node_phase[i]+=0.02
            dx = math.sin(self.node_phase[i])*self.node_amp[i]
            dy = math.cos(self.node_phase[i])*self.node_amp[i]

            x=n["x"]+dx
            y=n["y"]+dy

            self.canvas.coords(n["circ"],x-22,y-22,x+22,y+22)
            self.canvas.coords(n["label"],x,y+36)

        for i,n in enumerate(self.nodes):
            self.canvas.coords(self.edges[i],
                self.canvas.coords(n["circ"])[0]+22,
                self.canvas.coords(n["circ"])[1]+22,
                self.graph_center_x,
                self.graph_center_y
            )

        self.root.after(40,self.graph_motion)


    # ================= PACKETS =================
    def generate_packets(self):
        if not self.running or self.paused or self.info_visible:
            self.root.after(300,self.generate_packets)
            return

        node=random.choice(self.nodes)
        proto=random.choice(["HTTP","HTTPS","FTP","DNS","TELNET"])
        size=random.choice([64,128,256,512,1024])
        bad=random.random() < (0.25 if self.mitm else 0.12)

        msg=f"[PACKET] {proto} {size}B | SRC {node['name']} -> SERVER"
        color="#ff3333" if bad else "#48bfff"

        if bad:
            msg+=" !!! SUSPICIOUS !!!"
            self.suspicious +=1

        self.packet_count+=1
        self.log(msg,color)
        self.spawn_packet(node, color)

        self.root.after(random.randint(200,600),self.generate_packets)

    def spawn_packet(self, node, color):
        if not self.graph:
            return

        x1, y1, x2, y2 = self.canvas.coords(node["circ"])
        sx = (x1 + x2) / 2
        sy = (y1 + y2) / 2

        dot = self.canvas.create_oval(
            sx - 3, sy - 3, sx + 3, sy + 3,
            fill=color, outline=""
        )

        self.packets.append({
            "dot": dot,
            "x": sx, "y": sy,
            "dx": (self.graph_center_x - sx) / 30,
            "dy": (self.graph_center_y - sy) / 30,
            "life": 30
        })

    def animate_packets(self):
        if not self.running or self.info_visible:
            self.root.after(30, self.animate_packets)
            return

        for p in self.packets[:]:
            self.canvas.move(p["dot"], p["dx"], p["dy"])
            p["life"] -= 1

            if p["life"] <= 0:
                self.canvas.delete(p["dot"])
                self.packets.remove(p)

        self.root.after(30, self.animate_packets)

    # ================= STATS ===================
    def update_stats(self):
        self.canvas.itemconfig(self.stats_text,
            text=(
                "SESSION STATS\n------------------\n"
                f"Packets: {self.packet_count}\n"
                f"Threats: {self.suspicious}\n"
                f"Nodes: {len(self.nodes)}\n"
                f"MITM: {'ON' if self.mitm else 'OFF'}\n"
                f"GRAPH: {'ON' if self.graph else 'OFF'}"
            )
        )
        self.root.after(900,self.update_stats)


    # ================= LOG =====================
    def log(self,msg,color="#48bfff"):
        lines=self.canvas.itemcget(self.log_text,"text").split("\n")
        lines.append(msg)
        self.canvas.itemconfig(self.log_text,
            text="\n".join(lines[-self.max_log_lines:]),
            fill=color)


    # ================= BUTTON ACTIONS =========
    def toggle_mitm(self):
        self.mitm=not self.mitm
        self.log(f"[MITM] {'ON' if self.mitm else 'OFF'}","#ffaa00")

    def toggle_pause(self):
        self.paused=not self.paused
        self.log(f"[SYSTEM] {'PAUSED' if self.paused else 'RUNNING'}","#ffaa00")

    def toggle_graph(self):
        self.graph=not self.graph
        self.log(f"[GRAPH] {'ON' if self.graph else 'OFF'}","#ffaa00")

    def clear_logs(self):
        self.packet_count=0
        self.suspicious=0
        self.canvas.itemconfig(self.log_text,text="")
        self.log("[SYSTEM] Logs cleared","#ffaa00")

    def fake_mac(self):
        return ":".join(f"{random.randint(0,255):02X}" for _ in range(6))

    # ================= FINAL THEORY =================
    def show_big_theory_panels(self):
        self.clear_info_elements()
        w, h = self.canvas.winfo_screenwidth(), self.canvas.winfo_screenheight()

        self.info_overlay = self.canvas.create_rectangle(
            0, 0, w, h, fill="black", stipple="gray50"
        )

        # LEFT PANEL — WHAT IS SNIFFER
        self.info_big_panel1 = self.canvas.create_rectangle(
            w//2 - 460, h//2 - 180,
            w//2 - 20,  h//2 + 180,
            fill="#060b12", outline="#48bfff", width=2
        )

        self.info_big_text1 = self.canvas.create_text(
            w//2 - 240, h//2,
            text=
            "ЧТО ТАКОЕ NETWORK SNIFFER\n\n"
            "Сниффер — программа для перехвата\n"
            "и анализа сетевых пакетов.\n\n"
            "Позволяет:\n"
            "• видеть трафик\n"
            "• анализировать протоколы\n"
            "• выявлять атаки\n\n"
            "Но также может использоваться\n"
            "для:\n"
            "• кражи паролей\n"
            "• шпионажа\n"
            "• MITM атак",
            fill="#aee6ff",
            font=("Consolas", 12),
            width=380,
            justify="left"
        )

        # RIGHT PANEL — DEFENSE
        self.info_big_panel2 = self.canvas.create_rectangle(
            w//2 + 20,  h//2 - 180,
            w//2 + 460, h//2 + 180,
            fill="#060b12", outline="#ff4444", width=2
        )

        self.info_big_text2 = self.canvas.create_text(
            w//2 + 240, h//2,
            text=
            "КАК ЗАЩИЩАТЬСЯ\n\n"
            "Защита от перехвата:\n\n"
            "• HTTPS / TLS\n"
            "• VPN\n"
            "• IDS / IPS\n"
            "• сегментация сети\n\n"
            "• обнаружение MITM\n"
            "• контроль DNS\n\n"
            "• анализ сетевых логов\n\n"
            "Основа защиты — наблюдать\n"
            "аномалии.",
            fill="#ffd0d0",
            font=("Consolas", 12),
            width=380,
            justify="left"
        )

        self.info_counter = self.canvas.create_text(
            w//2, h - 40,
            text="CLICK TO EXIT INFO",
            fill="#48bfff",
            font=("Consolas", 11, "bold")
        )

        for obj in (
            self.info_overlay,
            self.info_big_panel1, self.info_big_text1,
            self.info_big_panel2, self.info_big_text2,
            self.info_counter
        ):
            self.canvas.tag_bind(obj, "<Button-1>", self.hide_info)
            self.canvas.tag_raise(obj)

    # ================= EXIT ===================
    def exit(self):
        self.running=False
        self.canvas.delete("all")
        self.exit_callback()
        self.matrix_active = False



