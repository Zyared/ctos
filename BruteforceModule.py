import random
import string
import tkinter as tk
import math

class BruteforceModule:
    def __init__(self, canvas, root, on_exit):
        self.canvas = canvas
        self.root = root
        self.on_exit = on_exit
        self.is_alive = True

        self.target_ssid = "LAB-ROUTER-01"
        self.target_password = "ctos_lab_demo_2025"

        self.networks = [
            {"ssid": "TP-LINK_2A3F",      "signal": -66},
            {"ssid": "SCHOOL-GUEST",      "signal": -78},
            {"ssid": "MIWIFI",            "signal": -72},
            {"ssid": "LAB-ROUTER-01",     "signal": -40, "target": True},
            {"ssid": "ANDROID-HOTSPOT",   "signal": -81},
        ]
        for n in self.networks:
            n.setdefault("target", False)

        self.logs = []
        self.ready = False
        self.idx = 0
        self.attempt = 0
        self.max_attempts = 80

        self.net_nodes = []
        self.net_edges = []
        self.net_phase = []
        self.net_amp = []
        self.net_active = False

        self.attack_active = False
        self.attack_flash = False
        self.attack_target_name = None
        self.attack_success = False

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

        self.w = self.canvas.winfo_screenwidth()
        self.h = self.canvas.winfo_screenheight()

        # header
        self.canvas.create_text(
            self.w // 2, 35,
            text="CtOS  //  BRUTEFORCE (SIMULATION)",
            fill="#9ef", font=("Consolas", 20, "bold")
        )

        # BACK
        self.back = self.canvas.create_rectangle(30, 20, 140, 60, outline="#48bfff", width=2, fill="")
        self.back_t = self.canvas.create_text(
            85, 40, text="BACK", fill="#48bfff", font=("Consolas", 12, "bold")
        )
        for i in (self.back, self.back_t):
            self.canvas.tag_bind(i, "<Button-1>", lambda e: self.exit())
            self.canvas.tag_bind(i, "<Enter>", lambda e: self.canvas.itemconfig(self.back, fill="#0b2b3a"))
            self.canvas.tag_bind(i, "<Leave>", lambda e: self.canvas.itemconfig(self.back, fill=""))

        # NETWORK PANEL
        self.canvas.create_rectangle(40, 90, 380, self.h - 120,
                                     outline="#2a6a8a", width=2, fill="#050b11")
        self.canvas.create_text(60, 100, anchor="nw", text="AVAILABLE NETWORKS:",
                                fill="#6fbad8", font=("Consolas", 12, "bold"))

        self.network_items = []
        self.network_rects = []

        base = 135
        line = 32

        for i, net in enumerate(self.networks):
            y = base + i * line

            rect = self.canvas.create_rectangle(
                50, y - 3, 370, y + 20,
                outline="", fill="#050b11"
            )
            text = self.canvas.create_text(
                60, y, anchor="nw",
                text=f"[..] {net['ssid']}  {net['signal']} dBm",
                fill="#666", font=("Consolas", 11)
            )

            self.canvas.tag_bind(rect, "<Enter>",  lambda e, i=i: self.hover_on(i))
            self.canvas.tag_bind(text, "<Enter>",  lambda e, i=i: self.hover_on(i))
            self.canvas.tag_bind(rect, "<Leave>",  lambda e, i=i: self.hover_off(i))
            self.canvas.tag_bind(text, "<Leave>",  lambda e, i=i: self.hover_off(i))
            self.canvas.tag_bind(rect, "<Button-1>", lambda e, i=i: self.select(i))
            self.canvas.tag_bind(text, "<Button-1>", lambda e, i=i: self.select(i))

            self.network_rects.append(rect)
            self.network_items.append(text)

        # LOG PANEL
        self.canvas.create_rectangle(410, 90, self.w - 40, self.h - 120,
                                     outline="#2a6a8a", width=2, fill="#050b11")
        self.canvas.create_text(430, 100, anchor="nw", text="ATTACK LOG:",
                                fill="#6fbad8", font=("Consolas", 12, "bold"))

        self.logbox = self.canvas.create_text(
            430, 130,
            anchor="nw",
            text="",
            fill="#d9e7ef",
            font=("Consolas", 11),
            width=self.w - 480,
            justify="left"
        )

        # ================= NETWORK MAP PANEL =================
        map_x1 = self.w - 420
        map_y1 = 110
        map_x2 = self.w - 60
        map_y2 = self.h - 180

        self.canvas.create_rectangle(
            map_x1, map_y1, map_x2, map_y2,
            outline="#2a6a8a", width=2, fill="#03070c"
        )

        self.canvas.create_text(
            (map_x1 + map_x2) // 2, map_y1 + 15,
            text="NETWORK MAP",
            fill="#6fbad8",
            font=("Consolas", 11, "bold")
        )

        self.network_center = (
            (map_x1 + map_x2) // 2,
            (map_y1 + map_y2) // 2 + 20
        )

        self.draw_network_map()

        # PROGRESS BAR (CtOS style)
        self.pb_y = self.h - 85

        self.canvas.create_rectangle(
            40, self.pb_y, self.w - 40, self.pb_y + 22,
            outline="#2a6a8a", width=2
        )

        self.pb_fill = self.canvas.create_rectangle(
            42, self.pb_y + 2, 42, self.pb_y + 20,
            fill="#48bfff", width=0
        )

        self.pb_text = self.canvas.create_text(
            self.w // 2, self.pb_y + 11,
            text="PROGRESS: 0%",
            fill="#6fbad8",
            font=("Consolas", 10, "bold")
        )

    def update_progress(self, percent):
        percent = max(0, min(100, percent))
        full_width = (self.w - 84)
        new_width = int(full_width * (percent / 100))

        self.canvas.coords(
            self.pb_fill,
            42,
            self.pb_y + 2,
            42 + new_width,
            self.pb_y + 20
        )

        self.canvas.itemconfig(self.pb_text, text=f"PROGRESS: {percent}%")

    def calculate_log_limit(self):
        panel_top = 130
        panel_bottom = self.h - 260
        panel_height = panel_bottom - panel_top
        line_height = 16
        self.log_max_lines = int(panel_height / line_height)

    # ================== HOVER ==================
    def hover_on(self, idx):
        if not self.ready:
            return
        self.canvas.itemconfig(self.network_rects[idx], fill="#13384a")

    def hover_off(self, idx):
        self.canvas.itemconfig(self.network_rects[idx], fill="#050b11")

    # ================== LOG ==================
    def log(self, text):
        self.logs.append(text)
        if len(self.logs) > self.log_max_lines:
            self.logs = self.logs[-self.log_max_lines:]

        self.canvas.itemconfig(self.logbox, text="\n".join(self.logs))
        self.canvas.update_idletasks()

    def draw_network_map(self):
        cx, cy = self.network_center

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
            x2 = cx + self.net_devices[i]["pos"][0]
            y2 = cy + self.net_devices[i]["pos"][1]

            line = self.canvas.create_line(
                x1, y1, x2, y2,
                fill="#2a6a8a", width=1
            )
            self.net_edges.append(line)

        # узлы
        r = 22
        for dev in self.net_devices:
            x = cx + dev["pos"][0]
            y = cy + dev["pos"][1]

            role = dev.get("role", "node")

            color = "#48bfff"  # все устройства по умолчанию синие

            circ = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                outline=color, width=2
            )

            ico = self.canvas.create_text(
                x, y,
                text=dev["icon"],
                fill=color,
                font=("Consolas", 18)
            )

            txt = self.canvas.create_text(
                x, y + 34,
                text=dev["name"],
                fill="#9ecfe0",
                font=("Consolas", 9, "bold")
            )

            self.net_nodes.append({
                "circ": circ,
                "ico": ico,
                "txt": txt,
                "x": x,
                "y": y
            })

            self.net_phase.append(random.uniform(0, 6.28))
            self.net_amp.append(random.uniform(0.6, 1.6))

        self.net_active = True
        self.animate_network_map()

    def animate_network_map(self):
        if not self.net_active:
            return

        for i, node in enumerate(self.net_nodes):
            self.net_phase[i] += 0.02
            dx = math.sin(self.net_phase[i]) * self.net_amp[i]
            dy = math.cos(self.net_phase[i]) * self.net_amp[i]

            x = node["x"] + dx
            y = node["y"] + dy

            r = 22
            self.canvas.coords(node["circ"], x - r, y - r, x + r, y + r)
            self.canvas.coords(node["ico"], x, y)
            self.canvas.coords(node["txt"], x, y + 32)

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
            fill="#bfeaff"
        )
        self.log(f"Found SSID: {net['ssid']}")
        self.idx += 1
        self.root.after(350, self.scan_step)

    # ================== SELECT ==================
    def select(self, idx):
        if not self.ready:
            self.log("Please wait for scan.")
            return

        for r in self.network_rects:
            self.canvas.itemconfig(r, outline="", width=1)

        self.canvas.itemconfig(self.network_rects[idx], outline="#48bfff", width=2)

        net = self.networks[idx]
        self.log("")
        self.log(f"TARGET SELECTED: {net['ssid']}")

        # случайно выбираем цель атаки
        possible = ["ROUTER", "PHONE", "LAPTOP"]
        self.attack_target_name = random.choice(possible)
        self.log(f"ATTACK VECTOR: {self.attack_target_name}")

        self.start_attack(net)

    # ================== ATTACK ==================
    def start_attack(self, net):
        self.current = net
        self.attempt = 0
        self.log("")
        self.log("Capturing handshake (simulated)...")
        # старт цвета атаки
        self.attack_active = True
        self.attack_success = False
        self.animate_attack_nodes()

        self.root.after(1000, self.attack_step)

    def attack_step(self):
        if self.attempt >= self.max_attempts:
            self.success() if self.current.get("target") else self.fail()
            return

        fake = "".join(random.choice(string.ascii_letters + "0123456789") for _ in range(10))
        self.log(f"[TRY {self.attempt:03d}] {fake}  → denied")

        progress = int((self.attempt / self.max_attempts) * 100)
        self.update_progress(progress)

        self.attempt += 1
        self.root.after(100, self.attack_step)

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
        self.log("Password not found.")
        self.log("Simulation finished.")
        self.log("No real hacking occurred.")
        self.update_progress(0)
        self.attack_active = False
        self.attack_success = False

    def animate_attack_nodes(self):
        if not self.attack_active:
            return

        self.attack_flash = not self.attack_flash

        for node in self.net_nodes:
            name = self.canvas.itemcget(node["txt"], "text").strip()

            # атакующее устройство (YOU)
            if name == "YOU":
                color = "#9ef" if self.attack_flash else "#48bfff"

            # цель атаки
            elif name == self.attack_target_name:
                if self.attack_success:
                    color = "#22ff66"  # зелёный — успешно взломан
                else:
                    color = "#ff3333" if self.attack_flash else "#ffaaaa"

            # остальные
            else:
                color = "#2a6a8a"

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
        # затемнение + панель
        self.canvas.create_rectangle(
            0, 0, self.w, self.h,
            fill="#000000", stipple="gray50", tags="edu"
        )

        x1 = self.w // 2 - 420
        y1 = self.h // 2 - 270
        x2 = self.w // 2 + 420
        y2 = self.h // 2 + 270

        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#48bfff", width=2, fill="#020b13",
            tags="edu"
        )

        self.canvas.create_text(
            (x1 + x2) // 2, y1 + 25,
            text="SECURITY EDUCATION MODULE",
            fill="#48bfff",
            font=("Consolas", 16, "bold"),
            tags="edu"
        )

        # рамка под текст
        tx1 = x1 + 20
        ty1 = y1 + 60
        tx2 = x2 - 20
        ty2 = y2 - 80

        self.canvas.create_rectangle(
            tx1, ty1, tx2, ty2,
            outline="#2a6a8a", width=1, fill="#020509",
            tags="edu"
        )

        # Text + Scrollbar как объекты CANVAS
        self.edu_text = tk.Text(
            self.canvas,
            font=("Consolas", 11),
            bg="#020509",
            fg="#cceeff",
            wrap="word",
            relief="flat",
            insertbackground="#48bfff"
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
            tx1 + 5,
            ty1 + 5,
            anchor="nw",
            window=self.edu_text,
            width=(tx2 - tx1) - 30,
            height=(ty2 - ty1) - 10,
            tags="edu"
        )

        self.canvas.create_window(
            tx2 - 18,
            ty1 + 5,
            anchor="nw",
            window=self.edu_scroll,
            height=(ty2 - ty1) - 10,
            tags="edu"
        )

        # кнопка CLOSE
        bx1 = (x1 + x2) // 2 - 100
        bx2 = (x1 + x2) // 2 + 100
        by1 = y2 - 45
        by2 = y2 - 15

        btn = self.canvas.create_rectangle(
            bx1, by1, bx2, by2,
            outline="#48bfff", width=2,
            tags="edu"
        )
        txt = self.canvas.create_text(
            (bx1 + bx2) // 2, (by1 + by2) // 2,
            text="CLOSE",
            fill="#48bfff",
            font=("Consolas", 12, "bold"),
            tags="edu"
        )

        for i in (btn, txt):
            self.canvas.tag_bind(i, "<Button-1>", lambda e: self.close_education())
            self.canvas.tag_bind(i, "<Enter>", lambda e: self.canvas.itemconfig(btn, fill="#0b2b3a"))
            self.canvas.tag_bind(i, "<Leave>", lambda e: self.canvas.itemconfig(btn, fill=""))

        self.canvas.tag_raise("edu")
        self.canvas.tag_raise("mivlgu")

    def close_education(self):
        # уничтожаем виджеты и всё, что помечено тегом edu
        try:
            self.edu_text.destroy()
            self.edu_scroll.destroy()
        except Exception:
            pass
        self.canvas.delete("edu")
        self.canvas.tag_raise("mivlgu")

    def get_education_text(self):
        return (
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

    # ================== EXIT ==================
    def exit(self):
        self.is_alive = False  # ⛔ модуль мёртв
        self.attack_active = False
        self.net_active = False

        try:
            self.edu_text.destroy()
            self.edu_scroll.destroy()
        except:
            pass

        self.canvas.delete("all")
        self.on_exit()

    # ================== MIVLGU GLITCH ==================
    def restore_mivlgu(self):
        self.mivlgu = self.canvas.create_text(
            self.w - 20, self.h - 20,
            anchor="se",
            text="МИВЛГУ",
            fill="white",
            font=("Arial Black", 22),
            tags="mivlgu"
        )
        self.animate_mivlgu()

    def animate_mivlgu(self):
        dx = random.randint(-10, 10)
        dy = random.randint(-6, 6)

        glitch = self.canvas.create_text(
            self.w - 20 + dx,
            self.h - 20 + dy,
            anchor="se",
            text="МИВЛГУ",
            fill=random.choice(["#ffffff", "#cccccc", "#bbbbbb"]),
            font=("Arial Black", 22),
            tags="mivlgu"
        )

        self.canvas.tag_raise("mivlgu")
        self.canvas.after(70, lambda: self.canvas.delete(glitch))
        self.root.after(random.randint(2500, 5000), self.animate_mivlgu)

    # ================== SIGNAL SIM ==================
    def simulate_signal(self):
        for i, net in enumerate(self.networks):
            delta = random.randint(-2, 2)
            net["signal"] += delta
            net["signal"] = max(-90, min(-30, net["signal"]))

            status = "[OK]" if i < self.idx else "[..]"
            color = "#bfeaff" if i < self.idx else "#666"

            self.canvas.itemconfig(
                self.network_items[i],
                text=f"{status} {net['ssid']}   {net['signal']} dBm",
                fill=color
            )

        self.root.after(1500, self.simulate_signal)
